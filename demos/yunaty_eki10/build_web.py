#!/usr/bin/env python3
"""Render content.json → exam.html-style interactive page for content course.

Differences from exam: no answer/source/trap — instead culture note per
chapter, vocab table includes kana (furigana column), no "blind" variant.
Audio player + click-any-timestamp-to-play same as exam-handout-builder.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent


def esc(t: str) -> str:
    return (t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


CSS = """
:root { --pink:#e11d48; --crim:#9f1239; --gold:#f59e0b; --ink:#1f2937; --bg:#fdf2f8; }
* { box-sizing: border-box; }
body { margin:0; padding:0 0 96px; font:15px/1.7 -apple-system,"PingFang TC","Hiragino Sans","Noto Sans JP",sans-serif;
  color:var(--ink); background:var(--bg); }
.wrap { max-width:780px; margin:0 auto; padding:0 14px; }
header { background:linear-gradient(135deg,var(--crim),var(--pink)); color:#fff; padding:20px 14px; }
header h1 { margin:0 0 6px; font-size:20px; line-height:1.35; }
header .meta { font-size:12.5px; opacity:.95; }
header .src { font-size:11.5px; opacity:.85; margin-top:4px; }
header a { color:#fef9c3; }
.howto { background:#fff; border-left:4px solid var(--crim); border-radius:8px;
  padding:12px 15px; margin:14px 0; font-size:13.5px; color:#374151; }
.howto b { color:var(--crim); }
.intro { background:#fff7ed; border-left:4px solid var(--gold); border-radius:8px;
  padding:11px 15px; font-size:13px; color:#7c2d12; }
/* chapter */
.ch { background:#fff; border-radius:14px; margin:18px 0; overflow:hidden;
  box-shadow:0 1px 4px rgba(0,0,0,.07); }
.ch-bar { background:#1e293b; color:#fff; padding:13px 16px; display:flex;
  align-items:center; gap:11px; }
.ch-bar .rank { font-size:22px; font-weight:900; color:var(--gold); min-width:52px; text-align:center; }
.ch-bar .rank.open { color:#94a3b8; font-size:13px; }
.ch-bar .ja { font-size:17px; font-weight:800; line-height:1.3; }
.ch-bar .zh { font-size:12.5px; color:#cbd5e1; margin-top:2px; }
.ch-bar .meta { font-size:11px; color:#94a3b8; margin-top:2px; }
.hl { background:#fef3c7; padding:7px 16px; font-size:13px; color:#92400e; font-weight:600;
  border-bottom:1px solid #fde68a; }
.hl::before { content:"✦ "; color:var(--gold); }
.ctx { padding:10px 16px; font-size:13px; color:#475569; background:#f8fafc;
  border-bottom:1px solid #e5e7eb; }
.sec { padding:13px 16px; }
.sec h3 { font-size:12.5px; font-weight:800; color:var(--crim); margin:0 0 8px;
  letter-spacing:.4px; }
/* vocab */
.vocab { width:100%; border-collapse:collapse; font-size:13.5px; }
.vocab td { padding:6px 9px; border-bottom:1px solid #f3f4f6; vertical-align:top; }
.vocab td.ja { font-weight:700; width:38%; color:var(--ink); }
.vocab td.ja .kana { display:block; font-size:10.5px; color:#94a3b8; font-weight:500; margin-top:1px; }
.vocab td.zh { color:#6b7280; }
.vocab tr:hover td { background:#fdf4ff; }
/* patterns */
.pat { font-size:13.5px; margin:6px 0; padding-bottom:7px; border-bottom:1px dotted #e5e7eb; }
.pat .pja { font-weight:700; color:#0f766e; }
.pat .pzh { color:#374151; }
.pat .pnote { color:#9ca3af; font-size:11.5px; display:block; margin-top:1px; }
/* dialogue */
.dlg-h { font-size:13.5px; font-weight:800; color:var(--crim); margin:8px 16px 4px; }
.dlg-h span { font-size:11px; color:#9ca3af; font-weight:500; }
.line { display:flex; gap:9px; padding:7px 16px; border-bottom:1px solid #f9fafb;
  cursor:pointer; transition:background .12s; }
.line:hover { background:#fdf4ff; }
.line.playing { background:#fef3c7; }
.ts { flex:0 0 52px; font:700 12px ui-monospace,Menlo,monospace; color:#fff;
  background:var(--crim); border:none; border-radius:6px; padding:3px 0; height:fit-content;
  cursor:pointer; }
.ts:active { transform:scale(.94); }
.line .lb { flex:1; min-width:0; }
.line .lja { font-weight:500; }
.line .lzh { color:#9ca3af; font-size:12.5px; margin-top:1px; }
/* culture */
.cul { background:#fff7ed; border-left:4px solid var(--gold); padding:10px 14px;
  margin:13px 16px 0; border-radius:6px; font-size:13px; color:#7c2d12; }
.cul .lbl { font-weight:800; color:#9a3412; display:block; margin-bottom:4px; }
/* player */
.player { position:fixed; bottom:0; left:0; right:0; background:#0f172a; color:#fff;
  padding:9px 12px; box-shadow:0 -2px 12px rgba(0,0,0,.25); z-index:50; }
.player .row { max-width:780px; margin:0 auto; display:flex; align-items:center; gap:10px; }
.player button.pp { width:46px; height:46px; border-radius:50%; border:none;
  background:var(--gold); color:#0f172a; font-size:19px; cursor:pointer; flex:0 0 auto; }
.player .bar { flex:1; height:6px; background:#334155; border-radius:3px; cursor:pointer;
  position:relative; }
.player .bar .fill { position:absolute; left:0; top:0; bottom:0; background:var(--gold);
  border-radius:3px; width:0; }
.player .tnow { font:700 12px ui-monospace,Menlo,monospace; min-width:80px; text-align:right; }
.player .spd { display:flex; gap:3px; }
.player .spd button { background:#334155; color:#cbd5e1; border:none; border-radius:5px;
  font-size:11px; padding:4px 6px; cursor:pointer; }
.player .spd button.on { background:var(--gold); color:#0f172a; font-weight:700; }
"""

JS = """
const A = document.getElementById('aud');
const pp = document.getElementById('pp');
const fill = document.getElementById('fill');
const tnow = document.getElementById('tnow');
const bar = document.getElementById('bar');
const fmt = s => (isNaN(s)?'0:00':Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0'));
function play(sec){ if(sec>=0){ A.currentTime=sec; } A.play(); }
document.querySelectorAll('[data-t]').forEach(el=>{
  el.addEventListener('click',e=>{ e.stopPropagation(); play(parseFloat(el.dataset.t)); });
});
pp.onclick = ()=> A.paused ? A.play() : A.pause();
A.onplay = ()=> pp.textContent='⏸';
A.onpause= ()=> pp.textContent='▶';
A.ontimeupdate = ()=>{
  fill.style.width = (A.currentTime/A.duration*100||0)+'%';
  tnow.textContent = fmt(A.currentTime)+' / '+fmt(A.duration);
  let cur=null;
  document.querySelectorAll('.line[data-t]').forEach(l=>{
    if(parseFloat(l.dataset.t)<=A.currentTime) cur=l;
  });
  document.querySelectorAll('.line.playing').forEach(l=>{ if(l!==cur) l.classList.remove('playing'); });
  if(cur && !cur.classList.contains('playing')) cur.classList.add('playing');
};
bar.onclick = e=>{ const r=bar.getBoundingClientRect();
  A.currentTime=(e.clientX-r.left)/r.width*A.duration; };
document.querySelectorAll('.spd button').forEach(b=>{
  b.onclick=()=>{ A.playbackRate=parseFloat(b.dataset.s);
    document.querySelectorAll('.spd button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on'); };
});
"""


def build(content: dict, audio_filename: str) -> str:
    parts = []
    src = content.get('source_url', '')
    parts.append(f"""<header><div class="wrap">
      <h1>{esc(content.get('title',''))}</h1>
      <div class="meta">🎌 {esc(content.get('channel',''))} ·
        {len(content['chapters'])} 章 · {content['duration_sec']//60} 分鐘 · 點時間戳即播原音</div>
      <div class="src">原片：<a href="{esc(src)}" target="_blank">{esc(src)}</a></div>
    </div></header>""")
    parts.append('<div class="wrap">')
    parts.append('<div class="howto"><b>怎麼用</b>：① 點任何<b>紅色時間戳</b>，音檔就跳到那一秒。'
                 '② 對話會自動高亮跟著走。③ 每章前先看詞彙＋句型，再聽原文；'
                 '聽完看「🏛 文化筆記」加深背景。④ 下方播放器可調 0.7/0.85 倍跟讀。</div>')
    if content.get('intro_zh'):
        parts.append(f'<div class="intro">{esc(content["intro_zh"])}</div>')

    for ch in content['chapters']:
        rank = ('開場' if ch['n'] == 0 else
                '結尾' if ch['n'] < 0 else f"#{ch['n']}")
        rank_cls = ' open' if ch['n'] <= 0 else ''
        parts.append(f'<div class="ch">')
        parts.append(f"""<div class="ch-bar">
          <div class="rank{rank_cls}">{rank}</div>
          <div><div class="ja">{esc(ch['title_ja'])}</div>
            <div class="zh">{esc(ch['title_zh'])}</div>
            <div class="meta">{esc(ch['kind'])} · {esc(ch['start_t'])}–{esc(ch['end_t'])} · {ch['n_lines']} 句</div></div>
        </div>""")
        if ch.get('highlight'):
            parts.append(f'<div class="hl">{esc(ch["highlight"])}</div>')
        parts.append(f'<div class="ctx">{esc(ch["context_zh"])}</div>')

        if ch['vocab']:
            vrows = ''.join(
                f'<tr><td class="ja">{esc(v["ja"])}'
                + (f'<span class="kana">{esc(v["kana"])}</span>' if v.get('kana') else '')
                + f'</td><td class="zh">{esc(v["zh"])}'
                + (f' <span style="color:#9ca3af">— {esc(v["tip"])}</span>' if v.get('tip') else '')
                + '</td></tr>'
                for v in ch['vocab'])
            parts.append(f'<div class="sec"><h3>📚 重點詞彙</h3>'
                         f'<table class="vocab">{vrows}</table></div>')
        if ch['patterns']:
            pats = ''.join(
                f'<div class="pat"><span class="pja">{esc(p["ja"])}</span>'
                f' — <span class="pzh">{esc(p["zh"])}</span>'
                + (f'<span class="pnote">{esc(p["note"])}</span>' if p.get('note') else '')
                + '</div>'
                for p in ch['patterns'])
            parts.append(f'<div class="sec"><h3>🔑 必背句型</h3>{pats}</div>')

        if ch['dialogue']:
            parts.append(f'<div class="dlg-h">📺 旁白原文 <span>— 點時間戳跳秒播放</span></div>')
            for ln in ch['dialogue']:
                parts.append(
                    f'<div class="line" data-t="{ln["s"]}">'
                    f'<button class="ts" data-t="{ln["s"]}">{esc(ln["t"])}</button>'
                    f'<div class="lb"><div class="lja">{esc(ln["ja"])}</div>'
                    f'<div class="lzh">{esc(ln["zh"])}</div></div></div>')

        if ch.get('culture'):
            parts.append(f'<div class="cul"><span class="lbl">🏛 文化筆記</span>'
                          f'{esc(ch["culture"])}</div>')
            parts.append('<div style="height:14px"></div>')
        parts.append('</div>')  # .ch
    parts.append('</div>')  # .wrap

    parts.append(f"""<div class="player"><div class="row">
      <button class="pp" id="pp">▶</button>
      <div class="bar" id="bar"><div class="fill" id="fill"></div></div>
      <div class="tnow" id="tnow">0:00 / 0:00</div>
      <div class="spd">
        <button data-s="0.7">0.7×</button>
        <button data-s="0.85">0.85×</button>
        <button data-s="1" class="on">1×</button>
      </div>
    </div></div>
    <audio id="aud" src="{esc(audio_filename)}" preload="metadata"></audio>""")

    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(content.get("title",""))}</title>'
            f'<style>{CSS}</style></head><body>{"".join(parts)}'
            f'<script>{JS}</script></body></html>')


def main():
    content = json.loads((HERE / 'content.json').read_text(encoding='utf-8'))
    html = build(content, 'full.mp3')
    out = HERE / 'index.html'
    out.write_text(html, encoding='utf-8')
    print(f'✓ {out.relative_to(HERE.parent)} ({len(content["chapters"])} chapters)')


if __name__ == '__main__':
    main()
