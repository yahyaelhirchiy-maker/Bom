# Installation — PC Windows fixe (24/7)

Commandes à lancer dans **PowerShell en administrateur**, sauf mention contraire.

## 1. Python et Git
```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git
```
Fermer puis rouvrir PowerShell, vérifier : `python --version` et `git --version`.
Sans droits admin : `winget install -e --id Python.Python.3.12 --scope user` suffit.
Si `python --version` affiche « Python was not found » : c'est le raccourci du Microsoft Store ; rouvrir PowerShell après l'installation (Python 3.12 passe alors devant).

## 2. Chemins longs (SharePoint produit des chemins > 260 caractères)
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
git config --system core.longpaths true
```
Redémarrer le PC.
Vérifier d'abord : si `(Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem").LongPathsEnabled` vaut déjà 1, ne rien faire côté Windows ; pour Git, `git config --global core.longpaths true` (sans admin) suffit.

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
Erreur `Invalid class string` = MS Project (bureau) n'est pas installé sur ce PC : `planning.py extraire` ne peut pas tourner sans lui.

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

L'application Claude (bureau) ne fournit pas la commande `claude` : l'installation ci-dessus reste nécessaire pour les tâches planifiées.

**Outlook bureau (classique, pas le « nouvel Outlook »)** doit être installé, connecté à la boîte du projet et **ouvert en permanence** : les scripts le lisent en texte et y créent les brouillons (moins de tokens et plus fiable que le navigateur, et les pièces jointes fonctionnent).
Test : `python D:\BK\00_SYSTEME\scripts\outlook.py lister --jours 1`

En secours seulement : extension **Claude in Chrome** + Outlook Web.

Si Outlook classique reste bloqué sur « Adding… » (compte d'entreprise refusé sur un PC personnel) : se connecter à Outlook Web **dans le navigateur intégré de l'appli Claude** (Ctrl+Shift+B), connexion gardée. Les mails sont alors traités à la demande (skill `traiter-mail` §0) ; ne pas créer la tâche planifiée `BOSKO\Mails`, qui a besoin d'Outlook classique.

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

## 8. Deux passages par jour (lun.–ven.)
Depuis le 14/11/2026, **2 sessions Claude par jour ouvré** (avant : 7), en tâches planifiées **de l'appli Claude** (elles ont besoin du navigateur intégré pour Outlook Web) :
- **BOSKO – Matin** (`bosko-mails`, 7h30) : notes dictées, mails, `importer_pilotage.py`, `digest.py`, briefing (avec « En bref »), publication de la page, notification.
- **BOSKO – Après-midi** (`bosko-apres-midi`, 14h) : notes, mails, récap court, publication, notification ; le vendredi, + rapport hebdo.
Consignes : `modeles\consignes\matin.md`, `apres-midi.md`, `mails_web.md`. Un passage ne lit que `CLAUDE.md`, `ETAT.md`, `_cache\digest.md`, les notes en attente et les nouveaux mails.
Livrables : `D:\BK_PUBLIER\<briefing|mails|hebdo|cr|odj>\`. Page : https://claude.ai/artifact/592VnZ8SfbeMx6JqwDGbBM.

À régler dans l'appli, pour **chaque** tâche : modèle **Sonnet**, puis **Run now** une fois pour valider les autorisations.
`bosko-publier` est désactivée. Les tâches Windows `BOSKO\Briefing`, `Recap`, `Hebdo` sont supprimées. Reste `BOSKO\Sauvegarde` (sans Claude).
`scripts\lancer_tache.ps1` n'est plus utilisé (gardé pour un éventuel retour en tâche Windows ou le secours OmniRoute).

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
