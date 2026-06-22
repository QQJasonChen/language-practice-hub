#!/usr/bin/env python3
"""Build PRODUCT A — 考古題完整版 (full pack, contains 3rd-party transcripts/audio).
For personal practice / grey-area distribution only.

Assembles existing PDFs + audio + an offline index into dist/A2-luisteren-考古題完整版/
then zips it. The index is link-only HTML, so it works by double-click (file://) —
no server, no fetch.
"""
import json, os, re, shutil, glob, pathlib, html
ROOT = pathlib.Path(__file__).parent
OUT = ROOT / 'output'
TRANS = ROOT / 'transcripts'
DIST = ROOT / 'dist'
PACK = DIST / 'A2-luisteren-考古題完整版'

def slug(s, maxlen=90):
    s = re.sub(r'[\\/:*?"<>|]', '_', (s or '').strip())
    s = re.sub(r'\s+', ' ', s).replace('#', '').replace('！', '!').replace('？', '?')
    return s[:maxlen].rstrip(' .')

def esc(t): return html.escape(str(t or ''))

YT11 = re.compile(r'^[A-Za-z0-9_-]{11}$')

def lessons():
    rows = []
    for ej in sorted(OUT.glob('*/exam.json')):
        vid = ej.parent.name
        ex = json.loads(ej.read_text(encoding='utf-8'))
        title = ex.get('title') or vid
        channel = ex.get('channel') or '_unknown'
        cs, ts = slug(channel, 60), slug(title, 90)
        pdf_full = TRANS / cs / f'{ts}.pdf'
        pdf_blind = TRANS / cs / f'{ts} · 純荷文盲練.pdf'
        mp3 = sorted((OUT / vid).glob('*.mp3'))
        rows.append({'vid': vid, 'title': title, 'channel': channel,
                     'pdf_full': pdf_full if pdf_full.exists() else None,
                     'pdf_blind': pdf_blind if pdf_blind.exists() else None,
                     'mp3': mp3[0] if mp3 else None,
                     'n_q': ex.get('n_questions', 0),
                     'yt': vid if YT11.match(vid) else None})
    return rows

def build():
    if PACK.exists(): shutil.rmtree(PACK)
    (PACK / '講義PDF').mkdir(parents=True)
    (PACK / '音檔').mkdir(parents=True)
    rows = lessons()
    cards = []
    for i, r in enumerate(rows, 1):
        ts = slug(r['title'], 90)
        links = []
        if r['pdf_full']:
            dst = PACK / '講義PDF' / f'{i:02d} {ts}.pdf'
            shutil.copy2(r['pdf_full'], dst)
            links.append(f'<a class="lk pdf" href="講義PDF/{esc(dst.name)}">📄 完整講義</a>')
        if r['pdf_blind']:
            dst = PACK / '講義PDF' / f'{i:02d} {ts} · 純荷文盲練.pdf'
            shutil.copy2(r['pdf_blind'], dst)
            links.append(f'<a class="lk blind" href="講義PDF/{esc(dst.name)}">🙈 純荷文盲練</a>')
        if r['mp3']:
            dst = PACK / '音檔' / f'{i:02d} {ts}.mp3'
            shutil.copy2(r['mp3'], dst)
            links.append(f'<a class="lk audio" href="音檔/{esc(dst.name)}">🎧 音檔</a>')
        if r['yt']:
            links.append(f'<a class="lk yt" href="https://www.youtube.com/watch?v={r["yt"]}" target="_blank">▶ 原始影片</a>')
        cards.append(f'''<div class="card">
      <div class="num">{i:02d}</div>
      <div class="meta"><div class="ti">{esc(r["title"])}</div>
        <div class="ch">{esc(r["channel"])}{f" · {r['n_q']} 題" if r['n_q'] else ""}</div></div>
      <div class="links">{"".join(links)}</div>
    </div>''')
    index = INDEX_TMPL.replace('{{CARDS}}', '\n'.join(cards)).replace('{{N}}', str(len(rows)))
    (PACK / '00-開始這裡.html').write_text(index, encoding='utf-8')
    (PACK / 'README.txt').write_text(README, encoding='utf-8')
    return rows

INDEX_TMPL = '''<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>A2 Luisteren 考古題完整版</title><style>
*{box-sizing:border-box}body{margin:0;background:#0f1115;color:#e8e8f0;
 font:15px/1.6 -apple-system,"PingFang TC","Hiragino Sans",sans-serif}
.wrap{max-width:820px;margin:0 auto;padding:28px 18px 80px}
h1{font-size:24px;margin:0 0 4px}.sub{color:#9ca3af;font-size:13px;margin-bottom:18px}
.note{background:#1a1410;border:1px solid #5a3d1a;border-radius:10px;padding:12px 15px;
 font-size:12.5px;color:#e5c79a;margin-bottom:22px}
.card{display:flex;align-items:center;gap:14px;background:#161922;border:1px solid #232838;
 border-radius:12px;padding:13px 15px;margin-bottom:10px;flex-wrap:wrap}
.num{font-size:13px;font-weight:800;color:#5eead4;flex:0 0 28px}
.meta{flex:1;min-width:180px}.ti{font-weight:700;font-size:14.5px}.ch{color:#9ca3af;font-size:11.5px;margin-top:2px}
.links{display:flex;gap:7px;flex-wrap:wrap}
.lk{font-size:12px;font-weight:700;text-decoration:none;padding:6px 10px;border-radius:8px;white-space:nowrap}
.lk.pdf{background:#1e3a8a33;color:#93c5fd;border:1px solid #1e40af}
.lk.blind{background:#3f3a1e33;color:#fcd34d;border:1px solid #78690f}
.lk.audio{background:#0f3d3333;color:#5eead4;border:1px solid #0f5e4e}
.lk.yt{background:#3a1414;color:#fca5a5;border:1px solid #7f1d1d}
</style></head><body><div class="wrap">
<h1>🎧 A2 Luisteren 考古題完整版</h1>
<div class="sub">{{N}} 課 · 完整講義 + 純荷文盲練 + 音檔 · 全離線可用</div>
<div class="note">📌 用法：每課先「🙈 純荷文盲練」測自己聽懂多少 → 對「📄 完整講義」（含中譯＋單字＋語序詳解）→ 配「🎧 音檔」反覆精聽。<br>
⚠️ 本包含第三方頻道素材，僅供個人學習使用，請勿公開散布。</div>
{{CARDS}}
</div></body></html>'''

README = '''A2 Luisteren 考古題完整版
==========================

打開「00-開始這裡.html」即可（雙擊用瀏覽器開，完全離線、不需網路）。

內容：
  講義PDF/   每課兩個版本——「完整講義」(逐字稿+中譯+單字+語序詳解) 與
             「純荷文盲練」(只有荷文，先自測聽力)
  音檔/      每課對應的聽力音檔 (mp3)

學習流程：
  1. 先聽音檔 + 看「純荷文盲練」，測自己聽懂多少
  2. 再對「完整講義」，補中譯、單字、語序
  3. 反覆精聽到能跟讀

⚠️ 著作權聲明
  本包內的逐字稿與音檔，部分整理自公開 YouTube 頻道教材，
  僅供「個人」學習練習使用。請勿公開散布或商業販售。
  （想公開販售，請改用「原創精華版」。）
'''

if __name__ == '__main__':
    rows = build()
    print(f'✓ assembled {len(rows)} lessons into {PACK.relative_to(ROOT)}')
