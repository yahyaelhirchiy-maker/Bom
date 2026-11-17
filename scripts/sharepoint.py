r"""Agent SharePoint : carte du SharePoint du chantier et dépôts SANS RISQUE.

Le dossier 038 de D:\BK\01_MIROIR est synchronisé par OneDrive : y copier un fichier = le mettre sur SharePoint.
Règles codées ici (pas seulement dans les consignes) :
- on AJOUTE seulement : jamais d'écrasement (un nom déjà pris → « (v2) », « (v3) »…), jamais de suppression,
  jamais de déplacement ni de renommage d'un fichier existant ;
- uniquement sous 038 ; création d'un sous-dossier seulement avec --creer ;
- chaque dépôt est journalisé dans 03_TRAVAIL\registres\sharepoint_journal.csv.

Commandes :
  carte [--profondeur 4]          → 03_TRAVAIL\_cache\sharepoint_carte.txt (dossiers, nb fichiers, dernier fichier)
  cherche "<mot>" [--max 30]      → fichiers dont le nom contient le mot (chemin relatif à 038)
  existe "<nom de fichier>"       → le fichier est-il déjà sur SharePoint (même nom, n'importe où) ?
  deposer <fichier…> --dans "<dossier relatif à 038>" [--creer] [--motif "…"]
"""
import argparse, csv, datetime as dt, os, shutil, sys
from pathlib import Path

RACINE = Path(r"D:\BK\01_MIROIR\OneDrive - AEDGE Partners\038")
TRAVAIL = Path(r"D:\BK\03_TRAVAIL")
CARTE = TRAVAIL / "_cache" / "sharepoint_carte.txt"
JOURNAL = TRAVAIL / "registres" / "sharepoint_journal.csv"


def rel(p):
    return str(Path(p).relative_to(RACINE))


def carte(profondeur):
    lignes = []
    for d, sous, fichiers in os.walk(RACINE):
        niv = len(Path(d).relative_to(RACINE).parts)
        if niv >= profondeur:
            sous[:] = []
        sous.sort()
        if niv == 0:
            continue
        dernier = ""
        if fichiers:
            f = max(fichiers, key=lambda x: os.path.getmtime(os.path.join(d, x)))
            dernier = f"{dt.datetime.fromtimestamp(os.path.getmtime(os.path.join(d, f))):%Y-%m-%d} {f[:70]}"
        lignes.append(f"{'  ' * (niv - 1)}{Path(d).name} [{len(fichiers)}] {dernier}")
    CARTE.write_text("\n".join(lignes), encoding="utf-8")
    print(f"{len(lignes)} dossiers → {CARTE}")


def cherche(mot, maxi):
    mot, n = mot.lower(), 0
    for d, _, fichiers in os.walk(RACINE):
        for f in fichiers:
            if mot in f.lower():
                print(rel(os.path.join(d, f)))
                n += 1
                if n >= maxi:
                    return


def existe(nom):
    nom = nom.lower()
    for d, _, fichiers in os.walk(RACINE):
        for f in fichiers:
            if f.lower() == nom:
                print(f"OUI : {rel(os.path.join(d, f))}")
                return
    print("NON")


def nom_libre(cible):
    if not cible.exists():
        return cible
    for i in range(2, 100):
        c = cible.with_name(f"{cible.stem} (v{i}){cible.suffix}")
        if not c.exists():
            return c
    sys.exit(f"Trop de versions : {cible}")


def deposer(fichiers, dans, creer, motif):
    dossier = (RACINE / dans).resolve()
    if RACINE.resolve() not in dossier.parents and dossier != RACINE.resolve():
        sys.exit("Refusé : le dossier doit être sous 038.")
    if not dossier.is_dir():
        if not creer:
            sys.exit(f"Dossier absent : {dans} (ajoute --creer pour le créer)")
        dossier.mkdir(parents=True)
        print(f"DOSSIER CRÉÉ : {rel(dossier)}")
    neuf = not JOURNAL.exists()
    deposes = []
    with open(JOURNAL, "a", encoding="utf-8-sig", newline="") as j:
        w = csv.writer(j, delimiter=";")
        if neuf:
            w.writerow(["date", "fichier", "source", "motif"])
        for f in fichiers:
            src = Path(f)
            if not src.is_file():
                print(f"ABSENT, ignoré : {src}")
                continue
            if RACINE.resolve() in src.resolve().parents:
                print(f"Déjà sur SharePoint, ignoré : {src}")
                continue
            cible = nom_libre(dossier / src.name)
            shutil.copy2(src, cible)  # copie : l'original reste où il est
            w.writerow([f"{dt.datetime.now():%Y-%m-%d %H:%M}", rel(cible), str(src), motif])
            print(f"DÉPOSÉ : {rel(cible)}")
            deposes.append(str(cible))
    if deposes:  # second cerveau : le document déposé devient cherchable tout de suite
        try:
            import subprocess
            subprocess.run([sys.executable, str(Path(__file__).with_name("cerveau.py")), "ajouter", *deposes],
                           timeout=600, check=False)
        except Exception as e:
            print(f"Index du cerveau non mis à jour : {e}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = argparse.ArgumentParser()
    s = a.add_subparsers(dest="cmd", required=True)
    s.add_parser("carte").add_argument("--profondeur", type=int, default=4)
    c = s.add_parser("cherche"); c.add_argument("mot"); c.add_argument("--max", type=int, default=30)
    s.add_parser("existe").add_argument("nom")
    d = s.add_parser("deposer"); d.add_argument("fichiers", nargs="+"); d.add_argument("--dans", required=True)
    d.add_argument("--creer", action="store_true"); d.add_argument("--motif", default="")
    x = a.parse_args()
    {"carte": lambda: carte(x.profondeur), "cherche": lambda: cherche(x.mot, x.max), "existe": lambda: existe(x.nom),
     "deposer": lambda: deposer(x.fichiers, x.dans, x.creer, x.motif)}[x.cmd]()
