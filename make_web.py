#!/usr/bin/env python3
"""Generate an interactive, audio-synced study page from exam.json.

The PDF handout (make_pdfs.py) is static. This builds output/<id>/exam.html:
a single self-contained page with the same 場景制 content PLUS the video's
audio.mp3 wired up — every timestamp (dialogue line, answer-source citation)
is a button that seeks the audio and plays. The currently-playing line
highlights and auto-scrolls. Each question has a 看解答 toggle for self-test.

This is the "click-to-hear-the-source" web version.

Usage:
  python3 make_web.py                # every video with an exam.json
  python3 make_web.py <video_id>...  # specific videos
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / 'output'
LETTERS = 'ABCDEFG'


def esc(t: str) -> str:
    return (t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def secs(t: str) -> float:
    """'1:17' / '~6:35' → seconds. Returns -1 if unparseable."""
    t = (t or '').strip().lstrip('~')
    m = re.match(r'^(\d+):(\d{1,2})$', t)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else -1


CSS = """
:root { --blue:#1e3a8a; --blue2:#3b82f6; --amber:#f59e0b; --ink:#1f2937; }
* { box-sizing: border-box; }
body { margin:0; padding:0 0 96px; font:15px/1.65 -apple-system,"PingFang TC","Hiragino Sans",sans-serif;
  color:var(--ink); background:#f1f5f9; }
.wrap { max-width:760px; margin:0 auto; padding:0 14px; }
header { background:var(--blue); color:#fff; padding:18px 14px; }
header .wrap { padding:0 14px; }
header h1 { margin:0 0 4px; font-size:19px; line-height:1.35; }
header .meta { font-size:12px; color:#bfdbfe; }
.howto { background:#fff; border-left:4px solid var(--blue); border-radius:8px;
  padding:11px 14px; margin:14px 0; font-size:13px; color:#374151; }
.howto b { color:var(--blue); }
/* scenario */
.scene { background:#fff; border-radius:12px; margin:16px 0; overflow:hidden;
  box-shadow:0 1px 3px rgba(0,0,0,.07); }
.scene-bar { background:var(--blue); color:#fff; padding:11px 15px; display:flex;
  align-items:baseline; gap:9px; }
.scene-bar .sn { font-size:12px; font-weight:800; background:#fbbf24; color:var(--blue);
  padding:2px 9px; border-radius:11px; white-space:nowrap; }
.scene-bar .st { font-size:16px; font-weight:800; flex:1; }
.scene-bar .sk { font-size:11px; color:#bfdbfe; }
.scene-ctx { background:#eff6ff; padding:8px 15px; font-size:12.5px; color:#1e40af; }
.scene-ctx .nl { color:#94a3b8; }
.sec { padding:12px 15px; }
.sec h3 { font-size:12.5px; font-weight:800; color:#b45309; margin:4px 0 7px;
  letter-spacing:.4px; }
/* vocab + patterns */
.vocab { width:100%; border-collapse:collapse; font-size:13px; }
.vocab td { padding:5px 8px; border:1px solid #f0e6d2; }
.vocab td.nl { font-weight:700; width:46%; }
.vocab td.zh { color:#6b7280; }
.vocab tr:nth-child(even) td { background:#fffdf7; }
.pat { font-size:13px; margin:5px 0; padding-bottom:5px; border-bottom:1px dotted #e5e7eb; }
.pat .pnl { font-weight:700; color:#0f766e; }
.pat .pnote { color:#9ca3af; font-size:11.5px; display:block; }
/* dialogue */
.dlg-h { font-size:13.5px; font-weight:800; color:var(--blue); margin:14px 15px 4px; }
.dlg-h span { font-size:11px; color:#9ca3af; font-weight:500; }
.line { display:flex; gap:9px; padding:7px 15px; border-bottom:1px solid #f3f4f6;
  cursor:pointer; transition:background .12s; }
.line:hover { background:#f8fafc; }
.line.playing { background:#fef3c7; }
.ts { flex:0 0 50px; font:700 12px ui-monospace,Menlo,monospace; color:#fff;
  background:var(--blue2); border:none; border-radius:6px; padding:2px 0; height:fit-content;
  cursor:pointer; }
.ts:active { transform:scale(.94); }
.line .lb { flex:1; min-width:0; }
.line .lnl { font-weight:500; }
.line .lzh { color:#9ca3af; font-size:12.5px; }
/* question */
.q { margin:12px 15px; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; }
.q-h { background:#fef3c7; padding:9px 12px; display:flex; gap:8px; align-items:baseline;
  border-bottom:1px solid #fde68a; }
.q-h .qn { font-size:11px; font-weight:800; color:#fff; background:var(--amber);
  padding:2px 9px; border-radius:10px; white-space:nowrap; }
.q-h .qt { flex:1; font-size:14px; font-weight:800; color:#92400e; }
.q-h .recon { font-size:9.5px; color:#b45309; border:1px solid #fcd34d; border-radius:8px;
  padding:1px 6px; white-space:nowrap; }
.q-body { padding:10px 12px; }
.q-zh { font-size:12.5px; color:#6b7280; margin-bottom:8px; }
.opt { padding:7px 9px; margin:4px 0; border:1px solid #e5e7eb; border-radius:7px;
  font-size:13.5px; cursor:pointer; }
.opt .ol { font-weight:800; color:#6b7280; margin-right:5px; }
.opt .ozh { color:#9ca3af; font-size:12px; }
.opt.picked { border-color:var(--blue2); background:#eff6ff; }
.q.revealed .opt.correct { border-color:#22c55e; background:#dcfce7; }
.q.revealed .opt.correct .ol { color:#15803d; }
.q.revealed .opt.wrongpick { border-color:#ef4444; background:#fef2f2; }
.reveal-btn { width:100%; padding:9px; margin-top:6px; border:none; border-radius:8px;
  background:var(--blue); color:#fff; font-size:13.5px; font-weight:700; cursor:pointer; }
.answer { display:none; margin-top:10px; }
.q.revealed .answer { display:block; }
.q.revealed .reveal-btn { display:none; }
.src { background:#f0f9ff; border:1px solid #bae6fd; border-radius:8px; padding:8px 10px; }
.src .sh { font-size:11px; font-weight:800; color:#0369a1; margin-bottom:5px; }
.src .sl { display:flex; gap:8px; padding:3px 0; cursor:pointer; }
.src .sl:hover { background:#e0f2fe; border-radius:5px; }
.src .sl.playing { background:#fde68a; border-radius:5px; }
.src .sl .slnl { font-weight:600; color:#0c4a6e; font-size:13px; }
.src .sl .slzh { color:#64748b; font-size:11.5px; }
.explain { font-size:13px; margin-top:9px; }
.explain .lbl { font-weight:800; color:#1d4ed8; }
.trap { font-size:12.5px; background:#fff7ed; border-left:3px solid #fb923c;
  padding:7px 10px; margin-top:7px; border-radius:5px; color:#7c2d12; }
.trap .lbl { font-weight:800; color:#c2410c; }
.note { background:#fef9c3; border-left:3px solid #ca8a04; padding:9px 12px; margin:12px 15px;
  border-radius:6px; font-size:12.5px; color:#713f12; }
/* player */
.player { position:fixed; bottom:0; left:0; right:0; background:#0f172a; color:#fff;
  padding:9px 12px; box-shadow:0 -2px 12px rgba(0,0,0,.25); z-index:50; }
.player .row { max-width:760px; margin:0 auto; display:flex; align-items:center; gap:10px; }
.player button.pp { width:44px; height:44px; border-radius:50%; border:none;
  background:var(--amber); color:#0f172a; font-size:19px; cursor:pointer; flex:0 0 auto; }
.player .bar { flex:1; height:6px; background:#334155; border-radius:3px; cursor:pointer;
  position:relative; }
.player .bar .fill { position:absolute; left:0; top:0; bottom:0; background:var(--amber);
  border-radius:3px; width:0; }
.player .tnow { font:700 12px ui-monospace,Menlo,monospace; min-width:80px; text-align:right; }
.player .spd { display:flex; gap:3px; }
.player .spd button { background:#334155; color:#cbd5e1; border:none; border-radius:5px;
  font-size:11px; padding:4px 6px; cursor:pointer; }
.player .spd button.on { background:var(--amber); color:#0f172a; font-weight:700; }
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
  // highlight current dialogue line
  let cur=null;
  document.querySelectorAll('.line[data-t]').forEach(l=>{
    if(parseFloat(l.dataset.t)<=A.currentTime) cur=l;
  });
  document.querySelectorAll('.line.playing').forEach(l=>{ if(l!==cur) l.classList.remove('playing'); });
  if(cur && !cur.classList.contains('playing')){
    cur.classList.add('playing');
  }
};
bar.onclick = e=>{ const r=bar.getBoundingClientRect();
  A.currentTime=(e.clientX-r.left)/r.width*A.duration; };
document.querySelectorAll('.spd button').forEach(b=>{
  b.onclick=()=>{ A.playbackRate=parseFloat(b.dataset.s);
    document.querySelectorAll('.spd button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on'); };
});
// question interactions
document.querySelectorAll('.q').forEach(q=>{
  const ans=parseInt(q.dataset.ans);
  q.querySelectorAll('.opt').forEach((o,i)=>{
    o.onclick=()=>{
      q.querySelectorAll('.opt').forEach(x=>x.classList.remove('picked'));
      o.classList.add('picked'); q.dataset.pick=i;
    };
  });
  const rb=q.querySelector('.reveal-btn');
  if(rb) rb.onclick=()=>{
    q.classList.add('revealed');
    const pick=q.dataset.pick;
    q.querySelectorAll('.opt').forEach((o,i)=>{
      if(i===ans) o.classList.add('correct');
      else if(pick!==undefined && i===parseInt(pick)) o.classList.add('wrongpick');
    });
  };
});
"""


def build(exam: dict) -> str:
    vid = exam['video_id']
    parts = []
    parts.append(f"""<header><div class="wrap">
      <h1>{esc(exam.get('title',''))}</h1>
      <div class="meta">🎧 {esc(exam.get('exam_type',''))} ·
        {len(exam['scenarios'])} 場景 · {exam['n_questions']} 題 · 點時間戳即播原音</div>
    </div></header>""")
    parts.append('<div class="wrap">')
    parts.append('<div class="howto"><b>怎麼用</b>：① 點任何<b>藍色時間戳</b>，'
                 '音檔就跳到那一秒播放。② 對話會跟著高亮。③ 每題先自己選答案，'
                 '再按「看解答」——解答裡的 <b>📍 出處</b>每一句也能點來聽。'
                 '④ 下方播放器可調 0.7/0.85 倍慢速跟讀。</div>')
    if exam.get('intro'):
        parts.append(f'<div class="howto">{esc(exam["intro"])}</div>')

    for sc in exam['scenarios']:
        parts.append('<div class="scene">')
        parts.append(f'<div class="scene-bar"><span class="sn">場景 {sc["n"]}</span>'
                      f'<span class="st">{esc(sc["title_zh"])}</span>'
                      f'<span class="sk">{esc(sc["kind"])}</span></div>')
        parts.append(f'<div class="scene-ctx">{esc(sc["context_zh"])}'
                      f'<br><span class="nl">{esc(sc["title_nl"])}</span></div>')
        # preview
        vrows = ''.join(f'<tr><td class="nl">{esc(v["nl"])}</td>'
                        f'<td class="zh">{esc(v["zh"])}</td></tr>' for v in sc['vocab'])
        pats = ''.join(f'<div class="pat"><span class="pnl">{esc(p["nl"])}</span> — '
                       f'{esc(p["zh"])}<span class="pnote">{esc(p.get("note",""))}</span></div>'
                       for p in sc['patterns'])
        parts.append(f'<div class="sec"><h3>📚 重點單字</h3><table class="vocab">{vrows}</table>'
                      f'<h3 style="margin-top:12px">🔑 必背句型</h3>{pats}</div>')
        # dialogue
        nq = len(sc['questions'])
        rnote = f'考試中此段重播 {nq} 次，這裡只列一次' if nq > 1 else '考試播放後作答'
        parts.append(f'<div class="dlg-h">📺 {esc(sc["kind"])}原文 <span>— {rnote}</span></div>')
        for ln in sc['dialogue']:
            s = secs(ln['t'])
            parts.append(
                f'<div class="line" data-t="{s}">'
                f'<button class="ts" data-t="{s}">{esc(ln["t"])}</button>'
                f'<div class="lb"><div class="lnl">{esc(ln["nl"])}</div>'
                f'<div class="lzh">{esc(ln["zh"])}</div></div></div>')
        if sc.get('no_questions'):
            parts.append('<div class="note">本場景的考題影片未收錄，僅附對話與單字供額外練習。</div>')
        # questions
        for q in sc['questions']:
            recon = ('<span class="recon">題幹重建</span>'
                     if q.get('reconstructed') else '')
            opts = ''.join(
                f'<div class="opt"><span class="ol">{LETTERS[i]}.</span>'
                f'{esc(o["nl"])} <span class="ozh">{esc(o["zh"])}</span></div>'
                for i, o in enumerate(q['options']))
            slines = ''
            for s in q['source']:
                ss = secs(s['t'])
                slines += (f'<div class="sl" data-t="{ss}"><button class="ts" '
                           f'data-t="{ss}">{esc(s["t"])}</button>'
                           f'<div><div class="slnl">{esc(s["nl"])}</div>'
                           f'<div class="slzh">{esc(s["zh"])}</div></div></div>')
            trap = (f'<div class="trap"><span class="lbl">⚠️ 陷阱：</span>'
                    f'{esc(q["trap"])}</div>' if q.get('trap') else '')
            parts.append(f"""<div class="q" data-ans="{q['answer']}">
              <div class="q-h"><span class="qn">考題 {q['n']}</span>
                <span class="qt">{esc(q['q_nl'])}</span>{recon}</div>
              <div class="q-body">
                <div class="q-zh">{esc(q['q_zh'])}</div>
                {opts}
                <button class="reveal-btn">看解答 ✓</button>
                <div class="answer">
                  <div class="src"><div class="sh">📍 答案出處（點時間聽原音）</div>{slines}</div>
                  <div class="explain"><span class="lbl">💡 反推：</span>{esc(q['explain'])}</div>
                  {trap}
                </div>
              </div></div>""")
        parts.append('</div>')  # .scene
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
    <audio id="aud" src="audio.mp3" preload="metadata"></audio>""")

    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(exam.get("title","聽力講義"))}</title>'
            f'<style>{CSS}</style></head><body>{"".join(parts)}'
            f'<script>{JS}</script></body></html>')


def main():
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    n = 0
    for d in sorted(p for p in OUT.iterdir() if p.is_dir()):
        if only and d.name not in only:
            continue
        ej = d / 'exam.json'
        if not ej.is_file():
            continue
        exam = json.loads(ej.read_text(encoding='utf-8'))
        html = build(exam)
        out = d / 'exam.html'
        out.write_text(html, encoding='utf-8')
        audio = '✓ audio.mp3' if (d / 'audio.mp3').exists() else '✗ NO audio.mp3'
        print(f"  ✓ {out.relative_to(ROOT)}  ({audio})")
        n += 1
    print(f"\n🎧 {n} interactive pages built")


if __name__ == '__main__':
    main()
