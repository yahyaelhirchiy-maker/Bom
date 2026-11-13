# Lance une tâche planifiée Claude Code (briefing, recap, hebdo, mails).
# Usage : powershell -ExecutionPolicy Bypass -File lancer_tache.ps1 -Tache mails
#
# - Modèle choisi par tâche dans modeles\routage.json (le moins cher qui suffit).
# - Mails : tri gratuit en Python d'abord ; Claude n'est lancé que s'il y a du nouveau.
# - Chaque passage est journalisé (tokens, coût équivalent) dans 03_TRAVAIL\logs\consommation.csv.
# - Limite atteinte : bascule sur OmniRoute si la tâche l'autorise, sinon mise en attente.
# - Aucun envoi de mail possible (outils limités, outlook.py n'a pas d'envoi).
param([Parameter(Mandatory)][ValidateSet("briefing","recap","hebdo","mails")][string]$Tache)

# PowerShell 5.1 : UTF-8 sans BOM partout (sortie de claude/python, entrée de claude, journaux >>).
$Utf8 = New-Object Text.UTF8Encoding $false
[Console]::OutputEncoding = $Utf8; [Console]::InputEncoding = $Utf8; $OutputEncoding = $Utf8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$Systeme = "D:\BK\00_SYSTEME"; $Travail = "D:\BK\03_TRAVAIL"; $Scripts = "$Systeme\scripts"
$Sortie  = "D:\BK\04_PUBLIER\$Tache"
$Date    = Get-Date -Format "yyyy-MM-dd_HHmm"
$Log     = "$Travail\logs\${Tache}_$Date.log"
New-Item -ItemType Directory -Force -Path $Sortie, "$Travail\logs" | Out-Null
$Routage = Get-Content "$Systeme\modeles\routage.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$Outils  = "Read,Grep,Glob,Write,Edit,Skill,Bash(python D:/BK/00_SYSTEME/scripts/*)," +
           "Bash(git -C D:/BK/03_TRAVAIL add:*),Bash(git -C D:/BK/03_TRAVAIL commit:*),Bash(git -C D:/BK/03_TRAVAIL log:*)"
Set-Location $Systeme   # CLAUDE.md, skills et permissions sont ici

function Journal($cle, $modele, $voie, $j) {
  $f = "$Travail\logs\consommation.csv"
  if (-not (Test-Path $f)) { "date;tache;modele;voie;entree;cache_lu;cache_ecrit;sortie;cout_usd" | Out-File $f -Encoding utf8 }
  $u = $j.usage
  ("{0};{1};{2};{3};{4};{5};{6};{7};{8}" -f (Get-Date -Format "yyyy-MM-dd HH:mm"), $cle, $modele, $voie,
    $u.input_tokens, $u.cache_read_input_tokens, $u.cache_creation_input_tokens, $u.output_tokens,
    ([string]$j.total_cost_usd).Replace(".", ",")) | Out-File $f -Append -Encoding utf8
}

function Appel($consigne, $modele) {
  # Consigne par l'entrée standard : en argument, PowerShell 5.1 casse les guillemets des objets de mail.
  $brut = $consigne | claude -p --model $modele --output-format json --add-dir "D:\BK" --allowedTools $Outils 2>> $Log
  try { return ($brut -join "`n") | ConvertFrom-Json } catch { ($brut -join "`n") | Out-File $Log -Append; return $null }
}

function Lancer($cle, $consigne) {
  $r = $Routage.$cle
  $j = Appel $consigne $r.modele
  if ($j -and -not $j.is_error) { Journal $cle $r.modele "claude" $j; return $j.result }

  $texte = if ($j) { [string]$j.result } else { Get-Content $Log -Raw }
  $limite = $texte -match "limit|quota|usage"
  if ($limite -and $r.secours -and $env:OMNIROUTE_URL) {
    $env:ANTHROPIC_BASE_URL = $env:OMNIROUTE_URL; $env:ANTHROPIC_AUTH_TOKEN = $env:OMNIROUTE_KEY
    $j = Appel $consigne $env:OMNIROUTE_MODELE
    Remove-Item Env:ANTHROPIC_BASE_URL, Env:ANTHROPIC_AUTH_TOKEN -ErrorAction SilentlyContinue
    if ($j -and -not $j.is_error) { Journal $cle $env:OMNIROUTE_MODELE "secours" $j; return "[SECOURS - modèle gratuit, à relire]`n" + $j.result }
  }
  $raison = if ($limite) { "limite atteinte, reprise au prochain passage" } else { "erreur, voir $Log" }
  "$Date ; $cle ; $raison" | Out-File "D:\BK\04_PUBLIER\en_attente.txt" -Append -Encoding utf8
  return $null
}

if ($Tache -eq "mails") {
  python "$Scripts\tri_mails.py" trier >> $Log
  foreach ($niv in "delicat", "simple") {
    $liste = "$Travail\_cache\a_traiter_$niv.txt"
    if (-not (Test-Path $liste) -or (Get-Item $liste).Length -eq 0) { continue }   # rien = 0 token
    $consigne = (Get-Content "$Systeme\modeles\consignes\mails.md" -Raw -Encoding UTF8) +
                "`n`nNiveau : $niv`nMails à traiter :`n" + (Get-Content $liste -Raw -Encoding UTF8)
    $res = Lancer "mails_$niv" $consigne
    if ($res) { $res | Out-File "$Sortie\${Date}_$niv.md" -Encoding utf8; python "$Scripts\tri_mails.py" valider $niv >> $Log }
  }
} else {
  $res = Lancer $Tache (Get-Content "$Systeme\modeles\consignes\$Tache.md" -Raw -Encoding UTF8)
  if ($res) { $res | Out-File "$Sortie\$Date.md" -Encoding utf8 }
}
