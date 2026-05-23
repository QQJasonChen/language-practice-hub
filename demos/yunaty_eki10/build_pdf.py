#!/usr/bin/env python3
"""Render content.json → PDF handout (static, for printing / offline study).

Single variant — content courses don't benefit from a "blind" version like
exam handouts do. Includes QR back to the YouTube source so reader can jump
to the audio version on phone.
"""
import json
import os
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).parent
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def esc(t: str) -> str:
    return (t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def qr(url: str, size: int = 100) -> str:
    enc = urllib.parse.quote(url, safe='')
    return (f'<img src="https://api.qrserver.com/v1/create-qr-code/'
            f'?size={size*2}x{size*2}&data={enc}" alt="QR" />')


CSS = """
@page { size: A4; margin: 16mm 15mm 18mm; @bottom-center {
  content: counter(page) " / " counter(pages); font: 10px -apple-system,sans-serif; color:#9ca3af; } }
body { margin:0; padding:0; font:13.5px/1.6 -apple-system,"PingFang TC","Hiragino Sans","Noto Sans JP",sans-serif;
  color:#1f2937; }
h1 { font-size:20px; margin:0 0 6px; line-height:1.35; }
.cover { display:flex; gap:14px; border-bottom:2px solid #9f1239; padding-bottom:12px; margin-bottom:14px; }
.cover .left { flex:1; }
.cover .meta { font-size:11.5px; color:#6b7280; }
.cover .meta span + span::before { content:" · "; color:#d1d5db; padding:0 3px; }
.cover .qr { flex:0 0 92px; text-align:center; }
.cover .qr img { width:92px; height:92px; }
.cover .qr .lbl { font-size:8.5px; color:#9ca3af; margin-top:3px; }
.howto { background:#fdf2f8; border-left:3px solid #9f1239; border-radius:5px;
  padding:9px 13px; font-size:12px; color:#7c2d12; margin:8px 0; }
.howto b { color:#9f1239; }
.intro { background:#fff7ed; border-left:3px solid #f59e0b; border-radius:5px;
  padding:9px 13px; font-size:11.5px; color:#7c2d12; margin:6px 0 12px; }
/* chapter */
.ch { page-break-before: always; }
.ch:first-of-type { page-break-before: auto; }
.ch-bar { background:#1e293b; color:#fff; border-radius:6px 6px 0 0; padding:8px 14px;
  display:flex; align-items:baseline; gap:10px; }
.ch-bar .rank { font-size:14px; font-weight:900; color:#f59e0b; min-width:36px; }
.ch-bar .rank.open { color:#94a3b8; font-size:11px; }
.ch-bar .ja { font-size:15px; font-weight:800; flex:1; }
.ch-bar .zh { font-size:11px; color:#cbd5e1; }
.hl { background:#fef3c7; padding:5px 14px; font-size:11.5px; color:#92400e; font-weight:600;
  border-bottom:1px solid #fde68a; }
.hl::before { content:"✦ "; color:#f59e0b; }
.ctx { background:#f8fafc; padding:6px 14px; font-size:11.5px; color:#475569;
  border-bottom:1px solid #e5e7eb; }
.prev { display:flex; gap:14px; margin:10px 0 8px; break-inside:avoid; }
.prev .col { flex:1; min-width:0; }
.prev h3 { font-size:11.5px; font-weight:800; color:#9f1239; margin:0 0 6px;
  letter-spacing:.4px; }
.vocab { width:100%; border-collapse:collapse; font-size:11.5px; }
.vocab td { padding:4px 7px; border:1px solid #f3e8d0; vertical-align:top; }
.vocab td.ja { font-weight:700; width:42%; }
.vocab td.ja .kana { display:block; font-size:9.5px; color:#94a3b8; font-weight:500; }
.vocab td.zh { color:#6b7280; }
.vocab tr:nth-child(even) td { background:#fffdf7; }
.pat { font-size:11.5px; margin:0 0 6px; padding-bottom:5px; border-bottom:1px dotted #e5e7eb; }
.pat .pja { font-weight:700; color:#0f766e; }
.pat .pnote { color:#9ca3af; font-size:10.5px; display:block; }
.dlg-h { font-size:12.5px; font-weight:800; color:#9f1239; margin:12px 0 4px; }
.line { display:flex; gap:9px; padding:5px 0; border-bottom:1px dashed #f0f0f0;
  break-inside:avoid; }
.line .ts { flex:0 0 42px; font:700 10.5px ui-monospace,Menlo,monospace; color:#9f1239; padding-top:1px; }
.line .lb { flex:1; min-width:0; }
.line .lja { color:#1f2937; }
.line .lzh { color:#9ca3af; font-size:11.5px; }
.cul { background:#fff7ed; border-left:3px solid #f59e0b; padding:8px 12px;
  font-size:11.5px; color:#7c2d12; margin-top:9px; border-radius:4px; break-inside:avoid; }
.cul .lbl { font-weight:800; color:#9a3412; }
"""


def build(content: dict) -> str:
    parts = []
    src = content.get('source_url', '')
    parts.append(f"""<div class="cover">
      <div class="left">
        <h1>{esc(content.get('title',''))}</h1>
        <div class="meta">
          <span>🎌 {esc(content.get('channel',''))}</span>
          <span>📚 內容課（topic-based）</span>
          <span>📖 {len(content['chapters'])} 章</span>
          <span>⏱ {content['duration_sec']//60} 分鐘</span>
          <span>📝 {sum(c['n_lines'] for c in content['chapters'])} 句</span>
        </div>
      </div>
      <div class="qr">{qr(src)}<div class="lbl">原片 / 互動版</div></div>
    </div>""")
    parts.append('<div class="howto"><b>講義用法</b>：每章先讀詞彙＋句型→讀原文（QR 進互動版可邊聽邊跟）'
                 '→看文化筆記補背景。本講義對應 N4→N3 程度的旅遊／文化主題日文。</div>')
    if content.get('intro_zh'):
        parts.append(f'<div class="intro">{esc(content["intro_zh"])}</div>')

    for ch in content['chapters']:
        rank = '開場' if ch['n'] == 0 else '結尾' if ch['n'] < 0 else f"#{ch['n']}"
        rank_cls = ' open' if ch['n'] <= 0 else ''
        parts.append('<div class="ch">')
        parts.append(f"""<div class="ch-bar"><div class="rank{rank_cls}">{rank}</div>
          <div class="ja">{esc(ch['title_ja'])}</div>
          <div class="zh">{esc(ch['title_zh'])} · {esc(ch['start_t'])}–{esc(ch['end_t'])}</div></div>""")
        if ch.get('highlight'):
            parts.append(f'<div class="hl">{esc(ch["highlight"])}</div>')
        parts.append(f'<div class="ctx">{esc(ch["context_zh"])}</div>')

        # vocab + patterns side by side
        vrows = ''.join(
            f'<tr><td class="ja">{esc(v["ja"])}'
            + (f'<span class="kana">{esc(v["kana"])}</span>' if v.get('kana') else '')
            + f'</td><td class="zh">{esc(v["zh"])}</td></tr>'
            for v in ch['vocab'])
        pats = ''.join(
            f'<div class="pat"><span class="pja">{esc(p["ja"])}</span> — {esc(p["zh"])}'
            + (f'<span class="pnote">{esc(p["note"])}</span>' if p.get('note') else '')
            + '</div>'
            for p in ch['patterns'])
        parts.append(f"""<div class="prev">
          <div class="col"><h3>📚 重點詞彙</h3><table class="vocab">{vrows}</table></div>
          <div class="col"><h3>🔑 必背句型</h3>{pats}</div>
        </div>""")

        if ch['dialogue']:
            parts.append('<div class="dlg-h">📺 旁白原文</div>')
            for ln in ch['dialogue']:
                parts.append(
                    f'<div class="line"><div class="ts">{esc(ln["t"])}</div>'
                    f'<div class="lb"><div class="lja">{esc(ln["ja"])}</div>'
                    f'<div class="lzh">{esc(ln["zh"])}</div></div></div>')

        if ch.get('culture'):
            parts.append(f'<div class="cul"><span class="lbl">🏛 文化筆記：</span>'
                          f'{esc(ch["culture"])}</div>')
        parts.append('</div>')  # .ch

    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<title>{esc(content.get("title",""))}</title>'
            f'<style>{CSS}</style></head><body>{"".join(parts)}</body></html>')


def render_pdf(html: str, pdf: Path) -> bool:
    pdf.parent.mkdir(parents=True, exist_ok=True)
    if pdf.exists(): pdf.unlink()
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html); html_path = f.name
    proc = subprocess.Popen([
        CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
        '--no-margins', '--virtual-time-budget=15000',
        f'--print-to-pdf={pdf}', f'file://{html_path}',
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        t0 = time.time(); last = -1; stable = 0.0
        while time.time() - t0 < 120:
            if proc.poll() is not None: break
            time.sleep(0.4)
            sz = pdf.stat().st_size if pdf.exists() else 0
            if sz != last: last = sz; stable = 0
            elif sz > 1000:
                stable += 0.4
                if stable >= 2.0: break
    finally:
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired: proc.kill()
        os.unlink(html_path)
    return pdf.exists() and pdf.stat().st_size > 1000


def main():
    content = json.loads((HERE / 'content.json').read_text(encoding='utf-8'))
    out = HERE / 'handout.pdf'
    ok = render_pdf(build(content), out)
    print(f"  {'✓' if ok else '✗'} {out.name} ({out.stat().st_size//1024} KB)" if ok
          else f"  ✗ {out.name}")


if __name__ == '__main__':
    main()
