# Installation — PC Windows fixe (24/7)

Commandes à lancer dans **PowerShell en administrateur**, sauf mention contraire.

## 1. Python et Git
```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git
```
Fermer puis rouvrir PowerShell, vérifier : `python --version` et `git --version`.

## 2. Chemins longs (SharePoint produit des chemins > 260 caractères)
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
git config --system core.longpaths true
```
Redémarrer le PC.

## 3. Arborescence C:\BK
```powershell
mkdir C:\BK\01_MIROIR, C:\BK\02_ENTRANT, C:\BK\03_TRAVAIL\registres, C:\BK\03_TRAVAIL\_texte, C:\BK\04_PUBLIER
```
- `01_MIROIR` : synchroniser la bibliothèque SharePoint via OneDrive (« Ajouter un raccourci » / « Synchroniser »), puis pointer ou copier ici. **Lecture seule** : clic droit > Propriétés > « Lecture seule » sur le dossier.

## 4. Cloner ce dépôt (code uniquement)
```powershell
git clone -b claude/code-usage-question-2rjw1o https://github.com/yahyaelhirchiy-maker/Bom C:\BK\00_SYSTEME
cd C:\BK\00_SYSTEME
python -m pip install -r requirements.txt
```
(Après fusion dans la branche principale, retirer `-b ...`.)

Tester le pilotage MS Project (pywin32) :
```powershell
python -c "import win32com.client as w; print(w.Dispatch('MSProject.Application').Version)"
```

## 5. Dépôt local des registres (jamais poussé sur GitHub)
```powershell
cd C:\BK\03_TRAVAIL
git init
copy C:\BK\00_SYSTEME\modeles\ETAT.md .
copy C:\BK\00_SYSTEME\modeles\registres\*.csv registres\
"@C:/BK/00_SYSTEME/CLAUDE.md" | Out-File CLAUDE.md -Encoding utf8   # importe les règles, une seule source
"_texte/`nlogs/" | Out-File .gitignore -Encoding utf8
git add . ; git commit -m "Initialisation registres"
```
Ne **jamais** faire `git remote add` dans ce dossier.

## 6. Claude Code
PowerShell **utilisateur normal** :
```powershell
irm https://claude.ai/install.ps1 | iex
claude          # première connexion au compte
```
Puis installer l'extension **Claude in Chrome** dans Chrome et se connecter à Outlook Web dans ce même Chrome.

## 7. Démarrage automatique avec Remote Control
Le PC doit rester allumé et la session ouverte (Chrome et Outlook ont besoin d'une session interactive) :
```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```
Créer la tâche au démarrage de session :
```powershell
schtasks /Create /TN "BOSKO\RemoteControl" /SC ONLOGON /RL LIMITED `
  /TR "powershell -NoProfile -WindowStyle Minimized -Command `"cd C:\BK\03_TRAVAIL; claude remote-control`""
```
Ensuite, depuis le téléphone (app Claude) : se connecter à la session du PC.

## 8. Tâches planifiées (jours ouvrés lun.–ven.)
```powershell
$s = "powershell -NoProfile -ExecutionPolicy Bypass -File C:\BK\00_SYSTEME\scripts\lancer_tache.ps1"
schtasks /Create /TN "BOSKO\Briefing"  /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:30 /TR "$s -Tache briefing"
schtasks /Create /TN "BOSKO\Recap"     /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 17:00 /TR "$s -Tache recap"
schtasks /Create /TN "BOSKO\Hebdo"     /SC WEEKLY /D FRI                 /ST 12:00 /TR "$s -Tache hebdo"
```
Résultats dans `C:\BK\04_PUBLIER\<tâche>\`, journaux dans `C:\BK\03_TRAVAIL\logs\`.
Tester une fois à la main : `schtasks /Run /TN "BOSKO\Briefing"`.

> Les tâches planifiées travaillent sur les **registres et ETAT.md** uniquement (outils limités, pas de navigateur).
> La lecture des mails Outlook se fait dans la session interactive (Remote Control), qui alimente les registres.
