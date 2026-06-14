#!/usr/bin/env python3
"""Pre-generate a detailed per-sentence AI explanation for every dialogue line
in each mock, so the exam page can show it on demand (tap 💡 on a line).

Output: output/<vid>/analysis.json  =  { normalized_nl: {breakdown, grammar, listen} }
  breakdown: [[dutch_chunk, 中文], ...]   逐塊拆解
  grammar:   一兩句文法重點（語序/可分動詞/時態…）
  listen:    一句聽力重點（連音/弱讀/容易漏聽）

Resumable: keeps existing entries, only fills missing ones.
"""
import json, os, subprocess, sys, pathlib
from make_web import resegment_dialogue

ROOT = pathlib.Path(__file__).parent
MOCKS = ['mock3_a2_2026', '_iC1Pooi2UA', 'AMVy2zPNLso']
BATCH = 12

# load .env
env = ROOT / '.env'
if env.exists():
    for line in env.read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
KEY = os.environ.get('OPENAI_API_KEY')
assert KEY, 'OPENAI_API_KEY required'

norm = lambda s: ' '.join((s or '').lower().split())

PROMPT = """你是荷蘭語 A2 聽力老師，學生母語是繁體中文（台灣）。
以下是模擬考對話中的句子（荷蘭文＋中文翻譯）。請為「每一句」產出精簡但實用的解說，幫助聽不懂的學生看懂這句。

只回傳 JSON 物件 {"items": [...]}（不要 markdown、不要多餘文字）。
items 是陣列，每個元素：
{"i": 編號,
 "breakdown": [["荷蘭文片段","中文意思"], ...],   // 2-5 個關鍵片段，照原句順序
 "grammar": "一到兩句文法重點（語序、可分動詞、modal、時態、固定搭配等）",
 "listen": "一句聽力重點（哪裡連音/弱讀/容易漏聽，例如 niet/je/het 被吃掉）"}

繁體中文（台灣用語）。grammar/listen 各 ≤ 40 字。

句子：
"""

def call(batch):
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": PROMPT + json.dumps(
            [{"i": i, "nl": b["nl"], "zh": b["zh"]} for i, b in enumerate(batch)],
            ensure_ascii=False)}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }, ensure_ascii=False)
    # pass the JSON body via stdin (-d @-) to avoid any argv escaping issues
    r = subprocess.run(['curl', '-s', 'https://api.openai.com/v1/chat/completions',
                        '-H', 'Content-Type: application/json',
                        '-H', f'Authorization: Bearer {KEY}', '-d', '@-'],
                       input=payload, capture_output=True, text=True, timeout=120)
    d = json.loads(r.stdout)
    if 'error' in d:
        raise RuntimeError(d['error'].get('message', '')[:200])
    content = d['choices'][0]['message']['content']
    obj = json.loads(content)
    items = obj.get('items') or obj.get('results') or (obj if isinstance(obj, list) else [])
    return items

def main():
    only = set(sys.argv[1:]) or set(MOCKS)
    for vid in MOCKS:
        if vid not in only:
            continue
        ex = json.loads((ROOT / 'output' / vid / 'exam.json').read_text(encoding='utf-8'))
        # collect unique sentences
        seen, sents = set(), []
        for sc in ex['scenarios']:
            for u in resegment_dialogue(sc['dialogue']):
                k = norm(u['nl'])
                if k and k not in seen and len(u['nl']) >= 3:
                    seen.add(k)
                    sents.append({'nl': u['nl'], 'zh': u['zh'], 'k': k})
        out_path = ROOT / 'output' / vid / 'analysis.json'
        result = {}
        if out_path.exists():
            try: result = json.loads(out_path.read_text(encoding='utf-8'))
            except Exception: result = {}
        todo = [s for s in sents if s['k'] not in result]
        print(f'{vid}: {len(sents)} unique sentences, {len(todo)} to analyze')
        for bi in range(0, len(todo), BATCH):
            batch = todo[bi:bi + BATCH]
            for attempt in range(3):
                try:
                    items = call(batch)
                    for it in items:
                        idx = it.get('i')
                        if idx is None or idx >= len(batch): continue
                        result[batch[idx]['k']] = {
                            'breakdown': it.get('breakdown', []),
                            'grammar': it.get('grammar', ''),
                            'listen': it.get('listen', ''),
                        }
                    break
                except Exception as e:
                    print(f'  batch {bi//BATCH} attempt {attempt+1} failed: {e}')
            out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
            print(f'  {min(bi+BATCH,len(todo))}/{len(todo)} done')
        print(f'  ✓ {out_path.relative_to(ROOT)} ({len(result)} entries)')

if __name__ == '__main__':
    main()
