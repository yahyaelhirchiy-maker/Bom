#!/usr/bin/env python
"""Second cerveau - jour 5 : dossier compact des passages + contrôle de santé.

Usage :
  dossier.py [--projet TBRP] [--sans-memoire] [--marquer]

Python seul, zéro token, aucune écriture hors 03_TRAVAIL\\_cache.
1. relance memoire.py (sauf --sans-memoire) pour avoir l'état des lots du jour ;
2. compare avec la photo du dernier dossier (_cache\\dossier_prev.json) : ce qui a changé
   depuis le dernier passage (points P, nouveaux documents par lot, nouveaux trous) ;
3. marque les URGENCES (chemin critique : échéance dépassée, trou possible, décision D due,
   santé en panne) : elles sont lues au passage suivant, aucun réveil immédiat ;
4. contrôle de santé : disque D:, Outlook, OneDrive/miroir, Ollama, scripts (compilation),
   passages précédents, fraîcheur du digest/index/mémoire ;
5. écrit _cache\\dossier.md (60 lignes max), lu par les passages à côté de digest.md.
--marquer : enregistre la photo du jour (à faire une seule fois par passage, en dernier).
"""
import argparse, json, py_compile, shutil, subprocess, sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SCRIPTS = Path(__file__).resolve().parent
TRAVAIL = Path(r"D:\BK\03_TRAVAIL")
CACHE = TRAVAIL / "_cache"
MIROIR = Path(r"D:\BK\01_MIROIR")
MAX = 60


def d(s):
    try:
        return datetime.strptime((s or "")[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def court(t, n=90):
    t = " ".join((t or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


def age_j(p):
    try:
        return (datetime.now() - datetime.fromtimestamp(Path(p).stat().st_mtime)).total_seconds() / 86400
    except Exception:
        return None


def processus(nom):
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {nom}"], capture_output=True, text=True,
                             errors="replace", timeout=20).stdout
        return nom.lower() in out.lower()
    except Exception:
        return None


def sante(auj):
    """Liste de (niveau, texte). niveau : OK | ALERTE."""
    r = []
    try:
        libre = shutil.disk_usage("D:\\").free / 1e9
        r.append(("OK" if libre >= 10 else "ALERTE", f"Disque D: {libre:.0f} Go libres"))
    except Exception:
        r.append(("ALERTE", "Disque D: illisible"))
    for nom, label in (("OUTLOOK.EXE", "Outlook classique"), ("OneDrive.exe", "OneDrive")):
        p = processus(nom)
        r.append(("OK" if p else "ALERTE", f"{label} {'ouvert' if p else 'ne tourne pas' if p is False else 'non vérifiable'}"))
    try:
        recents = sorted((q.stat().st_mtime for q in (MIROIR / "OneDrive - AEDGE Partners").rglob("*.*") if q.is_file()),
                         reverse=True)[:1]
        a = (datetime.now().timestamp() - recents[0]) / 86400 if recents else None
        r.append(("OK" if a is not None and a < 10 else "ALERTE",
                  f"Miroir SharePoint : fichier le plus récent il y a {a:.0f} j" if a is not None else "Miroir SharePoint vide"))
    except Exception:
        r.append(("ALERTE", "Miroir SharePoint illisible"))
    r.append(("OK", "Ollama " + ("ouvert" if processus("ollama.exe") else "fermé (normal si rien ne tourne)")))
    mauvais = []
    for s in sorted(SCRIPTS.glob("*.py")):
        try:
            py_compile.compile(str(s), cfile=str(CACHE / "_compile.pyc"), doraise=True)
        except Exception:
            mauvais.append(s.name)
    r.append(("ALERTE" if mauvais else "OK", f"Scripts : {'erreur dans ' + ', '.join(mauvais) if mauvais else 'tous compilent'}"))
    manques = []
    for jr in (1, 2, 3):
        j = auj - timedelta(days=jr)
        if j.weekday() >= 5:
            continue
        for ps in ("matin", "apres-midi"):
            if (CACHE / f"passage_{ps}_{j:%Y-%m-%d}.debut").exists() and not (CACHE / f"passage_{ps}_{j:%Y-%m-%d}.ok").exists():
                manques.append(f"{ps} {j:%d/%m}")
    r.append(("ALERTE" if manques else "OK", f"Passages : {'commencés sans fin : ' + ', '.join(manques) if manques else 'aucun passage resté ouvert (3 derniers jours)'}"))
    for nom, chemin, max_j in (("Digest", CACHE / "digest.md", 2), ("Index cerveau", CACHE / "cerveau.db", 3),
                               ("Mémoire des lots", TRAVAIL / "analyses" / "memoire" / "memoire.json", 2)):
        a = age_j(chemin)
        r.append(("ALERTE" if a is None or a > max_j else "OK",
                  f"{nom} : {'absent' if a is None else f'mis à jour il y a {a:.1f} j'}"))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projet", default="TBRP")
    ap.add_argument("--sans-memoire", action="store_true")
    ap.add_argument("--marquer", action="store_true")
    a = ap.parse_args()
    auj = date.today()
    if not a.sans_memoire:
        subprocess.run([sys.executable, str(SCRIPTS / "memoire.py"), "--projet", a.projet], capture_output=True, timeout=600)
    mem = json.loads((TRAVAIL / "analyses" / "memoire" / "memoire.json").read_text(encoding="utf-8"))
    etat = json.loads((TRAVAIL / "pilotage" / f"{a.projet.lower()}_state.json").read_text(encoding="utf-8"))
    prev_f = CACHE / "dossier_prev.json"
    prev = json.loads(prev_f.read_text(encoding="utf-8")) if prev_f.exists() else {}

    # photo du jour
    pts = {p["id"]: p for p in etat["points_chantier"]}
    photo = {"date": f"{auj:%Y-%m-%d}",
             "points": {i: [p.get("statut"), p.get("echeance"), p.get("maj_le") or ""] for i, p in pts.items()},
             "docs": {k: v.get("dernier_document") or "" for k, v in mem["lots"].items()},
             "trous": sorted(t for v in mem["lots"].values() for t in v.get("trous", []))}

    # 1. changements
    ch = []
    pp = prev.get("points", {})
    for i, v in photo["points"].items():
        if i not in pp:
            ch.append(f"- Nouveau point {i} {court(pts[i]['sujet'], 50)} ({v[0]})") if prev else None
        elif pp[i][:2] != v[:2]:
            ch.append(f"- {i} {court(pts[i]['sujet'], 40)} : {pp[i][0]}/{pp[i][1]} → {v[0]}/{v[1]}")
        elif pp[i][2] != v[2]:
            ch.append(f"- {i} {court(pts[i]['sujet'], 40)} : mis à jour le {v[2]}")
    for i in pp:
        if i not in photo["points"]:
            ch.append(f"- {i} n'est plus dans l'état")
    for k, dd in photo["docs"].items():
        if dd and dd != prev.get("docs", {}).get(k, dd):
            ch.append(f"- {k} ({mem['lots'][k]['intitule'][:34]}) : nouveau document du {dd}")
    photo["trous"] = sorted(set(photo["trous"]))
    nouveaux_trous = [t for t in photo["trous"] if t not in prev.get("trous", [])] if prev else []

    # 2. urgences
    decs = {x["id"]: x for x in etat.get("decisions_mo", [])}
    urg = []
    for k, v in mem["lots"].items():
        if not v.get("chemin_critique"):
            continue
        for p in v.get("points", []):
            e = d(p.get("echeance"))
            if e and e < auj and not p.get("interne") and (auj - e).days >= 1:
                urg.append(f"- {k} {p['id']} {court(p['sujet'], 40)} ({court(p.get('responsable'), 16)}) : échéance dépassée de {(auj - e).days} j")
        for dec in v.get("decisions", []):
            e = d(decs.get(dec.get("id"), {}).get("echeance"))
            if e and e <= auj + timedelta(days=3):
                urg.append(f"- {k} décision {dec.get('id', '')} {court(dec.get('decision'), 40)} : à décider avant le {e:%d/%m}")
        for t in v.get("trous", []):
            urg.append(f"- {k} trou possible : {court(t, 110)}")
    sa = sante(auj)
    for niv, tx in sa:
        if niv == "ALERTE":
            urg.append(f"- SANTÉ : {tx}")

    L = [f"# Dossier compact — {auj:%d/%m/%Y} {datetime.now():%H:%M}",
         f"_Python seul, aucun réveil. Lu par les passages à côté de digest.md. Mémoire des lots du {mem.get('date')}._", ""]
    L.append(f"## Urgences ({len(urg)}) — à traiter à ce passage, pas de réveil entre deux")
    L += (urg[:14] + ([f"- … +{len(urg) - 14} autres"] if len(urg) > 14 else [])) if urg else ["- aucune"]
    L += ["", f"## Changements depuis le dossier du {prev.get('date', '(premier dossier)')} ({len(ch)})"]
    L += (ch[:16] + ([f"- … +{len(ch) - 16} autres"] if len(ch) > 16 else [])) if ch else ["- aucun changement détecté"]
    if nouveaux_trous:
        L += ["", f"## Nouveaux trous possibles ({len(nouveaux_trous)})"] + [f"- {court(t, 120)}" for t in nouveaux_trous[:6]]
    L += ["", "## Santé"] + [f"- {'⚠ ' if n == 'ALERTE' else ''}{t}" for n, t in sa]
    L += ["", "_Questions pour Yahya, jamais des décisions : un trou possible est à vérifier, pas un constat._"]
    (CACHE / "dossier.md").write_text("\n".join(L[:MAX]) + "\n", encoding="utf-8")
    if a.marquer:
        prev_f.write_text(json.dumps(photo, ensure_ascii=False), encoding="utf-8")
    print(f"dossier.md : {len(urg)} urgence(s), {len(ch)} changement(s), {sum(1 for n, _ in sa if n == 'ALERTE')} alerte(s) santé")


if __name__ == "__main__":
    main()
