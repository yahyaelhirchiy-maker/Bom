"""Outlook (bureau) en texte : lister, lire, préparer un brouillon. N'ENVOIE JAMAIS.

  python outlook.py lister [--jours 2] [--non-lus]
  python outlook.py lire N
  python outlook.py brouillon N --corps corps.txt [--pj fichier1 fichier2 ...]

N = numéro court donné par `lister` (1, 2…) ou par tri_mails.py (M1, M2…).
Le brouillon est une « Répondre à tous » dans le fil existant, Cc ajoutés
depuis contacts.csv (cc_systematique = oui), puis ENREGISTRÉ dans Brouillons.
Ce script ne contient volontairement aucun appel à .Send().
"""
import argparse, csv, html, json, re, sys
from datetime import datetime, timedelta
from pathlib import Path

import win32com.client

TRAVAIL = Path(r"D:\BK\03_TRAVAIL")
CACHE = TRAVAIL / "_cache" / "outlook_ids.json"
CONTACTS = TRAVAIL / "registres" / "contacts.csv"
BOITE_RECEPTION, CC = 6, 2


def ns():
    return win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")


def recu(m):
    """Date de réception sans fuseau (pywin32 la rend « aware », non comparable à datetime.now())."""
    return m.ReceivedTime.replace(tzinfo=None)


def recents(jours, non_lus=False):
    """Mails de la boîte de réception des N derniers jours, du plus récent au plus ancien.
    Pas de Restrict sur la date : son format dépend de la langue de Windows (M/d/yyyy en anglais)."""
    items = ns().GetDefaultFolder(BOITE_RECEPTION).Items
    if non_lus:
        items = items.Restrict("[UnRead] = True")
    items.Sort("[ReceivedTime]", True)
    depuis = datetime.now() - timedelta(days=jours)
    for m in items:
        try:
            if recu(m) < depuis:
                break
        except AttributeError:  # élément sans date de réception (rapport, etc.)
            continue
        if m.Class == 43:  # 43 = mail
            yield m


def expediteur(m):
    try:
        if m.SenderEmailType == "EX":
            return m.Sender.GetExchangeUser().PrimarySmtpAddress
    except Exception:
        pass
    return m.SenderEmailAddress


def couper_historique(texte):
    """Garde le message, coupe l'historique cité (économie de tokens)."""
    for motif in (r"\n_{5,}", r"\nDe\s?:.*\nEnvoy", r"\nFrom:.*\nSent", r"\nLe .* a écrit"):
        r = re.search(motif, texte)
        if r:
            texte = texte[: r.start()] + "\n[... historique coupé]"
            break
    return re.sub(r"\n\s*\n+", "\n\n", texte).strip()


def lister(jours, non_lus):
    ids = {k: v for k, v in (json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}).items() if k.startswith("M")}
    for i, m in enumerate(recents(jours, non_lus), 1):
        ids[str(i)] = m.EntryID
        apercu = " ".join((m.Body or "").split())[:160]
        pj = f" [PJ:{m.Attachments.Count}]" if m.Attachments.Count else ""
        print(f"{i} | {m.ReceivedTime:%Y-%m-%d %H:%M} | {expediteur(m)} | {m.Subject}{pj} | {apercu}")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(ids), encoding="utf-8")


def mail(n):
    ids = json.loads(CACHE.read_text(encoding="utf-8"))
    return ns().GetItemFromID(ids[str(n).upper()])


def lire(n):
    m = mail(n)
    print(f"DE: {m.SenderName} <{expediteur(m)}>\nA: {m.To}\nCC: {m.CC}")
    print(f"DATE: {m.ReceivedTime:%Y-%m-%d %H:%M}\nOBJET: {m.Subject}")
    for a in m.Attachments:
        print(f"PJ: {a.FileName}")
    print("\n" + couper_historique(m.Body))


def envoye(sujet, date):
    """Mail ENVOYÉ par Yahya (dossier Éléments envoyés) dont l'objet contient `sujet`, le plus récent
    à la date AAAA-MM-JJ donnée (ou le plus récent tout court). Sert à répondre à tous sur son propre mail."""
    items = ns().GetDefaultFolder(5).Items  # 5 = Éléments envoyés
    items.Sort("[SentOn]", True)
    for m in items:
        try:
            if sujet.lower() in (m.Subject or "").lower() and (not date or f"{m.SentOn:%Y-%m-%d}" == date):
                return m
        except Exception:
            continue
    sys.exit(f"Aucun mail envoyé trouvé : « {sujet} » {date or ''} (synchronisation d'Outlook terminée ?)")


def brouillon_envoye(sujet, date, corps, pjs, objet=None):
    r = envoye(sujet, date).ReplyAll()
    if objet:
        r.Subject = objet
    remplir(r, corps, pjs)


def brouillon(n, corps, pjs):
    remplir(mail(n).ReplyAll(), corps, pjs)


def remplir(r, corps, pjs):
    deja = (r.To + ";" + r.CC).lower()
    with open(CONTACTS, encoding="utf-8-sig") as f:
        for c in csv.DictReader(f, delimiter=";"):
            if c["cc_systematique"].strip().lower() == "oui" and c["email"].lower() not in deja:
                r.Recipients.Add(c["email"]).Type = CC
    r.Recipients.ResolveAll()
    texte = Path(corps).read_text(encoding="utf-8-sig").strip()
    paras = "".join(f"<p>{html.escape(l)}</p>" for l in texte.split("\n\n")).replace("\n", "<br>")
    bloc = f'<div style="font-family:Calibri;font-size:11pt">{paras}</div>'
    # Dans le <body> du fil (avant <html>, Outlook peut l'ignorer ou mal l'afficher).
    corps_fil, n = re.subn(r"(<body[^>]*>)", lambda x: x.group(1) + bloc, r.HTMLBody, count=1, flags=re.I)
    r.HTMLBody = corps_fil if n else bloc + r.HTMLBody
    for p in pjs or []:
        r.Attachments.Add(str(Path(p).resolve()))
    r.Save()  # Brouillons. Jamais Send().
    print(f"BROUILLON ENREGISTRÉ : {r.Subject}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    s = a.add_subparsers(dest="cmd", required=True)
    l = s.add_parser("lister"); l.add_argument("--jours", type=int, default=2); l.add_argument("--non-lus", action="store_true")
    s.add_parser("lire").add_argument("n")
    b = s.add_parser("brouillon"); b.add_argument("n"); b.add_argument("--corps", required=True); b.add_argument("--pj", nargs="*")
    e = s.add_parser("brouillon-envoye", help="répondre à tous sur un mail envoyé par Yahya")
    e.add_argument("sujet"); e.add_argument("--date", help="AAAA-MM-JJ d'envoi"); e.add_argument("--corps", required=True)
    e.add_argument("--pj", nargs="*"); e.add_argument("--objet", help="remplace l'objet de la réponse")
    x = a.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    {"lister": lambda: lister(x.jours, x.non_lus), "lire": lambda: lire(x.n),
     "brouillon": lambda: brouillon(x.n, x.corps, x.pj),
     "brouillon-envoye": lambda: brouillon_envoye(x.sujet, x.date, x.corps, x.pj, x.objet)}[x.cmd]()
