#!/usr/bin/env python3
"""
Build the Language Practice Hub app.
Scans output/ for generated videos and builds app.html with the video library.
"""
import json
import os

def main():
    output_dir = 'output'
    videos = []

    # Collect all videos first, then sort
    all_ids = [v for v in os.listdir(output_dir) if v not in ['Dt_UbEyYqUo', 'eBVlVfAMtWc']]

    # We'll sort after collecting data
    for video_id in all_ids:
        data_path = os.path.join(output_dir, video_id, 'data.json')
        if not os.path.isfile(data_path):
            continue

        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        info = data.get('video_info', {})
        ai = data.get('ai_data', {})

        videos.append({
            'id': video_id,
            'title': info.get('title', 'Unknown'),
            'channel': info.get('channel', ''),
            'duration': info.get('duration', 0),
            'lang': data.get('lang', '?'),
            'native': data.get('native', 'zh-TW'),
            'segments': len(ai.get('segments', [])),
        })

    # Sort: Luisteren first, then by exam number
    import re
    def sort_key(v):
        t = v['title']
        # Luisteren always first
        if 'luisteren' in t.lower(): return (0, 0, t)
        # Tips second
        if 'TIPS' in t or 'tips' in t: return (1, 0, t)
        # Extract exam number
        m = re.search(r'[Oo]efenexamen\s*(\d+)', t)
        num = int(m.group(1)) if m else 99
        # Group by channel
        ch = v.get('channel', '')
        if 'Ad Appel' in ch: return (2, num, t)
        if 'Frederika' in ch or 'LearnDutch' in ch: return (3, num, t)
        return (4, num, t)

    videos.sort(key=sort_key)

    print(f"Found {len(videos)} videos:")
    for v in videos:
        print(f"  [{v['lang']}] {v['title'][:50]} ({v['segments']} segments)")

    # Read template
    with open('app.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # Inject video data
    videos_json = json.dumps(videos, ensure_ascii=False, indent=2)
    html = html.replace('VIDEOS_JSON_PLACEHOLDER', videos_json)

    # Write final app
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ Built index.html with {len(videos)} videos")
    print(f"   Open: file://{os.path.abspath('index.html')}")


if __name__ == '__main__':
    main()
