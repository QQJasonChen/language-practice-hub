#!/usr/bin/env python3
"""Scan all reducties examples + flag segments whose audio is mostly silent.
These are likely Whisper hallucinations (Whisper fakes text on silent regions
in long audio). Outputs a list of (vid, idx) pairs to exclude.

Then rebuild reducties.json without those.

Usage: python3 find_silent_segments.py
"""
import json, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).parent
RED_JSON = ROOT / 'output' / 'reducties.json'
SILENCE_LIST = ROOT / 'output' / '_silent_segments.json'
THRESH_DB = -30
MIN_VOICE_FRACTION = 0.25  # at least 25% of segment must be NON-silent
WORKERS = 8

def check_segment(vid, idx, start, end):
    """Returns True if segment has enough voice content, False if mostly silent.
    Uses ffmpeg volumedetect on the SLICED audio (extracted first to /tmp)."""
    dur = end - start
    audio = ROOT / 'output' / vid / 'audio.mp3'
    if not audio.exists() or dur < 0.5:
        return True
    # Extract just the slice, then check its mean volume
    r = subprocess.run([
        'ffmpeg', '-y', '-hide_banner', '-nostats',
        '-ss', str(start), '-i', str(audio), '-t', str(dur),
        '-af', 'volumedetect',
        '-f', 'null', '-'
    ], capture_output=True, text=True, timeout=10)
    mean_db = None
    max_db = None
    for line in r.stderr.split('\n'):
        if 'mean_volume:' in line:
            try: mean_db = float(line.split('mean_volume:')[1].strip().split()[0])
            except (ValueError, IndexError): pass
        if 'max_volume:' in line:
            try: max_db = float(line.split('max_volume:')[1].strip().split()[0])
            except (ValueError, IndexError): pass
    # A silent slice has mean_volume << -50dB and max_volume < -30dB
    # Normal speech: mean ~ -18 to -25dB, max around 0dB
    if mean_db is None: return True
    if mean_db < -50 and (max_db is None or max_db < -30):
        return False  # silent
    return True

def main():
    d = json.loads(RED_JSON.read_text(encoding='utf-8'))
    # Collect all unique (vid, idx, start, end) tuples
    seen = {}
    for p in d['patterns']:
        for ex in p['examples']:
            key = (ex['vid'], ex['idx'])
            seen[key] = (ex['start'], ex['end'], ex['text'])
    print(f'▶ Checking {len(seen)} unique segments for silence (threshold {THRESH_DB}dB)...')

    silent = set()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {
            ex.submit(check_segment, vid, idx, start, end): (vid, idx, text)
            for (vid, idx), (start, end, text) in seen.items()
        }
        for i, fut in enumerate(as_completed(futures)):
            vid, idx, text = futures[fut]
            try:
                ok = fut.result()
            except Exception as e:
                ok = True  # don't filter on error
            if not ok:
                silent.add((vid, idx))
                print(f'  ✗ SILENT  {vid[:5]} idx={idx}  "{text[:60]}"')
            if (i + 1) % 20 == 0:
                print(f'    [{i+1}/{len(seen)}] checked', flush=True)

    print(f'\n✓ Found {len(silent)} silent (hallucinated) segments to exclude')
    # Save for build_reducties.py to use
    SILENCE_LIST.write_text(json.dumps(
        {'silent': [[v, i] for v, i in sorted(silent)]},
        ensure_ascii=False, indent=2
    ), encoding='utf-8')
    print(f'  → {SILENCE_LIST.relative_to(ROOT)}')

    # Filter reducties.json directly
    removed = 0
    for p in d['patterns']:
        before = len(p['examples'])
        p['examples'] = [e for e in p['examples']
                         if (e['vid'], e['idx']) not in silent]
        p['count'] = len(p['examples'])
        removed += before - len(p['examples'])
    RED_JSON.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n✓ Removed {removed} entries from reducties.json')
    total = sum(p['count'] for p in d['patterns'])
    print(f'  Final: {total} drill items across {len(d["patterns"])} patterns')

if __name__ == '__main__':
    main()
