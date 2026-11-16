"""Résumé compact de la consommation Claude des N derniers jours (pour le rapport d'optimisation du dimanche).

Lit les journaux de session de Claude Code (~/.claude/projects/*/*.jsonl) sans les afficher :
par session, tokens (entrée, cache, sortie), nombre d'appels d'outils par type, captures d'écran,
gros résultats d'outils. Sortie : un tableau texte court, à lire à la place des journaux.

Usage : python D:/BK/00_SYSTEME/scripts/audit_semaine.py [--jours 7]
"""
import argparse, collections, datetime as dt, glob, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = argparse.ArgumentParser()
p.add_argument("--jours", type=int, default=7)
a = p.parse_args()
depuis = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.jours)

def nom_outil(n):
    n = n.replace("mcp__", "")
    return n[:40]

sessions = []
tot_outils = collections.Counter()
for chemin in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
    if dt.datetime.fromtimestamp(os.path.getmtime(chemin), dt.timezone.utc) < depuis:
        continue
    s = dict(fichier=os.path.basename(chemin)[:8], projet=os.path.basename(os.path.dirname(chemin))[:20],
             titre="", debut=None, tours=0, entree=0, cache_lu=0, cache_ecrit=0, sortie=0,
             outils=collections.Counter(), images=0, gros=0)
    with open(chemin, encoding="utf-8", errors="ignore") as f:
        for ligne in f:
            try:
                j = json.loads(ligne)
            except Exception:
                continue
            ts = j.get("timestamp")
            if ts:
                try:
                    t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    t = None
                if t and t < depuis:
                    continue
                if t and not s["debut"]:
                    s["debut"] = t
            if j.get("type") == "summary" and j.get("summary"):
                s["titre"] = j["summary"][:50]
            m = j.get("message") or {}
            contenu = m.get("content") if isinstance(m.get("content"), list) else []
            if j.get("type") == "user" and isinstance(m.get("content"), str) and not s["titre"]:
                s["titre"] = m["content"][:50].replace("\n", " ")
            if j.get("type") == "assistant":
                u = m.get("usage") or {}
                s["tours"] += 1
                s["entree"] += u.get("input_tokens") or 0
                s["cache_lu"] += u.get("cache_read_input_tokens") or 0
                s["cache_ecrit"] += u.get("cache_creation_input_tokens") or 0
                s["sortie"] += u.get("output_tokens") or 0
                for c in contenu:
                    if c.get("type") == "tool_use":
                        n = nom_outil(c.get("name", "?"))
                        s["outils"][n] += 1
                        tot_outils[n] += 1
            if j.get("type") == "user":
                for c in contenu:
                    if c.get("type") != "tool_result":
                        continue
                    r = c.get("content")
                    parts = r if isinstance(r, list) else [{"type": "text", "text": r or ""}]
                    for x in parts:
                        if isinstance(x, dict) and x.get("type") == "image":
                            s["images"] += 1
                        elif isinstance(x, dict) and len(str(x.get("text", ""))) > 20000:
                            s["gros"] += 1
    if s["tours"]:
        sessions.append(s)

k = lambda n: f"{n/1000:.0f}k"
sessions.sort(key=lambda s: s["cache_lu"] + s["cache_ecrit"] + s["entree"], reverse=True)
print(f"Sessions des {a.jours} derniers jours : {len(sessions)}")
print("debut | titre | tours | entrée | cache lu | cache écrit | sortie | images | gros résultats | outils principaux")
for s in sessions[:25]:
    d = s["debut"].astimezone().strftime("%d/%m %H:%M") if s["debut"] else "?"
    top = ", ".join(f"{n}×{c}" for n, c in s["outils"].most_common(5))
    print(f"{d} | {s['titre']} | {s['tours']} | {k(s['entree'])} | {k(s['cache_lu'])} | {k(s['cache_ecrit'])} | {k(s['sortie'])} | {s['images']} | {s['gros']} | {top}")
T = lambda c: sum(s[c] for s in sessions)
print(f"\nTOTAL : entrée {k(T('entree'))}, cache lu {k(T('cache_lu'))}, cache écrit {k(T('cache_ecrit'))}, sortie {k(T('sortie'))}, images {T('images')}, gros résultats {T('gros')}")
print("Outils les plus appelés : " + ", ".join(f"{n}×{c}" for n, c in tot_outils.most_common(15)))
