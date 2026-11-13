Traitement des mails, TBRP Bosko. Respecte CLAUDE.md.
La liste ci-dessous a déjà été triée (newsletters, notifications et mails déjà traités sont exclus).
1. Pour chaque mail : `python D:/BK/00_SYSTEME/scripts/outlook.py lire <N>` (N = M1, M2…).
2. S'il demande une réponse, une date, un document ou une action : applique la procédure du skill traiter-mail.
3. S'il apporte seulement une info utile (date, décision, montant) : mets à jour le registre concerné, avec la source.
4. Niveau « simple » : si un mail se révèle délicat (financier, réclamation, engagement, conflit), ne rédige rien,
   écris son N sur une ligne dans D:/BK/03_TRAVAIL/_cache/a_reclasser.txt ; il sera repris par le modèle le plus puissant.
5. Rends : un bloc de 5 lignes par brouillon préparé, puis une ligne par mail sans suite, puis les mails reclassés.
