# Style d'écriture de Yahya (à appliquer à tout ce qu'il envoie)

Tiré de ses ~400 mails envoyés de janvier à août 2026 (avant Claude), de son tableau de bord des sujets en suspens (09/09), de ses TCO et analyses d'offres. Tout texte qui part sous son nom (mail, CR, ODJ, colonne Commentaires d'un tableau, message WhatsApp proposé) doit ressembler à ça : un chef de projet qui connaît son dossier, pas un rapport d'IA.

## Règle n°1 : il ne cite jamais ses sources
Yahya pilote : l'info est dans sa tête, il ne la justifie pas.
- Interdit dans un texte envoyé : « mail de Sami du 11/10 », « selon le mail de… », « d'après WhatsApp », « dernier décompte classé : … », « document dont nous disposons », « (source : …) », « reçu le … par mail de … », noms de fichiers ou chemins dans le corps.
- Interdit aussi : « je ne sais pas », « aucune pièce ne permet de… ». À la place : poser la question directement (« Marwane, peux-tu me confirmer le reste dû BKTP ? ») ou écrire « à confirmer ».
- Une date n'apparaît que pour un **événement** ou une **échéance** : « suite à la visite de la SRM du 11/05 », « réunion du 08/09 », « au plus tard le 16/09 ». Jamais pour dater d'où vient l'info.
- Les sources restent obligatoires dans les **registres** (CSV, `historique` de `tbrp_state.json`) : c'est interne. Elles ne passent jamais dans le texte envoyé.

## Mails
- **Court.** Médiane : 250 caractères, 2 à 5 phrases. Long seulement pour un récapitulatif d'offres, des non-conformités ou un DCE.
- Ouverture : « Bonjour à tous, » ; « Bonjour Marwane, » ; à deux : « Bonjour Marwane, Bonjour Sami, ».
- Clôture : « Bien cordialement, » (la signature Outlook suit). Parfois avant : « Merci de ton retour rapide, », « Dans l'attente de ton retour, », « Aimable relance, » (relance).
- Débuts de phrase typiques : « Suite à… », « Je fais suite à… », « Tu trouveras en pièce jointe… », « Tu trouveras ci-dessous… », « Vous trouverez ci-dessous… », « En complément de mon précédent mail, ».
- Liaisons : « Il est à noter que… », « Par ailleurs, », « En conséquence, », « Pour récapituler, », « Compte tenu de… », « À ce titre, ».
- Demandes : « Merci de valider… », « Merci de lancer les travaux… », « Merci de nous confirmer… », « Merci de nous transmettre dans les plus brefs délais… », « Qu'en penses-tu ? ».
- « Nous » face aux entreprises (AEDGE), « je » en interne quand c'est lui qui a fait (« Je fais suite aux réunions de négociation… »).
- Montants : **MAD** (pas « DH »), espace pour les milliers, virgule pour les décimales, HT/TTC après : « 192 493,75 MAD HT ». En liste ou tableau, le nombre seul.
- Comparatifs et récapitulatifs : un **tableau** (une ligne par entreprise ou par poste, total en bas), pas une longue phrase.
- Listes : puces courtes, première lettre majuscule, « ; » en fin d'élément, phrase d'introduction terminée par « : » ou « notamment : ».
- Pas de tiret long « – » dans les phrases, pas de gras, pas de titres, pas d'emoji, pas de « N.B. », pas de formules creuses (« n'hésitez pas », « je reste à disposition »).
- Ton : direct, constatif, ferme avec les entreprises (« Ces constats ne sont pas conformes aux exigences de qualité du projet et nécessitent… »), simple en interne.

## Tableaux (tableau de bord, suivi, TCO, analyse d'offres)
- Colonnes de son tableau de bord : `N° | ITEM | Priorité (1 à 3) | Sujet d'instance | Intervenant | Commentaires | (action à mener)`.
- **Sujet d'instance** : état en quelques mots (« Travaux à l'arrêt », « Livrable en attente », « Cadence lente », « Vitrage approvisionné »).
- **Intervenant** : l'entreprise ou le couple bloqué (« KONE x GROUPE MSAA », « MO », « GIDNA GO »).
- **Commentaires** : une à trois phrases complètes, constat + cause + condition : « Travaux lancés mais bloqués en raison de l'absence d'électricité sur chantier », « Dans l'attente de la transmission du devis de ABAT », « Le dernier engagement communiqué par GIDNA prévoit un approvisionnement au plus tard le 11/09 », « Le sujet a été évoqué en off avec GIDNA… ».
- **Action** : infinitif court : « Vérifier l'avance… », « Préparer le BC… », « Transmettre le budget… », « Arbitrer… ».
- Analyse d'offre : colonne `Commentaire` = la raison de l'écart en une phrase (« La quantité n'est pas conforme aux plans, et doit être retirée »).
- Jamais de colonne « Source » ni de « Fiabilité » dans un tableau qui part ; si besoin, une feuille interne à part, non envoyée.

## CR / point de suivi
- Sujets numérotés (« 1. Verrière », « 2. Monocouche »…), sous chaque sujet des puces d'action à l'infinitif : « Définir… », « Établir et transmettre… », « Anticiper… », « Assurer le suivi… ». Ou une puce de constat : « Le vitrage est actuellement approvisionné. »
- Rappel : CR/ODJ = travaux seulement (voir `CLAUDE.md`).

## Avant de déposer un brouillon : relire avec ces questions
1. Est-ce qu'une phrase dit d'où vient l'info ? → la retirer.
2. Est-ce plus long que nécessaire ? → couper.
3. « DH » → « MAD » ; tirets longs, gras, parenthèses explicatives → retirer.
4. Est-ce que Yahya l'aurait écrit comme ça depuis son téléphone ? Sinon, simplifier.
