"""Convertit une seule fois les documents (PDF, DOCX, XLSX) en texte.

Usage :  python convertir_texte.py C:\\BK\\02_ENTRANT [C:\\BK\\03_TRAVAIL\\_texte]

- Ne lit jamais deux fois le même fichier : si le .txt existe et est plus
  récent que l'original, il est ignoré.
- Ne modifie ni ne supprime jamais l'original (lecture seule).
"""
import sys
from pathlib import Path

SORTIE_DEFAUT = Path(r"C:\BK\03_TRAVAIL\_texte")


def lire_pdf(p):
    from pypdf import PdfReader
    return "\n".join((page.extract_text() or "") for page in PdfReader(p).pages)


def lire_docx(p):
    from docx import Document
    return "\n".join(par.text for par in Document(p).paragraphs)


def lire_xlsx(p):
    from openpyxl import load_workbook
    lignes = []
    for ws in load_workbook(p, read_only=True, data_only=True).worksheets:
        lignes.append(f"### Feuille : {ws.title}")
        for row in ws.iter_rows(values_only=True):
            if any(c is not None for c in row):
                lignes.append(";".join("" if c is None else str(c) for c in row))
    return "\n".join(lignes)


LECTEURS = {".pdf": lire_pdf, ".docx": lire_docx, ".xlsx": lire_xlsx, ".xlsm": lire_xlsx}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    source = Path(sys.argv[1])
    sortie = Path(sys.argv[2]) if len(sys.argv) > 2 else SORTIE_DEFAUT
    faits = ignores = erreurs = 0
    for f in source.rglob("*"):
        lecteur = LECTEURS.get(f.suffix.lower())
        if not lecteur or f.name.startswith("~$"):
            continue
        cible = sortie / f.relative_to(source).with_suffix(f.suffix + ".txt")
        if cible.exists() and cible.stat().st_mtime >= f.stat().st_mtime:
            ignores += 1
            continue
        try:
            texte = lecteur(f)
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_text(f"SOURCE: {f}\n\n{texte}", encoding="utf-8")
            faits += 1
        except Exception as e:  # un fichier illisible ne bloque pas les autres
            print(f"ERREUR {f} : {e}")
            erreurs += 1
    print(f"Convertis : {faits} | déjà à jour : {ignores} | erreurs : {erreurs}")


if __name__ == "__main__":
    main()
