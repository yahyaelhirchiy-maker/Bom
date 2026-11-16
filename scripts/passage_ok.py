r"""Repère des passages BOSKO (matin / apres-midi) pour le rattrapage automatique. Gratuit, sans Claude.

  python passage_ok.py etat          -> OK | EN_COURS | A_FAIRE <passage>  (passage selon l'heure : avant 12h30 = matin)
  python passage_ok.py debut <passage>   (premier geste d'un passage)
  python passage_ok.py fin <passage>     (dernier geste, après publication)
Marqueurs : 03_TRAVAIL\_cache\passage_<passage>_AAAA-MM-JJ.debut / .ok
"""
import sys, time
from datetime import datetime
from pathlib import Path

C = Path(r"D:\BK\03_TRAVAIL\_cache")
EN_COURS_MIN = 25


def f(p, ext):
    return C / f"passage_{p}_{datetime.now():%Y-%m-%d}.{ext}"


def main():
    a = sys.argv[1:] or ["etat"]
    C.mkdir(exist_ok=True)
    if a[0] in ("debut", "fin"):
        f(a[1], "debut" if a[0] == "debut" else "ok").write_text(f"{datetime.now():%H:%M}\n")
        print("noté")
        return
    p = "matin" if datetime.now().hour * 60 + datetime.now().minute < 12 * 60 + 30 else "apres-midi"
    if f(p, "ok").exists():
        print("OK")
    elif f(p, "debut").exists() and time.time() - f(p, "debut").stat().st_mtime < EN_COURS_MIN * 60:
        print("EN_COURS")
    else:
        print("A_FAIRE", p)


if __name__ == "__main__":
    main()
