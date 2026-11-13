"""Tri GRATUIT (sans IA) des mails des 3 derniers jours, avant de réveiller Claude.

  python tri_mails.py trier      -> _cache/a_traiter_delicat.txt et a_traiter_simple.txt
  python tri_mails.py valider N  -> marque comme traités les mails du lot N (delicat|simple)

Rien de nouveau = fichiers vides = Claude n'est pas lancé = 0 token.
Un mail n'est marqué « traité » qu'après un passage réussi de Claude :
si la limite est atteinte, il est repris au passage suivant.
"""
import csv, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import outlook  # noqa: E402

C = outlook.TRAVAIL / "_cache"
TRAITES = C / "traites.txt"
RECLASSER = C / "a_reclasser.txt"       # N écrits par Claude : « simple » qui était délicat
FORCES = C / "forces_delicat.txt"       # EntryID à repasser en délicat

IGNORER_EXP = re.compile(r"no-?reply|ne-pas-repondre|newsletter|notification|mailer-daemon|sharepoint|teams|calendar", re.I)
IGNORER_OBJ = re.compile(r"^(accepté|refusé|provisoire|accepted|declined|tentative)\b|réponse automatique|automatic reply|out of office|absent", re.I)
DELICAT = re.compile(r"montant|d[ée]compte|avenant|p[ée]nalit|r[ée]clamation|retard|mise en demeure|litige|factur|paiement|"
                     r"budget|surco[uû]t|contentieux|r[ée]siliation|r[ée]serve|garantie|caution|prix|devis", re.I)
ROLES_DELICATS = {"investisseur", "direction", "moa", "fonds"}


def lire_set(f):
    return set(f.read_text(encoding="utf-8").split()) if f.exists() else set()


def roles():
    f = outlook.CONTACTS
    if not f.exists():
        return {}
    with open(f, encoding="utf-8-sig") as h:
        return {c["email"].lower(): c["role"].lower() for c in csv.DictReader(h, delimiter=";")}


def trier():
    C.mkdir(parents=True, exist_ok=True)
    deja, forces, role = lire_set(TRAITES), lire_set(FORCES), roles()
    # Lus ou non : un mail ouvert sur le téléphone doit quand même être traité.
    ids = json.loads(outlook.CACHE.read_text(encoding="utf-8")) if outlook.CACHE.exists() else {}
    lots = {"delicat": ([], []), "simple": ([], [])}
    ignores = 0
    for i, m in enumerate(outlook.recents(3), 1):
        if m.EntryID in deja:
            continue
        exp = (outlook.expediteur(m) or "").lower()
        if IGNORER_EXP.search(exp) or IGNORER_OBJ.search(m.Subject or ""):
            ignores += 1
            deja.add(m.EntryID)
            continue
        texte = (m.Subject or "") + " " + (m.Body or "")[:2000]
        niv = "delicat" if (m.EntryID in forces or DELICAT.search(texte) or role.get(exp) in ROLES_DELICATS) else "simple"
        n = f"M{i}"
        ids[n] = m.EntryID
        apercu = " ".join((m.Body or "").split())[:160]
        lots[niv][0].append(f"{n} | {m.ReceivedTime:%Y-%m-%d %H:%M} | {exp} | {m.Subject} | {apercu}")
        lots[niv][1].append(m.EntryID)
    outlook.CACHE.write_text(json.dumps(ids), encoding="utf-8")
    TRAITES.write_text("\n".join(deja), encoding="utf-8")
    for niv, (lignes, eids) in lots.items():
        (C / f"a_traiter_{niv}.txt").write_text("\n".join(lignes), encoding="utf-8")
        (C / f"lot_{niv}.json").write_text(json.dumps(eids), encoding="utf-8")
    print(f"délicats : {len(lots['delicat'][0])} | simples : {len(lots['simple'][0])} | ignorés : {ignores}")


def valider(niv):
    ids = json.loads(outlook.CACHE.read_text(encoding="utf-8"))
    a_reclasser = {ids[n] for n in lire_set(RECLASSER) if n in ids}
    eids = set(json.loads((C / f"lot_{niv}.json").read_text(encoding="utf-8")))
    with open(TRAITES, "a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(eids - a_reclasser))
    if a_reclasser:
        with open(FORCES, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(a_reclasser))
    RECLASSER.unlink(missing_ok=True)
    print(f"{len(eids - a_reclasser)} traités, {len(a_reclasser)} repassés en délicat")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    trier() if sys.argv[1] == "trier" else valider(sys.argv[2])
