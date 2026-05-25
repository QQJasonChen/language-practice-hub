#!/usr/bin/env python3
"""audio.mp3 (nl) → data.json (Whisper nl segments + zh-TW translation)."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

API = os.environ['OPENAI_API_KEY']
HERE = Path(__file__).parent
AUDIO = HERE / 'audio.mp3'
OUT = HERE / 'data.json'

CHUNK_SEC = 720  # 12 min — full file fits in one chunk


def transcribe_chunk(mp3: Path, offset: float) -> tuple:
    print(f'  whisper {mp3.name} (offset={offset:.0f}s, word-level)...')
    out = subprocess.run([
        'curl', '-s', 'https://api.openai.com/v1/audio/transcriptions',
        '-H', f'Authorization: Bearer {API}',
        '-F', f'file=@{mp3}',
        '-F', 'model=whisper-1',
        '-F', 'language=nl',
        '-F', 'response_format=verbose_json',
        '-F', 'timestamp_granularities[]=segment',
        '-F', 'timestamp_granularities[]=word',
    ], capture_output=True, text=True, timeout=300)
    if out.returncode != 0 or not out.stdout.strip():
        print('  STDERR:', out.stderr[:300]); sys.exit(1)
    res = json.loads(out.stdout)
    if 'error' in res:
        print('  API ERROR:', res['error']); sys.exit(1)
    segs = [{'start': round(s['start'] + offset, 3),
             'end': round(s['end'] + offset, 3),
             'text': s['text'].strip()} for s in res.get('segments', [])]
    words = [{'word': w['word'],
              'start': round(w['start'] + offset, 3),
              'end': round(w['end'] + offset, 3)}
             for w in res.get('words', [])]
    return segs, words


def post_chat(payload: dict) -> dict:
    out = subprocess.run([
        'curl', '-s', 'https://api.openai.com/v1/chat/completions',
        '-H', f'Authorization: Bearer {API}',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps(payload),
    ], capture_output=True, text=True, timeout=120)
    return json.loads(out.stdout)


def make_chunks(mp3: Path, chunk_sec: int) -> list:
    dur = float(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'csv=p=0', str(mp3)]).strip())
    if dur <= chunk_sec + 60:
        return [(mp3, 0.0)]
    out = []
    tmp = Path(tempfile.mkdtemp(prefix='chunks_'))
    t = 0.0; i = 0
    while t < dur:
        p = tmp / f'c{i}.mp3'
        subprocess.run(['ffmpeg', '-y', '-ss', str(t), '-i', str(mp3),
                        '-t', str(chunk_sec), '-ac', '1', '-ar', '16000',
                        '-ab', '64k', '-vn', str(p)],
                       check=True, capture_output=True)
        out.append((p, t)); t += chunk_sec; i += 1
    return out


def translate_batch(nl_lines: list) -> list:
    BATCH = 30
    out = []
    for i in range(0, len(nl_lines), BATCH):
        batch = nl_lines[i:i + BATCH]
        numbered = '\n'.join(f'{n+1}. {t}' for n, t in enumerate(batch))
        prompt = ('把以下荷蘭文逐行翻成繁體中文（台灣用語），保留口語感、'
                  '不要過度書面化。一行對一行，保留編號。只輸出譯文，'
                  '不要解釋。\n\n' + numbered)
        print(f'  translate {i+1}-{i+len(batch)} / {len(nl_lines)}')
        resp = post_chat({
            'model': 'gpt-4o-mini', 'temperature': 0.3,
            'messages': [{'role': 'user', 'content': prompt}]
        })
        text = resp['choices'][0]['message']['content']
        zh = {}
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            m = line.split('. ', 1)
            if len(m) == 2 and m[0].isdigit():
                zh[int(m[0])] = m[1].strip()
        for j in range(len(batch)):
            out.append(zh.get(j + 1, ''))
    return out


def main():
    if not AUDIO.exists():
        print(f'✗ {AUDIO} missing'); sys.exit(1)
    chunks = make_chunks(AUDIO, CHUNK_SEC)
    print(f'→ {len(chunks)} chunks')
    all_segs, all_words = [], []
    for p, off in chunks:
        s, w = transcribe_chunk(p, off)
        all_segs.extend(s); all_words.extend(w)
    print(f'✓ {len(all_segs)} segments / {len(all_words)} words transcribed')

    # Refine segment boundaries with word-level timestamps (Whisper's segment
    # times often snap to whole seconds; word times are sub-second precise).
    if all_words:
        wi = 0
        for s in all_segs:
            # find first word whose start is within this segment's text span
            ws = [w for w in all_words if w['start'] >= s['start'] - 0.5
                                       and w['end']   <= s['end']   + 0.5]
            if ws:
                s['start'] = min(s['start'], ws[0]['start'])
                s['end']   = max(s['end'],   ws[-1]['end'])
        print('✓ segment boundaries refined using word timestamps')

    nl = [s['text'] for s in all_segs]
    zh = translate_batch(nl)
    for s, t in zip(all_segs, zh):
        s['translation'] = t
    data = {
        'video_id': 'mock3_a2_2026',
        'video_info': {
            'title': '荷蘭文 A2 luisteren 模擬考三（QQ 自製真實做題版）',
            'channel': '自製模擬考',
            'duration': int(all_segs[-1]['end']) + 5 if all_segs else 0,
        },
        'lang': 'nl', 'native': 'zh-TW',
        'ai_data': {'segments': all_segs, 'words': all_words},
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'✓ {OUT.name} ({len(all_segs)} segs)')


if __name__ == '__main__':
    main()
