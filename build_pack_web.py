#!/usr/bin/env python3
"""Build the INTERACTIVE OFFLINE WEB pack — buyers double-click an index page and
practise exactly like the live site: play audio, follow-along highlight, tap words,
questions + AI 詳解. Every lesson's exam.html is already self-contained (no fetch;
audio is a local audio.mp3), so we just bundle them with a fetch-free index.

Usage:
  python3 build_pack_web.py            # all lessons that have exam.html+audio.mp3
  python3 build_pack_web.py orig_01 .. # only the given ids
"""
import json, re, shutil, sys, pathlib, html, urllib.parse
ROOT = pathlib.Path(__file__).parent
OUT = ROOT / 'output'
DIST = ROOT / 'dist'
PACK = DIST / 'A2-luisteren-互動網頁版'

def slug(s, maxlen=80):
    s = (s or '').strip().replace('#', '').replace('?', '').replace('!', '')
    s = re.sub(r'[\\/:*"<>|]', '_', s)
    s = re.sub(r'\s+', ' ', s)
    return s[:maxlen].rstrip(' .')

def esc(t): return html.escape(str(t or ''))
def url(t): return urllib.parse.quote(t)

def ready_ids(only):
    ids = []
    for d in sorted(OUT.glob('*/')):
        vid = d.name
        if only and vid not in only: continue
        if (d / 'exam.html').exists() and (d / 'audio.mp3').exists():
            ids.append(vid)
    return ids

def build(only):
    if PACK.exists(): shutil.rmtree(PACK)
    (PACK / '課程').mkdir(parents=True)
    cards = []
    ids = ready_ids(only)
    for i, vid in enumerate(ids, 1):
        ex = json.loads((OUT / vid / 'exam.json').read_text(encoding='utf-8'))
        title = ex.get('title') or vid
        nq = ex.get('n_questions', 0)
        nsc = len(ex.get('scenarios', []))
        folder = f'{i:02d} {slug(title)}'
        dst = PACK / '課程' / folder
        dst.mkdir()
        shutil.copy2(OUT / vid / 'exam.html', dst / 'exam.html')
        shutil.copy2(OUT / vid / 'audio.mp3', dst / 'audio.mp3')
        href = f'課程/{url(folder)}/exam.html'
        cards.append(f'''<a class="card" href="{href}">
      <div class="num">{i:02d}</div>
      <div class="meta"><div class="ti">{esc(title)}</div>
        <div class="sub">🗂 {nsc} 場景 · ❓ {nq} 題</div></div>
      <div class="go">▶ 開始練習</div>
    </a>''')
    index = INDEX_TMPL.replace('{{CARDS}}', '\n'.join(cards)).replace('{{N}}', str(len(ids)))
    (PACK / '00-開始這裡.html').write_text(index, encoding='utf-8')
    (PACK / 'README.txt').write_text(README, encoding='utf-8')
    return ids

INDEX_TMPL = '''<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>A2 Luisteren 互動練習</title><style>
*{box-sizing:border-box}body{margin:0;background:#faf6ee;color:#2a2620;
 font:15px/1.6 -apple-system,"PingFang TC","Hiragino Sans",sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:30px 16px 80px}
h1{font-size:25px;margin:0 0 4px;color:#b8421f}.sub{color:#8a7f6e;font-size:13px;margin-bottom:18px}
.note{background:#fff;border:1px solid #e4d9c4;border-left:4px solid #e0a93c;border-radius:10px;
 padding:13px 16px;font-size:12.5px;color:#6b5d44;margin-bottom:22px}
.card{display:flex;align-items:center;gap:14px;background:#fff;border:1px solid #ece2d0;
 border-radius:12px;padding:14px 16px;margin-bottom:10px;text-decoration:none;color:inherit;
 box-shadow:0 1px 2px rgba(0,0,0,.03);transition:border-color .15s}
.card:hover{border-color:#e0a93c}
.num{font-size:14px;font-weight:800;color:#b8421f;flex:0 0 30px}
.meta{flex:1;min-width:0}.ti{font-weight:700;font-size:15px}
.sub{color:#9c8f78;font-size:12px;margin:2px 0 0}
.go{flex:none;font-size:13px;font-weight:800;color:#0d8a6a;background:#e9faf4;
 border:1px solid #aee6d4;border-radius:8px;padding:7px 12px;white-space:nowrap}
</style></head><body><div class="wrap">
<h1>🎧 A2 Luisteren 互動練習</h1>
<div class="sub">{{N}} 課 · 點一課即可直接練習：撥放音檔、逐句跟讀高亮、點字看意思、題目＋AI 詳解</div>
<div class="note">📌 用法：點任一課 → 按播放，畫面會跟著高亮目前那句；聽不懂用 ⏪ 重聽；不會的字直接點；下面有題目和詳解。<br>
全程<b>離線</b>，不需要網路（影片模式才需網路，音檔模式完全離線）。</div>
{{CARDS}}
</div></body></html>'''

README = '''A2 Luisteren 互動練習（離線網頁版）
====================================

打開「00-開始這裡.html」即可（雙擊用瀏覽器開）。
點任一課就能直接練習，完全離線、不需要架站、不需要網路：

  · 按播放鍵聽音檔，畫面自動高亮目前唸到的句子（跟讀）
  · ⏪ ⏩ 倒退/快轉，聽不懂的地方反覆重聽
  · 點任何荷文字 → 看中文意思
  · 每段下方有題目 + 💡 AI 詳解（中譯、單字、語序拆解）

建議用 Chrome 或 Safari 開。手機也可以：把整個資料夾放進手機，
用檔案 App 開「00-開始這裡.html」。

（影片模式需要網路；預設的「音檔模式」完全離線。）
'''

if __name__ == '__main__':
    only = set(a for a in sys.argv[1:])
    ids = build(only)
    print(f'✓ {len(ids)} interactive lessons bundled into {PACK.relative_to(ROOT)}')
    for i in ids[:3]: print('  -', i)
    if len(ids) > 3: print(f'  … +{len(ids)-3} more')
