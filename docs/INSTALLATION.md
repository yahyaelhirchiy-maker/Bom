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

## 3. Arborescence D:\BK
```powershell
mkdir D:\BK\01_MIROIR, D:\BK\02_ENTRANT, D:\BK\03_TRAVAIL\registres, D:\BK\03_TRAVAIL\_texte, D:\BK\04_PUBLIER
```
- `01_MIROIR` : synchroniser la bibliothèque SharePoint via OneDrive (« Ajouter un raccourci » / « Synchroniser »), puis pointer ou copier ici. **Lecture seule** : clic droit > Propriétés > « Lecture seule » sur le dossier.

## 4. Cloner ce dépôt (code uniquement)
```powershell
git clone -b claude/code-usage-question-2rjw1o https://github.com/yahyaelhirchiy-maker/Bom D:\BK\00_SYSTEME
cd D:\BK\00_SYSTEME
python -m pip install -r requirements.txt
```
(Après fusion dans la branche principale, retirer `-b ...`.)

Tester le pilotage MS Project (pywin32) :
```powershell
python -c "import win32com.client as w; print(w.Dispatch('MSProject.Application').Version)"
```

## 5. Dépôt local des registres (jamais poussé sur GitHub)
```powershell
cd D:\BK\03_TRAVAIL
git init
copy D:\BK\00_SYSTEME\modeles\ETAT.md .
copy D:\BK\00_SYSTEME\modeles\registres\*.csv registres\
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
mkdir D:\BK\00_SYSTEME\.claude -Force
copy D:\BK\00_SYSTEME\modeles\claude-settings.json D:\BK\00_SYSTEME\.claude\settings.json
```

**Outlook bureau** doit être installé, connecté à la boîte du projet et **ouvert en permanence** : les scripts le lisent en texte et y créent les brouillons (moins de tokens et plus fiable que le navigateur, et les pièces jointes fonctionnent).
Test : `python D:\BK\00_SYSTEME\scripts\outlook.py lister --jours 1`

En secours seulement : extension **Claude in Chrome** + Outlook Web.

Planning : renseigner le chemin du .mpp puis extraire une première fois :
`python D:\BK\00_SYSTEME\scripts\planning.py extraire "D:\BK\01_MIROIR\<chemin>\planning.mpp"`

## 7. Démarrage automatique avec Remote Control
Le PC doit rester allumé et la session ouverte (Outlook a besoin d'une session interactive) :
```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```
Créer la tâche au démarrage de session :
```powershell
schtasks /Create /TN "BOSKO\RemoteControl" /SC ONLOGON /RL LIMITED `
  /TR "powershell -NoProfile -WindowStyle Minimized -Command `"cd D:\BK\00_SYSTEME; claude remote-control`""
```
Ensuite, depuis le téléphone (app Claude) : se connecter à la session du PC.

## 8. Tâches planifiées (jours ouvrés lun.–ven.)
```powershell
$s = "powershell -NoProfile -ExecutionPolicy Bypass -File D:\BK\00_SYSTEME\scripts\lancer_tache.ps1"
schtasks /Create /TN "BOSKO\Briefing"  /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:30 /TR "$s -Tache briefing"
schtasks /Create /TN "BOSKO\Recap"     /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 17:00 /TR "$s -Tache recap"
schtasks /Create /TN "BOSKO\Hebdo"     /SC WEEKLY /D FRI                 /ST 12:00 /TR "$s -Tache hebdo"
schtasks /Create /TN "BOSKO\Mails"     /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 07:00 /RI 30 /DU 12:00 /TR "$s -Tache mails"
```
Résultats dans `D:\BK\04_PUBLIER\<tâche>\`, journaux dans `D:\BK\03_TRAVAIL\logs\`.
Tester une fois à la main : `schtasks /Run /TN "BOSKO\Briefing"`.

> **BOSKO\Mails** trie les mails toutes les 30 min (7h–19h) en Python, **sans IA** ; Claude n'est réveillé que s'il y a un vrai mail à traiter. Au premier passage, il reprend les 3 derniers jours. Tu n'as plus qu'à relire et envoyer depuis Outlook.
> Les tâches ne peuvent rien envoyer : `outlook.py` ne contient aucun appel d'envoi.

## 9. Secours OmniRoute (quand la limite Claude est atteinte)
Fonctionnement : chaque tâche a un modèle Claude (`modeles\routage.json`). Si la limite est atteinte :
- tâche avec `"secours": true` (récap, briefing, mails simples) → relancée via **OmniRoute** sur un modèle gratuit, réponse marquée `[SECOURS]` ;
- tâche avec `"secours": false` (mails délicats, rapport hebdo) → **mise en attente** dans `04_PUBLIER\en_attente.txt`, reprise au passage suivant (la limite Claude se réinitialise par fenêtre de quelques heures).

⚠ **Confidentialité.** Les fournisseurs gratuits peuvent conserver ou réutiliser ce qu'on leur envoie, et les tâches contiennent des données du projet.
Configurer dans OmniRoute, dans l'ordre : 1) un **modèle local** (Ollama, sur ce PC : gratuit et rien ne sort), 2) seulement ensuite un fournisseur gratuit en ligne, en connaissance de cause.
Ne **pas** brancher l'abonnement Claude dans OmniRoute : Claude Code reste connecté directement ; OmniRoute ne sert que de secours.

Installation (à faire ensemble, d'après le README officiel du projet OmniRoute sur GitHub) :
1. Installer OmniRoute et, si possible, Ollama + un modèle adapté à la carte graphique du PC.
2. Dans OmniRoute, créer une route `bosko-secours` (local d'abord), puis noter son adresse et sa clé.
3. Enregistrer les variables (PowerShell utilisateur) :
```powershell
setx OMNIROUTE_URL    "http://localhost:<port>"
setx OMNIROUTE_KEY    "<clé OmniRoute>"
setx OMNIROUTE_MODELE "bosko-secours"
```
Sans ces variables, il n'y a pas de bascule : les tâches attendent simplement le retour de Claude.

## 10. Suivre la consommation
- Tâches automatiques : `python D:\BK\00_SYSTEME\scripts\conso.py --jours 7` (aussi en annexe du rapport du vendredi).
- Session interactive (tes vocaux) : commande `/usage` dans Claude Code.
- Si une tâche coûte trop : baisser son modèle dans `routage.json` ou espacer la relève des mails (`/RI 30` → `/RI 60`).
