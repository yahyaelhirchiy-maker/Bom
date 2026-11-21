r"""Mesure le coût réel de chaque passage planifié, depuis les transcriptions de Claude Code. Gratuit.

  python conso_passages.py            # ajoute à consommation.csv les passages terminés pas encore notés
  python conso_passages.py --resume   # moyenne par passage (derniers 14 jours)

Passage reconnu à la balise <scheduled-task name="..."> du début : matin, apres-midi, rattrapage, sharepoint, optimisation, etc.
Colonnes de consommation.csv : date;tache;modele;voie;entree;cache_lu;cache_ecrit;sortie;cout_usd
(voie = « appli » ; coût = équivalent au tarif API, estimé : barème ci-dessous à ajuster).
Lancé par le dernier geste de chaque passage ; aucune IA. Session encore active (< 10 min) : ignorée.
"""
import csv, glob, json, os, sys, time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

PROJETS = Path.home() / ".claude" / "projects"
CSV = Path(r"D:\BK\03_TRAVAIL\logs\consommation.csv")
VUS = Path(r"D:\BK\03_TRAVAIL\logs\.passages_notes.txt")
# $ par million de tokens : entrée, cache lu, cache écrit, sortie
BAREME = {"opus": (5, 0.5, 6.25, 25), "sonnet": (3, 0.3, 3.75, 15), "haiku": (1, 0.1, 1.25, 5), "fable": (5, 0.5, 6.25, 25)}
import re
ALIAS = {"bosko-mails": "matin", "bosko-apres-midi": "apres-midi", "bosko-apres-midi-auto": "apres-midi"}  # sinon : nom de la tâche sans « bosko- »


def famille(m):
    m = (m or "").lower()
    return next((k for k in BAREME if k in m), "sonnet")


def lire(f):
    tache, msgs, t0 = None, {}, None
    for l in open(f, encoding="utf-8", errors="replace"):
        try:
            j = json.loads(l)
        except ValueError:
            continue
        if j.get("timestamp") and not t0:
            t0 = j["timestamp"]
        if tache is None and j.get("type") in ("user", "queue-operation"):
            c = j.get("content") if j.get("type") == "queue-operation" else j["message"].get("content")
            c = c if isinstance(c, str) else " ".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
            if j.get("type") == "user" or c:
                mt = re.match(r'\s*<scheduled-task name="([^"]+)"', c or "")
                tache = (ALIAS.get(mt.group(1)) or mt.group(1).replace("bosko-", "")) if mt else ("" if j.get("type") == "user" else None)
        m = j.get("message") or {}
        if j.get("type") == "assistant" and m.get("usage"):
            msgs[m.get("id") or j.get("uuid")] = (m.get("model"), m["usage"])  # dernier état de chaque message
    return tache, t0, msgs


def main():
    if "--resume" in sys.argv:
        S, lim = defaultdict(lambda: [0, 0.0, 0, 0]), (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        for r in csv.DictReader(open(CSV, encoding="utf-8-sig"), delimiter=";"):
            if r["voie"] == "appli" and r["date"] >= lim:
                s = S[r["tache"]]
                s[0] += 1; s[1] += float(r["cout_usd"].replace(",", ".")); s[2] += int(r["cache_lu"]); s[3] += int(r["entree"]) + int(r["sortie"])
        for t, (n, c, cl, io) in sorted(S.items()):
            print(f"{t:12} {n:3} passages  moy. {c / n:5.2f} $  cache lu {cl / n / 1e6:5.2f} M  entrée+sortie {io // n:,} tokens".replace(",", " "))
        return
    vus = set(VUS.read_text().split()) if VUS.exists() else set()
    new = not CSV.exists()
    lignes = []
    for f in glob.glob(str(PROJETS / "D--BK*" / "*.jsonl")):
        sid = Path(f).stem
        if sid in vus or time.time() - os.path.getmtime(f) < 600:
            continue
        tache, t0, msgs = lire(f)
        if tache is None:
            continue
        vus.add(sid)  # session non-passage : on ne la relit plus
        if not tache or not msgs:
            continue
        tot, cout = defaultdict(int), 0.0
        for mod, u in msgs.values():
            a, b, c, d = (u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens"))
            tot["e"] += a; tot["l"] += b; tot["w"] += c; tot["s"] += d
            p = BAREME[famille(mod)]
            cout += (a * p[0] + b * p[1] + c * p[2] + d * p[3]) / 1e6
        mod = famille(next(iter(msgs.values()))[0])
        d = datetime.fromisoformat(t0.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
        lignes.append([d, tache, mod, "appli", tot["e"], tot["l"], tot["w"], tot["s"], f"{cout:.4f}".replace(".", ",")])
    CSV.parent.mkdir(exist_ok=True)
    with open(CSV, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        if new:
            w.writerow("date;tache;modele;voie;entree;cache_lu;cache_ecrit;sortie;cout_usd".split(";"))
        w.writerows(sorted(lignes))
    VUS.write_text("\n".join(sorted(vus)))
    print(f"{len(lignes)} passage(s) ajouté(s) à consommation.csv")


if __name__ == "__main__":
    main()
