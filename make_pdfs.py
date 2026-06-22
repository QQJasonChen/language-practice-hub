#!/usr/bin/env python3
"""Generate A2-listening study handouts (講義) as PDF, from exam.json.

v3 — 場景制 (scenario-based):
- Collapses the exam's per-question video replays: each scenario's dialogue
  is listed ONCE, followed by all its questions.
- Each question: ✓ answer + 📍 complete source citation (the question-and-
  answer exchange, with timestamps) + 💡 reasoning + ⚠️ trap note.
- Per-scenario 預習: vocabulary table + sentence patterns.
- Two variants: 講義版 (answers inline) / 純荷文版 (blind practice, full
  answer key at the end).

Reads output/<id>/exam.json (built by make_exam.py). Videos without an
exam.json are skipped.

Usage:
  python3 make_pdfs.py                # every video with an exam.json
  python3 make_pdfs.py <video_id>...  # specific videos
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / 'output'
PDF_DIR = ROOT / 'transcripts'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
LIVE_BASE = 'https://qqjasonchen.github.io/language-practice-hub/output'
LETTERS = 'ABCDEFG'


# ── Helpers ──

def slug(s: str, maxlen: int = 90) -> str:
    s = re.sub(r'[\\/:*?"<>|]', '_', (s or '').strip())
    s = re.sub(r'\s+', ' ', s).replace('#', '').replace('！', '!').replace('？', '?')
    return s[:maxlen].rstrip(' .')

def esc(t: str) -> str:
    return (t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def qr_img(url: str, size: int = 100) -> str:
    enc = urllib.parse.quote(url, safe='')
    return (f'<img src="https://api.qrserver.com/v1/create-qr-code/'
            f'?size={size*2}x{size*2}&data={enc}" alt="QR" />')


# ── CSS ──

CSS = """
  @page { size: A4; margin: 16mm 15mm 18mm; @bottom-center {
    content: counter(page) " / " counter(pages); font: 10px -apple-system,sans-serif; color:#9ca3af; } }
  html, body { margin: 0; padding: 0; }
  body { font: 13.5px/1.6 -apple-system, "Helvetica Neue", "PingFang TC", "Hiragino Sans", sans-serif;
    color: #1f2937; background: #fff; }
  h1 { font-size: 20px; font-weight: 800; margin: 0 0 6px; line-height: 1.34; }
  .page-break { page-break-before: always; }
  /* Cover */
  .cover { display: flex; gap: 14px; align-items: flex-start;
    border-bottom: 2px solid #1e3a8a; padding-bottom: 12px; margin-bottom: 14px; }
  .cover .left { flex: 1; }
  .cover .meta { font-size: 11.5px; color: #6b7280; font-weight: 500; }
  .cover .meta span + span::before { content: " · "; color: #d1d5db; padding: 0 3px; }
  .cover .qr { flex: 0 0 92px; text-align: center; }
  .cover .qr img { width: 92px; height: 92px; }
  .cover .qr .qr-label { font-size: 8.5px; color: #9ca3af; margin-top: 3px; }
  /* Intro / how-to */
  .howto { background: #f8fafc; border: 1px solid #e5e7eb; border-left: 3px solid #1e3a8a;
    border-radius: 5px; padding: 10px 14px; font-size: 12px; color: #374151; margin-bottom: 6px; }
  .howto b { color: #1e3a8a; }
  /* Scenario */
  .scene { page-break-before: always; }
  .scene-bar { background: #1e3a8a; color: #fff; border-radius: 6px 6px 0 0;
    padding: 8px 14px; display: flex; align-items: baseline; gap: 10px; }
  .scene-bar .sn { font-size: 12px; font-weight: 800; letter-spacing: 1px;
    background: #fbbf24; color: #1e3a8a; padding: 1px 8px; border-radius: 10px; }
  .scene-bar .st { font-size: 15.5px; font-weight: 800; flex: 1; }
  .scene-bar .sk { font-size: 10.5px; color: #bfdbfe; font-weight: 600; }
  .scene-ctx { background: #eff6ff; border: 1px solid #dbeafe; border-top: none;
    padding: 7px 14px; font-size: 11.5px; color: #1e40af; }
  /* Preview */
  .prev { display: flex; gap: 14px; margin: 12px 0 6px; break-inside: avoid; }
  .prev .col { flex: 1; min-width: 0; }
  .prev h3 { font-size: 11.5px; font-weight: 800; color: #b45309; margin: 0 0 5px;
    letter-spacing: 0.4px; }
  table.vocab { width: 100%; border-collapse: collapse; font-size: 11.5px; }
  table.vocab td { padding: 3.5px 7px; border: 1px solid #f0e6d2; vertical-align: top; }
  table.vocab td.nl { font-weight: 700; color: #1f2937; width: 46%; }
  table.vocab td.zh { color: #6b7280; }
  table.vocab tr:nth-child(even) td { background: #fffdf7; }
  .pat { font-size: 11.5px; margin: 0 0 7px; padding-bottom: 6px; border-bottom: 1px dotted #e5e7eb; }
  .pat .pnl { font-weight: 700; color: #0f766e; }
  .pat .pzh { color: #374151; }
  .pat .pnote { color: #9ca3af; font-size: 10.5px; }
  /* Dialogue */
  .dlg { margin: 10px 0 4px; }
  .dlg-h { font-size: 13px; font-weight: 800; color: #1e3a8a; margin: 14px 0 4px; }
  .dlg-note { font-size: 10.5px; color: #9ca3af; font-weight: 500; }
  .line { display: flex; gap: 9px; padding: 4px 0; border-bottom: 1px dashed #f0f0f0;
    break-inside: avoid; }
  .line .lt { flex: 0 0 38px; font: 600 10.5px ui-monospace, "SF Mono", Menlo, monospace;
    color: #94a3b8; padding-top: 2px; }
  .line .lb { flex: 1; min-width: 0; }
  .line .lnl { color: #1f2937; }
  .line .lzh { color: #9ca3af; font-size: 11.5px; }
  /* Question card */
  .q { border: 1px solid #e5e7eb; border-radius: 7px; margin: 11px 0; break-inside: avoid;
    overflow: hidden; }
  .q-h { background: #fef3c7; padding: 6px 12px; display: flex; align-items: baseline; gap: 8px;
    border-bottom: 1px solid #fde68a; }
  .q-h .qn { font-size: 11px; font-weight: 800; color: #fff; background: #f59e0b;
    padding: 1px 8px; border-radius: 9px; letter-spacing: 0.5px; }
  .q-h .qt { font-size: 13.5px; font-weight: 800; color: #92400e; flex: 1; }
  .q-h .qts { font: 600 10.5px ui-monospace, Menlo, monospace; color: #b45309; }
  .q-h .recon { font-size: 9px; color: #b45309; background: #fffbeb; border: 1px solid #fcd34d;
    padding: 0 5px; border-radius: 8px; font-weight: 700; }
  .q-body { padding: 9px 12px; }
  .q-zh { font-size: 11.5px; color: #6b7280; margin: 0 0 7px; }
  .opt { padding: 3px 0 3px 4px; font-size: 12.5px; }
  .opt .ol { font-weight: 700; color: #6b7280; }
  .opt.correct { background: #dcfce7; border-radius: 4px; padding-left: 6px;
    margin-left: -2px; }
  .opt.correct .ol { color: #15803d; }
  .opt.correct .ot { font-weight: 700; color: #14532d; }
  .opt .ozh { color: #9ca3af; font-size: 11px; }
  .opt .tick { color: #16a34a; font-weight: 800; }
  /* Source box */
  .src { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 5px;
    padding: 7px 10px; margin: 8px 0 0; }
  .src .sh { font-size: 10.5px; font-weight: 800; color: #0369a1; margin-bottom: 4px;
    letter-spacing: 0.4px; }
  .src .sl { display: flex; gap: 8px; padding: 2px 0; }
  .src .sl .slt { flex: 0 0 34px; font: 700 10px ui-monospace, Menlo, monospace; color: #0284c7;
    padding-top: 1px; }
  .src .sl .slnl { font-weight: 600; color: #0c4a6e; font-size: 11.5px; }
  .src .sl .slzh { color: #64748b; font-size: 10.5px; }
  .explain { font-size: 11.5px; color: #374151; margin: 7px 0 0; padding-left: 4px; }
  .explain .lbl { font-weight: 800; color: #1d4ed8; }
  .trap { font-size: 11px; color: #7c2d12; background: #fff7ed; border-left: 3px solid #fb923c;
    padding: 6px 10px; margin: 6px 0 0; border-radius: 4px; }
  .trap .lbl { font-weight: 800; color: #c2410c; }
  /* Answer key */
  .keytable { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
  .keytable th { background: #1e3a8a; color: #fff; padding: 5px 8px; font-weight: 700; }
  .keytable td { border: 1px solid #e5e7eb; padding: 4px 8px; text-align: center; }
  .keytable td.ans { font-weight: 800; color: #15803d; }
  .keytable td.ql { text-align: left; color: #6b7280; }
  h2.sec { font-size: 16px; font-weight: 800; color: #1e3a8a; margin: 22px 0 8px; }
  .blind { background: #fef9c3; border-left: 3px solid #ca8a04; padding: 8px 12px;
    font-size: 11.5px; color: #713f12; border-radius: 4px; margin: 8px 0; }
"""


# ── Builders ──

def build_cover(exam: dict, nl_only: bool) -> str:
    live = f"{LIVE_BASE}/{exam['video_id']}/index.html"
    mode = '純荷文 · 盲練版' if nl_only else '講義版 · 完整詳解'
    nq = exam['n_questions']
    nsc = len(exam['scenarios'])
    is_orig = str(exam.get('video_id', '')).startswith('orig_')
    dsec = exam.get('duration', 0) or 0
    dlabel = f'{dsec} 秒' if dsec < 60 else f'{dsec // 60} 分鐘'
    qr = '' if is_orig else f'<div class="qr">{qr_img(live, 92)}<div class="qr-label">線上練習</div></div>'
    return f"""
    <div class="cover">
      <div class="left">
        <h1>{esc(exam.get('title','(untitled)'))}</h1>
        <div class="meta">
          <span>📺 {esc(exam.get('channel',''))}</span>
          <span>⏱ {dlabel}</span>
          <span>🎧 {esc(exam.get('exam_type',''))}</span>
          <span>🗂 {nsc} 個場景</span>
          <span>❓ {nq} 題</span>
          <span>📖 {mode}</span>
        </div>
      </div>
      {qr}
    </div>
    """

def build_howto(exam: dict, nl_only: bool) -> str:
    is_orig = str(exam.get('video_id', '')).startswith('orig_')
    listen = '聽音檔的' if is_orig else '聽（線上）'
    qr_tip = '' if is_orig else '左上 QR 可回線上版練習。'
    if nl_only:
        body = ('<b>盲練版用法</b>：先不看任何中文。每個場景先讀單字、再' + listen + '對話原文，'
                '然後作答。全部做完後，翻到最後的「答案與詳解」對答案、看反推說明。')
    else:
        body = ('<b>這份講義怎麼用</b>：① 先讀場景的「考前預習」（單字＋句型）。'
                '② 讀一次對話原文。③ 做考題——每題下方有 <b>📍 答案出處</b>（標出原文'
                '哪幾句）、<b>💡 反推</b>（為什麼選這個）、<b>⚠️ 陷阱</b>（為什麼別的不對）。'
                + qr_tip)
    return (f'<div class="howto">{body}</div>'
            f'<div class="howto">{esc(exam.get("intro",""))}</div>')

def build_preview(sc: dict, nl_only: bool) -> str:
    vrows = []
    for v in sc['vocab']:
        zh = '____________' if nl_only else esc(v['zh'])
        vrows.append(f'<tr><td class="nl">{esc(v["nl"])}</td><td class="zh">{zh}</td></tr>')
    vocab = ('<table class="vocab">' + ''.join(vrows) + '</table>') if vrows else ''
    pats = []
    for p in sc['patterns']:
        zh = '' if nl_only else f'<span class="pzh"> — {esc(p["zh"])}</span>'
        note = '' if nl_only else f'<div class="pnote">{esc(p.get("note",""))}</div>'
        pats.append(f'<div class="pat"><span class="pnl">{esc(p["nl"])}</span>{zh}{note}</div>')
    pat_h = '猜猜中文' if nl_only else '中文'
    return f"""
    <div class="prev">
      <div class="col"><h3>📚 重點單字（{pat_h}）</h3>{vocab}</div>
      <div class="col"><h3>🔑 必背句型</h3>{''.join(pats)}</div>
    </div>"""

def build_dialogue(sc: dict, nl_only: bool) -> str:
    nq = len(sc['questions'])
    replay = (f'考試中此段會重播 {nq} 次（每題一次），這裡只列一次。'
              if nq > 1 else '考試中此段播放後作答。')
    lines = []
    for ln in sc['dialogue']:
        zh = '' if nl_only else f'<div class="lzh">{esc(ln["zh"])}</div>'
        lines.append(f'<div class="line"><div class="lt">{esc(ln["t"])}</div>'
                      f'<div class="lb"><div class="lnl">{esc(ln["nl"])}</div>{zh}</div></div>')
    kind = esc(sc['kind'])
    return (f'<div class="dlg-h">📺 {kind}原文 '
            f'<span class="dlg-note">— {replay}</span></div>'
            f'<div class="dlg">{"".join(lines)}</div>')

def build_question(q: dict, nl_only: bool, reveal: bool) -> str:
    """reveal=True shows answer/source/explain/trap inline."""
    recon = ('<span class="recon">題幹重建</span>' if q.get('reconstructed') else '')
    opts = []
    for i, o in enumerate(q['options']):
        correct = reveal and (i == q['answer'])
        tick = ' <span class="tick">✓</span>' if correct else ''
        zh = '' if nl_only else f' <span class="ozh">{esc(o["zh"])}</span>'
        cls = 'opt correct' if correct else 'opt'
        opts.append(f'<div class="{cls}"><span class="ol">{LETTERS[i]}.</span> '
                     f'<span class="ot">{esc(o["nl"])}</span>{zh}{tick}</div>')
    q_zh = '' if nl_only else f'<div class="q-zh">{esc(q["q_zh"])}</div>'
    extra = ''
    if reveal:
        slines = []
        for s in q['source']:
            zh = '' if nl_only else f'<div class="slzh">{esc(s["zh"])}</div>'
            slines.append(f'<div class="sl"><div class="slt">{esc(s["t"])}</div>'
                           f'<div><div class="slnl">{esc(s["nl"])}</div>{zh}</div></div>')
        src = (f'<div class="src"><div class="sh">📍 答案出處（原文哪幾句）</div>'
               f'{"".join(slines)}</div>')
        explain = (f'<div class="explain"><span class="lbl">💡 反推：</span>'
                   f'{esc(q["explain"])}</div>')
        trap = (f'<div class="trap"><span class="lbl">⚠️ 陷阱：</span>{esc(q["trap"])}</div>'
                if q.get('trap') else '')
        extra = src + explain + trap
    return f"""
    <div class="q">
      <div class="q-h"><span class="qn">考題 {q['n']}</span>
        <span class="qt">{esc(q['q_nl'])}</span>{recon}
        <span class="qts">{esc(q['t'])}</span></div>
      <div class="q-body">{q_zh}{''.join(opts)}{extra}</div>
    </div>"""

def build_scenario(sc: dict, nl_only: bool) -> str:
    head = (f'<div class="scene-bar"><span class="sn">場景 {sc["n"]}</span>'
            f'<span class="st">{esc(sc["title_zh"])}</span>'
            f'<span class="sk">{esc(sc["kind"])} · {esc(sc["start"])}</span></div>'
            f'<div class="scene-ctx">{esc(sc["context_zh"])}'
            f'<br><span style="color:#94a3b8">{esc(sc["title_nl"])}</span></div>')
    prev = build_preview(sc, nl_only)
    dlg = build_dialogue(sc, nl_only)
    if sc.get('no_questions'):
        qs = '<div class="blind">本場景的考題影片未收錄，僅附對話與重點單字供額外聽力練習。</div>'
    else:
        # 講義版: reveal inline. 純荷文版: hide (answers go to key section).
        qs = ''.join(build_question(q, nl_only, reveal=(not nl_only))
                     for q in sc['questions'])
    return f'<section class="scene">{head}{prev}{dlg}{qs}</section>'

def build_answerkey(exam: dict, nl_only: bool) -> str:
    """講義版: compact grid. 純荷文版: full reveal of every question."""
    if nl_only:
        blocks = ['<h2 class="sec">✅ 答案與詳解（做完再翻）</h2>'
                  '<div class="blind">下面是每一題的正解、出處與反推。先自己作答完，'
                  '再逐題對照。</div>']
        for sc in exam['scenarios']:
            if sc.get('no_questions') or not sc['questions']:
                continue
            blocks.append(f'<div class="dlg-h">場景 {sc["n"]}　{esc(sc["title_zh"])}</div>')
            for q in sc['questions']:
                blocks.append(build_question(q, nl_only=False, reveal=True))
        return f'<section class="page-break">{"".join(blocks)}</section>'
    rows = []
    for sc in exam['scenarios']:
        for q in sc['questions']:
            ans = f"{LETTERS[q['answer']]}. {esc(q['options'][q['answer']]['nl'])}"
            rows.append(f'<tr><td>{q["n"]}</td><td class="ql">{esc(q["q_nl"])}</td>'
                         f'<td class="ans">{ans}</td><td>{esc(q["t"])}</td></tr>')
    return (f'<section class="page-break"><h2 class="sec">📋 答案速查表</h2>'
            f'<table class="keytable"><tr><th>題</th><th>題目</th>'
            f'<th>正解</th><th>時間</th></tr>{"".join(rows)}</table></section>')


def build_html(exam: dict, nl_only: bool = False) -> str:
    parts = [build_cover(exam, nl_only), build_howto(exam, nl_only)]
    for sc in exam['scenarios']:
        parts.append(build_scenario(sc, nl_only))
    parts.append(build_answerkey(exam, nl_only))
    body = ''.join(parts)
    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<title>{esc(exam.get("title","講義"))}</title>'
            f'<style>{CSS}</style></head><body>{body}</body></html>')


# ── Chrome PDF (poll-then-kill) ──

def render_pdf(html: str, pdf_path: Path, settle: float = 2.0,
               deadline_s: int = 120, verbose: bool = False) -> bool:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html); html_path = f.name
    proc = subprocess.Popen([
        CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
        '--no-margins', '--virtual-time-budget=15000',
        f'--print-to-pdf={pdf_path}', f'file://{html_path}',
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        t0 = time.time()
        last_size = -1; stable_for = 0.0
        while time.time() - t0 < deadline_s:
            if proc.poll() is not None:
                break
            time.sleep(0.4)
            sz = pdf_path.stat().st_size if pdf_path.exists() else 0
            if sz != last_size:
                last_size = sz; stable_for = 0
            elif sz > 1000:
                stable_for += 0.4
                if stable_for >= settle:
                    break
    finally:
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired: proc.kill()
        os.unlink(html_path)
    return pdf_path.exists() and pdf_path.stat().st_size > 1000


def main():
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    if not Path(CHROME).exists():
        print(f"✗ Chrome not at {CHROME}"); sys.exit(1)
    done = 0; failed = []
    for d in sorted(p for p in OUT.iterdir() if p.is_dir()):
        if only and d.name not in only:
            continue
        ej = d / 'exam.json'
        if not ej.is_file():
            if only:
                print(f"  – {d.name}: no exam.json (run make_exam.py)")
            continue
        exam = json.loads(ej.read_text(encoding='utf-8'))
        ch_slug = slug(exam.get('channel') or '_unknown', 60)
        title_slug = slug(exam.get('title') or d.name, 90)
        for nl_only, suffix in [(False, ''), (True, ' · 純荷文盲練')]:
            pdf = PDF_DIR / ch_slug / f'{title_slug}{suffix}.pdf'
            ok = render_pdf(build_html(exam, nl_only=nl_only), pdf)
            print(f"  {'✓' if ok else '✗'} {pdf.relative_to(ROOT)}")
            if ok: done += 1
            else: failed.append(f"{d.name}{suffix}")
    print(f"\n📄 {done} PDFs produced under {PDF_DIR.relative_to(ROOT)}/")
    if failed:
        print(f"   failed: {failed}")


if __name__ == '__main__':
    main()
