#!/usr/bin/env python3
"""Auto-build a QUIZ-LESS exam.json from a transcript (data.json), so a channel
video becomes a transcript study page with all the listening tools (follow-along,
word-tap, 🔁 loop, 遮中文, 💡 AI 詳解) — but no questions/answers.

Why: the hand-authored make_exam.py needs the correct answers (only known for
'met ANTWOORDEN' videos). For the bulk channel videos we skip the quiz and keep
the high-value, fully-reliable transcript + tools.

Pipeline position:  generate.py → make_exam_auto.py → make_web.py → analyze_sentences.py

Usage: python3 make_exam_auto.py <video_id> [--title "..."] [--duration 600] [--channel "..."]
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / 'output'

env = ROOT / '.env'
if env.exists():
    for line in env.read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
KEY = os.environ.get('OPENAI_API_KEY')

def ts(sec):
    return f"{int(sec // 60)}:{int(sec % 60):02d}"

def dedup_dialogue(segs):
    """A2 mock audio replays each line ~3×. Keep first occurrence per text,
    in time order → one clean playthrough."""
    seen, out = set(), []
    for s in segs:
        text = (s.get('text') or '').strip()
        zh = (s.get('translation') or '').strip()
        if not text:
            continue
        k = ' '.join(text.lower().split())
        if k in seen:
            continue
        seen.add(k)
        out.append({'t': ts(float(s.get('start') or 0)), 'nl': text, 'zh': zh})
    return out

PROMPT = """你是荷蘭語 A2 聽力老師（學生母語繁體中文台灣）。以下是一段 A2 聽力測驗的荷蘭文逐字稿（已去除重播）。
請產出這支影片的學習中繼資料，只回傳 JSON 物件（不要 markdown）：
{"title_zh":"這支內容的簡短中文標題（例：在市政府辦出生登記）",
 "context_zh":"一句話說明情境（誰、在哪、做什麼）",
 "kind":"類型，從 {對話, 廣播/留言, 訪問, 短句練習} 擇一",
 "vocab":[["荷蘭文片語/單字","中文"], ...],   // 10-15 個本片最關鍵、考試會用到的字（用原文出現的形式；不要人名地名）
 "patterns":[{"nl":"句型骨架","zh":"中文","note":"文法重點(≤30字)"}, ...]}  // 4-6 個 A2 重要句型
繁體中文。逐字稿："""

def ai_meta(dialogue):
    if not KEY:
        return {}
    text = '\n'.join(f"{d['nl']}" for d in dialogue)[:6000]
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": PROMPT + text}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }, ensure_ascii=False)
    try:
        r = subprocess.run(['curl', '-s', 'https://api.openai.com/v1/chat/completions',
                            '-H', 'Content-Type: application/json',
                            '-H', f'Authorization: Bearer {KEY}', '-d', '@-'],
                           input=payload, capture_output=True, text=True, timeout=120)
        d = json.loads(r.stdout)
        if 'error' in d:
            print('  ⚠ AI meta error:', d['error'].get('message', '')[:120]); return {}
        return json.loads(d['choices'][0]['message']['content'])
    except Exception as e:
        print('  ⚠ AI meta failed:', e); return {}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vid')
    ap.add_argument('--title', default='')
    ap.add_argument('--duration', type=int, default=0)
    ap.add_argument('--channel', default='Inburgeren examen A2')
    args = ap.parse_args()

    dpath = OUT / args.vid / 'data.json'
    if not dpath.is_file():
        print(f'✗ {dpath} not found (run generate.py first)'); sys.exit(1)
    segs = json.loads(dpath.read_text(encoding='utf-8'))['ai_data']['segments']
    duration = args.duration or int(max((float(s.get('end') or 0) for s in segs), default=0))
    dialogue = dedup_dialogue(segs)
    if len(dialogue) < 2:
        print('✗ too few dialogue lines'); sys.exit(1)

    meta = ai_meta(dialogue)
    vocab = [{'nl': v[0], 'zh': v[1]} for v in meta.get('vocab', [])
             if isinstance(v, list) and len(v) >= 2]
    patterns = [p for p in meta.get('patterns', []) if isinstance(p, dict) and p.get('nl')]

    scenario = {
        'n': 1,
        'title_zh': meta.get('title_zh') or (args.title or args.vid),
        'title_nl': args.title,
        'kind': meta.get('kind') or '聽力',
        'context_zh': meta.get('context_zh') or '',
        'start': dialogue[0]['t'],
        'no_questions': True,
        'dialogue': dialogue,
        'vocab': vocab,
        'patterns': patterns,
        'questions': [],
    }
    exam = {
        'video_id': args.vid,
        'title': args.title or args.vid,
        'channel': args.channel,
        'duration': duration,
        'exam_type': 'A2 Luisteren · Inburgering',
        'n_questions': 0,
        'scenarios': [scenario],
    }
    (OUT / args.vid / 'exam.json').write_text(
        json.dumps(exam, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'  ✓ exam.json ({len(dialogue)} lines, {len(vocab)} vocab, {len(patterns)} patterns)')

if __name__ == '__main__':
    main()
