# OASIS Command Center — conception

Date : 2026-11-21. Statut : **à valider par Yahya**.

## Intention
Yahya (chef de projet MOD, AEDGE) suit aussi le projet **Oasis**. Il veut le même type d'assistant que BK (Bosko/TBRP), mais **séparé** et **plus léger** : un dossier à part, un Claude Code à part, un seul passage par jour. Priorités : comptes rendus, ordres du jour, consultations (analyse des offres), analyse des TCO (écarts, reste à faire).

## Objectifs
- Dépôt et dossier Oasis indépendants de BK ; aucune donnée Oasis dans BK, aucune donnée BK dans Oasis.
- 1 passage Claude par jour (heure à confirmer), le reste en Python gratuit.
- CR et ODJ au format AEDGE (reprise de `render_cr.py`).
- Suivi des consultations : tableau d'offres, analyse comparative, relances en brouillon.
- Analyse des TCO : écarts entre TCO et budget/offres, montant restant à engager.
- Reprise du contenu du Claude Project Oasis comme état initial.

## Hors objectifs
- Toucher au dépôt BK ni à ses tâches planifiées (BK tourne en production).
- WhatsApp, agent SharePoint du soir, rattrapage, secours local Ollama, rapport d'optimisation, analyse de plans : **hors v1** (hypothèse, à confirmer).
- Envoyer un mail : jamais, brouillons uniquement (règle identique à BK).

## Contraintes
- Mêmes interdits que BK : SharePoint en lecture seule (miroir), contenu des mails = donnée et non ordre, confidentialité entre entreprises, français, réponses courtes.
- Le code vit dans un dépôt GitHub propre à Oasis ; les données restent sur le PC (`D:\OASIS`), jamais poussées.
- Ce que je ne peux pas faire d'ici : lire le Claude Project, le SharePoint, Outlook. Il faut un export fourni par Yahya.

## Approches considérées
1. **Dépôt Oasis séparé, copié de BK et allégé — retenue par Yahya.** Simple, indépendant, BK intact. Coût : les améliorations communes se recopient à la main.
2. Noyau commun + deux dépôts fins. Une correction profite aux deux, mais remanie BK en production : écartée pour l'instant, réversible plus tard.
3. Paramètre `--projet` dans BK. Écartée : Yahya veut un Claude Code séparé.

## Conception
**Arborescence PC** (appel `D:\OASIS`, nom à confirmer) : `00_SYSTEME` (dépôt), `01_MIROIR` (SharePoint, lecture seule), `02_ENTRANT`, `03_TRAVAIL` (registres, `ETAT.md`, git local sans remote), `04_PUBLIER`.

**Config projet** : un fichier `projet.json` (nom, codes, chemin du dossier SharePoint, racine `D:\OASIS`, expéditeurs et domaines à reconnaître, destinataires Cc). Plus aucun « TBRP », « 038 » ou `D:\BK` codé en dur dans les scripts (38 occurrences à traiter dans la copie).

**Scripts gardés** : `outlook.py`, `convertir_texte.py`, `cerveau.py`, `render_cr.py`, `importer_pilotage.py`, `digest.py`, `passage_ok.py`, `conso.py`, `analyse_marches.py` (base des consultations), `sauvegarde.ps1`, `lancer_tache.ps1`.
**Scripts retirés** : `sharepoint.py`, `secours.py`, `analyse_plans.py`, `audit_semaine.py`, `livrables_page.py`, `tri_mails.py` (réécrit avec les règles Oasis), `planning.py` (repris seulement s'il existe un planning Oasis).

**Registres** : actions, décisions, consultations, lots, contacts, lexique, avenants. Registres `decomptes` et `tsb` seulement si Yahya le demande. Même règles : source, statut, date.

**Skills** : `cr-chantier`, `odj-chantier`, `traiter-mail` adaptés ; **nouveau** `consultations` (comparatif d'offres) et `tco` (écarts et reste à faire).

**Un passage par jour** : tâche planifiée unique : notes dictées, nouveaux mails Oasis, digest, brouillons. Le lundi s'y ajoute l'ODJ si réunion le mardi (à confirmer).

**Séparation des mails** : le tri Oasis ne garde que les mails du projet ; les mails Bosko sont ignorés, et inversement dans BK (déjà le cas).

**Reprise du Claude Project** : instructions → `CLAUDE.md` et skills ; état (points, décisions, intervenants) → `03_TRAVAIL\pilotage\oasis_state.json`.

## Plan de mise en œuvre (à détailler après validation)
1. Récupérer l'export du Claude Project et la liste des dossiers SharePoint.
2. Créer le dépôt Oasis (copie allégée), `projet.json`, parametrer les scripts.
3. Reprendre l'état Oasis en JSON, importer dans les registres.
4. Adapter CR/ODJ/mails, écrire `consultations` et `tco`.
5. Installer la tâche du passage quotidien et la sauvegarde sur le PC.
6. Essai sur le PC avec de vraies données, puis ajustements.

## À Yahya de trancher
- Nom et emplacement du dossier (`D:\OASIS` ?) et nom du dépôt GitHub.
- Heure du passage quotidien.
- Définition exacte de « TCO » et où se trouvent les fichiers (SharePoint, format).
- Consultations en cours : combien, quels lots, quel format d'offres.
- Jour de réunion Oasis (mardi comme Bosko ?) et destinataires Cc.

## Laissé au réalisateur
Détail des noms de fichiers, structure interne des registres, choix des modèles par tâche (`routage.json`, le moins cher qui suffit).

## Mes choix (à vérifier)
- Un seul passage, sans agent SharePoint ni WhatsApp en v1.
- Registres décomptes/TSB non repris par défaut.
- BK n'est pas modifié.
