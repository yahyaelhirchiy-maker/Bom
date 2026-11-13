# Lance une tâche planifiée Claude Code (briefing, recap, hebdo).
# Usage : powershell -ExecutionPolicy Bypass -File lancer_tache.ps1 -Tache briefing
# La consigne est lue dans modeles\consignes\<Tache>.md ; le résultat va dans 04_PUBLIER.
param([Parameter(Mandatory)][ValidateSet("briefing","recap","hebdo")][string]$Tache)

$Systeme = "C:\BK\00_SYSTEME"
$Travail = "C:\BK\03_TRAVAIL"
$Sortie  = "C:\BK\04_PUBLIER\$Tache"
New-Item -ItemType Directory -Force -Path $Sortie, "$Travail\logs" | Out-Null

$Date     = Get-Date -Format "yyyy-MM-dd_HHmm"
$Consigne = Get-Content "$Systeme\modeles\consignes\$Tache.md" -Raw -Encoding UTF8

Set-Location $Travail
# Outils limités : lecture + écriture locale. Aucun envoi de mail possible.
claude -p $Consigne --add-dir $Systeme `
  --allowedTools "Read,Grep,Glob,Write,Edit" `
  > "$Sortie\$Date.md" 2> "$Travail\logs\${Tache}_$Date.log"
