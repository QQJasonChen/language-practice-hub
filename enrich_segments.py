#!/usr/bin/env python3
"""Enrich every segment in 3 mocks' data.json with GPT-authored analysis:
- words_hard: [{nl, zh, level}] — words an A2 inburgering learner likely doesn't know
- grammar: short note on the grammatical pattern (e.g. "om + te 子句")
- reductions: [{written, spoken}] — connected speech / clitic reduction (e.g. "Heb je → Hebbie")
- trap: A2 listening trap (negation, false friend, etc.) — null if none

Also aggregates all unique hard-words → output/all_vocab.json

Run: python3 enrich_segments.py
Cost: ~$0.30 via gpt-4o-mini for 1000 segments.
"""
import json, os, subprocess, sys, time
from pathlib import Path

API = os.environ['OPENAI_API_KEY']
ROOT = Path(__file__).parent
OUT = ROOT / 'output'
MOCKS = ['_iC1Pooi2UA', 'AMVy2zPNLso', 'mock3_a2_2026']
BATCH = 10  # segments per GPT call

PROMPT_TMPL = """你是荷蘭語 A2 Inburgering 考試的聽力教練。下面 {n} 句來自 A2 luisteren 模擬考。對每一句給出 JSON 分析。

對每一句輸出：
- `i`: 句子編號（從 1 開始）
- `words_hard`: 對 A2 學習者來說「可能不認識」的內容字（去掉 de/het/een/maar/dat/dus/wel 等高頻虛詞）。每個帶 {{nl, zh, level}}，level 用 A1/A2/B1/B2。如果這句太簡單沒生字就 []。
- `grammar`: 一句話標示文法骨架（如 "om + te + inf"、"hadden afgesproken om..."、"祈使句"）。
- `reductions`: 如有連音/縮讀就列 [{{written, spoken}}]，如 {{"written": "Heb je", "spoken": "Hebbie"}}。沒有就 []。
- `trap`: 如有 A2 學習者典型聽力陷阱（否定詞、wel/niet 反轉、數字陷阱、相似詞混淆）寫 1 句中文說明；無陷阱寫 null。

只輸出 JSON array，不要解釋，不要 markdown fence。

句子：
{lines}
"""

def call_gpt(payload):
    """POST to chat completions via curl to dodge Python 3.9 SSL issues."""
    out = subprocess.run([
        'curl', '-s', 'https://api.openai.com/v1/chat/completions',
        '-H', f'Authorization: Bearer {API}',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps(payload),
    ], capture_output=True, text=True, timeout=120)
    return json.loads(out.stdout)

def enrich_batch(batch):
    """batch = list of segments. Returns list of analysis dicts indexed same."""
    lines = '\n'.join(f'{i+1}. {s["text"].strip()}' for i, s in enumerate(batch))
    prompt = PROMPT_TMPL.format(n=len(batch), lines=lines)
    resp = call_gpt({
        'model': 'gpt-5-nano',
        'response_format': {'type': 'json_object'},
        'messages': [
            {'role': 'system', 'content': '你只能輸出有效 JSON。把 array 包在 {"data": [...]} 裡。'},
            {'role': 'user', 'content': prompt},
        ],
    })
    if 'error' in resp:
        print('  API ERROR:', resp['error']); return [None]*len(batch)
    text = resp['choices'][0]['message']['content']
    try:
        obj = json.loads(text)
        arr = obj.get('data', obj if isinstance(obj, list) else [])
        # Index by i (1-based) → map to position
        out = [None] * len(batch)
        for item in arr:
            idx = item.get('i', 0) - 1
            if 0 <= idx < len(batch):
                out[idx] = {
                    'words_hard': item.get('words_hard', []),
                    'grammar': item.get('grammar', ''),
                    'reductions': item.get('reductions', []),
                    'trap': item.get('trap'),
                }
        return out
    except Exception as e:
        print('  parse fail:', e, text[:200]); return [None]*len(batch)

def main():
    all_vocab = {}  # normalized key → {nl, zh, level, count, sources:[(vid, segidx)]}
    for vid in MOCKS:
        path = OUT / vid / 'data.json'
        d = json.loads(path.read_text(encoding='utf-8'))
        segs = d['ai_data']['segments']
        print(f'\n▶ {vid}  {len(segs)} segs')
        for i in range(0, len(segs), BATCH):
            batch = segs[i:i+BATCH]
            t0 = time.time()
            analyses = enrich_batch(batch)
            for j, a in enumerate(analyses):
                if a:
                    segs[i+j]['analysis'] = a
                    for w in a.get('words_hard', []):
                        key = w['nl'].lower().strip()
                        if not key: continue
                        if key in all_vocab:
                            all_vocab[key]['count'] += 1
                            all_vocab[key]['sources'].append([vid, i+j])
                        else:
                            all_vocab[key] = {
                                'nl': w['nl'], 'zh': w.get('zh',''),
                                'level': w.get('level','A2'),
                                'count': 1, 'sources': [[vid, i+j]],
                            }
            dt = time.time() - t0
            print(f'  [{i+len(batch):3d}/{len(segs)}]  {dt:.1f}s  vocab_total={len(all_vocab)}')
        d['ai_data']['segments'] = segs
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'  ✓ wrote {path.name}')

    # Write aggregated vocab
    vocab_list = sorted(all_vocab.values(), key=lambda v: (-v['count'], v['nl']))
    out_path = OUT / 'all_vocab.json'
    out_path.write_text(json.dumps({
        'count': len(vocab_list),
        'words': vocab_list,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n✓ {out_path.relative_to(ROOT)} — {len(vocab_list)} unique words')

if __name__ == '__main__':
    main()
