#!/usr/bin/env python3
"""PRODUCT B — 原創精華版 (clean, sellable) packaging.

Bundles the 10 original mocks (PDF 完整版 + 純荷文盲練 + Xander 音檔) plus an
offline index into dist/A2-luisteren-原創精華版/ and zips it.
100% original script + Apple TTS voice → safe to sell.
"""
import json, re, shutil, pathlib, html
ROOT = pathlib.Path(__file__).parent
OUT = ROOT / 'output'
TRANS = ROOT / 'transcripts'
DIST = ROOT / 'dist'
PACK = DIST / 'A2-luisteren-原創精華版'

def slug(s, maxlen=90):
    s = re.sub(r'[\\/:*?"<>|]', '_', (s or '').strip())
    s = re.sub(r'\s+', ' ', s).replace('#', '').replace('！', '!').replace('？', '?')
    return s[:maxlen].rstrip(' .')

def esc(t): return html.escape(str(t or ''))

def build():
    if PACK.exists(): shutil.rmtree(PACK)
    (PACK / '講義PDF').mkdir(parents=True)
    (PACK / '音檔').mkdir(parents=True)
    cards = []
    ids = sorted(d.name for d in OUT.glob('orig_*') if (d / 'exam.json').exists())
    for i, vid in enumerate(ids, 1):
        ex = json.loads((OUT / vid / 'exam.json').read_text(encoding='utf-8'))
        title = ex['title']; ch = ex.get('channel', '')
        cs, ts = slug(ch, 60), slug(title, 90)
        links = []
        for suffix, cls, lbl in [('', 'pdf', '📄 完整講義'), (' · 純荷文盲練', 'blind', '🙈 純荷文盲練')]:
            src = TRANS / cs / f'{ts}{suffix}.pdf'
            if src.exists():
                dst = PACK / '講義PDF' / f'{i:02d} {ts}{suffix}.pdf'
                shutil.copy2(src, dst)
                links.append(f'<a class="lk {cls}" href="講義PDF/{esc(dst.name)}">{lbl}</a>')
        mp3 = sorted((OUT / vid).glob('*.mp3'))
        if mp3:
            dst = PACK / '音檔' / f'{i:02d} {slug(ex["scenarios"][0]["title_nl"],80)}.mp3'
            shutil.copy2(mp3[0], dst)
            links.append(f'<a class="lk audio" href="音檔/{esc(dst.name)}">🎧 音檔</a>')
        sc = ex['scenarios'][0]
        cards.append(f'''<div class="card">
      <div class="num">{i:02d}</div>
      <div class="meta"><div class="ti">{esc(sc["title_zh"])}　<span class="nl">{esc(sc["title_nl"])}</span></div>
        <div class="ch">{esc(ex.get("exam_type",""))} · {ex.get("n_questions",0)} 題</div></div>
      <div class="links">{"".join(links)}</div>
    </div>''')
    index = INDEX_TMPL.replace('{{CARDS}}', '\n'.join(cards)).replace('{{N}}', str(len(ids)))
    (PACK / '00-開始這裡.html').write_text(index, encoding='utf-8')
    (PACK / 'README.txt').write_text(README, encoding='utf-8')
    (PACK / 'LICENSE-授權.txt').write_text(LICENSE, encoding='utf-8')
    return ids

INDEX_TMPL = '''<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>A2 Luisteren 原創精華版</title><style>
*{box-sizing:border-box}body{margin:0;background:#faf6ee;color:#2a2620;
 font:15px/1.6 -apple-system,"PingFang TC","Hiragino Sans",sans-serif}
.wrap{max-width:820px;margin:0 auto;padding:30px 18px 80px}
h1{font-size:25px;margin:0 0 4px;color:#b8421f}.sub{color:#8a7f6e;font-size:13px;margin-bottom:18px}
.note{background:#fff;border:1px solid #e4d9c4;border-left:4px solid #e0a93c;border-radius:10px;
 padding:13px 16px;font-size:12.5px;color:#6b5d44;margin-bottom:22px}
.card{display:flex;align-items:center;gap:14px;background:#fff;border:1px solid #ece2d0;
 border-radius:12px;padding:13px 16px;margin-bottom:10px;flex-wrap:wrap;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.num{font-size:14px;font-weight:800;color:#b8421f;flex:0 0 28px}
.meta{flex:1;min-width:200px}.ti{font-weight:700;font-size:15px}.ti .nl{color:#a89880;font-weight:500;font-size:13px}
.ch{color:#9c8f78;font-size:11.5px;margin-top:2px}
.links{display:flex;gap:7px;flex-wrap:wrap}
.lk{font-size:12px;font-weight:700;text-decoration:none;padding:6px 11px;border-radius:8px;white-space:nowrap;border:1px solid}
.lk.pdf{background:#eef4ff;color:#2563eb;border-color:#c7dafc}
.lk.blind{background:#fff7e6;color:#b7791f;border-color:#f0d9a0}
.lk.audio{background:#e9faf4;color:#0d8a6a;border-color:#aee6d4}
</style></head><body><div class="wrap">
<h1>🎧 A2 Luisteren 原創精華版</h1>
<div class="sub">{{N}} 套原創情境模擬 · 對話＋題目＋單字＋語序詳解＋荷語音檔 · 全離線</div>
<div class="note">📌 用法：先聽「🎧 音檔」配「🙈 純荷文盲練」測自己聽懂多少 → 再對「📄 完整講義」（中譯＋單字＋🧩語序詳解＋答案出處）。每套涵蓋一個常考生活場景。<br>
✅ 全部對話為原創、配音為合成荷語，無第三方素材。</div>
{{CARDS}}
</div></body></html>'''

README = '''A2 Luisteren 原創精華版
========================

打開「00-開始這裡.html」即可（雙擊用瀏覽器開，完全離線）。

10 套原創情境模擬，涵蓋 inburgering A2 聽力最常考的生活場景：
看醫生預約、請病假、車站誤點、商店換貨、餐廳訂位、市政府登記、
報名課程、暖氣報修、銀行掛失、健身房報名。

每套包含：
  · 完整講義 PDF：荷文對話＋中譯＋重點單字＋必背句型＋
    考題（含答案出處、💡反推、⚠️陷阱）＋🧩語序詳解
  · 純荷文盲練 PDF：先遮中文自測聽力
  · 荷語音檔 (mp3)：可反覆精聽、跟讀

建議流程：
  1. 聽音檔 + 看純荷文盲練，先自測
  2. 對完整講義補中譯、單字、語序
  3. 重聽到能跟讀、能秒懂題目
'''

LICENSE = '''授權說明 / License
====================

本產品（A2 Luisteren 原創精華版）之所有對話腳本、題目、單字整理、
語序詳解皆為原創內容；音檔為合成語音（Apple Nederlands TTS），
不含任何第三方錄音或他人逐字稿。

購買者授權：
  ✓ 個人學習使用
  ✓ 列印自用

請勿：
  ✗ 轉售、再散布原始檔案
  ✗ 公開上傳到網路供他人免費下載

© 內容原創，保留一切權利。
'''

if __name__ == '__main__':
    ids = build()
    print(f'✓ assembled {len(ids)} original mocks into {PACK.relative_to(ROOT)}')
