r"""Analyse locale et gratuite des marchés d'un projet (modèle Ollama sur le PC).

  python analyse_marches.py [etapes...] [--projet TBRP] [--lots GO REV] [--date AAAA-MM-JJ]

Étapes (défaut : toutes, dans l'ordre) :
  inventaire  marché / CPT / bordereau / avenants / TS / OS repérés pour chaque lot
  extraction  postes des bordereaux retenus -> <travail>\analyses\postes.csv
  croisement  contrôles Python sans modèle : mots-clés absents ou en double, désignations
              identiques dans 2 lots, prix unitaires très différents, erreurs q × PU
  analyse     Qwen (Ollama, localhost) relit les postes par paquets ; réponses en cache
              (<travail>\analyses\_cache), donc relançable sans refaire les appels
  avancement  derniers décomptes / situations / avancements trouvés en texte
  rapport     <publier>\analyses\<date>_marches.md (+ pistes.csv, inventaire.csv)

Config du projet : modeles\analyse_marches\<projet>.json (dossiers, bordereaux retenus,
périmètres, mots sensibles). Rien n'est écrit dans 01_MIROIR. Toute piste reste « à vérifier ».
"""
import argparse, csv, json, re, sys, time, unicodedata, urllib.error, urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SCRIPTS = Path(__file__).resolve().parent
SYSTEME = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

OLLAMA = "http://localhost:11434/api/chat"
MODELE = "qwen3:14b"
DELAI_S = 600
TAILLE_PAQUET = 45          # postes par appel (contexte 8k du 14b)
ETAPES = ["inventaire", "extraction", "croisement", "analyse", "avancement", "rapport"]

# ---------------------------------------------------------------- outils

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


VIDES = {"fourniture", "pose", "compris", "selon", "toutes", "sujetions", "mise", "oeuvre", "ouvrage",
         "ouvrages", "type", "dimensions", "dimension", "avec", "pour", "dans", "sous", "realisation",
         "travaux", "details", "detail", "architecte", "plans", "suivant", "ensemble", "metre", "carre",
         "cube", "lineaire", "unite", "prix", "fonction", "toute", "tout", "entre", "chaque", "conforme"}


def mots(s):
    return {m for m in re.findall(r"[a-z]{4,}", norm(s)) if m not in VIDES}


def lire(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return []


def date_nom(nom):
    """Date tirée d'un nom de fichier (AAAA-MM-JJ, JJ.MM.AAAA, JJ MM AAAA, AAMMJJ) ou ''."""
    for rx, ordre in [(r"(20\d\d)[.\-_ ](\d\d)[.\-_ ](\d\d)", "ymd"),
                      (r"(\d\d)[.\-_ ](\d\d)[.\-_ ](20\d\d)", "dmy"),
                      (r"(?<!\d)(2[3-9])(\d\d)(\d\d)(?!\d)", "yymmdd"),
                      (r"(?<!\d)(\d\d)(\d\d)(20\d\d)(?!\d)", "dmy")]:
        m = re.search(rx, nom)
        if not m:
            continue
        a, b, c = m.groups()
        y, mo, d = {"ymd": (a, b, c), "dmy": (c, b, a), "yymmdd": ("20" + a, b, c)}[ordre]
        if 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
            return f"{y}-{mo}-{d}"
    return ""


def fmt(x):
    return "" if x in (None, "") else (f"{x:,.0f}".replace(",", " ") if isinstance(x, (int, float)) else str(x))


# ---------------------------------------------------------------- config

class Projet:
    def __init__(self, nom):
        self.cfg = json.loads((SYSTEME / "modeles" / "analyse_marches" / f"{nom}.json").read_text(encoding="utf-8"))
        self.nom = nom
        self.racine = Path(self.cfg["racine_texte"])
        self.travail = Path(self.cfg["travail"])
        self.publier = Path(self.cfg["publier"])
        self.sortie = self.travail / "analyses"
        self.cache = self.sortie / "_cache"
        self.lots = {}
        lc = Path(self.cfg.get("lots_csv", ""))
        if lc.exists():
            with lc.open(encoding="utf-8-sig") as f:
                for r in csv.DictReader(f, delimiter=";"):
                    self.lots[r["lot_code"]] = {"intitule": r["lot_intitule"], "entreprise": r["entreprise"]}
        for code, c in self.cfg["lots"].items():
            d = self.lots.setdefault(code, {"intitule": c.get("intitule", code), "entreprise": c.get("entreprise", "")})
            d.update(c)

    def rel(self, p):
        try:
            return str(Path(p).relative_to(self.racine))
        except ValueError:
            return str(p)

    def source(self, rel):
        """Chemin de l'original (1re ligne SOURCE:)."""
        l = lire(self.racine / rel)[:1]
        return l[0][7:].strip() if l and l[0].startswith("SOURCE:") else rel


# ---------------------------------------------------------------- 1. inventaire

CLASSES = [("avenant", r"avenant"), ("ts", r"(?<![a-z])ts(?![a-z])|travaux suppl"),
           ("os", r"(?<![a-z])os(?![a-z])|ordre de service"),
           ("bordereau", r"bdp|bpu|dqe|dpgf|boq|bordereau|offre|devis|tco|metre|bpde"),
           ("cpt", r"cpt|cctp|descriptif"), ("marche", r"piece de marche|contrat|marche|bon de commande|(?<![a-z])bc(?![a-z])")]


def score(rel):
    n = norm("/".join(Path(rel).parts[-4:]))   # dossiers proches seulement
    s = 0
    s -= 50 if re.search(r"(^|[/\\])(old|archive)", n) else 0
    s += 20 if re.search(r"piece de marche|avenant n", n) else 0
    s += 30 if re.search(r"contrat|marche|imprimer|offre finale|post nego", n) else 0
    s += 5 if n.endswith(".pdf.txt") else 0
    return (s, date_nom(Path(rel).name) or "0000", rel)


def inventaire(P):
    lignes = []
    for code, lot in P.lots.items():
        trouve = defaultdict(list)
        for d in lot.get("dossiers", []):
            for f in (P.racine / d).rglob("*.txt"):
                nom = norm(f.name.replace(".txt", ""))
                if re.search(r"fiche|plan|nsi|planning|attestation|declaration|acte d|page de garde|annexe \d|etude", nom):
                    continue
                chemin = norm("/".join(Path(P.rel(f)).parts[-4:-1]))
                for cl, rx in CLASSES:
                    if re.search(rx, nom) or (cl == "avenant" and re.search(r"avenant (n|\d)|projet d.avenant", chemin)):
                        trouve[cl].append(P.rel(f))
                        break
        for cl in ["marche", "cpt", "bordereau"]:
            if trouve[cl]:
                lignes.append({"lot": code, "piece": cl, "fichier": max(trouve[cl], key=score), "nb_versions": len(trouve[cl])})
            else:
                lignes.append({"lot": code, "piece": cl, "fichier": "(non trouvé)", "nb_versions": 0})
        for f in lot.get("dqe", []):
            lignes.append({"lot": code, "piece": "bordereau retenu", "fichier": f, "nb_versions": ""})
        vus = set()
        for cl in ["avenant", "ts", "os"]:
            for f in sorted(trouve[cl], key=score, reverse=True):
                cle = (cl, norm(Path(f).name))
                if cle in vus or score(f)[0] < -10:
                    continue
                vus.add(cle)
                if sum(1 for c, _ in vus if c == cl) > 10:
                    break
                lignes.append({"lot": code, "piece": cl, "fichier": f, "nb_versions": ""})
    P.sortie.mkdir(parents=True, exist_ok=True)
    ecrire_csv(P.sortie / "inventaire.csv", lignes, ["lot", "piece", "fichier", "nb_versions"])
    print(f"Inventaire : {len(lignes)} lignes -> {P.sortie / 'inventaire.csv'}")
    return lignes


# ---------------------------------------------------------------- 2. extraction

UNITES = {"m3", "m³", "m2", "m²", "ml", "m", "u", "u.", "un", "unite", "ens", "ens.", "e", "f", "ff", "ft", "fft",
          "forfait", "kg", "t", "l", "pce", "nb", "nbre", "jour", "j", "h", "mois", "pm"}
NUMERO = re.compile(r"^((?:[A-Z]{1,3}[.\-]?)?\d+(?:\s?[.,\-]\s?\d+)*[a-z]?\.?|[IVX]+\.(?:\s?\d+\.?)*[a-z]?\.?)\s+(.*)$")
GENERIQUE = re.compile(r"^(le|la|les|l'|l’)\s?\w*", re.I)
NUM_TXT = re.compile(r"^(?:[\d.,\u202f\xa0\-]+|PM|P\.M\.?|\s)+$", re.I)


def nombre(s, excel=False):
    s = (s or "").strip().replace("\u202f", " ").replace("\xa0", " ")
    if not s or s in "-–":
        return None
    if re.fullmatch(r"p\.?m\.?", s, re.I):
        return "PM"
    try:
        if excel:
            return float(s.replace(" ", "").replace(",", "."))
        if "," in s:
            return float(s.replace(" ", "").replace(".", "").replace(",", "."))
        s = s.replace(" ", "")
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
            s = s.replace(".", "")
        return float(s)
    except ValueError:
        return None


def nombres_pdf(reste, insecable=False):
    """insecable=True : le fichier sépare les milliers par une espace insécable, donc une
    espace ordinaire sépare toujours deux colonnes."""
    vals = []
    reste = re.sub(r"(?<=\d)[ \xa0](?=\d{3})", "", reste)   # séparateur de milliers insécable
    for bloc in re.split(r"\s+" if insecable else r"\s{2,}", reste.strip()):
        if not bloc:
            continue
        v = nombre(bloc)
        if v is not None and (v == "PM" or re.fullmatch(r"\d{1,3}(?:[ .]\d{3})*(?:,\d+)?|\d+(?:[.,]\d+)?", bloc)):
            vals.append(v)
            continue
        for t in re.findall(r"\d{1,3}(?:[ .]\d{3}(?!\d))+(?:,\d+)?(?!\d)|\d+(?:[.,]\d+)?|P\.?M\.?", bloc, re.I):
            v = nombre(t)
            if v is not None:
                vals.append(v)
    return vals


def poste(lot, rel, ligne, n, des, u, vals):
    q, pu, mt = (vals + [None, None, None])[:3]
    if len(vals) == 2 and all(isinstance(v, float) for v in vals) and vals[0] and abs(vals[1] / vals[0] - 1) < 1e-6:
        q, pu, mt = 1.0, vals[0], vals[1]   # forfait : PU = montant
    ctrl = ""
    if all(isinstance(v, float) for v in (q, pu, mt)) and mt:
        ecart = abs(q * pu - mt)
        if ecart > max(100, 0.01 * abs(mt)):
            ctrl = f"q×PU={q * pu:,.0f} ≠ montant".replace(",", " ")
    return {"lot": lot, "fichier": rel, "ligne": ligne, "n": (n or "").strip(),
            "designation": re.sub(r"\s+", " ", des).strip()[:300], "unite": u,
            "quantite": q, "pu": pu, "montant": mt, "controle": ctrl}


def extraire_pdf(lot, rel, lignes):
    out, cour_n, cour_txt = [], "", ""
    ins = any(re.search(r"\d[  ]\d{3}", l) for l in lignes)
    for i, l in enumerate(lignes[1:], start=2):
        l = l.strip()
        if not l:
            continue
        if re.match(r"(sous[- ]?)?total|montant|report", l, re.I):
            cour_n, cour_txt = "", ""
            continue
        t = l.split()
        coupe = None
        for k in range(len(t) - 1, -1, -1):
            if t[k].lower() in UNITES and t[k].lower() != "pm":
                pos = [m.end() for m in re.finditer(rf"(?:(?<=\s)|^){re.escape(t[k])}(?=\s)", l)]
                reste = l[pos[-1]:] if pos else ""
                if reste.strip() and NUM_TXT.match(reste) and re.search(r"\d|PM", reste, re.I):
                    coupe = (" ".join(t[:k]), t[k], reste)
                    break
        if not coupe and NUM_TXT.match(l) and cour_txt:
            v = nombres_pdf(l, ins)              # ligne « q  PU  montant » sans unité (devis)
            if len(v) == 3 and all(isinstance(x, float) for x in v) and v[2] and abs(v[0] * v[1] - v[2]) <= 0.01 * v[2]:
                out.append(poste(lot, rel, i, cour_n, cour_txt, "U?", v))
                cour_n, cour_txt = "", ""
                continue
        if not coupe:
            m = NUMERO.match(l)
            if m and not re.fullmatch(r"[\d\s.,]+", l):
                cour_n, cour_txt = m.group(1), m.group(2)
            elif len(cour_txt) < 400:
                cour_txt += " " + l
            continue
        avant, u, reste = coupe
        vals = nombres_pdf(reste, ins)
        if not vals:
            continue
        if len(vals) > 3:                 # dimensions avant q / PU / montant : garder les 3 dernières
            vals = vals[-3:]
        m = NUMERO.match(avant)
        if m:
            n, d = m.group(1), m.group(2)
        else:
            n, d = cour_n, avant
            if len(d) < 15 or GENERIQUE.match(d):
                d = (cour_txt + " " + d).strip()
        out.append(poste(lot, rel, i, n, d, u.upper(), vals))
        cour_n, cour_txt = "", ""
    return out


def extraire_excel(lot, rel, lignes):
    out, titre = [], ""
    for i, l in enumerate(lignes[1:], start=2):
        if ";" not in l:
            continue
        c = [x.strip() for x in l.split(";")]
        iu = next((k for k, x in enumerate(c) if k > 0 and x.lower() in UNITES and x.lower() != "pm"
                   and any(nombre(y, True) is not None for y in c[k + 1:k + 4])), None)
        textes = [x for x in c if x and nombre(x, True) is None]
        if iu is None:
            if textes and len(max(textes, key=len)) > 3:
                titre = max(textes, key=len)[:120]
            continue
        avant = [x for x in c[:iu] if x]
        n = next((x for x in avant if re.fullmatch(r"[A-Z]{0,3}[\dIVX]+(?:[.,\-]\s?\w+)*\.?", x)), "")
        des = max([x for x in avant if x != n and nombre(x, True) is None] or [""], key=len)
        if len(des) < 20 and titre:
            des = f"{titre} / {des}"
        vals = [nombre(x, True) for x in c[iu + 1:] if nombre(x, True) is not None][:3]
        if vals:
            out.append(poste(lot, rel, i, n, des, c[iu].upper(), vals))
    return out


def extraction(P):
    postes = []
    for code, lot in P.lots.items():
        for rel in lot.get("dqe", []):
            lignes = lire(P.racine / rel)
            if not lignes:
                print(f"  {code} : fichier absent {rel}")
                continue
            excel = sum(";" in l for l in lignes) > len(lignes) / 3
            ps = (extraire_excel if excel else extraire_pdf)(code, rel, lignes)
            total = sum(p["montant"] for p in ps if isinstance(p["montant"], float))
            print(f"  {code} : {len(ps)} postes, total {fmt(total)} DH HT — {Path(rel).name}")
            postes += ps
    ecrire_csv(P.sortie / "postes.csv", postes,
               ["lot", "n", "designation", "unite", "quantite", "pu", "montant", "controle", "fichier", "ligne"])
    print(f"Extraction : {len(postes)} postes -> {P.sortie / 'postes.csv'}")
    return postes


def charger_postes(P):
    with (P.sortie / "postes.csv").open(encoding="utf-8-sig") as f:
        ps = list(csv.DictReader(f, delimiter=";"))
    for p in ps:
        for k in ("quantite", "pu", "montant"):
            v = p[k]
            p[k] = float(v) if re.fullmatch(r"-?[\d.]+(e-?\d+)?", v or "") else (v or None)
        p["ligne"] = int(p["ligne"])
    return ps


# ---------------------------------------------------------------- 3. croisement (sans modèle)

def provisions_tsb(P):
    """Lignes du TSB (feuille provisions) : lot, désignation, montant."""
    rel = P.cfg.get("tsb")
    lignes = lire(P.racine / rel) if rel else []
    out, dans, lot = [], False, ""
    for i, l in enumerate(lignes, start=1):
        if l.startswith("### Feuille"):
            dans = "provision" in norm(l)
            continue
        c = l.split(";")
        if not dans or len(c) < 5:
            continue
        lot = c[1].strip() or lot
        m = nombre(c[4], True)
        if c[2].strip() and isinstance(m, float):
            out.append({"lot_tsb": lot, "designation": c[2].strip(), "montant": m, "ligne": i})
    return out, rel


def piste(**k):
    base = {"lot": "", "type": "", "poste": "", "constat": "", "impact_dh": None, "impact_origine": "",
            "source": "", "ligne": "", "origine": "Python", "statut": "à vérifier", "qwen_dh": None}
    base.update(k)
    return base


def croisement(P, postes):
    pistes = []
    lots_dqe = sorted({p["lot"] for p in postes})
    tsb, tsb_rel = provisions_tsb(P)
    # a) mots sensibles : absents de tous les bordereaux, ou présents dans plusieurs lots
    for theme, cles in P.cfg.get("mots_sensibles", {}).items():
        par_lot = defaultdict(list)
        for p in postes:
            tete = " ".join(norm(p["designation"]).split()[:10])
            if any(c in tete for c in cles):
                par_lot[p["lot"]].append(p)
        t = [x for x in tsb if any(c in norm(x["designation"]) for c in cles)]
        tsb_txt = "; ".join(f"{x['lot_tsb']} « {x['designation']} » {fmt(x['montant'])}" for x in t)
        imp = sum(x["montant"] for x in t if x["montant"] > 0) or None
        if not par_lot:
            pistes.append(piste(type="oubli", lot="tous", poste=theme,
                                constat=f"Aucun bordereau analysé ne contient « {theme} »."
                                        + (f" Provision TSB : {tsb_txt}." if t else ""),
                                impact_dh=imp, impact_origine="provision TSB" if imp else "",
                                source=tsb_rel if t else f"{len(lots_dqe)} bordereaux"))
        elif len(par_lot) >= 2:
            det = "; ".join(f"{l} ({len(v)} poste(s), ex. ligne {v[0]['ligne']})" for l, v in par_lot.items())
            mt = sum(p["montant"] for v in par_lot.values() for p in v if isinstance(p["montant"], float))
            pistes.append(piste(type="doublon", lot="+".join(par_lot), poste=theme,
                                constat=f"Présent dans {len(par_lot)} lots : {det}. Vérifier qui fait quoi.",
                                impact_dh=mt or None, impact_origine="montant des postes",
                                source=" | ".join(f"{v[0]['fichier']} l.{v[0]['ligne']}" for v in par_lot.values())))
        lots_t = {x["lot_tsb"] for x in t}
        if len(lots_t) >= 2:
            pistes.append(piste(type="doublon", lot="TSB", poste=theme,
                                constat=f"Le TSB compte « {theme} » dans plusieurs lignes/lots : {tsb_txt}.",
                                impact_dh=min(x["montant"] for x in t if x["montant"] > 0) if imp else None,
                                impact_origine="plus petite ligne TSB", source=f"{tsb_rel} l.{t[0]['ligne']}"))
    # b) désignations proches dans deux lots (doublon) + prix unitaires très différents
    idx = defaultdict(list)
    for k, p in enumerate(postes):
        p["_m"] = mots(p["designation"])
        for m in p["_m"]:
            idx[m].append(k)
    vus = set()
    for k, p in enumerate(postes):
        if len(p["_m"]) < 3:
            continue
        cand = defaultdict(int)
        for m in p["_m"]:
            if len(idx[m]) < 60:
                for j in idx[m]:
                    if j > k and postes[j]["lot"] != p["lot"]:
                        cand[j] += 1
        for j, nb in cand.items():
            q = postes[j]
            jac = nb / len(p["_m"] | q["_m"])
            if jac < 0.5 or p["unite"] != q["unite"]:
                continue
            cle = (p["lot"], q["lot"], norm(p["designation"])[:40])
            if cle in vus:
                continue
            vus.add(cle)
            src = f"{p['fichier']} l.{p['ligne']} | {q['fichier']} l.{q['ligne']}"
            if jac >= 0.7:
                mt = [x["montant"] for x in (p, q) if isinstance(x["montant"], float)]
                pistes.append(piste(type="doublon", lot=f"{p['lot']}+{q['lot']}", poste=p["designation"][:90],
                                    constat=f"Désignation quasi identique dans {p['lot']} et {q['lot']} ({p['unite']}).",
                                    impact_dh=min(mt) if mt else None, impact_origine="plus petit montant", source=src))
            if isinstance(p["pu"], float) and isinstance(q["pu"], float) and min(p["pu"], q["pu"]) > 0:
                r = max(p["pu"], q["pu"]) / min(p["pu"], q["pu"])
                if r >= 2:
                    pistes.append(piste(type="incoherence", lot=f"{p['lot']}/{q['lot']}", poste=p["designation"][:90],
                                        constat=f"PU {fmt(p['pu'])} ({p['lot']}) contre {fmt(q['pu'])} ({q['lot']}) "
                                                f"pour un ouvrage proche, ×{r:.1f}.", source=src))
    # c) erreurs de calcul q × PU
    for p in postes:
        if p["controle"]:
            pistes.append(piste(type="incoherence", lot=p["lot"], poste=p["designation"][:90],
                                constat=f"{p['controle']} ({fmt(p['montant'])}).", impact_dh=None,
                                source=f"{p['fichier']} l.{p['ligne']}"))
        elif p["unite"] != "PM" and p["pu"] == "PM":
            pistes.append(piste(type="risque_avenant", lot=p["lot"], poste=p["designation"][:90],
                                constat="Prix « PM » (pour mémoire) : ouvrage non chiffré, payé hors forfait si réalisé.",
                                source=f"{p['fichier']} l.{p['ligne']}"))
    for p in postes:
        p.pop("_m", None)
    print(f"Croisement : {len(pistes)} pistes mécaniques")
    return pistes


# ---------------------------------------------------------------- 4. analyse Qwen

CONSIGNE = """Tu relis le bordereau de prix d'un lot d'un chantier de centre commercial, pour le maître d'ouvrage délégué.
Il ne peut plus signer d'avenant : il cherche tôt ce qui manque ou ce qui coûtera plus.
Lot relu : {lot} – {intitule} ({entreprise}).
Périmètre des autres lots (une ligne chacun) :
{perimetres}

Postes (L=ligne du fichier | n° | désignation | unité | quantité | PU | montant DH HT) :
{postes}

Cherche, uniquement à partir de ces postes et des périmètres :
- "oubli" : ouvrage nécessaire qui n'est ni dans ces postes ni clairement dans un autre lot (interfaces, rebouchages, réservations, raccords, finitions, protections, essais) ;
- "doublon" : poste qui semble aussi compté dans un autre lot ;
- "incoherence" : quantité, unité ou prix anormal ;
- "risque_avenant" : poste flou, "PM", "à confirmer", hors forfait, quantité sous-estimée.
Réponds en JSON : {{"pistes":[{{"type":"oubli|doublon|incoherence|risque_avenant","L":numéro de ligne ou null,"poste":"texte court","constat":"1 phrase simple en français","autre_lot":"code ou vide","impact_dh":nombre estimé ou null}}]}}
Ne cite pas les obligations générales déjà couvertes par le CCG/CPT et le forfait (essais, nettoyage, protection pendant
les travaux, plans d'exécution, installations de chantier). Cite seulement des ouvrages concrets.
6 pistes au maximum, les plus coûteuses d'abord. N'invente ni montant ni ligne : null si tu ne sais pas. Si rien, {{"pistes":[]}}."""


def demander(texte):
    from secours import demarrer_ollama   # lance « ollama serve » avec OLLAMA_MODELS=D:\Ollama\models
    demarrer_ollama()
    corps = json.dumps({"model": MODELE, "stream": False, "think": False, "format": "json",
                        "options": {"temperature": 0.2, "num_ctx": 8192, "num_predict": 1200},
                        "messages": [{"role": "user", "content": texte}]}).encode("utf-8")
    for essai in (1, 2):   # 1er appel parfois en erreur 500 pendant le chargement du modèle
        try:
            req = urllib.request.Request(OLLAMA, corps, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=DELAI_S) as r:
                return json.loads(r.read().decode("utf-8"))["message"]["content"]
        except urllib.error.HTTPError:
            if essai == 2:
                raise
            time.sleep(20)


def analyse(P, postes, lots):
    P.cache.mkdir(parents=True, exist_ok=True)
    perim = "\n".join(f"- {c} ({l.get('entreprise', '')}) : {l.get('perimetre', l.get('intitule', ''))}"
                      for c, l in P.lots.items())
    pistes = []
    for code in lots:
        ps = [p for p in postes if p["lot"] == code]
        lot = P.lots.get(code, {})
        paquets = [ps[i:i + TAILLE_PAQUET] for i in range(0, len(ps), TAILLE_PAQUET)]
        for k, paq in enumerate(paquets, start=1):
            f = P.cache / f"{code}_{k:03d}.json"
            if not f.exists():
                txt = "\n".join(f"L{p['ligne']} | {p['n']} | {p['designation'][:130]} | {p['unite']} | "
                                f"{fmt(p['quantite'])} | {fmt(p['pu'])} | {fmt(p['montant'])}" for p in paq)
                t0 = time.time()
                try:
                    rep = demander(CONSIGNE.format(lot=code, intitule=lot.get("intitule", ""),
                                                   entreprise=lot.get("entreprise", ""), perimetres=perim, postes=txt))
                except Exception as e:
                    print(f"  {code} paquet {k}/{len(paquets)} : échec ({e}), relancer plus tard")
                    continue
                f.write_text(json.dumps({"lot": code, "paquet": k, "lignes": [p["ligne"] for p in paq],
                                         "fichiers": sorted({p["fichier"] for p in paq}), "reponse": rep,
                                         "duree_s": round(time.time() - t0)}, ensure_ascii=False), encoding="utf-8")
                print(f"  {code} paquet {k}/{len(paquets)} : {round(time.time() - t0)} s", flush=True)
        pistes += lire_cache(P, code, ps)
    return pistes


def lire_cache(P, code, ps):
    par_ligne = {p["ligne"]: p for p in ps}
    out, vus = [], set()
    for f in sorted(P.cache.glob(f"{code}_*.json")):
        c = json.loads(f.read_text(encoding="utf-8"))
        try:
            rep = json.loads(c["reponse"])
        except json.JSONDecodeError:
            continue
        for x in (rep.get("pistes") or [])[:8]:
            if not isinstance(x, dict) or x.get("type") not in ("oubli", "doublon", "incoherence", "risque_avenant"):
                continue
            L = x.get("L")
            p = par_ligne.get(int(L)) if str(L or "").isdigit() and int(L) in c["lignes"] else None
            src = f"{p['fichier']} l.{p['ligne']}" if p else f"{c['fichiers'][0]} (ligne non retrouvée)"
            q = x.get("impact_dh")
            q = float(q) if isinstance(q, (int, float)) and q > 0 else None
            imp, orig = None, ""
            if p and isinstance(p["montant"], float) and p["montant"] > 0:
                imp, orig = p["montant"], "montant du poste concerné"
            cle = (code, x["type"], " ".join(sorted(mots(str(x.get("poste") or ""))))[:60])
            if cle in vus:
                continue
            vus.add(cle)
            autre = (x.get("autre_lot") or "").strip()
            out.append(piste(lot=code + (f"+{autre}" if autre and x["type"] == "doublon" else ""), type=x["type"],
                             poste=str(x.get("poste") or (p["designation"][:90] if p else ""))[:120],
                             constat=str(x.get("constat") or "")[:300], impact_dh=imp, impact_origine=orig,
                             source=src, ligne=p["ligne"] if p else "", origine="Qwen", qwen_dh=q))
    return out


# ---------------------------------------------------------------- 5. avancement

def avancement(P):
    res = {}
    fichiers = [f for d in P.cfg.get("dossiers_avancement", []) for f in (P.racine / d).rglob("*.txt")
                if re.search(r"d.?compte|situation|avancement|attachement", norm(f.name))]
    for code, lot in P.lots.items():
        cles = [norm(code)] + [norm(x) for x in lot.get("mots_avancement", [])]
        trouves = [f for f in fichiers if any(re.search(rf"(?<![a-z]){re.escape(c)}(?![a-z])", norm(P.rel(f))) for c in cles)]
        if not trouves:
            continue
        f = max(trouves, key=lambda x: date_nom(x.name) or "0")
        pct = []
        for l in lire(f)[1:]:
            if "%" in l and re.search(r"avancement|cumul|total|global|realise", norm(l)):
                pct.append(re.sub(r"[;\s]+", " ", l).strip()[:160])
        res[code] = {"date": date_nom(f.name) or "?", "fichier": P.rel(f), "extrait": pct[:2], "nb": len(trouves)}
    return res


# ---------------------------------------------------------------- 6. rapport

def ecrire_csv(f, lignes, champs):
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("w", encoding="utf-8-sig", newline="") as g:
        w = csv.DictWriter(g, fieldnames=champs, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)


def cellule(s):
    return str(s).replace("|", "/").replace("\n", " ")


def court(src):
    """Nom de fichier + ligne (le chemin complet reste dans pistes.csv)."""
    return " / ".join(cellule(Path(m.split(" l.")[0].split(" (")[0]).name + (" l." + m.split(" l.")[1] if " l." in m else "")
                      ) for m in str(src).split(" | "))


def rapport(P, jour, inv, postes, pistes, av):
    tri = lambda x: (-(x["impact_dh"] or 0), x["origine"] != "Python", -(x["qwen_dh"] or 0))
    main = sorted([x for x in pistes if x["type"] in ("oubli", "risque_avenant")], key=tri)
    dbl = sorted([x for x in pistes if x["type"] == "doublon"], key=tri)
    inc = sorted([x for x in pistes if x["type"] == "incoherence"], key=tri)
    lots_dqe = sorted({p["lot"] for p in postes})
    lots_qwen = sorted({x["lot"].split("+")[0] for x in pistes if x["origine"] == "Qwen"})
    top = main[0] if main else None
    ph1 = (f"{len(main)} pistes d'oubli ou de risque d'avenant sur {len(lots_dqe)} lots relus"
           + (f" ; la plus lourde : « {top['poste'][:60]} » (lot {top['lot']}"
              + (f", ~{fmt(top['impact_dh'])} DH" if top["impact_dh"] else "") + ")." if top else "."))
    ph2 = (f"{len(dbl)} doublons possibles entre lots ou dans le TSB"
           + (f", dont « {dbl[0]['poste'][:50]} »." if dbl else ".") + f" {len(inc)} incohérences de prix ou de calcul.")
    ph3 = (f"Avancement trouvé en texte pour {len(av)} lot(s) sur {len(P.lots)} ; les décomptes récents sont dans "
           f"Outlook, non lus ici. Tout est à vérifier avant usage.")
    L = [f"# Analyse des marchés {P.nom} – {jour}", "",
         "Pour Yahya seul (montants et positions internes). Pistes produites par Python et par Qwen "
         f"(modèle local) : **toutes à vérifier**. Lots relus par Qwen : {', '.join(lots_qwen) or 'aucun'}.", "",
         "## En bref", "", ph1, ph2, ph3, "",
         "## Oublis et risques d'avenant (classés par impact estimé)", "",
         "| # | Lot | Type | Poste / ouvrage | Constat | Impact estimé (DH HT) | Source | Statut |",
         "|---|---|---|---|---|---|---|---|"]
    for k, x in enumerate(main[:60], start=1):
        imp = f"{fmt(x['impact_dh'])} ({x['impact_origine']})" if x["impact_dh"] else (
            f"~{fmt(x['qwen_dh'])} (ordre de grandeur Qwen, non fiable)" if x["qwen_dh"] else "?")
        L.append(f"| {k} | {x['lot']} | {x['type'].replace('_', ' ')} | {cellule(x['poste'])} | {cellule(x['constat'])} "
                 f"| {imp} | {court(x['source'])} | {x['statut']} ({x['origine']}) |")
    if len(main) > 60:
        L.append(f"\n… {len(main) - 60} autres pistes dans `analyses\\pistes.csv`.")
    L += ["", "## Doublons possibles", "", "| Lots | Ouvrage | Constat | Montant en jeu | Source | Origine |",
          "|---|---|---|---|---|---|"]
    for x in dbl[:40]:
        L.append(f"| {x['lot']} | {cellule(x['poste'])} | {cellule(x['constat'])} | {fmt(x['impact_dh']) or '?'} "
                 f"| {court(x['source'])} | {x['origine']} |")
    L += ["", "## Incohérences (prix, unités, calculs)", "", "| Lot | Poste | Constat | Source | Origine |", "|---|---|---|---|---|"]
    for x in inc[:30]:
        L.append(f"| {x['lot']} | {cellule(x['poste'])} | {cellule(x['constat'])} | {court(x['source'])} | {x['origine']} |")
    L += ["", "## Avancement par lot", "",
          "Les décomptes et situations récents arrivent par Outlook : ils ne sont pas lus ici.", "",
          "| Lot | Entreprise | Dernière pièce trouvée | Date | Avancement lu | Source |", "|---|---|---|---|---|---|"]
    for code, lot in P.lots.items():
        a = av.get(code)
        if a:
            L.append(f"| {code} | {cellule(lot.get('entreprise', ''))} | {cellule(Path(a['fichier']).name)} | {a['date']} | "
                     f"{cellule(' / '.join(a['extrait']) or 'pourcentage non lisible')} | {cellule(P.source(a['fichier']))} |")
        else:
            L.append(f"| {code} | {cellule(lot.get('entreprise', ''))} | aucun décompte en texte | – | non trouvé | voir Outlook |")
    L += ["", "## Pièces de marché repérées", "", "| Lot | Pièce | Fichier |", "|---|---|---|"]
    for r in inv:
        if r["piece"] in ("marche", "bordereau retenu", "avenant"):
            L.append(f"| {r['lot']} | {r['piece']} | {cellule(r['fichier'])} |")
    notes = [f"- {c} : {l['note']}" for c, l in P.lots.items() if l.get("note")]
    sans = [c for c in P.lots if c not in lots_dqe]
    L += ["", "## Limites", "", f"- Lots sans bordereau chiffré lisible : {', '.join(sans) or 'aucun'}.", *notes,
          "- Les plans PDF (dessins) ne sont pas lus. Les TCO comparatifs : 1re offre du tableau seulement.",
          "- Détail : `03_TRAVAIL\\analyses\\postes.csv`, `pistes.csv`, `inventaire.csv`."]
    out = P.publier / "analyses" / f"{jour}_marches.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    ecrire_csv(P.sortie / "pistes.csv", main + dbl + inc,
               ["lot", "type", "poste", "constat", "impact_dh", "impact_origine", "qwen_dh", "source", "origine", "statut"])
    print(f"Rapport : {out}")
    return out


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("etapes", nargs="*", choices=ETAPES + [[]], default=[])
    ap.add_argument("--projet", default="TBRP")
    ap.add_argument("--lots", nargs="*", help="lots relus par Qwen (défaut : tous)")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    a = ap.parse_args()
    etapes = a.etapes or ETAPES
    P = Projet(a.projet)
    inv = inventaire(P) if "inventaire" in etapes else list(csv.DictReader(
        (P.sortie / "inventaire.csv").open(encoding="utf-8-sig"), delimiter=";"))
    if "extraction" in etapes:
        extraction(P)
    postes = charger_postes(P)
    pistes = croisement(P, postes)
    lots = a.lots or sorted({p["lot"] for p in postes})
    if "analyse" in etapes:
        pistes += analyse(P, postes, lots)
    else:
        for c in sorted({p["lot"] for p in postes}):
            pistes += lire_cache(P, c, [p for p in postes if p["lot"] == c]) if P.cache.exists() else []
    av = avancement(P)
    if "rapport" in etapes:
        rapport(P, a.date, inv, postes, pistes, av)


if __name__ == "__main__":
    main()
