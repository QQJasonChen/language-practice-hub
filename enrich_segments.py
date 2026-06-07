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

PROMPT_TMPL = """You are an A2 Dutch listening coach for inburgering exam. Output JSON only.

For each of {n} sentences, write analysis that helps the student RECOGNIZE patterns by ear.

## Output schema per sentence:
{{
  "i": 1,                          // 1-based
  "words_hard": [],                // [{{nl, zh, level}}] — content words A2 learners may not know
  "frame": "",                     // KEY sentence frame, format: "X ... Y ... | 中文" — see rules
  "stressed": [],                  // [string] — function words that listeners MUST catch
  "reductions": [],                // [{{written, spoken}}] — only real connected-speech blurs
  "trap": null                     // string OR null — listening-specific pitfall
}}

## STRICT RULES (read carefully):

### `frame` — listen-for-this pattern (PATTERN, NOT sentence!)
- Format: `<short pattern with ... placeholders> | <中文用途>`
- ABSTRACT the sentence into a 2-6 word pattern using `...` for variable content. DO NOT just paste the full sentence.
- ONLY fill when the sentence has a recognizable A2 pattern worth recognizing. Otherwise `""`.
- Short reactions ("Bedankt.", "Tot dan!", "Ja."): use `""`.
- Plain statements without trigger structure ("De kinderen spelen buiten.", "Ik kom uit Taiwan."): use `""`.

CORRECT examples:
  Sentence: "Hoe lang is Daniëlle al zwanger?"
  → frame: "Hoe lang ... al ...? | 問某狀態持續多久了"

  Sentence: "Wat leuk! Gefeliciteerd, joh!"
  → frame: "Wat ...! | 反應＋驚喜表達"

  Sentence: "Niet van die dikke, die moet ik zelf nog snijden."
  → frame: "Niet ... , maar ... | 否定排除，答案在 maar 後面"

  Sentence: "Ik wilde je uitnodigen om komende zaterdag bij ons te komen eten."
  → frame: "Ik wilde je uitnodigen om ... te ... | 邀請某人做某事"

  Sentence: "Komt u om 1 uur naar lokaal 15 als u deze cursus wilt volgen."
  → frame: "Komt u om ... naar ... als u ... | 條件式祈使（時間+地點+條件）"

WRONG examples (NEVER output these):
  ✗ "Hey Steven, hoe gaat het? | 你最近怎麼樣？"  ← full sentence with NO `...`
  ✗ "Steven komt Yari tegen op straat. | ..."     ← full sentence
  ✗ "Lees eerst de vraag. Kijk daarna naar de video." ← full sentence
  ✗ "[骨架字] ... [骨架字]"  ← literal placeholder
  → For sentences like the above with no real frame, output `""` (empty string).

### `stressed` — what ear should flag
ONLY pick from these categories (1-3 words max):
- **Polarity/scope flippers**: niet, wel, al, nog, juist, alleen, ook, maar, pas, helemaal, zelfs, eigenlijk
- **Negation**: geen, nooit, niets, niemand
- **Time/sequence flips**: eerst, eindelijk, straks, morgen, gisteren, vandaag, nu, dan
- **Comparative/superlative**: meer, minder, beter, slechter, -ste suffix words (mooist, leukst, het beste)
- **Numbers + units**: 5, vijf, half zes, 12,50 euro
- **Crucial verbs of opinion**: vindt, denkt, wil
- **Emphatic adjectives in reactions**: leuk (in "Wat leuk"), super, geweldig

NEVER pick:
- People's names (Daniëlle, Steven, Aron, Lars, ...)
- Concrete nouns (sportschool, kinderen, basisschool, water, brood, kaartje, ...) unless they ARE the answer
- Verbs in neutral statements (gaat, komt, hebt) — unless emphatic
- Articles, prepositions, pronouns

If sentence has no clear stress trigger, use `[]`.

### `reductions` — connected speech
ONLY mark if there's a REAL phonetic blur. Skip otherwise.
- Examples to mark:
  * "is Daniëlle" → "izDaniëlle"  (s+D voiced glide)
  * "Heb je een" → "Hebbie nuh"   (clitic je → bie, een → nuh)
  * "wilde ik je" → "wildikje"    (vowel deletion)
  * "Wat is dit" → "Watisdit"     (run-together)
  * "ga je" → "gaje" / "gaa-je"
- DO NOT just paste the whole sentence into both fields. Pick the specific BLUR span.
- If no blurring, use `[]`. Most sentences won't have any.

### `trap` — listening-only trap
A natural-language 1-sentence Chinese tip. Examples:
- "al 在 'is al zwanger' 唸得很輕，漏聽就不知道是『已經』"
- "maar 後面才是真正答案，前面 niet 否定的句子是干擾"
- "half zes = 5:30 不是 6:30！half + 數字 = 該數字前的半小時"
- "vroeg(早) 跟 vroeger(從前) 連音聽起來很像，要靠句尾 -er 區分"
If no real trap, use `null`.

### `words_hard`
Content words A2 inburgering learners likely don't know. Format `{{nl, zh, level}}` with level A1/A2/B1/B2.
Skip: de/het/een/dat/dus/maar/wel/niet/al/nog/...

## Few-shot examples (STUDY THESE):

Input: "Wat leuk! Gefeliciteerd, joh! Hoe lang is Daniëlle al zwanger?"
Output: {{
  "i": 1,
  "words_hard": [{{"nl":"gefeliciteerd","zh":"恭喜","level":"A2"}},{{"nl":"zwanger","zh":"懷孕的","level":"A2"}}],
  "frame": "Hoe lang ... al ...? | 問某狀態持續多久了",
  "stressed": ["al","leuk"],
  "reductions": [],
  "trap": "al 很輕、容易漏聽，但漏了就分不清是『現在懷孕』還是『已經懷孕多久了』"
}}

Input: "Niet van die dikke, die moet ik zelf dan nog snijden."
Output: {{
  "i": 2,
  "words_hard": [{{"nl":"dikke","zh":"粗的","level":"A2"}},{{"nl":"snijden","zh":"切","level":"B1"}}],
  "frame": "Niet ... | 否定排除（後面通常會接 maar 給正面答案）",
  "stressed": ["Niet","zelf"],
  "reductions": [],
  "trap": "Niet 開頭句聽到要等下一句 maar，答案在 maar 之後"
}}

Input: "Bedankt."
Output: {{"i": 3, "words_hard": [], "frame": "", "stressed": [], "reductions": [], "trap": null}}

Input: "Ik haal je om half zes bij jou thuis op."
Output: {{
  "i": 4,
  "words_hard": [{{"nl":"halen","zh":"接","level":"A2"}}],
  "frame": "Ik haal je om ... op | 我幾點接你（接人時間）",
  "stressed": ["half zes"],
  "reductions": [{{"written":"haal je","spoken":"haalje"}}],
  "trap": "half zes = 5:30 不是 6:30！half + 數字 = 該數字前的半小時"
}}

## Now analyze these sentences. Output strict JSON: {{"data": [...]}}.

Sentences:
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
