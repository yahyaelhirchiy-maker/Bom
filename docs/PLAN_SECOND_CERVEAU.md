# Plan — Second cerveau TBRP – Bosko

Validé par Yahya le 16/11/2026. Démarrage : pilote **clos couvert** (verrière GIDNA, menuiserie alu / murs-rideaux GM), traité de bout en bout. Extension lot par lot ensuite.

## Vision
Un « chef de projet bis » qui connaît tout le projet, pense au projet en continu et fait le travail de chef de projet. Il ne remonte à Yahya que les décisions humaines.

## Rôles
- **Python + Qwen (local, gratuit) = les petites mains.** Ils lisent tout (SharePoint, plans compris, mails, `tbrp_state.json`, planning), extraient des faits sourcés et préparent un dossier compact des changements. Ils ne jugent rien.
- **Claude = le chef de projet.** Il détecte les anomalies, analyse ce qu'elles signifient (chemin critique, marché, autres lots) et produit le livrable : note, demande de validation, brouillon de mail, point d'ODJ, mise à jour des registres ou du planning.
- **Claude contrôle Qwen.** Il vérifie chaque jour un échantillon et mesure le taux d'erreur par type de tâche. Qwen reste sur les tâches où il est fiable.
- **Yahya** prend les décisions humaines (décisions MO, choix techniques).

## Garde-fous (inchangés)
Les règles de `CLAUDE.md` s'appliquent : jamais d'envoi de mail (brouillons seulement), jamais de décision MO, SharePoint en écriture seulement par l'agent, aucune confidentialité violée. L'autonomie porte sur penser, vérifier et préparer.

## Qwen et usage du PC
Une seule file Qwen pour les plans (`analyse_marches.py`), les extractions et les mises à jour. Qwen se met en **pause ou en régime réduit dès que Yahya utilise le PC**. Il peut tourner de jour comme de nuit.

## Réveils de Claude (décidé le 16/11)
- **Deux passages par jour seulement**, greffés sur les tâches existantes `bosko-matin` (7h30) et `bosko-apres-midi` (14h). Aucun autre réveil de Claude.
- Chaque passage lit en plus le **dossier compact du cerveau** (changements, anomalies candidates, alertes), préparé en amont par Python et Qwen, à côté du `digest.md` actuel.
- Une urgence détectée entre deux passages est **signalée dans le dossier** et traitée au passage suivant. Pas de réveil immédiat.
- Plafond : 2 réveils par jour. Mémoire en fichiers, sessions courtes, aucune longue conversation.

## Étapes (pilote clos couvert, environ une semaine)
| Jour | Étape | Outil | Tokens | À la fin, Yahya peut… |
|---|---|---|---|---|
| 1 | **Sens** : index local (SQLite FTS5) des textes SharePoint, des mails `outlook.py`, de `tbrp_state.json` et du planning, avec mise à jour incrémentale et commande de recherche à extraits courts | Python | Faible, une fois | Retrouver toute info du clos couvert en une question |
| 2 | **Mains** : extraction de faits sourcés par Qwen (dates, versions, engagements, montants, acteurs) pour GIDNA et GM, plans compris (reprise de `analyse_marches.py`), avec pause automatique | Qwen | 0 | Voir les faits extraits par document |
| 3 | **Contrôle** : Claude vérifie un échantillon contre les sources et mesure la fiabilité de Qwen par type de tâche, puis on ajuste les consignes | Claude | Moyen | Savoir chiffres à l'appui ce que vaut Qwen |
| 4 | **Mémoire** : état vivant par lot, entreprise et BET, relié aux points P/D, avec la date du dernier document connu et les « trous possibles » | Python + Qwen, validé par Claude | Faible | Lire l'état verrière et alu à jour |
| 5 | **Dossier et passages** : dossier compact des changements pour les passages matin et après-midi, marquage des urgences, contrôle de santé (PC, Outlook, OneDrive, scripts) | Python | Faible | Recevoir des réveils utiles, sans bruit |
| 6 | **Chef de projet** : skill qui analyse, produit les livrables et ne remonte que les décisions | Claude | Moyen, une fois | Recevoir un travail fait, avec une seule question |
| 7 | **Apprentissage et bilan** : les corrections de Yahya deviennent des règles ; bilan sur la justesse des alertes, la qualité des livrables et le coût en tokens | Claude | Faible | Décider d'étendre à d'autres lots |

## Limites connues
- Plans : `qwen2.5vl:7b` lit les cartouches et le texte, pas les détails techniques fins.
- Ce qui n'est pas écrit (chantier, téléphone) reste inconnu sauf par les CR, WhatsApp ou des notes de Yahya.
- Abonnement Pro : les réveils autonomes consomment le même quota que les conversations.
- Fiabilité : comptez 3 à 4 semaines d'usage et de corrections avant une vraie autonomie.

## Critères pour étendre au-delà du pilote
Des alertes jugées justes par Yahya, des livrables utilisables presque sans retouche, et un coût en tokens compatible avec l'abonnement Pro.

## Suivi
Mis à jour par la tâche `bosko-second-cerveau`. État vérifié dans `scripts\` et `03_TRAVAIL\`.

| Étape | État | Où on en est |
|---|---|---|
| Jour 1 — index des textes SharePoint | fait (16/11) | `cerveau.py indexer` / `chercher` ; base `_cache\cerveau.db` |
| Jour 1 fin — mails, `tbrp_state.json`, planning, réindexation après dépôt SharePoint | fait (17/11) | `cerveau.py sources` (mails reçus+envoyés 90 j → `_texte\_mails`, points P/D → `_texte\_pilotage`, `taches.csv` → `_texte\_planning`), lancé chaque matin (`matin.md`, 7 j) ; `sharepoint.py deposer` appelle `cerveau.py ajouter`. 17/11 : 428 mails, 79 fiches état, 4 fiches planning ; 6370 documents indexés |
| Jour 2 — faits sourcés par Qwen (GIDNA, GM), plans compris, pause auto | fait (19/11) | Plans : `analyse_plans.py` (qwen2.5vl, `analyses\plans\ouvrages.csv`). Faits : `faits.py extraire` (18/11, qwen3:14b, config `TBRP.json` clé `faits`) — mails puis documents VER/ALU, passages à mots-clés, citation exacte vérifiée par Python, cache par document, attend si un autre modèle est chargé ou créneau réservé, régime réduit si le PC est utilisé, Oasis exclu. Sorties : `03_TRAVAIL\analyses\faits\faits.csv` + `par_document.md`. 18/11 : 54 documents lus (22 mails + 32 docs récents, surtout CR de chantier), 171 faits, citation retrouvée 164/171. 19/11 : les 168 documents sont lus, 554 faits (84 % de citations retrouvées), 83 min de Qwen au total. Un nouveau document est lu au prochain `faits.py extraire` |
| Jour 3 — contrôle d'un échantillon Qwen par Claude | fait (19/11) | 20 faits contrôlés → 5 inventés (tous attrapés par le contrôle de citation), 2/3 des faits vrais hors lot. Avis appliqués (consigne v2 de `faits.py`) puis 168 documents relus : 3 % de citations introuvables (écartées, `rejetes.csv`), 162 faits VER/ALU (`faits.csv`), 375 faits des autres lots triés (`autres_lots.csv`) ; 2e échantillon : 8/12 utiles et justes. Dossier : `04_PUBLIER\second_cerveau\revue_jour3_2026-11-19.md` |
| Jour 4 — mémoire par lot / entreprise / BET | à faire | À prévoir : fusionner les doublons recopiés d'un CR à l'autre (garder le plus récent), corriger `date_fait` (souvent = date du document) |
| Jour 5 — dossier compact des passages + santé | à faire | |
| Jour 6 — skill chef de projet | à faire | |
| Jour 7 — apprentissage et bilan | à faire | |

avis Yahya (revue jour 3) : 19/11 — 1) écarter les faits à citation introuvable : oui ; 2) faits hors lot : les garder, triés par lot, pour les autres lots ; 3) montants et acteurs retirés à Qwen si Claude le juge nécessaire ; 4) corriger la consigne et relire les 168 documents : oui.
avis Yahya (bilan jour 7) :

Journal :
- 2026-11-17 : jour 1 terminé (mails, état, planning dans l'index ; réindexation après dépôt). Prochaine étape : jour 2.
- 2026-11-18 : jour 2 avancé — `faits.py` créé, 54/168 documents lus (171 faits, 96 % de citations retrouvées). Deux appels Qwen ont dépassé 15 min (réponse plafonnée depuis). Lancé de nuit avec `--sans-horaires`. Reste : finir les 114 documents, puis jour 3 (revue).
- 2026-11-19 : jour 2 terminé (168/168 documents, 554 faits ; le 1er chargement de Qwen a renvoyé une erreur 500, la reprise automatique a suffi). Dossier de revue du jour 3 prêt ; arrêt en attendant l'avis de Yahya.
- 2026-11-19 (après-midi) : avis de Yahya reçu et appliqué (consigne v2, montants/acteurs retirés à Qwen, hors lot gardé à part), 168 documents relus en 53 min. Jour 3 terminé. Prochaine étape : jour 4 (mémoire par lot).
