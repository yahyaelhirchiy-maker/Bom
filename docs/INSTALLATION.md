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
"_texte/`nlogs/`n_cache/" | Out-File .gitignore -Encoding utf8
git add . ; git commit -m "Initialisation registres"
```
Ne **jamais** faire `git remote add` dans ce dossier.

## 6. Claude Code
PowerShell **utilisateur normal** :
```powershell
irm https://claude.ai/install.ps1 | iex
claude          # première connexion au compte
```
Permissions (ce qui est autorisé sans demander, et ce qui est interdit) :
```powershell
mkdir C:\BK\00_SYSTEME\.claude -Force
copy C:\BK\00_SYSTEME\modeles\claude-settings.json C:\BK\00_SYSTEME\.claude\settings.json
```

**Outlook bureau** doit être installé, connecté à la boîte du projet et **ouvert en permanence** : les scripts le lisent en texte et y créent les brouillons (moins de tokens et plus fiable que le navigateur, et les pièces jointes fonctionnent).
Test : `python C:\BK\00_SYSTEME\scripts\outlook.py lister --jours 1`

En secours seulement : extension **Claude in Chrome** + Outlook Web.

Planning : renseigner le chemin du .mpp puis extraire une première fois :
`python C:\BK\00_SYSTEME\scripts\planning.py extraire "C:\BK\01_MIROIR\<chemin>\planning.mpp"`

## 7. Démarrage automatique avec Remote Control
Le PC doit rester allumé et la session ouverte (Outlook a besoin d'une session interactive) :
```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```
Créer la tâche au démarrage de session :
```powershell
schtasks /Create /TN "BOSKO\RemoteControl" /SC ONLOGON /RL LIMITED `
  /TR "powershell -NoProfile -WindowStyle Minimized -Command `"cd C:\BK\00_SYSTEME; claude remote-control`""
```
Ensuite, depuis le téléphone (app Claude) : se connecter à la session du PC.

## 8. Tâches planifiées (jours ouvrés lun.–ven.)
```powershell
$s = "powershell -NoProfile -ExecutionPolicy Bypass -File C:\BK\00_SYSTEME\scripts\lancer_tache.ps1"
schtasks /Create /TN "BOSKO\Briefing"  /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:30 /TR "$s -Tache briefing"
schtasks /Create /TN "BOSKO\Recap"     /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 17:00 /TR "$s -Tache recap"
schtasks /Create /TN "BOSKO\Hebdo"     /SC WEEKLY /D FRI                 /ST 12:00 /TR "$s -Tache hebdo"
schtasks /Create /TN "BOSKO\Mails"     /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:00 /RI 30 /DU 12:00 /TR "$s -Tache mails"
```
Résultats dans `C:\BK\04_PUBLIER\<tâche>\`, journaux dans `C:\BK\03_TRAVAIL\logs\`.
Tester une fois à la main : `schtasks /Run /TN "BOSKO\Briefing"`.

> **BOSKO\Mails** relève les mails toutes les 30 min (7h–19h) et prépare les brouillons tout seul. Tu n'as plus qu'à relire et envoyer depuis Outlook.
> Les tâches ne peuvent rien envoyer : `outlook.py` ne contient aucun appel d'envoi.
