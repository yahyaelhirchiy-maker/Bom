"""MS Project en texte (pywin32). Ouvre le .mpp en LECTURE SEULE, ne l'enregistre jamais.

  python planning.py extraire D:\\BK\\01_MIROIR\\...\\planning.mpp
      -> D:\\BK\\03_TRAVAIL\\planning\\taches.csv (seulement si le .mpp a changé)
  python planning.py lot "verrière"
      -> tâches dont le chemin contient le mot-clé, en texte compact
  python planning.py lot "verrière" --xlsx
      -> en plus, extrait Excel dans D:\\BK\\04_PUBLIER\\pj\\ (pièce jointe)
"""
import argparse, csv, sys
from datetime import datetime
from pathlib import Path

DOSSIER = Path(r"D:\BK\03_TRAVAIL\planning")
TACHES = DOSSIER / "taches.csv"
PJ = Path(r"D:\BK\04_PUBLIER\pj")
COLS = ["id", "chemin", "nom", "debut", "fin", "debut_ref", "fin_ref", "ecart_fin_j",
        "avancement", "marge_j", "critique", "ressources"]


def d(v):
    try:
        return v.strftime("%Y-%m-%d")
    except AttributeError:
        return ""  # "NA" = pas de référence


def extraire(mpp):
    mpp = Path(mpp)
    if TACHES.exists() and TACHES.stat().st_mtime >= mpp.stat().st_mtime:
        print("Planning déjà à jour, rien à faire.")
        return
    import win32com.client
    app = win32com.client.Dispatch("MSProject.Application")
    app.Visible = False
    app.FileOpenEx(str(mpp), True)  # ReadOnly = True
    p = app.ActiveProject
    minutes_jour = p.HoursPerDay * 60
    parents, lignes = {}, []
    for t in p.Tasks:
        if t is None:
            continue
        parents[t.OutlineLevel] = t.Name
        chemin = " > ".join(parents[i] for i in range(1, t.OutlineLevel) if i in parents)
        fin, fin_ref = d(t.Finish), d(t.BaselineFinish)
        ecart = (datetime.fromisoformat(fin) - datetime.fromisoformat(fin_ref)).days if fin and fin_ref else ""
        lignes.append([t.ID, chemin, t.Name, d(t.Start), fin, d(t.BaselineStart), fin_ref, ecart,
                       t.PercentComplete, round(t.TotalSlack / minutes_jour, 1), "oui" if t.Critical else "",
                       t.ResourceNames])
    app.FileCloseEx(0)  # 0 = ne pas enregistrer
    DOSSIER.mkdir(parents=True, exist_ok=True)
    with open(TACHES, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(COLS + ["source", "date"])
        for l in lignes:
            w.writerow(l + [str(mpp), datetime.now().strftime("%Y-%m-%d")])
    print(f"{len(lignes)} tâches extraites -> {TACHES}")


def lot(mot, xlsx):
    with open(TACHES, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f, delimiter=";")
                if mot.lower() in (r["chemin"] + " " + r["nom"]).lower()]
    for r in rows:
        print(" | ".join(r[c] for c in ["id", "nom", "debut", "fin", "fin_ref", "ecart_fin_j", "avancement", "marge_j", "critique"]))
    if xlsx and rows:
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "Planning"
        entetes = ["Tâche", "Début", "Fin", "Fin référence", "Avancement %"]
        ws.append(entetes)
        for r in rows:
            ws.append([r["nom"], r["debut"], r["fin"], r["fin_ref"], r["avancement"]])
        PJ.mkdir(parents=True, exist_ok=True)
        out = PJ / f"Extrait_planning_{mot}_{datetime.now():%Y%m%d}.xlsx"
        wb.save(out)
        print(f"PJ: {out}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    s = a.add_subparsers(dest="cmd", required=True)
    s.add_parser("extraire").add_argument("mpp")
    l = s.add_parser("lot"); l.add_argument("mot"); l.add_argument("--xlsx", action="store_true")
    x = a.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    extraire(x.mpp) if x.cmd == "extraire" else lot(x.mot, x.xlsx)
