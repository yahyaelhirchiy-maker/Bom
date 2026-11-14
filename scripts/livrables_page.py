"""Rassemble les derniers livrables de D:\\BK\\04_PUBLIER pour la page privée « BOSKO – Livrables ».

  python livrables_page.py [--max 60]
      -> D:\\BK\\00_SYSTEME\\_page\\livrables.json (lu par modeles\\page_livrables\\index.html)
      -> affiche les livrables nouveaux depuis la dernière publication (pour la notification)
  python livrables_page.py --publie
      -> marque la publication comme faite (à lancer après un publish réussi)

Les .md sont repris en entier ; les PDF / xlsx (CR, ODJ, rapports) sont listés avec leur chemin sur le PC.
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

PUBLIER = Path(r"D:\BK\04_PUBLIER")
SORTIE = Path(r"D:\BK\00_SYSTEME\_page\livrables.json")
DERNIERE = Path(r"D:\BK\03_TRAVAIL\_cache\page_derniere_publication.txt")
TYPES = {"briefing": "Briefing", "mails": "Mails", "recap": "Récap", "hebdo": "Rapport hebdo",
         "cr": "CR de réunion", "odj": "Ordre du jour"}


def items():
    out = []
    for dossier, libelle in TYPES.items():
        for f in (PUBLIER / dossier).glob("*") if (PUBLIER / dossier).is_dir() else []:
            if f.suffix.lower() not in (".md", ".pdf", ".xlsx"):
                continue
            # un CR/ODJ = xlsx + pdf du même nom : une seule entrée, le PDF suffit
            if f.suffix.lower() == ".xlsx" and f.with_suffix(".pdf").exists():
                continue
            date = datetime.fromtimestamp(f.stat().st_mtime)
            md = f.read_text(encoding="utf-8-sig") if f.suffix.lower() == ".md" else ""
            out.append({"id": f"{dossier}/{f.name}", "type": dossier, "libelle": libelle,
                        "titre": f.stem, "date": date.isoformat(timespec="minutes"),
                        "md": md, "fichier": "" if md else str(f)})
    return sorted(out, key=lambda x: x["date"], reverse=True)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    a = argparse.ArgumentParser(); a.add_argument("--max", type=int, default=60); a.add_argument("--publie", action="store_true")
    x = a.parse_args()
    if x.publie:
        DERNIERE.parent.mkdir(parents=True, exist_ok=True)
        DERNIERE.write_text(datetime.now().isoformat(timespec="minutes"), encoding="utf-8")
        print("Publication notée.")
        return
    tous = items()[: x.max]
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps({"genere_le": datetime.now().isoformat(timespec="minutes"), "items": tous},
                                 ensure_ascii=False), encoding="utf-8")
    depuis = DERNIERE.read_text(encoding="utf-8").strip() if DERNIERE.exists() else ""
    nouveaux = [i for i in tous if i["date"] > depuis]
    print(f"{len(tous)} livrables dans la page ; nouveaux depuis {depuis or 'toujours'} : {len(nouveaux)}")
    for i in nouveaux:
        print(f"NOUVEAU | {i['libelle']} | {i['titre']}")


if __name__ == "__main__":
    main()
