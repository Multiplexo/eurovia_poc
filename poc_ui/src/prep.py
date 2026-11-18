# Erzeugt data.js (Beispiel-Positionen, Lieferanten, PLZ) aus den Original-Ausschreibungen und der NU-Liste.
# Aufruf im Ordner poc_ui/src:  python3 prep.py <Ordner mit Vergabepaketen> <NU-und Lieferantenliste.xlsm>
# Braucht: pip install openpyxl
import re,json,os,sys,collections,csv,importlib.util,unicodedata
import openpyxl
HERE=os.path.dirname(os.path.abspath(__file__))
A=os.path.join(HERE,'..','..','gaeb_gewerke')
spec=importlib.util.spec_from_file_location('g',A+'/gaeb_gewerke.py'); g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
exec(open(os.path.join(HERE,'gewerke_def.py'),encoding='utf-8').read())
if len(sys.argv)!=3: sys.exit('Aufruf: python3 prep.py <Vergabepakete_Dateien> <NU-und Lieferantenliste.xlsm>')
B,XLSM=sys.argv[1],sys.argv[2]
os.chdir(HERE)
MAIN={'K181_26_0272':'03-26-0005.D83','K181_26_0312':'1.D83','K182_0000001098':'22014-GAEB-2024-10-07.D83','K182_0000001109':'24009-WIS-GAEB.D83','K182_0000001128':'06-23-0031.D83','K182_26_0105':'06-25-0079.D83','K182_26_0168':'2026-S-11.D83'}
def lt(it): return ' '.join(r[5:74].strip() for r in it.records if r[:2]=='26')
corpus=[]
for pk,m in MAIN.items():
    d=f'{B}/{pk}'; _,root,_=g.parse(f'{d}/{m}')
    key=lambda it:(it.kurztext,[r for r in it.records if r[:2]=='21'][0][23:34])
    lab=collections.defaultdict(set)
    for f in [unicodedata.normalize('NFC',x) for x in os.listdir(d)]:  # macOS liefert Umlaute zerlegt (NFD)
        if f.endswith('.D83') and f!=m:
            c=g.gewerk_code(f,m); c=ALIAS.get(c,c)
            if c=='ARGE': continue
            _,r2,_=g.parse(f'{d}/{f}')
            for it in g.iter_items(r2): lab[key(it)].add(c)
    for it in g.iter_items(root):
        r21=[r for r in it.records if r[:2]=='21'][0]
        kat=re.sub(r'\D','',r21[40:72])
        corpus.append([(it.kurztext+' '+lt(it)[:200]).strip(), sorted(lab.get(key(it),())), kat, pk, it.kurztext.strip()])
# Lieferanten
plz={r['']:(round(float(r['lat']),4),round(float(r['lng']),4)) for r in csv.DictReader(open('plz.csv',encoding='utf-8'))}
wb=openpyxl.load_workbook(XLSM,read_only=True,data_only=True)
GEO=json.load(open('geocache.json',encoding='utf-8')) if os.path.exists('geocache.json') else {}
firms={}; rows=0; nogeo=0
s=lambda v:'' if v is None else str(v).strip()
for r in wb.worksheets[0].iter_rows(min_row=2,values_only=True):
    f=s(r[0]); 
    if not f: continue
    ort=s(r[8]); k=f+(f' ({ort})' if ort else '')
    p=s(r[7]); p=p.zfill(5) if p.isdigit() else p
    if k not in firms:
        ll=GEO.get(f"{s(r[6])}|{p}|{ort}") or plz.get(p)  # genaue Adresse, sonst PLZ-Mittelpunkt
        if not ll: nogeo+=1
        firms[k]={'id':len(firms),'firma':f,'ort':ort,'plz':p,'str':s(r[6]),'mail':s(r[3]),'tel':s(r[4]),'name':s(r[9]),'mobil':s(r[10]),'www':s(r[11]),'geo':ll,'arten':[],'bem':[]}
    F=firms[k]; a=s(r[2]); b=s(r[1])
    if a and a not in F['arten']: F['arten'].append(a)
    if b and b not in F['bem']: F['bem'].append(b)
    if not F['mail'] and s(r[3]): F['mail']=s(r[3])
# Orte -> PLZ fuer die Baustellensuche
orte=collections.defaultdict(collections.Counter)
for F in firms.values():
    if F['ort'] and F['geo']: orte[F['ort']][F['plz']]+=1
orte={o:c.most_common(1)[0][0] for o,c in orte.items()}
arten=sorted({a for F in firms.values() for a in F['arten']})
gew={k:{'name':n,'arten':[a for a in arten if any(w in a.lower() for w in kw)],'radius':rad} for k,(n,kw,rad) in G.items() if k not in ALIAS}
data={'corpus':corpus,'firms':list(firms.values()),'plz':plz,'orte':orte,'arten':arten,'gewerke':gew,'alias':ALIAS}
js='const DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';'
open('data.js','w',encoding='utf-8').write(js)
print(len(corpus),len(firms),'ohne geo',nogeo,len(js)//1024,'KB', sum(1 for F in firms.values() if any('nicht mehr anfragen' in b for b in F['bem'])))
