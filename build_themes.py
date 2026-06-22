#!/usr/bin/env python3
"""Group every listening scene across all videos by real-life THEME, so the
learner can break through by theme — master each theme's common vocabulary and
question patterns together.

Output: output/themes.json = { "themes":[ {key, emoji, label,
   scenes:[{vid,n,title_zh,kind,link}], vocab:[[nl,zh,count]], questions:[{q_nl,q_zh}] } ] }
"""
import json, os, re, subprocess, collections, pathlib
ROOT = pathlib.Path(__file__).parent
OUT = ROOT / 'output'
# all videos that have exam.json (3 mocks + 42 listening)
VIDS = sorted([p.parent.name for p in OUT.glob('*/exam.json')])
KEY = os.environ.get('OPENAI_API_KEY'); assert KEY

THEMES = [
    ("gemeente","🏛️","市政府・登記手續"),
    ("gezondheid","🏥","醫療・健康"),
    ("werk","💼","工作・職場"),
    ("vervoer","🚆","交通・出行"),
    ("winkelen","🛒","購物・商店"),
    ("eten","🍽️","餐飲・餐廳"),
    ("wonen","🏠","住房・居住"),
    ("afspraak","📞","預約・電話・留言"),
    ("school","🎓","學校・課程"),
    ("geld","🏦","銀行・金錢"),
    ("vrije_tijd","🎉","休閒・活動・節日"),
    ("overig","📌","其他生活情境"),
]
KEYS = [k for k,_,_ in THEMES]
LABEL = {k:(e,l) for k,e,l in THEMES}

def collect():
    scenes=[]
    for vid in VIDS:
        ex=json.loads((OUT/vid/'exam.json').read_text(encoding='utf-8'))
        multi=len(ex['scenarios'])>1
        for sc in ex['scenarios']:
            link=f"output/{vid}/exam.html"+(f"#scene-{sc['n']}" if multi else "")
            scenes.append({'vid':vid,'n':sc['n'],'title_zh':sc.get('title_zh',''),
                'context_zh':sc.get('context_zh',''),'kind':sc.get('kind',''),'link':link,
                'vocab':sc.get('vocab',[]),
                'questions':[{'q_nl':q.get('q_nl',''),'q_zh':q.get('q_zh','')} for q in sc.get('questions',[])]})
    return scenes

# keyword-based classification (no API) — matches 中文 title/context + 荷文 vocab
KW = {
 'gemeente': ['市政府','政府','登記','申報','出生','結婚','身分證','證件','戶政','aangifte','geboorte','legitimatie','trouwboekje','paspoort','burgerzaken','inschrijv','gemeente'],
 'gezondheid': ['醫','病','藥','健康','診','牙','dokter','arts','ziekenhuis','apotheek','huisarts','gezond','ziek','tandarts','recept','patiënt'],
 'werk': ['工作','職','上班','老闆','同事','面試','薪','徵','baas','werk','collega','sollicit','kantoor','personeel','dienst','vergader','bedrijf','baan','rooster'],
 'vervoer': ['交通','火車','公車','巴士','塞車','車站','地鐵','腳踏車','機場','道路','航班','trein','bus','station','file','snelweg','fiets','reizen','vertrek','spoor','perron','vliegtuig','ns-bus'],
 'winkelen': ['購物','商店','買','超市','折扣','特價','winkel','kopen','aanbieding','korting','markt','supermarkt','folder'],
 'eten': ['餐','吃','咖啡','飲','點餐','菜','restaurant','eten','koffie','bestellen','snackbar','lunch','drinken','menu','etenswaren'],
 'wonen': ['住','房','租','屋','鄰居','搬','公寓','huis','huur','woning','buren','verhuiz','appartement'],
 'afspraak': ['預約','電話','留言','語音','聯絡','afspraak','voicemail','bellen','telefoon','terugbellen'],
 'school': ['學校','上課','課程','老師','學生','cursus','les','school','docent','huiswerk','inburger','opleiding'],
 'geld': ['銀行','付款','帳單','保險','費用','bank','betalen','rekening','verzekering','factuur'],
 'vrije_tijd': ['運動','健身','活動','派對','節日','假期','旅','音樂','慶','sport','feest','koningsdag','vakantie','zwemmen','sportschool','uitnodig','verjaardag','concert','vieren'],
}
def classify(scenes):
    by={}
    for i,s in enumerate(scenes):
        text=' '.join([s['title_zh'],s['context_zh']]+
            [str(v.get('nl',''))+str(v.get('zh','')) for v in s['vocab']]).lower()
        best,score='overig',0
        for k,words in KW.items():
            c=sum(1 for w in words if w.lower() in text)
            if c>score: best,score=k,c
        by[i]=best
    return by

def main():
    scenes=collect()
    print(f'{len(scenes)} scenes from {len(VIDS)} videos')
    theme_of=classify(scenes)
    groups={k:[] for k in KEYS}
    for i,s in enumerate(scenes):
        groups.setdefault(theme_of.get(i,'overig'),[]).append(s)
    out={'themes':[]}
    for k,e,l in THEMES:
        scs=groups.get(k,[])
        if not scs: continue
        # aggregate vocab (dedup by nl, count across scenes)
        vc=collections.Counter(); vz={}
        for s in scs:
            for v in s['vocab']:
                nl=(v.get('nl') or '').strip()
                if nl: vc[nl]+=1; vz.setdefault(nl,v.get('zh',''))
        vocab=[[nl,vz[nl],c] for nl,c in vc.most_common(40)]
        # sample questions (from mocks that have them)
        qs=[q for s in scs for q in s['questions'] if q['q_nl']][:12]
        out['themes'].append({'key':k,'emoji':e,'label':l,
            'scenes':[{'vid':s['vid'],'n':s['n'],'title_zh':s['title_zh'],'kind':s['kind'],'link':s['link']} for s in scs],
            'vocab':vocab,'questions':qs})
    (OUT/'themes.json').write_text(json.dumps(out,ensure_ascii=False,indent=1),encoding='utf-8')
    print('✓ output/themes.json')
    for t in out['themes']:
        print(f"  {t['emoji']} {t['label']}: {len(t['scenes'])} 場景, {len(t['vocab'])} 單字, {len(t['questions'])} 問句")

if __name__=='__main__':
    main()
