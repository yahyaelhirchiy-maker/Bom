---
name: cr-chantier
description: Établir le compte rendu de la réunion de chantier TBRP du mardi à partir des notes (souvent dictées) du chef de projet — mise à jour de tbrp_state.json, CR xlsx + pdf au format AEDGE, brouillon Outlook Web prêt à envoyer. À utiliser dès que Yahya donne ses notes de réunion.
---

# CR de réunion de chantier (mardi 9h, site TBRP)

Source de vérité des points : `D:\BK\03_TRAVAIL\pilotage\tbrp_state.json` (`points_chantier`, `decisions_mo`, `regles`).

## 1. Notes
Yahya donne ses notes par lot (GIDNA GO, GIDNA ELEC, GIDNA FLUIDES, ABAT, GM, BATISOLAIRE…). Corriger les noms avec `registres\lexique.csv` (« Gina » = GIDNA).

## 2. Mettre à jour tbrp_state.json
Chaque note met à jour un point existant (action, échéance, statut, observations, `historique` daté) ou crée un point `Nouveau` dans la bonne section (id suivant : P0xx).
- Statuts : `Engagement` (une entreprise s'engage sur une date), `Retard` (engagement non tenu), `Reconduit` (point non abordé), `Clos` (soldé), `En cours`.
- « cette semaine » → vendredi ; « semaine prochaine » → vendredi suivant ; le signaler.
- Points abordés : `maj_le` = date de la réunion. `maj_le` du fichier = aujourd'hui.
- Garder l'indentation et l'encodage UTF-8 du fichier. Vérifier qu'il se relit (`python -c "import json;json.load(open(r'D:\BK\03_TRAVAIL\pilotage\tbrp_state.json',encoding='utf-8'))"`).

## 3. Générer
`python D:/BK/00_SYSTEME/scripts/render_cr.py D:/BK/03_TRAVAIL/pilotage/tbrp_state.json --type cr --date <AAAA-MM-JJ> --next "Mardi JJ/MM/AAAA à 9h – site TBRP" --outdir D:/BK/04_PUBLIER/cr`
→ `<AAMMJJ>.TBRP CR Réunion chantier.xlsx` + `.pdf` (A3, via Excel). Contrôler le texte du PDF (pypdf) : nombre de points, aucune ligne SharePoint/GED.

## 4. Brouillon (Outlook Web, navigateur intégré, texte seulement)
Sur le dernier mail du fil « TBRP - CR réunion de chantier » : « Répondre à tous », corps :
« Bonjour à tous, Vous trouverez en pièce jointe le compte rendu de la réunion de chantier du JJ/MM/AAAA, qui s'est tenue sur site TBRP. Merci de noter que la prochaine réunion de chantier aura lieu le mardi JJ/MM/AAAA à 9h toujours sur site TBRP. Bien à vous, »
L'heure doit être celle du CR. Quitter sans envoyer. La pièce jointe ne peut pas être ajoutée automatiquement : donner à Yahya le chemin du PDF à joindre.

## 5. Registres et traces
- `python D:/BK/00_SYSTEME/scripts/importer_pilotage.py`, puis commit local dans `03_TRAVAIL` : « CR réunion du JJ/MM ».
- `ETAT.md` si le chemin critique ou une alerte change.
- Proposer à Yahya seul de classer le CR sur SharePoint (`04. Construction/03. Travaux/10. PV Réunions/1. Réunions de Chantier/`). Ne rien déposer soi-même.

## 6. Rendre compte
PDF produit, brouillon prêt, et la liste à vérifier : points mis à jour depuis les mails plutôt que les notes, échéances déduites, formulations durcies.
