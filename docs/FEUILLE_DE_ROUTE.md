# Feuille de route

Règle : on ne construit l'étape suivante que lorsque la précédente a tourné sur le PC avec de vraies données.
Principe commun : **Python détecte gratuitement, Claude n'est réveillé que pour rédiger ou analyser.**

## 0. Socle (écrit, à tester sur le PC)
Installation, lecture Outlook, planning MS Project, brouillons, tri des mails, modèle par tâche, consommation.

## 1. Robustesse (avant tout le reste)
- **Sauvegarde quotidienne** de `C:\BK\03_TRAVAIL` vers un second disque (robocopy). Aujourd'hui les registres n'existent que sur un seul PC.
- **Surveillance** : Outlook fermé, tâche en échec, PC redémarré par Windows Update → relance automatique, et une ligne « santé du système » en tête du briefing.
- Ouverture de session automatique après redémarrage, heures d'activité Windows Update réglées.

## 2. Alertes planning sans IA
À chaque nouvelle version du .mpp, Python compare avec l'extraction précédente : tâches qui glissent, marge devenue négative, entrée ou sortie du chemin critique, clos couvert en premier.
Claude n'est réveillé que s'il y a un écart, pour l'expliquer et proposer les relances.

## 3. Boucle des relances et suivi des envois
- Python repère chaque matin les actions échues et les consultations sans réponse (offres attendues, J-3 avant remise).
- Claude prépare les relances en brouillon, dans le fil.
- Python vérifie les **Éléments envoyés** : un brouillon envoyé passe l'action à `vérifié` sans intervention.
- Comparaison brouillon / mail réellement envoyé → un court fichier de style, pour que les brouillons suivants demandent moins de corrections.

## 3 bis. WhatsApp (lecture seule)
- D'abord à la demande, en session interactive, pour mesurer le coût en tokens.
- Ensuite deux relèves par jour (avant le briefing et avant le récap), limitées aux groupes de `whatsapp_sources.csv` et aux nouveaux messages.
- Photos et messages vocaux : non lus automatiquement ; signalés (« 3 photos de X à 10h12 ») pour que le chef de projet décide.
- Pas de bibliothèque non officielle (risque de blocage du compte) : seulement WhatsApp Web dans Chrome.

## 4. Pièces jointes et décomptes
- Enregistrement automatique des pièces jointes dans `02_ENTRANT\<date>_<expéditeur>\`, conversion en texte une seule fois.
- Contrôle arithmétique des décomptes en Python : cumul cohérent avec le décompte précédent, cumul ≤ marché + avenants signés, retenues. Claude ne regarde que les anomalies.

## 5. Réunions de chantier
Dictée vocale après la réunion → compte rendu, actions et décisions dans les registres, ordre du jour de la réunion suivante pré-rempli avec les points ouverts.
À aligner avec le skill `tbrp-pilotage` déjà présent sur le compte, pour ne pas avoir deux versions des consignes.

## 6. Confort
- Tableau de bord HTML généré en Python depuis les registres (zéro token).
- Notification sur le téléphone, sans contenu du projet (« 2 brouillons prêts, 1 alerte planning »).
