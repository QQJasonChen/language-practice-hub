#!/usr/bin/env python3
"""Generate exam-style multiple-choice practice questions from the listening
transcripts, so 題目速讀 has enough volume to really train question/option
reading (the user needs this to pass). AI writes BOTH the question and the
answer from the given text, so the answer is reliable; options mimic the real
exam's plausible distractors.

Output: output/qbank.json = [ {vid, ctx, q_nl, q_zh, options:[{nl,zh}], answer,
                               qb, asking, ob} ]  (resumable, keyed by vid+q text)
"""
import json, os, subprocess, pathlib
from ingest_listening import VIDS
ROOT = pathlib.Path(__file__).parent
OUT = ROOT / 'output'
N_PER = 4
KEY = os.environ.get('OPENAI_API_KEY')
assert KEY, 'OPENAI_API_KEY required'

def dedup(segs):
    seen, out = set(), []
    for s in segs:
        t=(s.get('text') or '').strip()
        if not t: continue
        k=' '.join(t.lower().split())
        if k in seen: continue
        seen.add(k); out.append(t)
    return ' '.join(out)

PROMPT = """你是 A2 inburgering luisteren 出題老師。根據下面的荷蘭文聽力內容，出 %d 題 A2 程度選擇題，
格式和真考試一樣：一個 Vraag + 3 個選項（只有 1 個正確，另外 2 個是似是而非的干擾項）。
題目測「聽懂內容」：人物要做什麼、時間、地點、原因、數量、條件等。

只回傳 JSON {"items":[...]}，每題：
{"q_nl":"荷文問題","q_zh":"中文",
 "options":[{"nl":"荷文選項","zh":"中文"},{"nl":"","zh":""},{"nl":"","zh":""}],
 "answer":正解的index(0/1/2),
 "qb":[["荷文片段","中文"],...],          // 問題文逐塊 2-4 個
 "asking":"要聽什麼(≤30字)",
 "ob":[ [["片段","中文"],...], ... ]}      // 每個選項逐塊（順序對應 options）
繁體中文。選項用內容裡真的會出現的詞。內容：
"""

def call(text, n):
    payload = json.dumps({"model":"gpt-4o-mini",
        "messages":[{"role":"user","content":(PROMPT%n)+text[:5000]}],
        "temperature":0.4,"response_format":{"type":"json_object"}}, ensure_ascii=False)
    r = subprocess.run(['curl','-s','https://api.openai.com/v1/chat/completions',
        '-H','Content-Type: application/json','-H',f'Authorization: Bearer {KEY}','-d','@-'],
        input=payload, capture_output=True, text=True, timeout=120)
    d=json.loads(r.stdout)
    if 'error' in d: raise RuntimeError(d['error'].get('message','')[:150])
    return json.loads(d['choices'][0]['message']['content']).get('items',[])

def main():
    out_path = OUT/'qbank.json'
    bank = []
    if out_path.exists():
        try: bank=json.loads(out_path.read_text(encoding='utf-8'))
        except Exception: bank=[]
    done_vids = {b['vid'] for b in bank}
    todo = [(v,t) for v,t in VIDS if v not in done_vids and (OUT/v/'data.json').is_file()]
    print(f'{len(todo)} videos to generate questions for')
    for n,(vid,title) in enumerate(todo,1):
        try:
            ex = json.loads((OUT/vid/'exam.json').read_text(encoding='utf-8')) if (OUT/vid/'exam.json').is_file() else {}
            ctx = (ex.get('scenarios',[{}])[0].get('context_zh','')) if ex else ''
            segs = json.loads((OUT/vid/'data.json').read_text(encoding='utf-8'))['ai_data']['segments']
            text = dedup(segs)
            if len(text) < 60: print(f'  [{n}] {vid} too short, skip'); continue
            for attempt in range(3):
                try:
                    items = call(text, N_PER); break
                except Exception as e:
                    print(f'  [{n}] {vid} try{attempt+1}: {e}'); items=[]
            for it in items:
                opts=it.get('options',[])
                if not it.get('q_nl') or len(opts)<2: continue
                bank.append({'vid':vid,'ctx':ctx,'q_nl':it['q_nl'],'q_zh':it.get('q_zh',''),
                    'options':[{'nl':o.get('nl',''),'zh':o.get('zh','')} for o in opts],
                    'answer':it.get('answer',0) if isinstance(it.get('answer'),int) else 0,
                    'qb':it.get('qb',[]),'asking':it.get('asking',''),'ob':it.get('ob',[])})
            out_path.write_text(json.dumps(bank,ensure_ascii=False,indent=1),encoding='utf-8')
            print(f'  [{n}/{len(todo)}] {vid}: bank now {len(bank)}')
        except Exception as e:
            print(f'  [{n}] {vid} FAIL: {e}')
    print(f'✓ {out_path} — {len(bank)} questions total')

if __name__ == '__main__':
    main()
