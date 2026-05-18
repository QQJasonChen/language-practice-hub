#!/usr/bin/env python3
"""Re-render every output/<id>/index.html from the CURRENT template.html
plus the existing data.json. Pure templating — NO download / transcribe /
AI. Run this after editing template.html so player/feature changes reach
every already-generated video without re-spending Whisper/AI."""
import json
import sys
from pathlib import Path

import generate  # reuse generate.generate_html for byte-identical output

OUT = Path(__file__).parent / 'output'

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    n = 0
    for d in sorted(p for p in OUT.iterdir() if p.is_dir()):
        if only and d.name != only:
            continue
        dj = d / 'data.json'
        if not dj.is_file():
            continue
        data = json.loads(dj.read_text(encoding='utf-8'))
        ai = data.get('ai_data', {})
        info = data.get('video_info', {})
        lang = data.get('lang', 'nl')
        native = data.get('native', 'zh-TW')
        generate.generate_html(ai, info, lang, native, str(d))
        n += 1
        print(f"  ✓ {d.name}: {len(ai.get('segments', []))} segs")
    print(f"\n✅ Re-rendered {n} page(s) from current template.html")

if __name__ == '__main__':
    main()
