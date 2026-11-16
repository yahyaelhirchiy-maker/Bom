"""Génère le CR (ou l'ODJ) TBRP au format AEDGE à partir de tbrp_state.json.
Usage : python render_cr.py tbrp_state.json --type cr|odj --date 2026-10-27 --next "Mardi 03/11/2026 à 9h – site TBRP" --outdir .
Sorties : <AAMMJJ>.TBRP CR Réunion chantier.xlsx + .pdf (via Excel sous Windows, sinon LibreOffice) ou <AAMMJJ>.TBRP ODJ Réunion chantier.xlsx + .pdf
"""
import json, sys, argparse, subprocess, os, glob
import datetime as dt
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule

D = dt.date
# (sujet, demandé par, responsable, priorité, action, échéance, statut, observations)

ap=argparse.ArgumentParser(); ap.add_argument("state"); ap.add_argument("--type",default="cr"); ap.add_argument("--date",required=True)
ap.add_argument("--next",default=""); ap.add_argument("--outdir",default=".")
A=ap.parse_args()
S=json.load(open(A.state,encoding="utf-8"))
DATE=dt.date.fromisoformat(A.date); DSTR=DATE.strftime("%d/%m/%Y"); TAG=DATE.strftime("%y%m%d")
IS_ODJ = A.type=="odj"
NEXT = A.next or S.get("prochaine_reunion","")
import re
# Règle Yahya 16/11 : CR et ODJ = uniquement les travaux. Les infos internes (départ d'entreprise, consultation,
# paiement, montant, avenant, validations AEDGE/MO…) vont dans `note_interne` (jamais imprimée) ou point `interne: true`.
INTERDIT = re.compile(r"(?i)quitte|d[ée]part d|remplacement d|impay|factur|paiement|r[èe]glement des|d[ée]compte|\bDP ?n?°|"
    r"\bTSB\b|budget|marge|\bHT\b|\bDH\b|\bMAD\b|\d{3}[  ]\d{3}|avenant|consultation|consulter|nouveau march|"
    r"loubna|marwane|\bsami\b|nadia|confirm[ée] par|brouillon|d[ée]cision MO|validation MOD|en attente (de la |du )?MO\b")
fuites=[]
order=[]; groups={}
for p in S["points_chantier"]:
    if p.get("interne"): continue
    if p["statut"]=="Clos" and (IS_ODJ or p.get("maj_le")!=A.date): continue
    for champ in ("sujet","responsable","action","observations"):
        m=INTERDIT.search(p.get(champ) or "")
        if m: fuites.append(f'{p.get("id")} {champ} : « {m.group(0)} » dans « {(p.get(champ) or "")[:120]} »')
    sec=p["section"]
    if sec not in groups: groups[sec]=[]; order.append(sec)
    e=dt.date.fromisoformat(p["echeance"]) if p.get("echeance") else None
    groups[sec].append((p["sujet"],p["demande_par"],p["responsable"],p["priorite"],p["action"],e,p["statut"],p.get("observations","")))
if fuites:
    sys.exit("REFUS : information interne dans un point publié (CR/ODJ = travaux seulement).\n"
             "Déplacer l'info dans `note_interne` du point, ou marquer le point `interne: true`, puis relancer :\n- " + "\n- ".join(fuites))
SECTIONS=[(s,groups[s]) for s in order]
ARIAL = "Arial"
thin = Side(style="thin", color="000000")
B = Border(left=thin, right=thin, top=thin, bottom=thin)
def f(bold=False, color="000000", size=9, italic=False): return Font(name=ARIAL, bold=bold, color=color, size=size, italic=italic)
def fill(c): return PatternFill("solid", start_color=c, end_color=c)
GREY = fill("D9D9D9"); LIGHT = fill("F2F2F2")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)

wb = Workbook(); ws = wb.active; ws.title = ("ODJ " if IS_ODJ else "CR ")+DATE.strftime("%d.%m.%Y")
ws.sheet_view.showGridLines = False
widths = {"A":14,"B":30,"C":15,"D":18,"E":10,"F":62,"G":12,"H":13,"I":34}
for k,v in widths.items(): ws.column_dimensions[k].width = v

# En-tête
hdr = [("Projet","TBRP – Bosko Shopping Center"),("Document","Ordre du jour – réunion de chantier" if IS_ODJ else "CR de la réunion de chantier"),("Date",DSTR),("Prochaine réunion",NEXT)]
for i,(k,v) in enumerate(hdr, start=2):
    ws.cell(i,1,k).font=f(True); ws.cell(i,1).fill=GREY; ws.cell(i,1).alignment=CENTER
    ws.merge_cells(start_row=i,start_column=1,end_row=i,end_column=2) if False else None
    ws.cell(i,2,v).font=f(); ws.cell(i,2).alignment=LEFT
    ws.merge_cells(start_row=i,start_column=2,end_row=i,end_column=4)
    for c in range(1,5): ws.cell(i,c).border=B
ws.cell(2,1).value="Projet"

# Table
TOP = 9
heads = ["N°","Sujet","Demandé par","Action","Ordre de priorité","Action","Échéance","Statut","Observations / Update"]
for j,h in enumerate(heads,1):
    c=ws.cell(TOP,j,h); c.font=f(True); c.fill=GREY; c.alignment=CENTER; c.border=B
r = TOP+1
rappels = [("Prochaine réunion",NEXT)]
for s,a in rappels:
    vals=["Rappel",s,"MOD","Tous",1,a,None,"",""]
    for j,v in enumerate(vals,1):
        c=ws.cell(r,j,v); c.font=f(j==2); c.border=B; c.alignment=LEFT if j in (2,6,9) else CENTER
    r+=1
n=1
first_item=None
for title, items in SECTIONS:
    r+=1
    ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=9)
    c=ws.cell(r,1,title); c.font=f(True,size=11); c.fill=LIGHT; c.alignment=Alignment(vertical="center")
    for j in range(1,10): ws.cell(r,j).border=B
    ws.row_dimensions[r].height=22
    r+=1
    for (s,dem,resp,p,act,ech,st,obs) in items:
        if first_item is None: first_item=r
        vals=[n,s,dem,resp,p,act,ech,st,obs]
        for j,v in enumerate(vals,1):
            c=ws.cell(r,j,v); c.border=B; c.font=f(j==2)
            c.alignment=LEFT if j in (2,6,9) else CENTER
        ws.cell(r,2).fill=GREY
        if ech: ws.cell(r,7).number_format="DD/MM/YYYY"
        lines=max(len(act)/70, len(obs)/38, len(s)/30)
        ws.row_dimensions[r].height=max(24, 12*(int(lines)+1)+6)
        n+=1; r+=1
last_item=r-1

# Mise en forme conditionnelle priorité & statut
rngP=f"E{TOP+1}:E{last_item}"
ws.conditional_formatting.add(rngP, CellIsRule(operator="equal", formula=["1"], fill=fill("FF0000"), font=Font(name=ARIAL,color="FFFFFF",bold=True)))
ws.conditional_formatting.add(rngP, CellIsRule(operator="equal", formula=["2"], fill=fill("FFC000"), font=Font(name=ARIAL,color="FFFFFF",bold=True)))
ws.conditional_formatting.add(rngP, CellIsRule(operator="equal", formula=["3"], fill=fill("002060"), font=Font(name=ARIAL,color="FFFFFF",bold=True)))
rngS=f"H{TOP+1}:H{last_item}"
for val,col,fc in [("Retard","FF0000","FFFFFF"),("Engagement","C6E0B4","000000"),("Nouveau","BDD7EE","000000"),("En cours","FFF2CC","000000"),("Reconduit","EDEDED","595959"),("Clos","A9D08E","000000")]:
    ws.conditional_formatting.add(rngS, CellIsRule(operator="equal", formula=[f'"{val}"'], fill=fill(col), font=Font(name=ARIAL,color=fc,bold=True)))
# observations en rouge si retard
ws.conditional_formatting.add(f"I{first_item}:I{last_item}", FormulaRule(formula=[f'$H{first_item}="Retard"'], font=Font(name=ARIAL,color="FF0000",bold=True)))

dv=DataValidation(type="list", formula1='"Nouveau,En cours,Engagement,Retard,Reconduit,Clos"', allow_blank=True)
ws.add_data_validation(dv); dv.add(f"H{first_item}:H{last_item}")
dvp=DataValidation(type="list", formula1='"1,2,3"', allow_blank=True); ws.add_data_validation(dvp); dvp.add(f"E{first_item}:E{last_item}")

# Tableau de synthèse (formules)
ws.cell(1,6,"Synthèse des points").font=f(True,size=10)
ws.cell(1,6).alignment=Alignment(vertical="bottom")
syn = [
 ("Points ouverts", f'=COUNT(A{first_item}:A{last_item})', "Priorité 1", f'=COUNTIF(E{first_item}:E{last_item},1)'),
 ("Nouveaux points", f'=COUNTIF(H{first_item}:H{last_item},"Nouveau")', "Priorité 2", f'=COUNTIF(E{first_item}:E{last_item},2)'),
 ("Engagements pris", f'=COUNTIF(H{first_item}:H{last_item},"Engagement")', "Priorité 3", f'=COUNTIF(E{first_item}:E{last_item},3)'),
 ("En retard", f'=COUNTIF(H{first_item}:H{last_item},"Retard")', f"Échéance ≤ {(DATE+dt.timedelta(days=7)).strftime('%d/%m/%Y')}", f'=COUNTIFS(G{first_item}:G{last_item},"<="&DATE({(DATE+dt.timedelta(days=7)).year},{(DATE+dt.timedelta(days=7)).month},{(DATE+dt.timedelta(days=7)).day}),G{first_item}:G{last_item},">="&DATE({DATE.year},{DATE.month},{DATE.day}))'),
 ("Reconduits (non abordés)", f'=COUNTIF(H{first_item}:H{last_item},"Reconduit")', "Actions à la charge du MOD", f'=COUNTIF(D{first_item}:D{last_item},"MOD")'),
]
for i,(l1,v1,l2,v2) in enumerate(syn, start=2):
    for col,val,bold in [(6,l1,True),(7,v1,False),(8,l2,True),(9,v2,False)]:
        c=ws.cell(i,col,val); c.border=B; c.font=f(bold, size=9); c.alignment=CENTER if col in (7,9) else LEFT
        if col in (6,8): c.fill=GREY
ws.cell(5,7).font=f(True,"FF0000")

ws.freeze_panes=ws.cell(TOP+1,1)
ws.print_title_rows=f"{TOP}:{TOP}"
ws.page_setup.paperSize=ws.PAPERSIZE_A3
ws.page_setup.orientation="portrait"
ws.page_setup.fitToWidth=1; ws.page_setup.fitToHeight=0
ws.sheet_properties.pageSetUpPr.fitToPage=True
ws.print_options.horizontalCentered=True
ws.page_margins.left=ws.page_margins.right=0.4
ws.oddFooter.center.text=f"AEDGE Partners – {'ODJ' if IS_ODJ else 'CR'} réunion de chantier TBRP du {DSTR} – page &P / &N"
ws.oddFooter.center.size=8
ws.print_area=f"A1:I{last_item}"

name=f"{TAG}.TBRP {'ODJ' if IS_ODJ else 'CR'} Réunion chantier"
out=os.path.join(A.outdir,name+".xlsx"); wb.save(out)
pdf=os.path.join(A.outdir,name+".pdf")
try:  # Windows : Excel (instance séparée, n'affecte pas un Excel déjà ouvert) ; sinon LibreOffice
    import win32com.client
    xl=win32com.client.DispatchEx("Excel.Application"); xl.Visible=False; xl.DisplayAlerts=False
    try:
        wbx=xl.Workbooks.Open(os.path.abspath(out), ReadOnly=True)
        wbx.ExportAsFixedFormat(0, os.path.abspath(pdf)); wbx.Close(False)
    finally: xl.Quit()
except ImportError:
    try: subprocess.run(["soffice","--headless","--convert-to","pdf","--outdir",A.outdir,out],check=False,capture_output=True,timeout=120)
    except Exception as e: print("PDF non généré:",e)
except Exception as e: print("PDF non généré:",e)
print(out)
if os.path.exists(pdf): print(pdf)
