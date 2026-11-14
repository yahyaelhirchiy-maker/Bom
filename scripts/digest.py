r"""Pré-digestion gratuite : écrit 03_TRAVAIL\_cache\digest.md (40 lignes max).

  python digest.py [--date AAAA-MM-JJ] [--projet TBRP]

Lit tbrp_state.json (source unique) et écrit : actions échues, dues sous 3 jours,
relances à faire, décisions MO dues sous 9 jours, chemin critique.
Les passages Claude lisent ce fichier au lieu des registres entiers. Aucun appel Claude.
"""
import argparse, json, re
from datetime import date, datetime, timedelta
from pathlib import Path

TRAVAIL = Path(r"D:\BK\03_TRAVAIL")
MAX = 40
RELANCE_APRES_J = 7  # une relance déjà faite il y a >= 7 jours, sans brouillon en attente
CRITIQUE = re.compile(r"verri[eè]re|menuiserie alu|murs? rideaux?|clos[- /]?couvert|\bGM\b", re.I)


def d(s):
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def court(t, n=70):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--projet", default="TBRP")
    a = ap.parse_args()
    auj = d(a.date) if a.date else date.today()
    base = TRAVAIL / "pilotage" / f"{a.projet.lower()}_state.json"
    etat = json.loads(base.read_text(encoding="utf-8"))
    pts = [p for p in etat["points_chantier"] if p.get("statut") != "Clos"]
    dec = [x for x in etat.get("decisions_mo", []) if x.get("statut") not in ("Prise", "Clos")]

    def ligne(p):
        return f"- {p['id']} {court(p['sujet'], 32)} ({court(p.get('responsable'), 18)}) : {court(p['action'], 60)}"

    echues, sous3, relances, critique = [], [], [], []
    for p in pts:
        e = d(p.get("echeance") or "")
        if e and e < auj:
            echues.append((e, f"{ligne(p)} [éch. {e:%d/%m}]"))
        elif e and e <= auj + timedelta(days=3):
            sous3.append((e, f"{ligne(p)} [éch. {e:%d/%m}]"))
        rel = p.get("relances") or []
        brouillon = [r for r in rel if "brouillon" in str(r.get("statut", ""))]
        faites = [d(r["date"]) for r in rel if "brouillon" not in str(r.get("statut", "")) and d(r.get("date", ""))]
        if brouillon:
            relances.append((auj, f"- {p['id']} {court(p['sujet'], 32)} : brouillon à envoyer par Yahya"))
        elif p.get("statut") == "Retard" and faites and (auj - max(faites)).days >= RELANCE_APRES_J:
            relances.append((max(faites), f"- {p['id']} {court(p['sujet'], 32)} ({court(p.get('responsable'), 18)}) : à relancer (dernière {max(faites):%d/%m})"))
        if CRITIQUE.search(" ".join([p["sujet"], p.get("section", ""), p.get("responsable") or ""])):
            critique.append(f"- {ligne(p)[2:]} [{p.get('statut')}{', éch. ' + p['echeance'][5:] if p.get('echeance') else ''}]")
    decs = []
    for x in dec:
        e = d(x.get("echeance") or "")
        if e and e <= auj + timedelta(days=9):
            decs.append((e, f"- {x['id']} {court(x['lot'], 36)} : {court(x['decision'], 60)} [{'dépassée ' if e < auj else ''}{e:%d/%m}]"))
    for x in dec:
        if CRITIQUE.search(x["lot"]):
            critique.append(f"- {x['id']} {court(x['lot'], 36)} : décision {x['statut']} [éch. {(x.get('echeance') or '?')[5:]}]")

    def bloc(titre, items, n):
        items = [t for _, t in sorted(items, key=lambda z: z[0])] if items and isinstance(items[0], tuple) else items
        out = [f"## {titre} ({len(items)})"] + (items[:n] or ["- rien"])
        if len(items) > n:
            out.append(f"- … +{len(items) - n} autres (voir tbrp_state.json)")
        return out

    L = [f"# Digest {a.projet} — {auj} (maj état {etat.get('maj_le')}, réunion {etat.get('prochaine_reunion', '')[:10]})"]
    # budgets de lignes : total <= 40
    L += bloc("Chemin critique (clos couvert)", critique, 7)
    L += bloc("Actions échues", echues, 8)
    L += bloc("Dues sous 3 jours", sous3, 4)
    L += bloc("Relances / brouillons", relances, 5)
    L += bloc("Décisions MO dues sous 9 jours", decs, 8)
    (TRAVAIL / "_cache").mkdir(exist_ok=True)
    texte = "\n".join(L[:MAX]) + "\n"
    (TRAVAIL / "_cache" / "digest.md").write_text(texte, encoding="utf-8")
    print(texte)
    print(f"[{len(L[:MAX])} lignes]")


if __name__ == "__main__":
    main()
