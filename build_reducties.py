#!/usr/bin/env python3
"""Scan all 3 mocks' transcripts for the highest-yield connected-speech /
weak-form patterns A2 inburgering learners miss. Output → output/reducties.json

These are the patterns where the SOUND ≠ the WRITTEN form, so reading
helps zero — the only fix is repeated listening at slow speed.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).parent
MOCKS = ['_iC1Pooi2UA', 'AMVy2zPNLso', 'mock3_a2_2026']
PER_PATTERN_CAP = 8  # max examples per pattern (avoid UI overload)

# Patterns: (id, name, category, zh, icon, desc, spoken_hint, regex)
# Order: function words first (highest priority), then multi-word reductions
PATTERNS = [
    # ── Single function words (small + often missed) ──
    {
        'id': 'niet', 'name': 'niet', 'category': 'function_word',
        'zh': '否定詞', 'icon': '❌',
        'desc': '最常被吃掉的字。漏聽就把否定句聽成肯定句 → 答案完全反過來。',
        'spoken_hint': "通常很輕、和前一個字連讀。'Het is niet' 聽起來像 'Hetisniet' 黏一坨。",
        'regex': r'\bniet\b',
    },
    {
        'id': 'wel', 'name': 'wel', 'category': 'function_word',
        'zh': '反向肯定', 'icon': '✅',
        'desc': '和 niet 對應的反向強調「就是有/就是會」。聽到 wel = 答案是肯定的。',
        'spoken_hint': "和 niet 同樣輕。在 'Ik kom wel' 裡的 wel 幾乎沒重音。",
        'regex': r'\bwel\b',
    },
    {
        'id': 'je', 'name': 'je', 'category': 'function_word',
        'zh': '你（弱讀 → e/ie）', 'icon': '👉',
        'desc': '幾乎看不到 j 音、整個吃進前面動詞。',
        'spoken_hint': "'Heb je' → 'Hebbie'，'Ga je' → 'Gaje'，'Wil je' → 'Wilje'。",
        'regex': r'\bje\b',
    },
    {
        'id': 'het', 'name': 'het', 'category': 'function_word',
        'zh': '它/這個 (中性代名詞)', 'icon': '🔘',
        'desc': "h 音幾乎不發、變成 't 黏在前一個字後面。",
        'spoken_hint': "'Ik heb het' → 'Ikhept'，'Doe het' → 'Doet'。",
        'regex': r'\bhet\b',
    },
    {
        'id': 'er', 'name': 'er', 'category': 'function_word',
        'zh': '在那裡（指代）', 'icon': '📍',
        'desc': "弱讀成 'r 黏在動詞後面。漏聽就分不清主詞。",
        'spoken_hint': "'Er is' → \"'ris\"，'Er staat' → \"'rstaat\"。",
        'regex': r'\ber\b',
    },
    {
        'id': 'al', 'name': 'al', 'category': 'function_word',
        'zh': '已經', 'icon': '⏰',
        'desc': '兩個字母、很輕、漏聽就分不清「現在 vs 已經多久」',
        'spoken_hint': "'is al zwanger' 裡的 al 幾乎聽不到，但漏聽就把『已經懷孕 X 個月』聽成『現在懷孕』。",
        'regex': r'\bal\b',
    },
    {
        'id': 'maar', 'name': 'maar', 'category': 'function_word',
        'zh': '但是 / 才（轉折）', 'icon': '🔄',
        'desc': '轉折詞 — maar 後面才是真資訊。前面是干擾。',
        'spoken_hint': "「Niet ..., maar ...」結構：聽到 maar 後面才是答案。",
        'regex': r'\bmaar\b',
    },
    {
        'id': 'nog', 'name': 'nog', 'category': 'function_word',
        'zh': '還 / 仍然', 'icon': '🔁',
        'desc': "'還要做'、'還沒做'、'再來一份' — A2 高頻時間/數量副詞",
        'spoken_hint': "'Heb je nog ...?' 'Nog niet'：常和 niet/geen 一起出現，要兩個都抓到。",
        'regex': r'\bnog\b',
    },
    {
        'id': 'pas', 'name': 'pas', 'category': 'function_word',
        'zh': '才 / 剛剛', 'icon': '⏳',
        'desc': "'才幾點'、'剛剛開始' — 時間限定詞",
        'spoken_hint': "'Het is pas drie uur'：pas = 才，否定預期。",
        'regex': r'\bpas\b',
    },
    # ── Multi-word reductions（高頻連音句頭） ──
    {
        'id': 'hebje', 'name': 'Heb je', 'category': 'reduction',
        'zh': '你有...嗎？', 'icon': '🔗',
        'desc': '問句最高頻句頭、變成一個字 \'Hebbie\'',
        'spoken_hint': 'Heb + je → Hebbie。聽到 Hebbie 就要反應「他在問你有沒有 X」',
        'regex': r'\bheb\s+je\b',
    },
    {
        'id': 'wilje', 'name': 'Wil je', 'category': 'reduction',
        'zh': '你要 / 想 ...嗎？', 'icon': '🔗',
        'desc': '邀請、提議句最高頻開頭、變成 \'Wilje\'',
        'spoken_hint': 'Wil + je → Wilje。',
        'regex': r'\bwil\s+je\b',
    },
    {
        'id': 'gaje', 'name': 'Ga je', 'category': 'reduction',
        'zh': '你去 / 要 ...嗎？', 'icon': '🔗',
        'desc': '變成 \'Gaje\' 或 \'Gah-je\'',
        'spoken_hint': 'Ga + je → Gaje',
        'regex': r'\bga\s+je\b',
    },
    {
        'id': 'kanje', 'name': 'Kan je', 'category': 'reduction',
        'zh': '你能 ...嗎？', 'icon': '🔗',
        'desc': '能力詢問、變成 \'Kanje\'',
        'spoken_hint': 'Kan + je → Kanje（很常見的請託開頭）',
        'regex': r'\bkan\s+je\b',
    },
    {
        'id': 'magje', 'name': 'Mag je', 'category': 'reduction',
        'zh': '你可以 ...嗎？', 'icon': '🔗',
        'desc': '許可詢問、變成 \'Magje\'',
        'spoken_hint': 'Mag + je → Magje。',
        'regex': r'\bmag\s+je\b',
    },
    {
        'id': 'watis', 'name': 'Wat is', 'category': 'reduction',
        'zh': '什麼是 ...？ / ...是什麼？', 'icon': '🔗',
        'desc': '黏成 \'Watis\'。A2 萬用問句。',
        'spoken_hint': 'Wat + is → Watis（一個字）',
        'regex': r'\bwat\s+is\b',
    },
    {
        'id': 'hoeis', 'name': 'Hoe is', 'category': 'reduction',
        'zh': '...怎麼樣？', 'icon': '🔗',
        'desc': '黏成 \'Hoeis\'',
        'spoken_hint': 'Hoe + is → Hoeis',
        'regex': r'\bhoe\s+is\b',
    },
    {
        'id': 'datis', 'name': 'Dat is', 'category': 'reduction',
        'zh': '那是 ...', 'icon': '🔗',
        'desc': '回答句、變成 \'Datis\'',
        'spoken_hint': 'Dat + is → Datis（dis 也可以）',
        'regex': r'\bdat\s+is\b',
    },
    {
        'id': 'ikheb', 'name': 'Ik heb', 'category': 'reduction',
        'zh': '我有 ...', 'icon': '🔗',
        'desc': "Ik 弱讀 → 'k，整個變成 'kheb 或 'khep\"",
        'spoken_hint': "Ik + heb → 'kheb（很快、幾乎一個音節）",
        'regex': r'\bik\s+heb\b',
    },
    {
        'id': 'ikben', 'name': 'Ik ben', 'category': 'reduction',
        'zh': '我是 ...', 'icon': '🔗',
        'desc': "變成 'kben",
        'spoken_hint': "Ik + ben → 'kben",
        'regex': r'\bik\s+ben\b',
    },
]


def main():
    out = {'patterns': []}
    all_segs = {}
    for vid in MOCKS:
        d = json.loads((ROOT / 'output' / vid / 'data.json').read_text(encoding='utf-8'))
        all_segs[vid] = d['ai_data']['segments']

    for pat in PATTERNS:
        regex = re.compile(pat['regex'], re.IGNORECASE)
        examples = []
        # Dedupe by (vid, normalized_text) — A2 mocks replay each scenario twice,
        # so the same sentence appears 2x in data.json. Keep only first occurrence.
        seen = set()
        for vid in MOCKS:
            for idx, seg in enumerate(all_segs[vid]):
                text = (seg.get('text') or '').strip()
                if not text:
                    continue
                m = regex.search(text)
                if not m:
                    continue
                if len(text) > 130:
                    continue
                key = (vid, text.lower())
                if key in seen:
                    continue
                seen.add(key)
                examples.append({
                    'vid': vid,
                    'idx': idx,
                    'text': text,
                    'zh': (seg.get('translation') or '').strip(),
                    'start': round(float(seg.get('start') or 0), 2),
                    'end': round(float(seg.get('end') or 0), 2),
                    'match_start': m.start(),
                    'match_end': m.end(),
                })
        # Sort by text length asc (easier first), cap
        examples.sort(key=lambda e: len(e['text']))
        examples = examples[:PER_PATTERN_CAP]
        out['patterns'].append({
            'id': pat['id'], 'name': pat['name'], 'category': pat['category'],
            'zh': pat['zh'], 'icon': pat['icon'], 'desc': pat['desc'],
            'spoken_hint': pat['spoken_hint'],
            'count': len(examples),
            'examples': examples,
        })

    out_path = ROOT / 'output' / 'reducties.json'
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    total = sum(p['count'] for p in out['patterns'])
    print(f'✓ {out_path.relative_to(ROOT)}')
    print(f'  {len(PATTERNS)} patterns, {total} drill items')
    for p in out['patterns']:
        print(f'    {p["icon"]} {p["name"]:10s} {p["count"]:2d} examples')


if __name__ == '__main__':
    main()
