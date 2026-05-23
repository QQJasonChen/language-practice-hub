#!/usr/bin/env python3
"""Transcribe full.mp3 (ja) → segments.json (ja + zh translation per segment).

Chunks at 6 min boundaries to dodge the verbose_json HTTP 500 we saw with
long audio + word timestamps. Re-encodes chunks (not -c copy) so offsets are
exact. Translates ja→zh in batches via OpenAI gpt-4o-mini.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

API = os.environ['OPENAI_API_KEY']
HERE = Path(__file__).parent
AUDIO = HERE / 'full.mp3'
OUT = HERE / 'segments.json'

CHUNK_SEC = 360  # 6 min


def transcribe_chunk(mp3: Path, offset: float) -> list:
    print(f'  whisper {mp3.name} (offset={offset:.0f}s)...')
    out = subprocess.run([
        'curl', '-s', 'https://api.openai.com/v1/audio/transcriptions',
        '-H', f'Authorization: Bearer {API}',
        '-F', f'file=@{mp3}',
        '-F', 'model=whisper-1',
        '-F', 'language=ja',
        '-F', 'response_format=verbose_json',
    ], capture_output=True, text=True, timeout=300)
    if out.returncode != 0 or not out.stdout.strip():
        print('  STDERR:', out.stderr[:300]); sys.exit(1)
    res = json.loads(out.stdout)
    if 'error' in res:
        print('  API ERROR:', res['error']); sys.exit(1)
    return [{'start': s['start'] + offset, 'end': s['end'] + offset,
             'text': s['text'].strip()} for s in res.get('segments', [])]


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
    t = 0.0
    i = 0
    while t < dur:
        p = tmp / f'c{i}.mp3'
        subprocess.run(['ffmpeg', '-y', '-ss', str(t), '-i', str(mp3),
                        '-t', str(chunk_sec), '-ac', '1', '-ar', '16000',
                        '-ab', '64k', '-vn', str(p)],
                       check=True, capture_output=True)
        out.append((p, t))
        t += chunk_sec
        i += 1
    return out


def translate_batch(jp_lines: list) -> list:
    """ja→zh-TC. Returns parallel list. Batches 30 at a time."""
    BATCH = 30
    out = []
    for i in range(0, len(jp_lines), BATCH):
        batch = jp_lines[i:i + BATCH]
        numbered = '\n'.join(f'{n+1}. {t}' for n, t in enumerate(batch))
        prompt = (f'把以下日文逐行翻成繁體中文（台灣用語）。一行對一行，'
                  f'保留編號。只輸出譯文，不要解釋。\n\n{numbered}')
        print(f'  translate {i+1}-{i+len(batch)} / {len(jp_lines)}')
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
    all_segs = []
    for p, off in chunks:
        all_segs.extend(transcribe_chunk(p, off))
    print(f'✓ {len(all_segs)} segments transcribed')
    jp = [s['text'] for s in all_segs]
    zh = translate_batch(jp)
    for s, t in zip(all_segs, zh):
        s['translation'] = t
    OUT.write_text(json.dumps(all_segs, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'✓ {OUT.relative_to(HERE.parent)} ({len(all_segs)} segs with translation)')


if __name__ == '__main__':
    main()
