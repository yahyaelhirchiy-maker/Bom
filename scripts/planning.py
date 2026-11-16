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


# ---------------------------------------------------------------------------
# Simulation sur la copie recalée (03_TRAVAIL\planning\recalage.csv)
#   python planning.py simuler                          -> scénario de base
#   python planning.py simuler --scenario tous --xlsx --xml
#   python planning.py simuler --decaler VERR=+28 --decaler lot:Paiements=+30 --duree REV=90
# Durées en jours calendaires. pred : "ID", "ID+14" (fin-début + délai), "ID:SS+42" (début-début).
# debut_min = pas avant ; fin_min = engagement de fin (la tâche ne finit pas avant, mais peut glisser).
# ---------------------------------------------------------------------------
RECALAGE = DOSSIER / "recalage.csv"
SCENARIOS = DOSSIER / "scenarios.json"
SORTIE = Path(r"D:\BK\04_PUBLIER\planning")
JALONS = [("HEHA", "Hors d'eau, hors d'air"), ("MAD_GMS", "Mise à disposition GMS"),
          ("MAD_GAL", "Mise à disposition galerie"), ("OPR_GEN", "Fin OPR générales"),
          ("LIVR", "Livraison du centre")]


def charger_recalage(path=RECALAGE):
    import re
    from datetime import date
    jour = lambda v: date.fromisoformat(v) if v else None
    taches = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            preds = []
            for tok in filter(None, (t.strip() for t in r["pred"].split(","))):
                m = re.fullmatch(r"(\w+?)(?::(SS|FS))?([+-]\d+)?", tok)
                if not m:
                    sys.exit(f"Prédécesseur illisible pour {r['id']} : {tok}")
                preds.append((m[1], m[2] or "FS", int(m[3] or 0)))
            taches[r["id"]] = dict(r, duree=int(r["duree_j"]), preds=preds,
                                   dmin=jour(r["debut_min"]), fmin=jour(r["fin_min"]))
    for t in taches.values():
        for p, _, _ in t["preds"]:
            if p not in taches:
                sys.exit(f"{t['id']} : prédécesseur inconnu {p}")
    return taches


def cibles(taches, cle):
    """'VERR' -> [VERR] ; 'lot:Paiements' -> toutes les tâches du lot ; 'FP*' -> préfixe."""
    if cle.startswith("lot:"):
        r = [i for i, t in taches.items() if t["lot"].lower() == cle[4:].lower()]
    elif cle.endswith("*"):
        r = [i for i in taches if i.startswith(cle[:-1])]
    else:
        r = [cle] if cle in taches else []
    if not r:
        sys.exit(f"Aucune tâche ne correspond à « {cle} »")
    return r


def calculer(taches, decaler=None, duree=None):
    """Passe avant/arrière (méthode du chemin critique). Dates internes : fin = début du lendemain."""
    from datetime import timedelta
    J = lambda n: timedelta(days=n)
    dec, dur = {}, {}
    for k, v in (decaler or {}).items():
        for i in cibles(taches, k):
            dec[i] = dec.get(i, 0) + int(v)
    for k, v in (duree or {}).items():
        for i in cibles(taches, k):
            dur[i] = int(v)
    res, ordre, en_cours = {}, [], set()

    def visiter(i):
        if i in res:
            return
        if i in en_cours:
            sys.exit(f"Boucle de dépendances autour de {i}")
        en_cours.add(i)
        t = taches[i]
        bornes = []
        for p, typ, lag in t["preds"]:
            visiter(p)
            bornes.append((res[p]["ef"] if typ == "FS" else res[p]["es"]) + J(lag))
        if t["dmin"]:
            bornes.append(t["dmin"])
        es = max(bornes) + J(dec.get(i, 0))
        d = dur.get(i, t["duree"])
        ef = es + J(d)
        if t["fmin"]:  # engagement de fin (inclusif) décalé avec la tâche
            ef = max(ef, t["fmin"] + J(1 + dec.get(i, 0)))
        res[i] = {"es": es, "ef": ef, "pilote": None}
        # prédécesseur qui fixe le début (pour tracer le chemin critique)
        for p, typ, lag in t["preds"]:
            if (res[p]["ef"] if typ == "FS" else res[p]["es"]) + J(lag) + J(dec.get(i, 0)) == es:
                res[i]["pilote"] = p
        en_cours.discard(i)
        ordre.append(i)

    for i in taches:
        visiter(i)
    fin_projet = max(r["ef"] for r in res.values())
    succ = {i: [] for i in taches}
    for i, t in taches.items():
        for p, typ, lag in t["preds"]:
            succ[p].append((i, typ, lag))
    for i in reversed(ordre):
        r = res[i]
        d = r["ef"] - r["es"]
        lf = fin_projet
        for s, typ, lag in succ[i]:
            ls_s = res[s]["ls"]
            lf = min(lf, ls_s - J(lag) if typ == "FS" else ls_s - J(lag) + d)
        r["lf"], r["ls"] = lf, lf - d
        r["marge"] = (lf - r["ef"]).days
    # chemin critique = remontée des pilotes depuis la livraison
    chemin, i = [], max(res, key=lambda k: res[k]["ef"])
    while i:
        chemin.append(i)
        i = res[i]["pilote"]
    return res, list(reversed(chemin))


def affiche(taches, i, r, res=None):
    """(début, fin) inclusifs. Un jalon prend la date de fin de la tâche qui le pilote."""
    from datetime import timedelta
    if r["ef"] > r["es"]:
        return r["es"].isoformat(), (r["ef"] - timedelta(days=1)).isoformat()
    p = r["pilote"]
    if res and p and any(q == p and typ == "FS" and lag == 0 for q, typ, lag in taches[i]["preds"]):
        j = affiche(taches, p, res[p], res)[1]
        return j, j
    return r["es"].isoformat(), r["es"].isoformat()


def simuler(scenario, decaler, duree, xlsx, xml):
    import json
    taches = charger_recalage()
    sc = json.loads(SCENARIOS.read_text(encoding="utf-8")) if SCENARIOS.exists() else {}
    if scenario == "tous":
        noms = list(sc)
    elif scenario:
        if scenario not in sc:
            sys.exit(f"Scénario inconnu : {scenario} (connus : {', '.join(sc)})")
        noms = [scenario]
    else:
        noms = [None]
    resultats = []
    for n in noms:
        s = sc.get(n, {}) if n else {}
        dec = dict(s.get("decaler", {})); dur = dict(s.get("duree", {}))
        for k, v in (x.split("=", 1) for x in decaler):
            dec[k] = dec.get(k, 0) + int(v)
        dur.update({k: int(v) for k, v in (x.split("=", 1) for x in duree)})
        titre = s.get("titre") or ("Base recalée" + (" + " + ", ".join(decaler + duree) if decaler or duree else ""))
        res, chemin = calculer(taches, dec, dur)
        resultats.append((n or "base", titre, res, chemin))
        print(f"\n== {titre}")
        for i, lib in JALONS:
            deb, fin = affiche(taches, i, res[i], res)
            print(f"  {lib:<28} {deb}" + (f" → {fin}" if fin != deb else ""))
        print("  Chemin critique : " + " → ".join(chemin))
    date_j = datetime.now().strftime("%Y-%m-%d")
    nom = "tous" if scenario == "tous" else (scenario or "base")
    if xlsx:
        exporter_xlsx(taches, resultats, SORTIE / f"{date_j}_simulation_{nom}.xlsx")
    if xml:
        for code, titre, res, _ in resultats:
            exporter_mspdi(taches, res, titre, SORTIE / f"{date_j}_simulation_{code}.xml")


def exporter_xlsx(taches, resultats, out):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    gras, rouge = Font(bold=True), PatternFill("solid", fgColor="F8CBAD")
    wb = Workbook(); ws = wb.active; ws.title = "Jalons"
    ws.append(["Scénario"] + [lib for _, lib in JALONS] + ["Fin livraison"])
    for _, titre, res, _ in resultats:
        ws.append([titre] + [affiche(taches, i, res[i], res)[0] for i, _ in JALONS] + [affiche(taches, "LIVR", res["LIVR"], res)[1]])
    for code, titre, res, chemin in resultats:
        w = wb.create_sheet(f"Tâches {code}"[:31])
        w.append([titre]); w["A1"].font = gras
        w.append(["Id", "Tâche", "Lot", "Début", "Fin", "Marge (j)", "Critique", "Fiabilité", "Source", "Hypothèse"])
        for i, t in sorted(taches.items(), key=lambda kv: res[kv[0]]["es"]):
            deb, fin = affiche(taches, i, res[i], res)
            w.append([i, t["nom"], t["lot"], deb, fin, res[i]["marge"], "oui" if i in chemin else "",
                      t["fiabilite"], t["source"], t["hypothese"]])
            if i in chemin:
                for c in w[w.max_row]:
                    c.fill = rouge
        w2 = wb.create_sheet(f"Chemin {code}"[:31])
        w2.append(["Ordre", "Id", "Tâche", "Début", "Fin", "Fiabilité"])
        for n, i in enumerate(chemin, 1):
            w2.append([n, i, taches[i]["nom"], *affiche(taches, i, res[i], res), taches[i]["fiabilite"]])
    for w in wb.worksheets:
        for col in w.columns:
            w.column_dimensions[col[0].column_letter].width = min(60, max(10, *(len(str(c.value or "")) for c in col)))
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"xlsx : {out}")


def exporter_mspdi(taches, res, titre, out):
    """MSPDI (XML MS Project) lisible par ProjectLibre. Calendrier 7j/7 = jours calendaires."""
    from xml.sax.saxutils import escape
    from datetime import timedelta
    ids = list(taches)
    uid = {i: n for n, i in enumerate(ids, 1)}
    debut = min(r["es"] for r in res.values())
    jours = "".join(f"<WeekDay><DayType>{k}</DayType><DayWorking>1</DayWorking><WorkingTimes>"
                    "<WorkingTime><FromTime>08:00:00</FromTime><ToTime>12:00:00</ToTime></WorkingTime>"
                    "<WorkingTime><FromTime>13:00:00</FromTime><ToTime>17:00:00</ToTime></WorkingTime>"
                    "</WorkingTimes></WeekDay>" for k in range(1, 8))
    lignes = []
    for n, i in enumerate(ids, 1):
        t, r = taches[i], res[i]
        d = (r["ef"] - r["es"]).days
        fin = (r["ef"] - timedelta(days=1)).isoformat() + "T17:00:00" if d else r["es"].isoformat() + "T08:00:00"
        liens = "".join(f"<PredecessorLink><PredecessorUID>{uid[p]}</PredecessorUID><Type>{1 if typ == 'FS' else 3}</Type>"
                        f"<LinkLag>{lag * 4800}</LinkLag><LagFormat>7</LagFormat></PredecessorLink>"
                        for p, typ, lag in t["preds"])
        note = escape(f"{i} | fiabilité : {t['fiabilite']} | source : {t['source']} | {t['hypothese']}")
        lignes.append(f"<Task><UID>{n}</UID><ID>{n}</ID><Name>{escape(t['nom'])}</Name><OutlineLevel>1</OutlineLevel>"
                      f"<Start>{r['es'].isoformat()}T08:00:00</Start><Finish>{fin}</Finish>"
                      f"<Duration>PT{d * 8}H0M0S</Duration><DurationFormat>7</DurationFormat>"
                      f"<Milestone>{0 if d else 1}</Milestone><Critical>{1 if r['marge'] <= 0 else 0}</Critical>"
                      f"<ConstraintType>4</ConstraintType><ConstraintDate>{r['es'].isoformat()}T08:00:00</ConstraintDate>"
                      f"<Notes>{note}</Notes>{liens}</Task>")
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Project xmlns="http://schemas.microsoft.com/project">'
           f"<Name>{escape(titre)}</Name><Title>{escape(titre)}</Title><ScheduleFromStart>1</ScheduleFromStart>"
           f"<StartDate>{debut.isoformat()}T08:00:00</StartDate><CalendarUID>1</CalendarUID>"
           "<MinutesPerDay>480</MinutesPerDay><MinutesPerWeek>3360</MinutesPerWeek><DaysPerMonth>30</DaysPerMonth>"
           f"<Calendars><Calendar><UID>1</UID><Name>Calendaire 7j/7</Name><IsBaseCalendar>1</IsBaseCalendar>"
           f"<WeekDays>{jours}</WeekDays></Calendar></Calendars><Tasks>" + "".join(lignes) + "</Tasks></Project>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml, encoding="utf-8")
    print(f"MSPDI : {out}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    s = a.add_subparsers(dest="cmd", required=True)
    s.add_parser("extraire").add_argument("mpp")
    l = s.add_parser("lot"); l.add_argument("mot"); l.add_argument("--xlsx", action="store_true")
    m = s.add_parser("simuler", help="recalcule la copie recalée avec des décalages")
    m.add_argument("--scenario", help="code dans scenarios.json, ou « tous »")
    m.add_argument("--decaler", action="append", default=[], help="ID=+N, lot:Nom=+N ou PREFIXE*=+N (jours)")
    m.add_argument("--duree", action="append", default=[], help="ID=N : nouvelle durée (jours)")
    m.add_argument("--xlsx", action="store_true"); m.add_argument("--xml", action="store_true")
    x = a.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if x.cmd == "extraire":
        extraire(x.mpp)
    elif x.cmd == "lot":
        lot(x.mot, x.xlsx)
    else:
        simuler(x.scenario, x.decaler, x.duree, x.xlsx, x.xml)
