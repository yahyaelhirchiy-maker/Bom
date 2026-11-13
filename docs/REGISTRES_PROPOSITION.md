# Registres — proposition de colonnes (À VALIDER, non figé)

Format proposé : CSV, séparateur `;`, UTF-8 avec BOM (ouverture directe dans Excel FR).
Montants en MAD HT. Dates AAAA-MM-JJ.
**Colonnes communes en fin de chaque registre :** `source ; statut ; date`
(statut = `vérifié` | `à confirmer` | `bloqué`).

## 1. lots.csv — lots / marchés
`lot_code ; lot_intitule ; entreprise ; marche_ref ; date_signature ; montant_initial_ht ; date_os ; delai_contractuel_j ; date_fin_contractuelle ; chemin_critique (oui/non) ; clos_couvert (oui/non)`

## 1b. avenants.csv
`avenant_id ; lot_code ; numero ; objet ; montant_ht ; incidence_delai_j ; etape (demande / chiffré / en négo / signé / refusé) ; date_signature`

## 2. decomptes.csv (données issues d'Outlook)
`decompte_id ; lot_code ; numero ; periode ; cumul_brut_ht ; montant_periode_ht ; retenue_garantie ; remb_avance ; penalites ; net_a_payer_ht ; net_ttc ; date_reception ; date_visa_moe ; date_validation_mod ; date_paiement ; etape ; ref_mail`

## 3. actions.csv — actions / relances
`action_id ; date_creation ; objet ; lot_code ; porteur ; demandeur ; echeance ; priorite (P1/P2/P3) ; chemin_critique ; nb_relances ; derniere_relance ; prochaine_relance ; etape (ouvert / en cours / clos) ; ref_fil_mail`

## 4. decisions.csv
`decision_id ; date_decision ; objet ; decision ; decideur ; instance (réunion chantier / COPIL / mail) ; lots_concernes ; impact_cout_ht ; impact_delai_j ; ref_cr`

## 5. consultations.csv — TSC
`consultation_id ; lot_code ; intitule ; mode (AO / gré à gré) ; date_envoi_dce ; date_remise_offres ; entreprises_consultees ; nb_offres ; estimation_ht ; moins_disant_ht ; entreprise_retenue ; montant_retenu_ht ; etape (DCE / consultation / analyse / négo / attribution / signé) ; date_attribution_cible ; date_besoin_chantier ; marge_j`

## 6. tsb.csv — TSB technique, atterrissage par lot
`lot_code ; lot_intitule ; budget_initial_ht ; budget_actualise_ht ; engage_ht (marché + avenants signés) ; avenants_en_cours_ht ; reste_a_engager_ht ; aleas_risques_ht ; atterrissage_ht ; ecart_vs_budget_ht ; commentaire`
avec `atterrissage = engagé + avenants en cours + reste à engager + aléas`.
