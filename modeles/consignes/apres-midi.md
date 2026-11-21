Passage de l'APRÈS-MIDI (14h, lun–ven), TBRP Bosko. Réponds en français, court. Respecte CLAUDE.md.
Lis seulement : CLAUDE.md, 03_TRAVAIL\ETAT.md, 03_TRAVAIL\_cache\digest.md (celui du matin), puis ce qui est demandé ci-dessous.
0. Tout premier geste : `python D:/BK/00_SYSTEME/scripts/passage_ok.py debut apres-midi`.
1. Notes : traite D:\BK\02_ENTRANT\notes_en_attente.md selon CLAUDE.md (section « Notes dictées »).
2. Mails : procédure `modeles/consignes/mails_outlook.md` (Outlook classique par `outlook.py`, texte seulement, brouillons avec PJ, jamais d'envoi ; Outlook Web seulement en secours), depuis le dernier passage.
2 bis. WhatsApp : procédure `modeles/consignes/whatsapp.md` (Chrome, lecture seule, conversations autorisées uniquement).
3. Si des points ont changé : `python D:/BK/00_SYSTEME/scripts/importer_pilotage.py` puis `python D:/BK/00_SYSTEME/scripts/digest.py`, commit local 03_TRAVAIL.
3 bis. `python D:/BK/00_SYSTEME/scripts/dossier.py --sans-memoire` puis lis 03_TRAVAIL\_cache\dossier.md (urgences et changements depuis le matin, santé) ; traite les urgences ; en dernier `dossier.py --sans-memoire --marquer`.
4. Récap court (1/2 page) dans 04_PUBLIER\briefing\<AAAA-MM-JJ>_recap.md : ce qui a avancé, ce qui reste ouvert, relances à préparer pour demain.
4 bis. LUNDI seulement : si `04_PUBLIER\odj\<AAMMJJ du mardi>.TBRP ODJ Réunion chantier.pdf` n'existe pas, prépare l'ODJ de la réunion de demain avec le skill `odj-chantier` (xlsx + pdf + brouillon Outlook, jamais d'envoi). S'il existe déjà, ne rien refaire.
4 ter. Si le passage du matin n'a pas publié (pas de notification ce jour-là), l'étape 8 ci-dessous rattrape : elle publie tout ce qui est nouveau, briefing du matin compris.
5. VENDREDI seulement : ajoute le rapport hebdo dans 04_PUBLIER\hebdo\<AAAA-MM-JJ>.md (avancement et chemin critique, TSB par lot, décomptes, consultations, décisions, actions ouvertes ; lis les registres tsb/decomptes/consultations ; chaque chiffre cite source et statut ; annexe `python D:/BK/00_SYSTEME/scripts/conso.py --jours 7`, 5 lignes).
6. Compte rendu des mails dans 04_PUBLIER\mails\<AAAA-MM-JJ_HHMM>.md. Signale les notes OASIS / « ? » en attente.
7. Mets à jour ETAT.md seulement si quelque chose a changé.
8. Publication : même procédure que le matin, y compris overwrite_unread ["livrables.json"] (livrables_page.py, Artifact read + publish, --publie, PushNotification discrète).
9. Tout dernier geste (même si une étape a échoué : note-le dans le compte rendu) : `python D:/BK/00_SYSTEME/scripts/passage_ok.py fin apres-midi`.
