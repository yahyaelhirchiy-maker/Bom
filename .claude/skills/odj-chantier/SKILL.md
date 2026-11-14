---
name: odj-chantier
description: Préparer l'ordre du jour de la réunion de chantier TBRP du mardi (la veille, lundi après-midi) — ODJ xlsx + pdf au format AEDGE depuis tbrp_state.json et brouillon Outlook Web. À utiliser pour « prépare l'ODJ » ou la tâche du lundi.
---

# Ordre du jour (lundi après-midi, réunion du mardi 9h)

1. Mettre `D:\BK\03_TRAVAIL\pilotage\tbrp_state.json` à jour avec les mails TBRP de la semaine (Outlook Web, texte seulement) : même règles que le skill `cr-chantier` §2, sans changer un statut sans source écrite.
2. Générer :
   `python D:/BK/00_SYSTEME/scripts/render_cr.py D:/BK/03_TRAVAIL/pilotage/tbrp_state.json --type odj --date <mardi AAAA-MM-JJ> --next "Mardi JJ/MM/AAAA à 9h – site TBRP" --outdir D:/BK/04_PUBLIER/odj`
   Tous les points non clos, par section, priorité 1 d'abord.
3. Brouillon Outlook Web : sur le dernier mail du fil « TBRP - CR réunion de chantier », « Répondre à tous », objet « TBRP - ODJ réunion de chantier du JJ/MM/AAAA », corps :
   « Bonjour à tous, Vous trouverez en pièce jointe l'ordre du jour de la réunion de chantier du mardi JJ/MM/AAAA à 9h sur site TBRP. Bien à vous, »
   Quitter sans envoyer ; donner à Yahya le chemin du PDF à joindre.
4. `python D:/BK/00_SYSTEME/scripts/importer_pilotage.py` puis commit local « ODJ du JJ/MM ».
5. Rendre compte en 3 lignes : PDF, brouillon, points à rattraper (CR manquants, notes attendues).
