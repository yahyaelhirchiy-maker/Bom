r"""Lecture locale des plans (PDF dessinés) par un modèle d'images (Ollama, gratuit, rien ne sort du PC).

  python analyse_plans.py [lire] [rapport] [--projet TBRP] [--lots VER ALU] [--sans-horaires]

lire    : chaque page de plan -> image (PyMuPDF, en mémoire) -> qwen2.5vl relève les ouvrages dessinés.
          Réponses mises en cache page par page (03_TRAVAIL\analyses\plans\_cache) : on reprend où on s'est arrêté.
          Respecte les horaires de la config (fin 18 h, pauses du dépannage local) ; s'arrête seul à l'heure de fin.
rapport : Python seul. ouvrages.csv + 04_PUBLIER\analyses\<date>_plans.md : ouvrages dessinés sans poste
          ressemblant au bordereau, repères apparus depuis les plans du marché, interfaces. Tout est « à vérifier ».
Config : modeles\analyse_marches\<projet>.json, clé « plans ». Les PDF de 01_MIROIR sont ouverts en lecture seule.
"""
import argparse, base64, csv, hashlib, json, re, sys, time, unicodedata, urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pymupdf

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from secours import demarrer_ollama  # noqa: E402

OLLAMA = "http://localhost:11434"
MODELE = "qwen2.5vl:7b"
ECHELLE = 1.6          # ~115 dpi : une page A3 = 1 image de 1900 px, lisible par le modèle
TUILE = 2000           # côté maxi d'une image envoyée ; les grands formats sont découpés
CONSIGNE = (
    "Page d'un plan de chantier (lot : {lot}). Relève en JSON ce qui est dessiné ou écrit : "
    '{{"titre":"","niveau":"","indice":"","ouvrages":[{{"repere":"","type":"","dimensions":"","quantite":"","materiau":"","remarque":""}}],'
    '"interfaces":[{{"ouvrage":"","lot_probable":""}}]}}. '
    "« ouvrages » : éléments du lot (repères, types, cotes, matériaux, accessoires, fixations). "
    "« interfaces » : ouvrages visibles qui relèvent d'un autre lot (réservations, rebouchages, calfeutrements, supports, habillages…). "
    "Recopie les textes et cotes lisibles. Laisse vide ce qui n'est pas lisible. N'invente rien. 25 ouvrages maximum."
)
MOTS_VIDES = set("avec pour dans sans selon type ensemble suivant compris toute toutes tous fourniture pose mise oeuvre "
                 "niveau plan detail details coupe vue vues dessus dessous elevation structure partie element elements "
                 "repere reperes ligne lignes route voiture voitures cimetiere intersection fabricant description "
                 "designation caracteristiques taille calcule communications feature features fonctionnalites "
                 "modifications titre legende echelle indice cartouche nord dessin dessine valeur valeurs".split())


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def mots(s):
    return {m for m in norm(s).split() if len(m) >= 5 and m not in MOTS_VIDES}


class Config:
    def __init__(self, projet):
        c = json.loads((SCRIPTS.parent / "modeles" / "analyse_marches" / f"{projet}.json").read_text(encoding="utf-8"))
        self.projet, self.lots_marche = projet, c["lots"]
        self.p = c["plans"]
        self.racine = Path(self.p["racine_miroir"])
        self.travail = Path(c["travail"]) / "analyses" / "plans"
        self.publier = Path(c["publier"]) / "analyses"
        self.postes = Path(c["travail"]) / "analyses" / "postes.csv"
        self.cache = self.travail / "_cache"
        self.exclure = re.compile(self.p["exclure"], re.I)
        self.garder = re.compile(self.p.get("garder", "."), re.I)

    def perimetre(self, lot):
        l = self.p["lots"][lot]
        return l.get("perimetre") or self.lots_marche.get(lot, {}).get("perimetre", "")

    def intitule(self, lot):
        l = self.p["lots"][lot]
        per = re.split(r" : | \(|;", self.perimetre(lot))[0].strip()
        return l.get("intitule") or self.lots_marche.get(lot, {}).get("intitule") or per or lot

    def fichiers(self, lot):
        """PDF du lot, plus récents d'abord (date AAMMJJ en tête de dossier, sinon date de fichier)."""
        l, vus = self.p["lots"][lot], {}
        for d in l["dossiers"] + l.get("marche", []):
            for f in (self.racine / d).rglob("*"):
                rel = str(f.relative_to(self.racine))
                if f.suffix.lower() == ".pdf" and not self.exclure.search(norm(rel)) and self.garder.search(norm(f.name)):
                    vus[rel] = f

        def cle(rel):
            m = re.findall(r"(?:^|[\\/])(\d{6})[ .]", rel)
            return (m[-1] if m else "000000", vus[rel].stat().st_mtime)
        return sorted(vus, key=cle, reverse=True)

    def marche(self, lot):
        return tuple(self.p["lots"][lot].get("marche", []))


# ---------- horaires ----------
def hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def minute():
    n = datetime.now()
    return n.hour * 60 + n.minute


def hors_horaires(cfg):
    h = cfg.p["horaires"]
    return not (hm(h["debut"]) <= minute() < hm(h["fin"]))


def ollama(chemin, corps=None, delai=900):
    req = urllib.request.Request(OLLAMA + chemin, json.dumps(corps).encode() if corps else None,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=delai) as r:
        return json.loads(r.read().decode("utf-8"))


def liberer():
    """Décharge le modèle d'images de la carte graphique (pour laisser la place au dépannage local)."""
    try:
        ollama("/api/generate", {"model": MODELE, "keep_alive": 0}, 60)
    except Exception:
        pass


def attendre_tour(cfg):
    """Pause du dépannage local (créneaux de la config) ou autre modèle chargé : on libère et on attend."""
    signale = False
    while True:
        dans_pause = any(hm(a) <= minute() < hm(b) for a, b in (p.split("-") for p in cfg.p["horaires"]["pauses"]))
        try:
            autres = [m["name"] for m in ollama("/api/ps", delai=10).get("models", []) if m["name"] != MODELE]
        except Exception:
            autres = []
        if not dans_pause and not autres:
            return
        if not signale:
            print(f"{datetime.now():%H:%M} pause (dépannage local / {', '.join(autres) or 'créneau réservé'})")
            liberer()
            signale = True
        if hors_horaires(cfg):
            return
        time.sleep(60)


# ---------- lecture ----------
def images(page):
    """Page -> liste d'images PNG (base64). A3+ en portrait = plan tourné : on le remet à l'endroit.
    Grand format : découpe en tuiles dans les coordonnées de la page (5 % de recouvrement)."""
    r = page.rect
    rot = 90 if (r.height > r.width and min(r.width, r.height) > 780) else 0   # > ~275 mm
    m = pymupdf.Matrix(ECHELLE, ECHELLE).prerotate(rot)
    nx, ny = -(-int(r.width * ECHELLE) // TUILE), -(-int(r.height * ECHELLE) // TUILE)
    if nx * ny == 1:
        return [base64.b64encode(page.get_pixmap(matrix=m, alpha=False).tobytes("png")).decode()]
    res, tw, th = [], r.width / nx, r.height / ny
    for j in range(ny):
        for i in range(nx):
            clip = pymupdf.Rect(r.x0 + max(0, i * tw - tw * .05), r.y0 + max(0, j * th - th * .05),
                                r.x0 + min(r.width, (i + 1) * tw + tw * .05), r.y0 + min(r.height, (j + 1) * th + th * .05))
            res.append(base64.b64encode(page.get_pixmap(matrix=m, clip=clip, alpha=False).tobytes("png")).decode())
    return res


def cle_cache(rel, n, t):
    return hashlib.md5(rel.encode("utf-8")).hexdigest()[:10] + f"_p{n:03d}_t{t}.json"


def lire(cfg, lots, horaires=True):
    demarrer_ollama()
    cfg.cache.mkdir(parents=True, exist_ok=True)
    total = 0
    for lot in lots:
        fichiers = cfg.fichiers(lot)
        print(f"{datetime.now():%H:%M} lot {lot} : {len(fichiers)} fichiers", flush=True)
        consigne = CONSIGNE.format(lot=cfg.intitule(lot))
        for rel in fichiers:
            try:
                doc = pymupdf.open(cfg.racine / rel)
            except Exception as e:
                print(f"  illisible : {rel} ({e})")
                continue
            for n, page in enumerate(doc):
                if (cfg.cache / cle_cache(rel, n, 0)).exists():
                    continue
                try:
                    imgs = images(page)
                except Exception as e:
                    print(f"  page {n + 1} non rendue : {e}")
                    continue
                for t, img in enumerate(imgs):
                    f = cfg.cache / cle_cache(rel, n, t)
                    if f.exists():
                        continue
                    if horaires:
                        if hors_horaires(cfg):
                            print(f"{datetime.now():%H:%M} heure de fin : arrêt ({total} images lues).")
                            liberer()
                            return False
                        attendre_tour(cfg)
                    t0 = time.time()
                    try:
                        rep = ollama("/api/chat", {
                            "model": MODELE, "stream": False, "format": "json", "keep_alive": "10m",
                            "options": {"temperature": 0.1, "num_ctx": 8192, "num_predict": 1500},
                            "messages": [{"role": "user", "content": consigne, "images": [img]}]})
                        contenu = rep["message"]["content"]
                        try:
                            data = json.loads(contenu)
                        except json.JSONDecodeError:
                            data = {"brut": contenu[:3000]}
                    except Exception as e:
                        print(f"  erreur modèle p{n + 1}/t{t} : {e} ; nouvel essai plus tard")
                        time.sleep(20)
                        continue
                    data.update(lot=lot, fichier=rel, page=n + 1, tuile=t, nb_tuiles=len(imgs))
                    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                    total += 1
                    print(f"  {lot} p{n + 1}/{len(doc)} t{t + 1}/{len(imgs)} {round(time.time() - t0)} s  {Path(rel).name[:60]}",
                          flush=True)
    liberer()
    return True


# ---------- rapport (Python seul) ----------
def court(rel, page):
    return f"{Path(rel).name} p.{page}"


def rapport(cfg):
    cfg.travail.mkdir(parents=True, exist_ok=True)
    cfg.publier.mkdir(parents=True, exist_ok=True)
    retenus = {rel for lot in cfg.p["ordre"] for rel in cfg.fichiers(lot)}
    reps = [r for r in (json.loads(f.read_text(encoding="utf-8")) for f in sorted(cfg.cache.glob("*.json")))
            if r["fichier"] in retenus]
    # bordereaux : mots des désignations par lot
    bord = defaultdict(set)
    if cfg.postes.exists():
        with cfg.postes.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter=";"):
                bord[r["lot"]] |= mots(r["designation"])
    tous_bord = set().union(*bord.values()) if bord else set()

    lignes, interfaces = [], []
    for r in reps:
        for o in r.get("ouvrages") or []:
            if not isinstance(o, dict):
                continue
            typ = str(o.get("type", "")).strip()
            if not typ and not o.get("repere"):
                continue
            lignes.append(dict(lot=r["lot"], repere=str(o.get("repere", "")).strip(), type=typ,
                               dimensions=o.get("dimensions", ""), quantite=o.get("quantite", ""),
                               materiau=o.get("materiau", ""), remarque=o.get("remarque", ""),
                               fichier=r["fichier"], page=r["page"], tuile=r["tuile"], statut="à vérifier"))
        for i in r.get("interfaces") or []:
            if isinstance(i, dict) and i.get("ouvrage") and not re.search(r"lot|moins.value|avenant", norm(i["ouvrage"])):
                interfaces.append((r["lot"], str(i["ouvrage"]).strip(), str(i.get("lot_probable", "")).strip(),
                                   court(r["fichier"], r["page"])))
    with (cfg.travail / "ouvrages.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]) if lignes else ["lot"], delimiter=";")
        w.writeheader()
        w.writerows(lignes)

    # 1. ouvrages dessinés sans mot commun avec le bordereau du lot (ni d'aucun lot)
    sans = defaultdict(lambda: {"n": 0, "src": [], "ailleurs": False})
    for l in lignes:
        m = mots(l["type"] + " " + str(l["materiau"]))
        if not m:
            continue
        ref = tous_bord if l["lot"] == "ARC" else bord.get(l["lot"], set())
        if not ref or m & ref:
            continue
        k = (l["lot"], norm(l["type"]))
        s = sans[k]
        s["n"] += 1
        s["type"] = l["type"]
        s["ailleurs"] = bool(m & tous_bord)
        src = court(l["fichier"], l["page"])
        if len(s["src"]) < 3 and src not in s["src"]:
            s["src"].append(src)

    # 2. repères apparus depuis les plans du marché
    nouveaux = []
    for lot in cfg.p["lots"]:
        mar = cfg.marche(lot)
        if not mar:
            continue
        rep_m = {norm(l["repere"]) for l in lignes if l["lot"] == lot and l["fichier"].startswith(mar)}
        if not rep_m:
            continue
        vus = {}
        for l in lignes:
            r = norm(l["repere"])
            if l["lot"] == lot and r and not l["fichier"].startswith(mar) and r not in rep_m and len(r) <= 12:
                vus.setdefault(r, (l["repere"], l["type"], court(l["fichier"], l["page"])))
        nouveaux += [(lot,) + v for v in vus.values()]

    # avancement de la lecture
    pages_lues = defaultdict(set)
    for r in reps:
        pages_lues[r["lot"]].add((r["fichier"], r["page"]))
    jour = datetime.now().strftime("%Y-%m-%d")
    top = sorted(sans.items(), key=lambda kv: -kv[1]["n"])
    L = [f"# Plans et marchés – {cfg.projet} – {jour}", "",
         "*Lecture des plans par le modèle local (qwen2.5vl), comparaison en Python. Tout est « à vérifier » sur le plan cité.*", "",
         "## En bref", "",
         f"{sum(len(v) for v in pages_lues.values())} pages de plans lues, {len(lignes)} ouvrages relevés, sur {len(pages_lues)} lot(s). "
         f"{len(top)} types d'ouvrages dessinés n'ont aucun mot commun avec le bordereau de leur lot : pistes d'oubli ou d'avenant. "
         f"{len(nouveaux)} repères apparaissent dans les plans récents sans figurer aux plans annexés au marché.", "",
         "## Ouvrages dessinés sans poste ressemblant au bordereau", "",
         "| Lot | Ouvrage dessiné | Vu | Dans un autre bordereau ? | Où (plan, page) |", "|---|---|---|---|---|"]
    for (lot, _), s in top[:80]:
        L.append(f"| {lot} | {s['type'][:70]} | {s['n']}× | {'oui' if s['ailleurs'] else 'non'} | {'; '.join(s['src'])} |")
    L += ["", "## Repères apparus depuis les plans du marché", ""]
    if nouveaux:
        L += ["| Lot | Repère | Type | Où |", "|---|---|---|---|"]
        L += [f"| {a} | {b} | {c[:50]} | {d} |" for a, b, c, d in nouveaux[:80]]
    else:
        L.append("Rien de comparable pour l'instant (plans du marché pas encore lus ou sans repères).")
    L += ["", "## Interfaces vues sur les plans (autre lot probable)", ""]
    vus_i = set()
    for lot, o, lp, src in interfaces:
        k = (lot, norm(o))
        if k in vus_i or len(vus_i) >= 60:
            continue
        vus_i.add(k)
        L.append(f"- {lot} : {o[:80]} → {lp or '?'} ({src})")
    L += ["", "## Avancement de la lecture", "", "| Lot | Pages lues |", "|---|---|"]
    L += [f"| {lot} | {len(pages_lues.get(lot, ()))} |" for lot in cfg.p["ordre"]]
    L += ["", "## Limites", "",
          "- Le modèle repère les ouvrages ; il ne mesure pas. Aucune quantité n'est fiable sans relecture du plan.",
          "- « Sans poste ressemblant » = aucun mot commun avec le bordereau retenu : un poste rédigé autrement peut exister.",
          "- ALU : bordereau GM scanné, comparaison faite avec le BOQ du DCE.", ""]
    sortie = cfg.publier / f"{jour}_plans.md"
    sortie.write_text("\n".join(L), encoding="utf-8")
    print(f"Écrit : {sortie} ; {cfg.travail / 'ouvrages.csv'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("etapes", nargs="*", default=["lire", "rapport"])
    ap.add_argument("--projet", default="TBRP")
    ap.add_argument("--lots", nargs="*")
    ap.add_argument("--sans-horaires", action="store_true")
    a = ap.parse_args()
    cfg = Config(a.projet)
    if "lire" in a.etapes:
        if not a.sans_horaires and hors_horaires(cfg):
            print("Hors horaires : rien à faire.")
        else:
            lire(cfg, a.lots or cfg.p["ordre"], not a.sans_horaires)
    if "rapport" in a.etapes:
        rapport(cfg)


if __name__ == "__main__":
    main()
