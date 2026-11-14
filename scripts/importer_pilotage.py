"""Rafraîchit actions.csv et decisions.csv depuis tbrp_state.json (D:\\BK\\03_TRAVAIL\\pilotage).

  python importer_pilotage.py [chemin\\tbrp_state.json]

- Points de chantier (P001…) -> actions.csv ; décisions MO (D001…) -> decisions.csv.
- Les lignes importées sont remplacées à chaque passage ; les autres lignes
  (ex. actions créées par le traitement des mails, A-…) sont conservées.
- Ne modifie jamais tbrp_state.json (lecture seule).
"""
import csv, json, sys
from pathlib import Path

SOURCE_DEFAUT = Path(r"D:\BK\03_TRAVAIL\pilotage\tbrp_state.json")
REG = Path(r"D:\BK\03_TRAVAIL\registres")


def montant(v):
    return "" if v is None else str(v).replace(".", ",")


def fusionner(fichier, prefixe, nouvelles):
    """Remplace les lignes dont l'id commence par `prefixe`, garde les autres."""
    with open(fichier, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f, delimiter=";")
        cols, gardees = r.fieldnames, [l for l in r if not l[r.fieldnames[0]].startswith(prefixe)]
    with open(fichier, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, cols, delimiter=";")
        w.writeheader()
        w.writerows(nouvelles + gardees)
    return len(nouvelles), len(gardees)


def actions(etat, src):
    lignes = []
    for p in etat["points_chantier"]:
        rel = p.get("relances") or []
        faites = [x["date"] for x in rel if "brouillon" not in str(x.get("statut", ""))]
        a_venir = [x.get("echeance") or x["date"] for x in rel if "brouillon" in str(x.get("statut", ""))]
        lignes.append({
            "action_id": p["id"], "date_creation": p.get("ouvert_le") or "",
            "objet": f"{p['sujet']} : {p['action']}", "lot_code": "",
            "porteur": p.get("responsable") or "", "demandeur": p.get("demande_par") or "",
            "echeance": p.get("echeance") or "", "priorite": p.get("priorite") or "",
            "chemin_critique": "", "nb_relances": len(faites),
            "derniere_relance": max(faites) if faites else "",
            "prochaine_relance": min(a_venir) if a_venir else "",
            "etape": p.get("statut") or "", "ref_mail": "",
            "source": f"{src} ({p.get('section', '')}) ; {p.get('observations') or ''}".strip(" ;"),
            "statut": "vérifié", "date": p.get("maj_le") or etat.get("maj_le", ""),
        })
    return lignes


def decisions(etat, src):
    return [{
        "decision_id": d["id"], "date_decision": "",
        "objet": d["lot"], "decision": f"[{d['statut']}] {d['decision']} — situation : {d.get('situation') or ''}",
        "decideur": d.get("porteur") or "", "instance": d.get("categorie") or "",
        "lots": d["lot"], "impact_cout_ht": montant(d.get("montant_ht")), "impact_delai_j": "",
        "ref_cr": d.get("source") or "", "source": src, "statut": "vérifié",
        "date": etat.get("maj_le", ""),
    } for d in etat["decisions_mo"]]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCE_DEFAUT
    etat = json.loads(source.read_text(encoding="utf-8"))
    src = f"{source} (maj {etat.get('maj_le', '?')})"
    na, ga = fusionner(REG / "actions.csv", "P", actions(etat, src))
    nd, gd = fusionner(REG / "decisions.csv", "D", decisions(etat, src))
    print(f"actions : {na} importées, {ga} conservées | décisions : {nd} importées, {gd} conservées")


if __name__ == "__main__":
    main()
