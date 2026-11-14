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


def lignes_mpxj(mpp):
    """Sans MS Project : lecture directe du .mpp par MPXJ (Java portable dans D:\\Outils\\jre21)."""
    import os
    os.environ.setdefault("JAVA_HOME", r"D:\Outils\jre21")
    import jpype, mpxj  # noqa: F401  (mpxj ajoute ses .jar au classpath)
    if not jpype.isJVMStarted():
        jpype.startJVM()
    try:
        from org.mpxj import TimeUnit
        from org.mpxj.reader import UniversalProjectReader
    except ImportError:
        from net.sf.mpxj import TimeUnit
        from net.sf.mpxj.reader import UniversalProjectReader
    p = UniversalProjectReader().read(str(mpp))
    props = p.getProjectProperties()
    jour = lambda v: str(v)[:10] if v is not None else ""
    parents, lignes = {}, []
    for t in p.getTasks():
        if not t.getName() or t.getOutlineLevel() is None or int(t.getOutlineLevel()) == 0:
            continue
        niv = int(t.getOutlineLevel())
        parents[niv] = str(t.getName())
        chemin = " > ".join(parents[i] for i in range(1, niv) if i in parents)
        fin, fin_ref = jour(t.getFinish()), jour(t.getBaselineFinish())
        ecart = (datetime.fromisoformat(fin) - datetime.fromisoformat(fin_ref)).days if fin and fin_ref else ""
        marge = t.getTotalSlack()
        marge = round(float(marge.convertUnits(TimeUnit.DAYS, props).getDuration()), 1) if marge is not None else ""
        lignes.append([int(t.getID()), chemin, str(t.getName()).strip(), jour(t.getStart()), fin, jour(t.getBaselineStart()),
                       fin_ref, ecart, float(t.getPercentageComplete() or 0), marge, "oui" if t.getCritical() else "",
                       str(t.getResourceNames() or "") if hasattr(t, "getResourceNames") else ""])
    return lignes


def extraire(mpp):
    mpp = Path(mpp)
    if TACHES.exists() and TACHES.stat().st_mtime >= mpp.stat().st_mtime:
        print("Planning déjà à jour, rien à faire.")
        return
    import win32com.client
    try:
        app = win32com.client.Dispatch("MSProject.Application")
    except Exception:  # MS Project absent : lecture directe du fichier
        ecrire(mpp, lignes_mpxj(mpp))
        return
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
    ecrire(mpp, lignes)


def ecrire(mpp, lignes):
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
