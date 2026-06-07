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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API = os.environ['OPENAI_API_KEY']
ROOT = Path(__file__).parent
OUT = ROOT / 'output'
MOCKS = ['_iC1Pooi2UA', 'AMVy2zPNLso', 'mock3_a2_2026']
BATCH = 15      # segments per GPT call
WORKERS = 5     # parallel API calls

PROMPT_TMPL = """你是荷蘭語 A2 Inburgering 聽力教練。你的學生「聽得到字、但腦袋反應不過來」。
下面 {n} 句來自 A2 luisteren 模擬考。對每一句給「**幫他聽得懂**」的分析（不是書面語法）。

對每一句輸出 JSON：
- `i`: 句子編號（從 1 開始）
- `words_hard`: 對 A2 學習者「可能不認識」的**內容字**（不含 de/het/een/dat/maar 等高頻虛詞）。{{nl, zh, level}}。沒有就 []。
- `frame`: 這句的**聽力句框**——把要聽的「骨架詞」抽出來、中間填 ...。**重點是學生一聽到骨架詞就要 trigger「啊這是 X 句型」**。例：
   * "Hoe lang ... al ...?" → 問「某狀態持續多久了」
   * "Wat leuk!" → 反應句、表驚喜
   * "Ik wil ... om ... te ..." → 表目的
   * "Niet ..., maar ..." → 否定 + 對比，答案在 maar 後面
  寫法：[骨架字]...{{中文用途說明 1 句}}。沒明顯句框就 ""。
- `stressed`: 這句**講者會重讀**的 1-3 個字（強讀＝聽力 trigger 點）。例：al / leuk / wel / niet / 數字 / 形容詞最高級。
- `reductions`: **連音黏字**——書寫 vs 真實發音。每個 {{written, spoken}}。例：
   * "is Daniëlle" → "izDaniëlle"（s+D 黏一起）
   * "Heb je een" → "Hebbie nuh"（clitic）
   * "wilde ik je" → "wildikje"
  沒有就 []。
- `trap`: 純聽力陷阱（不是文法陷阱）寫 1 句中文。例：
   * 「al 很輕、容易漏聽，但漏了就不知道是『已經』」
   * 「leuk 在 'Wat leuk' 講超快，A2 容易聽成單字 leuk 而非完整表達」
   無陷阱寫 null。

⚠️ 不要寫「疑問句 + 直接引語」這種書面文法。要寫「**聽的時候耳朵要警鈴的東西**」。

只輸出 JSON（外層 {{"data":[...]}}）。

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
        'reasoning_effort': 'minimal',
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
                    'frame': item.get('frame', '') or item.get('grammar', ''),
                    'stressed': item.get('stressed', []),
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
        print(f'\n▶ {vid}  {len(segs)} segs ({WORKERS} workers, batch={BATCH})')
        # Build list of (batch_start, batch_segs)
        batches = [(i, segs[i:i+BATCH]) for i in range(0, len(segs), BATCH)]
        t0_total = time.time()
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            future_to_start = {ex.submit(enrich_batch, b): i for i, b in batches}
            done = 0
            for fut in as_completed(future_to_start):
                i = future_to_start[fut]
                analyses = fut.result()
                for j, a in enumerate(analyses):
                    if a:
                        segs[i+j]['analysis'] = a
                        for w in a.get('words_hard', []):
                            if not isinstance(w, dict) or not w.get('nl'): continue
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
                done += 1
                print(f'  [{done*BATCH:3d}/{len(segs)}]  vocab={len(all_vocab)}', flush=True)
        d['ai_data']['segments'] = segs
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'  ✓ wrote {path.name} in {time.time()-t0_total:.0f}s')

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
