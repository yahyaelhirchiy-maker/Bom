#!/usr/bin/env python
"""Second cerveau - jour 1 : index plein texte local (SQLite FTS5).

Usage :
  cerveau.py indexer            # incremental : nouveaux/modifies, retire les disparus
  cerveau.py chercher "mots" [-n 5] [--chemin mot]   # extraits courts + source
  cerveau.py stats
  cerveau.py sources [--jours 90] [--sans-mails]   # mails Outlook, tbrp_state.json, planning -> _texte, puis indexer
  cerveau.py ajouter <fichier...>    # fichier depose sur SharePoint : conversion texte + indexation

Lit seulement 03_TRAVAIL/_texte/ (jamais les originaux). Ecrit seulement
03_TRAVAIL/_cache/cerveau.db et, pour `sources`/`ajouter`, des .txt dans _texte/.
Zero token : tout est local.
"""
import argparse, csv, hashlib, json, os, re, sqlite3, sys, time
from datetime import datetime, timedelta

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


TRAVAIL = os.path.join(RACINE, "03_TRAVAIL")
ETAT = os.path.join(TRAVAIL, "pilotage", "tbrp_state.json")
TACHES = os.path.join(TRAVAIL, "planning", "taches.csv")
MIROIR_038 = os.path.join(RACINE, "01_MIROIR", "OneDrive - AEDGE Partners", "038")


def ecrire(chemin, source, texte):
    """N'ecrit que si le contenu change (sinon l'index ne bouge pas)."""
    contenu = f"SOURCE: {source}\n\n{texte}"
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as fh:
            if fh.read() == contenu:
                return 0
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as fh:
        fh.write(contenu)
    return 1


def a_plat(v, retrait=""):
    if isinstance(v, dict):
        return "\n".join(f"{retrait}{k} : {a_plat(x, retrait + '  ').lstrip()}" for k, x in v.items()
                         if x not in (None, "", [], {}))
    if isinstance(v, list):
        return "\n" + "\n".join(f"{retrait}- {a_plat(x, retrait + '  ').lstrip()}" for x in v)
    return str(v)


def source_etat():
    """tbrp_state.json : un .txt par point P, decision D et rubrique (historique compris)."""
    with open(ETAT, encoding="utf-8") as fh:
        d = json.load(fh)
    sortie = os.path.join(TEXTE, "_pilotage")
    n = 0
    for cle, val in d.items():
        if isinstance(val, list) and val and all(isinstance(x, dict) and x.get("id") for x in val):
            for x in val:
                titre = f"{x['id']} - {x.get('sujet') or x.get('lot') or ''}"
                n += ecrire(os.path.join(sortie, f"{x['id']}.txt"), f"tbrp_state.json#{x['id']}",
                            f"{titre}\n{a_plat(x)}")
        else:
            n += ecrire(os.path.join(sortie, f"_{cle}.txt"), f"tbrp_state.json#{cle}", f"{cle}\n{a_plat(val)}")
    return n


def source_planning():
    """planning/taches.csv (extrait du .mpp) : un .txt par bloc de 40 taches, lisible."""
    with open(TACHES, encoding="utf-8-sig") as fh:
        lignes = list(csv.DictReader(fh, delimiter=";"))
    src = lignes[0]["source"] if lignes else TACHES
    sortie = os.path.join(TEXTE, "_planning")
    n = 0
    for i in range(0, len(lignes), 40):
        txt = []
        for t in lignes[i:i + 40]:
            crit = " | CRITIQUE" if (t.get("critique") or "").strip().lower() in ("1", "oui", "true", "vrai") else ""
            txt.append(f"{t['id']}. {t['chemin'].strip()} > {t['nom']} : {t['debut']} -> {t['fin']}"
                       f" | marge {t['marge_j']} j | avancement {t['avancement']}{crit}"
                       + (f" | {t['ressources']}" if t.get("ressources") else ""))
        n += ecrire(os.path.join(sortie, f"taches_{i // 40 + 1:02d}.txt"), src, "Planning (taches)\n" + "\n".join(txt))
    return n


def source_mails(jours):
    """Mails Outlook (recus + envoyes) des N derniers jours : un .txt par mail, historique coupe."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import outlook  # win32com : seulement si Outlook est utilise
    sortie = os.path.join(TEXTE, "_mails")
    depuis = datetime.now() - timedelta(days=jours)
    n = vus = 0
    for dossier, champ in ((6, "ReceivedTime"), (5, "SentOn")):
        items = outlook.ns().GetDefaultFolder(dossier).Items
        items.Sort(f"[{champ}]", True)
        for m in items:
            try:
                if m.Class != 43:
                    continue
                quand = getattr(m, champ).replace(tzinfo=None)
                if quand < depuis:
                    break
                cle = hashlib.sha1(m.EntryID.encode()).hexdigest()[:12]
                chemin = os.path.join(sortie, f"{quand:%Y-%m}", f"{quand:%Y-%m-%d_%H%M}_{cle}.txt")
                vus += 1
                if os.path.exists(chemin):
                    continue  # un mail ne change pas
                sens = "RECU" if dossier == 6 else "ENVOYE"
                pj = "; ".join(a.FileName for a in m.Attachments)
                entete = (f"MAIL {sens} {quand:%Y-%m-%d %H:%M}\nDE : {m.SenderName} <{outlook.expediteur(m)}>\n"
                          f"A : {m.To}\nCC : {m.CC}\nOBJET : {m.Subject}" + (f"\nPJ : {pj}" if pj else ""))
                n += ecrire(chemin, f"Outlook : {quand:%Y-%m-%d} {m.SenderName} - {m.Subject}",
                            entete + "\n\n" + outlook.couper_historique(m.Body or ""))
            except Exception as e:  # un element illisible ne bloque pas les autres
                print(f"Mail ignore : {e}")
    return n, vus


def sources(a):
    n = source_etat()
    print(f"tbrp_state.json : {n} fichier(s) mis a jour")
    n = source_planning()
    print(f"Planning : {n} fichier(s) mis a jour")
    if not a.sans_mails:
        try:
            n, vus = source_mails(a.jours)
            print(f"Mails : {n} nouveau(x) sur {vus} ({a.jours} j)")
        except Exception as e:
            print(f"Mails non lus (Outlook ferme ?) : {e}")
    indexer(a)


def ajouter(a):
    """Apres un depot SharePoint : convertit les fichiers deposes (sous 038) et met l'index a jour."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from convertir_texte import LECTEURS
    for f in a.fichiers:
        lecteur = LECTEURS.get(os.path.splitext(f)[1].lower())
        if not lecteur:
            continue
        try:
            rel = os.path.relpath(f, MIROIR_038)
            if rel.startswith(".."):
                continue
            ecrire(os.path.join(TEXTE, "038", rel + ".txt"), f, lecteur(f))
        except Exception as e:
            print(f"Conversion impossible {f} : {e}")
    indexer(a)


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
    s = sp.add_parser("sources")
    s.add_argument("--jours", type=int, default=90)
    s.add_argument("--sans-mails", action="store_true")
    s.set_defaults(f=sources)
    s = sp.add_parser("ajouter")
    s.add_argument("fichiers", nargs="+")
    s.set_defaults(f=ajouter)
    a = ap.parse_args()
    a.f(a)
