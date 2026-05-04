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

    # Custom sort: pin specific videos first
    PIN_FIRST = ['_iC1Pooi2UA']  # Luisteren exam first
    all_ids = sorted(os.listdir(output_dir))
    all_ids = [v for v in PIN_FIRST if v in all_ids] + [v for v in all_ids if v not in PIN_FIRST]

    for video_id in [v for v in all_ids if v not in ['Dt_UbEyYqUo', 'eBVlVfAMtWc']]:
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
