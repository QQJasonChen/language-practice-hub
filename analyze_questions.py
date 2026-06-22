#!/usr/bin/env python3
"""AI word/grammar breakdown for exam QUESTIONS + OPTIONS, so the learner can
read the Dutch question and choices fast (the key to A2 luisteren: read the
question first, then you know what to listen for).

Output: output/q_analysis.json = { "<vid>|<scn>|<qn>": {
   "qb":  [["荷文片段","中文"], ...],         # 問題文の逐塊
   "asking": "何を訊いてるか＝聽くべきポイント（≤30字）",
   "ob":  [ [["片段","中文"],...], ... ]      # 各選択肢の逐塊（options 順）
}}
"""
import json, os, subprocess, pathlib
ROOT = pathlib.Path(__file__).parent
OUT = ROOT / 'output'
MOCKS = ['mock3_a2_2026', '_iC1Pooi2UA', 'AMVy2zPNLso']
BATCH = 8
KEY = os.environ.get('OPENAI_API_KEY')
assert KEY, 'OPENAI_API_KEY required'

PROMPT = """你是荷蘭語 A2 聽力老師（學生母語繁體中文台灣）。以下是聽力測驗的「問題＋選項」。
A2 考試要先讀懂問題和選項，才知道要聽什麼。請幫學生「秒懂」每一題。

只回傳 JSON 物件 {"items":[...]}，每個元素：
{"id":"原樣回傳",
 "qb":[["荷文片段","中文"], ...],          // 問題文 2-4 個關鍵片段
 "asking":"這題在問什麼＝要聽什麼（≤30字）",
 "ob":[ [["片段","中文"],...], ... ]}       // 每個選項各 1-3 片段，照選項順序

繁體中文。題目："""

def call(batch):
    payload = json.dumps({"model":"gpt-4o-mini",
        "messages":[{"role":"user","content":PROMPT+json.dumps(batch,ensure_ascii=False)}],
        "temperature":0.2,"response_format":{"type":"json_object"}}, ensure_ascii=False)
    r = subprocess.run(['curl','-s','https://api.openai.com/v1/chat/completions',
        '-H','Content-Type: application/json','-H',f'Authorization: Bearer {KEY}','-d','@-'],
        input=payload, capture_output=True, text=True, timeout=120)
    d = json.loads(r.stdout)
    if 'error' in d: raise RuntimeError(d['error'].get('message','')[:150])
    return json.loads(d['choices'][0]['message']['content']).get('items', [])

def main():
    items = []
    for vid in MOCKS:
        ex = json.loads((OUT/vid/'exam.json').read_text(encoding='utf-8'))
        for sc in ex['scenarios']:
            for q in sc.get('questions', []):
                items.append({"id":f"{vid}|{sc['n']}|{q['n']}",
                    "q": q.get('q_nl',''), "options":[o.get('nl','') for o in q.get('options',[])]})
    out_path = OUT/'q_analysis.json'
    result = {}
    if out_path.exists():
        try: result = json.loads(out_path.read_text(encoding='utf-8'))
        except Exception: result = {}
    todo = [it for it in items if it['id'] not in result]
    print(f'{len(items)} questions, {len(todo)} to analyze')
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i+BATCH]
        for attempt in range(3):
            try:
                for r in call(batch):
                    if r.get('id'): result[r['id']] = {'qb':r.get('qb',[]),'asking':r.get('asking',''),'ob':r.get('ob',[])}
                break
            except Exception as e: print(f'  batch {i//BATCH} try {attempt+1}: {e}')
        out_path.write_text(json.dumps(result,ensure_ascii=False,indent=1),encoding='utf-8')
        print(f'  {min(i+BATCH,len(todo))}/{len(todo)}')
    print(f'✓ {out_path} ({len(result)} entries)')

if __name__ == '__main__':
    main()
