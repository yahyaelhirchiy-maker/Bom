# Sauvegarde quotidienne de D:\BK\03_TRAVAIL (registres, pilotage, ETAT.md, historique git) vers le disque C:.
# Usage : powershell -ExecutionPolicy Bypass -File sauvegarde.ps1
# _texte (reconstructible depuis 01_MIROIR) et _cache ne sont pas copiés.
$Source = "D:\BK\03_TRAVAIL"; $Cible = "C:\BOSKO_SAUVEGARDE\03_TRAVAIL"
$Log = "D:\BK\03_TRAVAIL\logs\sauvegarde.log"
New-Item -ItemType Directory -Force -Path $Cible, (Split-Path $Log) | Out-Null
robocopy $Source $Cible /MIR /XD "$Source\_texte" "$Source\_cache" /R:1 /W:1 /NFL /NDL /NP /NJH | Out-Null
$code = $LASTEXITCODE   # robocopy : 0 à 7 = réussite, 8 et plus = erreur
$etat = if ($code -lt 8) { "OK" } else { "ERREUR (code $code)" }
"$(Get-Date -Format 'yyyy-MM-dd HH:mm') ; $etat" | Out-File $Log -Append -Encoding utf8
if ($code -ge 8) { "$(Get-Date -Format 'yyyy-MM-dd_HHmm') ; sauvegarde ; $etat" | Out-File "D:\BK\04_PUBLIER\en_attente.txt" -Append -Encoding utf8 }
