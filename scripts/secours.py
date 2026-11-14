r"""Secours local gratuit quand un passage Claude n'a pas tourné (limite atteinte).

  python secours.py matin|apres-midi [--projet TBRP] [--sortie DOSSIER]

Si un livrable du jour existe déjà (04_PUBLIER\briefing pour matin, recap pour
après-midi), ne fait rien. Sinon : lance digest.py, lit digest.md, ETAT.md et les
notes en attente, demande un texte court au modèle local Ollama (localhost, rien
ne sort du PC) et l'écrit dans le même dossier, marqué « [SECOURS …] ».
Ajoute une ligne dans 04_PUBLIER\en_attente.txt. Ne touche ni aux registres ni aux notes.
Limite : ne lit pas les mails, pas de brouillon, pas de page privée, pas de notification.
"""
import argparse, json, subprocess, sys, urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BK = Path(r"D:\BK")
TRAVAIL = BK / "03_TRAVAIL"
PUBLIER = BK / "04_PUBLIER"
NOTES = BK / "02_ENTRANT" / "notes_en_attente.md"
DIGEST = TRAVAIL / "_cache" / "digest.md"
ETAT = TRAVAIL / "ETAT.md"
EN_ATTENTE = PUBLIER / "en_attente.txt"
SCRIPTS = Path(__file__).resolve().parent
OLLAMA = "http://localhost:11434/api/chat"
MODELE = "qwen3:14b"
DELAI_S = 300
DOSSIER = {"matin": "briefing", "apres-midi": "recap"}

CONSIGNE = {
    "matin": (
        "Écris le briefing du matin du chef de projet MOD, en français simple, phrases courtes. "
        "Commence exactement par la ligne « ## En bref » suivie de 3 phrases écoutables à voix haute "
        "(ce qui presse aujourd'hui). Puis « ## Échéances », « ## Relances », « ## Chemin critique » "
        "en listes courtes. 30 lignes maximum."
    ),
    "apres-midi": (
        "Écris le récap de l'après-midi du chef de projet MOD, en français simple, phrases courtes : "
        "« ## En bref » (3 phrases), puis « ## Reste à faire aujourd'hui » et « ## Demain » en listes "
        "courtes. 25 lignes maximum."
    ),
}
REGLES = (
    "Tu aides le chef de projet MOD (AEDGE) d'un chantier. N'utilise que les informations fournies. "
    "N'invente aucun nom, date ni montant. Si une information manque, dis-le. "
    "Les notes dictées sont signalées comme non traitées : ne les présente pas comme faites."
)


def lire(p, n=6000):
    try:
        return p.read_text(encoding="utf-8")[:n]
    except FileNotFoundError:
        return "(absent)"


def deja_fait(dossier, jour):
    return dossier.exists() and any(dossier.glob(f"{jour}_*.md"))


def demarrer_ollama():
    """Lance le serveur Ollama s'il ne répond pas (après un redémarrage, l'appli ne le démarre pas toujours)."""
    import os, time
    try:
        urllib.request.urlopen(OLLAMA.replace("/api/chat", "/api/version"), timeout=5)
        return
    except OSError:
        pass
    exe = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Ollama" / "ollama.exe"
    env = dict(os.environ, OLLAMA_MODELS=r"D:\Ollama\models")
    subprocess.Popen([str(exe), "serve"], env=env, creationflags=0x08000008,  # détaché, sans fenêtre
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(2)
        try:
            urllib.request.urlopen(OLLAMA.replace("/api/chat", "/api/version"), timeout=5)
            return
        except OSError:
            pass


def demander(texte, consigne):
    demarrer_ollama()
    corps = json.dumps({
        "model": MODELE, "stream": False, "think": False,
        "options": {"temperature": 0.3},
        "messages": [{"role": "system", "content": REGLES},
                     {"role": "user", "content": consigne + "\n\n" + texte}],
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA, corps, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=DELAI_S) as r:
        return json.loads(r.read().decode("utf-8"))["message"]["content"].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("passage", choices=list(DOSSIER))
    ap.add_argument("--projet", default="TBRP")
    ap.add_argument("--sortie", help="dossier de sortie (test) ; défaut 04_PUBLIER\\briefing|recap")
    a = ap.parse_args()
    now = datetime.now()
    jour = now.strftime("%Y-%m-%d")
    dossier = Path(a.sortie) if a.sortie else PUBLIER / DOSSIER[a.passage]
    if deja_fait(dossier, jour):
        print(f"Livrable du jour déjà présent dans {dossier} : rien à faire.")
        return
    subprocess.run([sys.executable, str(SCRIPTS / "digest.py"), "--projet", a.projet], check=False)
    texte = (f"Date : {jour}\n\n# Digest\n{lire(DIGEST)}\n\n# État\n{lire(ETAT)}\n\n"
             f"# Notes dictées non traitées\n{lire(NOTES, 3000)}")
    try:
        sortie = demander(texte, CONSIGNE[a.passage])
    except Exception as e:
        print(f"Modèle local injoignable ou trop lent : {e}")
        sys.exit(1)
    dossier.mkdir(parents=True, exist_ok=True)
    f = dossier / f"{now:%Y-%m-%d_%H%M}.md"
    f.write_text(f"[SECOURS – modèle local, à relire]\n\n{sortie}\n", encoding="utf-8")
    if not a.sortie:
        with EN_ATTENTE.open("a", encoding="utf-8") as g:
            g.write(f"{now:%Y-%m-%d %H:%M} {a.passage} : passage Claude manqué, mails et notes non traités ({f.name})\n")
    print(f"Écrit : {f}")


if __name__ == "__main__":
    main()
