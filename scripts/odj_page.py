"""Page ODJ à remplir en réunion (artifact claude.ai), générée depuis l'ODJ xlsx du mardi.
Usage : python odj_page.py 2026-11-24  → 04_PUBLIER\\odj\\odj_page.html
Chaque saisie est enregistrée dans la base de l'artifact, collection r<AAMMJJ>, document = id du point (P0xx),
champs : statut, ech, obs, vu ; document « divers » = points nouveaux en séance (texte).
La page est publiée toujours sur la même URL (voir modeles\\odj_page\\URL.txt)."""
import sys, json, datetime as dt, html as H
from pathlib import Path
import openpyxl

d = dt.date.fromisoformat(sys.argv[1]); tag = d.strftime("%y%m%d")
BK = Path(r"D:\BK")
S = json.load(open(BK / "03_TRAVAIL/pilotage/tbrp_state.json", encoding="utf-8"))
ids = {}
for p in S["points_chantier"]:
    if not p.get("interne") and p["statut"] != "Clos":
        ids.setdefault(p["sujet"].strip(), p["id"])
ws = openpyxl.load_workbook(BK / f"04_PUBLIER/odj/{tag}.TBRP ODJ Réunion chantier.xlsx", data_only=True).active
e = lambda x: H.escape(str(x))
STAT = ["", "Clos", "En cours", "Retard", "Engagement", "Reconduit", "Nouveau"]
out, manque = "", []
for r in ws.iter_rows(min_row=10, values_only=True):
    a = r[0]
    if a is None and not any(r[1:]):
        continue
    if a is not None and not any(c not in (None, "") for c in r[1:]):
        out += f'<div class="lot">{e(a)}</div>'; continue
    if not isinstance(a, (int, float)):
        continue
    n = int(a); sujet, dem, qui, prio, action, ech, statut, obs = r[1:9]
    pid = ids.get((sujet or "").strip())
    if not pid:
        manque.append(f"{n} {sujet}"); pid = f"N{n}"
    if isinstance(ech, dt.datetime): ech = ech.strftime("%d/%m")
    statut = statut or ""
    opts = "".join(f'<option value="{x}">{x or "Statut inchangé"}</option>' for x in STAT)
    out += (f'<div class="pt" data-n="{pid}" data-p="{e(prio)}"><div class="hd"><span class="num">{n}</span><span class="suj">{e(sujet)}</span>'
            f'<span class="chip s-{e(statut.split(" ")[0])}">{e(statut)}</span></div>'
            f'<div class="meta">{e(qui or "")} · P{e(prio)}{" · échéance " + e(ech) if ech else ""}</div>'
            f'<div class="act">{e(action or "")}</div>' + (f'<div class="obs">{e(obs)}</div>' if obs else "") +
            f'<div class="f"><select id="st{pid}" aria-label="Statut">{opts}</select><input id="ec{pid}" placeholder="Nouvelle échéance">'
            f'<textarea id="ob{pid}" placeholder="Update de la réunion"></textarea><label><input type="checkbox" id="vu{pid}"> Abordé</label></div></div>')
tpl = (BK / "00_SYSTEME/modeles/odj_page/odj_tpl.html").read_text(encoding="utf-8")
page = (tpl.replace("__LIST__", out).replace("__TAG__", tag)
        .replace("__DCOURT__", d.strftime("%d/%m")).replace("__DLONG__", d.strftime("%d/%m/%Y")))
dst = BK / "04_PUBLIER/odj/odj_page.html"
dst.write_text(page, encoding="utf-8")
print(dst, "| collection", "r" + tag)
if manque:
    print("Sans id P (saisie sous N<n>) :", "; ".join(manque))
