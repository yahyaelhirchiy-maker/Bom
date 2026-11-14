Rapport hebdomadaire (vendredi 12h), TBRP Bosko. Respecte CLAUDE.md.
0. Rafraîchis les registres : `python D:/BK/00_SYSTEME/scripts/importer_pilotage.py`, puis, si `git -C D:/BK/03_TRAVAIL status` montre un changement, `git -C D:/BK/03_TRAVAIL add -A` et `git -C D:/BK/03_TRAVAIL commit -m "Import pilotage"`.
1. Lis ETAT.md, puis les registres (git log de la semaine dans 03_TRAVAIL).
2. Rends un rapport structuré :
   - Avancement et chemin critique (clos couvert d'abord), écarts de planning.
   - TSB : atterrissage par lot, écarts vs budget, avenants en cours.
   - Décomptes de la semaine (statuts).
   - Consultations en cours.
   - Décisions prises / attendues.
   - Actions et relances ouvertes.
3. Ajoute en annexe la consommation de la semaine : `python D:/BK/00_SYSTEME/scripts/conso.py --jours 7` (5 lignes max, et une recommandation si une tâche coûte trop).
4. Chaque chiffre cite sa source et son statut (vérifié / à confirmer / bloqué).
