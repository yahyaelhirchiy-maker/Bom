#!/usr/bin/env python
"""Second cerveau - jour 1 : index plein texte local (SQLite FTS5).

Usage :
  cerveau.py indexer            # incremental : nouveaux/modifies, retire les disparus
  cerveau.py chercher "mots" [-n 5] [--chemin mot]   # extraits courts + source
  cerveau.py stats

Lit seulement 03_TRAVAIL/_texte/ (jamais les originaux). Ecrit seulement
03_TRAVAIL/_cache/cerveau.db. Zero token : tout est local.
"""
import argparse, os, re, sqlite3, sys, time

RACINE = r"D:\BK"
TEXTE = os.path.join(RACINE, "03_TRAVAIL", "_texte")
DB = os.path.join(RACINE, "03_TRAVAIL", "_cache", "cerveau.db")
TAILLE = 1200   # caracteres par passage
CHEV = 150      # chevauchement

sys.stdout.reconfigure(encoding="utf-8")


def connexion():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE IF NOT EXISTS docs(id INTEGER PRIMARY KEY, chemin TEXT UNIQUE, source TEXT, mtime REAL, taille INTEGER)")
    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5("
              "texte, doc UNINDEXED, tokenize='unicode61 remove_diacritics 2')")
    return c


def decouper(t):
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"(;\s*){3,}", "; ", t)       # cellules vides des tableurs
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    i, out = 0, []
    while i < len(t):
        j = min(len(t), i + TAILLE)
        if j < len(t):
            k = t.rfind("\n", i + TAILLE // 2, j)
            if k > 0:
                j = k
        out.append(t[i:j].strip())
        if j >= len(t):
            break
        i = max(j - CHEV, i + 1)
    return [p for p in out if p]


def indexer(_):
    c = connexion()
    t0 = time.time()
    connus = {r[1]: (r[0], r[2]) for r in c.execute("SELECT id, chemin, mtime FROM docs")}
    vus, nouveaux, maj = set(), 0, 0
    for dossier, _, fichiers in os.walk(TEXTE):
        for f in fichiers:
            if not f.endswith(".txt"):
                continue
            p = os.path.join(dossier, f)
            rel = os.path.relpath(p, TEXTE)
            vus.add(rel)
            mt = os.path.getmtime(p)
            if rel in connus and abs(connus[rel][1] - mt) < 1:
                continue
            with open(p, encoding="utf-8", errors="replace") as fh:
                contenu = fh.read()
            source = rel
            if contenu.startswith("SOURCE:"):
                source = contenu.split("\n", 1)[0][7:].strip()
            if rel in connus:
                did = connus[rel][0]
                c.execute("DELETE FROM passages WHERE doc=?", (did,))
                c.execute("UPDATE docs SET source=?, mtime=?, taille=? WHERE id=?", (source, mt, len(contenu), did))
                maj += 1
            else:
                did = c.execute("INSERT INTO docs(chemin, source, mtime, taille) VALUES(?,?,?,?)",
                                (rel, source, mt, len(contenu))).lastrowid
                nouveaux += 1
            c.executemany("INSERT INTO passages(texte, doc) VALUES(?,?)",
                          [(x, did) for x in decouper(contenu)])
            if (nouveaux + maj) % 500 == 0:
                c.commit()
    disparus = [(v[0],) for k, v in connus.items() if k not in vus]
    for (did,) in disparus:
        c.execute("DELETE FROM passages WHERE doc=?", (did,))
        c.execute("DELETE FROM docs WHERE id=?", (did,))
    c.commit()
    print(f"Index : {nouveaux} nouveaux, {maj} mis a jour, {len(disparus)} retires, "
          f"{len(vus)} documents ({time.time()-t0:.0f}s)")


def requete(q):
    mots = [m for m in re.findall(r"\w+", q.lower()) if len(m) > 1]
    return mots


def chercher(a):
    c = connexion()
    mots = requete(a.q)
    if not mots:
        print("Requete vide.")
        return
    for op in (" AND ", " OR "):
        m = op.join(f'"{w}"*' for w in mots)
        filtre = ""
        args = [m]
        if a.chemin:
            filtre = " AND d.source LIKE ?"
            args.append(f"%{a.chemin}%")
        args.append(a.n)
        lignes = c.execute(
            "SELECT d.source, snippet(passages, 0, '[', ']', ' ... ', 40) "
            "FROM passages JOIN docs d ON d.id = passages.doc "
            f"WHERE passages MATCH ?{filtre} ORDER BY bm25(passages) LIMIT ?", args).fetchall()
        if lignes:
            break
    if not lignes:
        print("Aucun resultat.")
        return
    vus = set()
    for src, ext in lignes:
        marque = "" if src not in vus else " (suite)"
        vus.add(src)
        src = src.split("\\038\\", 1)[-1]   # chemin court (le prefixe est connu)
        ext = re.sub(r"\s+", " ", ext)[:380]
        print(f"- {src}{marque}\n    {ext}")


def stats(_):
    c = connexion()
    d = c.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    p = c.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
    print(f"{d} documents, {p} passages, base {os.path.getsize(DB)/1e6:.0f} Mo")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("indexer").set_defaults(f=indexer)
    s = sp.add_parser("chercher")
    s.add_argument("q")
    s.add_argument("-n", type=int, default=5)
    s.add_argument("--chemin", default="")
    s.set_defaults(f=chercher)
    sp.add_parser("stats").set_defaults(f=stats)
    a = ap.parse_args()
    a.f(a)
