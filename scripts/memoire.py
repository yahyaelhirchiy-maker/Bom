#!/usr/bin/env python
"""Second cerveau - jour 4 : mémoire par lot, entreprise et BET.

Usage :
  memoire.py [--projet TBRP] [--aujourdhui AAAA-MM-JJ]

Lit (sans rien modifier) : pilotage/<projet>_state.json (points P, décisions D),
registres/lots.csv, analyses/faits/faits.csv + autres_lots.csv (faits Qwen contrôlés),
_cache/cerveau.db (dernier document connu par lot).
Écrit dans 03_TRAVAIL/analyses/memoire/ :
  etat_lots.md      état vivant : lots pilotes (verrière, alu) en détail, puis autres lots, puis BET
  memoire.json      même contenu, pour les passages et le dossier compact (jour 5)
  faits_uniques.csv faits dédoublonnés (copies d'un CR à l'autre fusionnées, le plus récent gardé)
                    et date_fait corrigée (retirée quand elle n'est que la date du document).
Python seul, zéro token, rien n'est décidé : les « trous possibles » sont des questions pour Yahya.
"""
import argparse, csv, json, re, sqlite3, sys, unicodedata
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SCRIPTS = Path(__file__).resolve().parent
OUVERT_EXCLU = {"clos", "soldé", "solde", "fait"}
MOIS = {"janv": 1, "févr": 2, "fevr": 2, "mars": 3, "avr": 4, "mai": 5, "juin": 6, "juil": 7,
        "août": 8, "aout": 8, "sept": 9, "oct": 10, "nov": 11, "déc": 12, "dec": 12}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/]+", " ", s)).strip()


def d_iso(s):
    try:
        return date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


def jjmm(d):
    return d.strftime("%d/%m") if d else "?"


# ---------- faits : doublons et date_fait ----------
def date_ecrite(texte, ref):
    """Première date écrite dans le texte (JJ/MM[/AA[AA]] ou JJ mois), année déduite du document."""
    t = texte or ""
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        return d_iso(m.group(0))
    m = re.search(r"\b([0-3]?\d)[/.]([01]?\d)(?:[/.](\d{2,4}))?\b", t)
    j = mo = an = None
    if m:
        j, mo = int(m.group(1)), int(m.group(2))
        an = int(m.group(3)) if m.group(3) else None
    else:
        m = re.search(r"\b([0-3]?\d)(?:er)?\s+(" + "|".join(MOIS) + r")\w*\.?(?:\s+(\d{4}))?", t, re.I)
        if m:
            j, mo = int(m.group(1)), MOIS[m.group(2).lower()]
            an = int(m.group(3)) if m.group(3) else None
    if not j:
        return None
    if an and an < 100:
        an += 2000
    if not an:
        if not ref:
            return None
        an = ref.year
    try:
        d = date(an, mo, j)
    except ValueError:
        return None
    if ref and not m.group(3):          # année non écrite : la plus proche de la date du document
        if (d - ref).days > 240:
            d = d.replace(year=an - 1)
        elif (ref - d).days > 240:
            d = d.replace(year=an + 1)
    return d


def faits_uniques(fichiers):
    groupes = defaultdict(list)
    for f in fichiers:
        if not f.exists():
            continue
        for x in csv.DictReader(f.open(encoding="utf-8-sig"), delimiter=";"):
            groupes[(x["lot"], x["type"], norm(x["citation"]) or norm(x["sujet"] + " " + x["valeur"]))].append(x)
    out = []
    for (lot, _, _), xs in groupes.items():
        xs.sort(key=lambda x: x["date_source"] or "0")
        x = dict(xs[-1])                                   # le plus récent
        ref = d_iso(x["date_source"])
        ecrite = date_ecrite(x["valeur"], ref) or date_ecrite(x["citation"], ref)
        avant = x["date_fait"]
        if ecrite:
            x["date_fait"] = ecrite.isoformat()
        elif avant and avant == x["date_source"]:
            x["date_fait"] = ""                            # ce n'était que la date du document
        x["date_corrigee"] = "oui" if x["date_fait"] != avant else ""
        x["copies"] = len(xs)
        x["premier_vu"] = xs[0]["date_source"]
        x["ids_fusionnes"] = " ".join(y["id"] for y in xs[:-1])
        out.append(x)
    out.sort(key=lambda x: (x["lot"], x["date_source"] or "0"), reverse=False)
    return out


# ---------- rattachement des points / décisions ----------
class Rattacheur:
    def __init__(self, m):
        self.sections = m["sections"]
        self.bet = m["bet"]
        self.mots = {l: re.compile("|".join(v), re.I) for l, v in m["mots"].items()}

    def lots(self, texte, section=""):
        """Lots cités dans le sujet + lot de l'entreprise de la section (ex. P005 Verrière -> VER et GO)."""
        trouves = [l for l, r in self.mots.items() if r.search(texte or "")]
        trouves += [l for k, l in self.sections.items() if section.startswith(k) and l not in trouves]
        return trouves

    def bets(self, *champs):
        t = " ".join(c or "" for c in champs)
        return sorted({v for k, v in self.bet.items() if k.lower() in t.lower()})


def ouvert(statut):
    return norm(statut) not in OUVERT_EXCLU


# ---------- dernier document par lot (index du jour 1) ----------
def date_source(src):
    m = re.search(r"(20\d\d-\d\d-\d\d)", src) or re.search(r"(?:^|[\\/ ])(\d{6})[ .]", src)
    if not m:
        return None
    g = m.group(1)
    return d_iso(g if "-" in g else f"20{g[:2]}-{g[2:4]}-{g[4:]}")


def derniers_docs(db, fts, auj, hors_projet, n=3):
    if not db.exists():
        return {}
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = {}
    for lot, q in fts.items():
        vus = {}
        try:
            lignes = c.execute("SELECT DISTINCT d.chemin, d.source FROM passages JOIN docs d ON d.id = passages.doc "
                               "WHERE passages MATCH ?", (q,)).fetchall()
        except sqlite3.Error:
            continue
        for chemin, src in lignes:
            if chemin.startswith(("_pilotage", "_planning")) or any(h in src.lower() for h in hors_projet):
                continue
            d = date_source(src)
            if d and d <= auj:
                vus[src] = d
        out[lot] = sorted(vus.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return out


# ---------- état ----------
def construire(projet, auj):
    cfg = json.loads((SCRIPTS.parent / "modeles" / "analyse_marches" / f"{projet}.json").read_text(encoding="utf-8"))
    m = cfg["memoire"]
    trav = Path(cfg["travail"])
    etat = json.loads((trav / "pilotage" / f"{projet.lower()}_state.json").read_text(encoding="utf-8"))
    lots_csv = {r["lot_code"]: r for r in csv.DictReader(open(cfg["lots_csv"], encoding="utf-8-sig"), delimiter=";")}
    rat = Rattacheur(m)
    faits = faits_uniques([trav / "analyses" / "faits" / "faits.csv", trav / "analyses" / "faits" / "autres_lots.csv"])
    docs = derniers_docs(trav / "_cache" / "cerveau.db", m["fts"], auj, m.get("hors_projet", ["oasis"]))

    lots = defaultdict(lambda: {"points": [], "decisions": [], "faits": [], "trous": []})
    bets = defaultdict(list)
    for p in etat.get("points_chantier", []) + [dict(x, interne=True) for x in etat.get("hors_cr", [])]:
        if not ouvert(p.get("statut")):
            continue
        r = {"id": p["id"], "sujet": p.get("sujet", ""), "statut": p.get("statut", ""),
             "responsable": p.get("responsable", ""), "echeance": p.get("echeance") or "",
             "maj_le": p.get("maj_le") or "", "interne": bool(p.get("interne")),
             "derniere_note": (p.get("historique") or [{}])[-1].get("note", "")[:220]}
        for l in rat.lots(p.get("sujet", ""), p.get("section", "")) or ["?"]:
            lots[l]["points"].append(r)
        for b in rat.bets(p.get("section"), p.get("responsable")):
            bets[b].append(r)
    for d in etat.get("decisions_mo", []):
        if norm(d.get("statut", "")) == "prise":
            continue
        r = {"id": d["id"], "lot": d.get("lot", ""), "statut": d.get("statut", ""), "decision": d.get("decision", "")[:200],
             "situation": (d.get("situation", "").split(" | ")[-1])[:220]}
        for l in rat.lots(d.get("lot", "") + " " + d.get("tache_planning", "")) or ["?"]:
            lots[l]["decisions"].append(r)

    for f in faits:
        lots[f["lot"]]["faits"].append(f)

    sil, sansnv = m["silence_j"], m["sans_nouvelle_j"]
    resultat = {}
    for code in sorted(set(lots) | set(lots_csv) | set(docs), key=lambda c: (c not in m["pilote"], c)):
        L = lots[code]
        info = lots_csv.get(code, {})
        dd = docs.get(code, [])
        dernier = dd[0][1] if dd else None
        trous = []
        for p in L["points"]:
            e, mj = d_iso(p["echeance"]), d_iso(p["maj_le"])
            if e and e < auj and (not mj or mj <= e):
                trous.append(f"{p['id']} {p['sujet']} : échéance du {jjmm(e)} dépassée, rien de noté depuis")
            elif not e and mj and (auj - mj).days > sansnv:
                trous.append(f"{p['id']} {p['sujet']} : sans échéance et sans nouvelle depuis le {jjmm(mj)}")
        if dernier and (auj - dernier).days > sil and (L["points"] or L["decisions"]):
            trous.append(f"aucun document depuis le {jjmm(dernier)} ({(auj - dernier).days} j) alors que des points ou décisions sont ouverts")
        # engagements datés échus dans les 30 derniers jours, sans fait plus récent sur le même sujet
        recents = [f for f in L["faits"] if f["type"] in ("engagement", "date") and d_iso(f["date_fait"])
                   and auj - timedelta(days=30) <= d_iso(f["date_fait"]) < auj]
        for f in sorted(recents, key=lambda f: f["date_fait"], reverse=True)[:4]:
            suite = [g for g in L["faits"] if g is not f and norm(g["sujet"])[:25] == norm(f["sujet"])[:25]
                     and (g["date_source"] or "") > f["date_fait"]]
            mots_f = {w for w in re.split(r"[ /]", norm(f["sujet"])) if len(w) > 4}
            suite += [p for p in L["points"] if p["maj_le"] >= f["date_fait"]          # point suivi depuis
                      and mots_f & {w for w in re.split(r"[ /]", norm(p["sujet"])) if len(w) > 4}]
            if not suite:
                trous.append(f"engagement du {jjmm(d_iso(f['date_fait']))} « {f['sujet'][:70]} » "
                             f"({f['acteur'] or 'acteur non écrit'}) : tenu ? aucune trace après")
        nv = max([p["maj_le"] for p in L["points"] if p["maj_le"]] or [""])
        intit, _, entr = m.get("intitules", {}).get(code, "|").partition("|")
        resultat[code] = {
            "intitule": info.get("lot_intitule", intit), "entreprise": info.get("entreprise", entr),
            "derniere_nouvelle_point": nv,
            "chemin_critique": info.get("chemin_critique") == "oui", "pilote": code in m["pilote"],
            "dernier_document": dernier.isoformat() if dernier else "",
            "documents_recents": [{"date": d.isoformat(), "source": s.split("\\038\\", 1)[-1]} for s, d in dd],
            "points": L["points"], "decisions": L["decisions"], "trous": trous,
            "faits": len(L["faits"]),
            "faits_recents": [{k: f[k] for k in ("id", "type", "sujet", "valeur", "acteur", "date_fait", "date_source", "copies")}
                              for f in sorted(L["faits"], key=lambda f: f["date_source"] or "0", reverse=True)[:8]],
        }
    return cfg, trav, faits, resultat, dict(bets)


def ecrire_md(res, bets, auj, nb_faits, nb_bruts):
    o = [f"# Mémoire par lot — {auj.strftime('%d/%m/%Y')}",
         "", "Pour Yahya seul (contient des points internes). Généré par `memoire.py` (Python, zéro token) ; "
         "« trous possibles » = questions, pas des constats. Faits Qwen : statut « à confirmer ».",
         f"Faits : {nb_bruts} relevés → {nb_faits} après fusion des copies d'un CR à l'autre.", ""]

    def bloc(code, r, detail):
        tete = f"## {code} — {r['intitule'] or '?'}" + (f" ({r['entreprise']})" if r["entreprise"] else "")
        o.append(tete)
        o.append(f"- Dernier document connu : {r['dernier_document'] or 'aucun'}"
                 + (f" — {r['documents_recents'][0]['source'].replace('Outlook : ', 'mail ')[:110]}" if r["documents_recents"] else "")
                 + (f" ; point mis à jour le {r['derniere_nouvelle_point']}" if r["derniere_nouvelle_point"] else ""))
        if r["points"]:
            o.append("- Points ouverts : " + " ; ".join(
                f"{p['id']} {p['sujet']} [{p['statut']}{', éch. ' + p['echeance'][8:10] + '/' + p['echeance'][5:7] if p['echeance'] else ''}]"
                + (" (interne)" if p["interne"] else "") for p in r["points"]))
        if r["decisions"]:
            o.append("- Décisions MO liées : " + " ; ".join(f"{d['id']} {d['lot'][:50]}" for d in r["decisions"]))
        if detail:
            for p in r["points"]:
                if p["derniere_note"]:
                    o.append(f"  - {p['id']} dernière note : {p['derniere_note']}")
            if r["faits_recents"]:
                o.append(f"- Faits récents ({r['faits']} au total) :")
                for f in r["faits_recents"]:
                    o.append(f"  - {f['date_source'] or '?'} {f['type']} — {f['sujet'][:70]} : {f['valeur'][:90]}"
                             + (f" (×{f['copies']})" if int(f["copies"]) > 1 else ""))
        if r["trous"]:
            o.append("- **Trous possibles** :")
            o.extend(f"  - {t}" for t in r["trous"][: (8 if detail else 3)])
        o.append("")

    o.append("# Lots pilotes (clos couvert)\n")
    for c, r in res.items():
        if r["pilote"]:
            bloc(c, r, True)
    o.append("# Autres lots\n")
    for c, r in res.items():
        if not r["pilote"] and c not in ("?", "AUTRE") and (r["points"] or r["decisions"] or r["faits"]):
            bloc(c, r, False)
    o.append("# BET et architectes (relances, pas décisions MO)\n")
    for b, ps in sorted(bets.items()):
        o.append(f"- **{b}** : " + " ; ".join(f"{p['id']} {p['sujet']} [{p['statut']}]" for p in ps))
    if res.get("?", {}).get("points"):
        o.append("\nPoints non rattachés à un lot : " + " ; ".join(p["id"] for p in res["?"]["points"]))
    return "\n".join(o) + "\n"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--projet", default="TBRP")
    a.add_argument("--aujourdhui", default=date.today().isoformat())
    a = a.parse_args()
    auj = date.fromisoformat(a.aujourdhui)
    cfg, trav, faits, res, bets = construire(a.projet, auj)
    sortie = trav / "analyses" / "memoire"
    sortie.mkdir(parents=True, exist_ok=True)
    champs = list(faits[0].keys()) if faits else []
    with (sortie / "faits_uniques.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, champs, delimiter=";")
        w.writeheader()
        w.writerows(faits)
    nb_bruts = sum(int(f["copies"]) for f in faits)
    (sortie / "memoire.json").write_text(json.dumps({"date": auj.isoformat(), "lots": res, "bet": bets},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
    (sortie / "etat_lots.md").write_text(ecrire_md(res, bets, auj, len(faits), nb_bruts), encoding="utf-8")
    corr = sum(1 for f in faits if f["date_corrigee"])
    print(f"Mémoire : {len(res)} lots, {sum(len(r['trous']) for r in res.values())} trous possibles ; "
          f"faits {nb_bruts} -> {len(faits)} uniques, {corr} date_fait corrigées -> {sortie}")


if __name__ == "__main__":
    main()
