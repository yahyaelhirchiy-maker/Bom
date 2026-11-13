# Registres — colonnes (v1, ajustables quand les vrais fichiers seront vus)

Modèles vides : `modeles/registres/*.csv` → à copier dans `C:\BK\03_TRAVAIL\registres\`.

## Format (choisi pour économiser les tokens)
- **CSV** plutôt que JSON : le nom des colonnes n'apparaît qu'une fois (JSON le répète à chaque ligne, soit 2 à 3 fois plus de tokens).
- Séparateur `;`, UTF-8 avec BOM, **virgule décimale**, sans séparateur de milliers : s'ouvre directement dans Excel FR.
- Montants en MAD HT. Dates AAAA-MM-JJ. Une ligne = un élément. Cellule vide plutôt que « N/A ».
- Toujours en fin de ligne : `source ; statut ; date` (statut = `vérifié` | `à confirmer` | `bloqué`).

## Registres
| Fichier | Contenu |
|---|---|
| `lots.csv` | Un lot = une ligne : marché, entreprise, montant initial, délais, chemin critique, clos couvert |
| `avenants.csv` | Un avenant = une ligne, rattaché à son lot par `lot_code` |
| `decomptes.csv` | Données lues dans Outlook. Colonne `retenues_ht` globale, à détailler quand les décomptes seront vus |
| `actions.csv` | Actions et relances (porteur, échéance, nb de relances, fil de mail) |
| `decisions.csv` | Décisions prises (qui, où, impact coût / délai) |
| `consultations.csv` | TSC : suivi des consultations jusqu'à l'attribution |
| `tsb.csv` | Budget par lot. `atterrissage = engagé + avenants en cours + reste à engager + aléas` |
| `whatsapp_sources.csv` | Conversations WhatsApp autorisées (reste sur le PC). Tout ce qui n'y figure pas est privé |
| `contacts.csv` | Reste **sur le PC uniquement** (exclu de GitHub). Lu seulement pour préparer un brouillon |

À trancher plus tard, sur pièces : codification des lots, détail des retenues et circuit de visa des décomptes, niveau de détail du TSB.
