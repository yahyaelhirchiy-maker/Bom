---
name: odj-chantier
description: Préparer l'ordre du jour de la réunion de chantier TBRP du mardi (la veille, lundi après-midi) — ODJ xlsx + pdf au format AEDGE depuis tbrp_state.json et brouillon Outlook (classique par Python, PJ incluse). À utiliser pour « prépare l'ODJ » ou la tâche du lundi.
---

# Ordre du jour (lundi après-midi, réunion du mardi 9h)

## 0. Public ou interne (règle absolue de Yahya, 16/11)
Le CR et l'ODJ partent à toutes les entreprises : on n'y parle **que des travaux** (qui fait quoi, où, pour quand, ce qui bloque sur le chantier).
**Jamais dans `sujet`, `action`, `observations`** : départ ou remplacement d'une entreprise (ex. ABAT), consultation ou nouveau marché, paiements, factures, décomptes, montants, avenants, TS (sauf s'ils bloquent un travail, et sans montant), attente d'une validation interne AEDGE/MO (Loubna, Marwane, Sami, Nadia, « validation MOD »), positions ou décisions internes du MOD, brouillons.
Ces informations vont dans le champ **`note_interne`** du point (jamais imprimé) ; un point entièrement interne prend **`"interne": true`** (exclu du CR/ODJ). Une note dictée de Yahya est par défaut une info **pour lui** : n'en publier que la partie travaux.
`render_cr.py` refuse de générer s'il trouve un mot interdit : corriger le point (déplacer vers `note_interne`), jamais contourner.

1. Mettre `D:\BK\03_TRAVAIL\pilotage\tbrp_state.json` à jour avec les mails TBRP de la semaine (`outlook.py lister`/`lire`, texte seulement) : même règles que le skill `cr-chantier` §2, sans changer un statut sans source écrite.
2. Générer :
   `python D:/BK/00_SYSTEME/scripts/render_cr.py D:/BK/03_TRAVAIL/pilotage/tbrp_state.json --type odj --date <mardi AAAA-MM-JJ> --next "Mardi JJ/MM/AAAA à 9h – site TBRP" --outdir D:/BK/04_PUBLIER/odj`
   Tous les points non clos, par section, priorité 1 d'abord.
3. Brouillon Outlook classique (Python), mail séparé du CR. Le champ `--next` de l'ODJ = la réunion du JJ elle-même (la veille de laquelle on l'envoie), pas la suivante. Corps dans `D:\BK\02_ENTRANT\corps_odj_<AAMMJJ>.txt` :
   « Bonjour à tous,\n\nVous trouverez en pièce jointe l'ordre du jour de la réunion de chantier du mardi JJ/MM/AAAA à 9h sur site TBRP.\n\nBien à vous, »
   `python D:/BK/00_SYSTEME/scripts/outlook.py brouillon-envoye "TBRP - CR réunion de chantier" --date <AAAA-MM-JJ du dernier CR envoyé> --corps <fichier.txt> --pj "D:/BK/04_PUBLIER/odj/<AAMMJJ>.TBRP ODJ Réunion chantier.pdf" --objet "TBRP - ODJ réunion de chantier du JJ/MM/AAAA"`
   Répond à tous sur le dernier CR envoyé par Yahya, joint le PDF, Cc habituels, enregistre en Brouillons : jamais d'envoi. Secours : Outlook Web, texte seulement.
4. `python D:/BK/00_SYSTEME/scripts/importer_pilotage.py` puis commit local « ODJ du JJ/MM ».
4 bis. Page ODJ à remplir en réunion : `python D:/BK/00_SYSTEME/scripts/odj_page.py <mardi AAAA-MM-JJ>` → `04_PUBLIER\odj\odj_page.html`, puis la publier avec l'outil Artifact **sur l'URL de `modeles\odj_page\URL.txt`** (paramètre `url`, toujours la même page ; la lire d'abord avec `action: "read"` si cette session ne l'a pas encore publiée). Ne pas changer `capabilities` (db + user). Les saisies de la semaine vont dans la collection `r<AAMMJJ>`, celles des semaines passées restent intactes.
5. Rendre compte en 3 lignes : PDF, brouillon, lien de la page ODJ, points à rattraper (CR manquants, notes attendues).


Style : tout texte envoyé (brouillon, CR, ODJ, commentaire de tableau, message proposé) suit `modeles/consignes/style_yahya.md` ; jamais de source citée dans le texte.
