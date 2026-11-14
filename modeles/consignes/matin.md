Passage du MATIN (7h30, lun–ven), TBRP Bosko. Réponds en français, court. Respecte CLAUDE.md.
Lis seulement : CLAUDE.md, 03_TRAVAIL\ETAT.md, puis ce qui est demandé ci-dessous.
1. Notes : traite D:\BK\02_ENTRANT\notes_en_attente.md selon CLAUDE.md (section « Notes dictées »).
2. Mails : procédure `modelesnsignesmails_web.md` (Outlook Web, texte seulement, brouillons, jamais d'envoi).
3. `python D:/BK/00_SYSTEME/scripts/importer_pilotage.py`, puis `python D:/BK/00_SYSTEME/scripts/digest.py`, puis commit local 03_TRAVAIL si changement.
4. Lis 03_TRAVAIL\_cache\digest.md (pas les registres). Écris le briefing dans 04_PUBLIER\briefing\<AAAA-MM-JJ>.md : 1 page max, d'abord « ## En bref » (3 phrases simples écoutables en voiture, sans codes P0xx, chemins ni tableaux), puis chemin critique (verrière GIDNA, menuiserie alu GM), actions échues/du jour, relances (brouillons proposés), points bloqués.
5. Compte rendu des mails dans 04_PUBLIER\mails\<AAAA-MM-JJ_HHMM>.md. Signale les notes OASIS / « ? » restées en attente.
6. Mets à jour ETAT.md seulement si quelque chose a changé.
7. Publication : `python D:/BK/00_SYSTEME/scripts/livrables_page.py` ; si « nouveaux : 0 », saute ; sinon Artifact read puis publish (url https://claude.ai/artifact/592VnZ8SfbeMx6JqwDGbBM, file_path D:\BK\00_SYSTEME\modeles\page_livrables\index.html, files {"livrables.json": "D:/BK/00_SYSTEME/_page/livrables.json"}, sans icon), puis `livrables_page.py --publie`, puis PushNotification discrète sans nom, montant ni « Claude » : « BOSKO : <n> nouveau(x) livrable(s) – <types> ».
