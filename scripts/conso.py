"""Combien coûte quoi : résumé de C:\\BK\\03_TRAVAIL\\logs\\consommation.csv.

  python conso.py [--jours 7]

Ne couvre que les tâches automatiques. Pour la session interactive : /usage.
"""
import argparse, csv, sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

F = Path(r"C:\BK\03_TRAVAIL\logs\consommation.csv")


def n(v):
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return 0.0


def main():
    a = argparse.ArgumentParser(); a.add_argument("--jours", type=int, default=7)
    depuis = (datetime.now() - timedelta(days=a.parse_args().jours)).strftime("%Y-%m-%d")
    t = defaultdict(lambda: [0, 0.0, 0.0, 0.0])  # passages, tokens entrée, tokens sortie, coût
    with open(F, encoding="utf-8-sig") as h:
        for r in csv.DictReader(h, delimiter=";"):
            if r["date"][:10] < depuis:
                continue
            k = (r["tache"], r["modele"], r["voie"])
            t[k][0] += 1
            t[k][1] += n(r["entree"]) + n(r["cache_lu"]) + n(r["cache_ecrit"])
            t[k][2] += n(r["sortie"])
            t[k][3] += n(r["cout_usd"])
    print(f"Depuis {depuis} | tâche | modèle | voie | passages | tokens entrée | tokens sortie | équiv. $")
    total = 0.0
    for (tache, mod, voie), (p, e, s, c) in sorted(t.items(), key=lambda x: -x[1][3]):
        print(f"{tache} | {mod} | {voie} | {p} | {e:,.0f} | {s:,.0f} | {c:.2f}".replace(",", " "))
        total += c
    print(f"TOTAL équivalent : {total:.2f} $")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
