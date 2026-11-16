Passage SHAREPOINT du soir (lun–ven 18h30), chantier TBRP – Bosko. Français, court.

Travaille depuis D:\BK\00_SYSTEME. Lis CLAUDE.md, puis D:\BK\03_TRAVAIL\ETAT.md, puis suis le skill `.claude\skills\sharepoint\SKILL.md` (règles, outils, plan de classement). Texte seulement : pas de navigateur, pas de capture, pas de computer use.

Étapes :
1. `python D:/BK/00_SYSTEME/scripts/sharepoint.py carte`.
2. Lis `D:\BK\03_TRAVAIL\_cache\sharepoint_dernier.txt` (AAAA-MM-JJ HH:MM ; absent = **premier passage**, voir plus bas). N jours = depuis cette date, arrondi au-dessus.
3. Mails : `outlook.py lister --jours N` et `outlook.py envoyes --jours N`. Garde seulement les mails TBRP – Bosko postérieurs au dernier passage. Pour chacun (lire avec `outlook.py lire N` si l'objet ne suffit pas) :
   - PJ utiles (plans, FT, PV, décomptes, offres, marchés, avenants, CR, ODJ, plannings, photos de chantier) → `exporter … --pj --vers D:/BK/03_TRAVAIL/_cache/sp_depot/<AAMMJJ>/<n>`, puis `existe` sur chaque nom, puis `deposer` dans le bon dossier avec `--motif "mail <date> <expéditeur> <objet>"`.
   - Mail important (définition dans le skill) → `exporter … --mail`, puis `deposer` dans `25.AEDGE PARTNERS - Technique\<AAMMJJ>.TBRP.Mails importants <sujet>` (un dossier par sujet ou lot ; réutiliser le dossier du même sujet s'il existe).
   - **Décomptes** : toujours déposés (PJ du mail de l'entreprise, puis version validée si elle passe dans un mail).
4. CR et ODJ : pour chaque fichier de `D:\BK\04_PUBLIER\cr` et `\odj` absent du SharePoint (`existe`), cherche le mail envoyé correspondant (`envoyes`, objet contenant « CR » ou « ordre du jour ») ; s'il est parti, `exporter --envoye … --pj` et `deposer` (CR → `10. PV Réunions\1. Réunions de Chantier`, ODJ → `25.AEDGE PARTNERS - Technique\Ordre du Jour`). Sinon, rien.
5. Livrables internes de la semaine dans `04_PUBLIER` (analyses, planning, optimisation exclue) : seulement ceux que Yahya a demandé de classer (notes dictées) → `25.AEDGE PARTNERS - Technique`.
6. Écris `sharepoint_dernier.txt` (date et heure de ce passage). Commit local `git -C D:/BK/03_TRAVAIL add -A` puis `commit -m "SharePoint <date>"`. Jamais de push.
7. Compte rendu `D:\BK\04_PUBLIER\sharepoint\<AAAA-MM-JJ>.md` : liste des dépôts (dossier ← fichier ← source), puis « Ce qui manque » (au plus 10 lignes : document attendu absent, dossier vide ou pas à jour, fichier mal classé ou en double — sans rien déplacer), puis les doutes de classement laissés à Yahya.
8. Notification téléphone courte sans nom, sans montant et sans le mot « Claude » (ex. « SharePoint : 6 documents classés »), seulement s'il y a eu des dépôts ou un manque important.

**Premier passage (pas de `sharepoint_dernier.txt`)** :
- Rattrapage des **30 derniers jours** de mails (étape 3) et de tous les CR/ODJ envoyés depuis le dernier CR présent sur SharePoint (étape 4).
- Rapport « Ce qui manque » complet (jusqu'à 30 lignes) : pour chaque lot, ce qui devrait exister (marché, avenants, décomptes, plans EXE, PV, planning) et n'est pas sur SharePoint, d'après la carte, `registres\lots.csv`, `avenants.csv` et `tbrp_state.json` (lignes du lot seulement).
