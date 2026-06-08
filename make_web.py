#!/usr/bin/env python3
"""Generate the interactive exam-handout web app from exam.json.

v2 — adds the 5 "monetisable" Tier-1 features on top of the v1 study page:
  1. 答題＋記分    — click an option, see live score in status bar
  2. 錯題池        — wrong answers go to a dedicated review tab
  3. SRS 排程      — Anki-lite intervals (1/3/7/14 days, ease=2.5)
  4. 考場模式      — 25-sec timer/question, no replay, final result page
  5. 成績歷史曲線  — SVG line chart of last 10 完整 attempts

All state is localStorage (keyed by video_id), no backend. Audio + click-
to-seek + speed control from v1 retained.
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
    t = (t or '').strip().lstrip('~')
    m = re.match(r'^(\d+):(\d{1,2})$', t)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else -1


CSS = r"""
:root { --blue:#1e3a8a; --blue2:#3b82f6; --amber:#f59e0b; --ink:#1f2937;
  --green:#16a34a; --red:#dc2626; --cyan:#0891b2; }
* { box-sizing: border-box; }
body { margin:0; padding:0 0 96px; font:15px/1.65 -apple-system,"PingFang TC","Hiragino Sans",sans-serif;
  color:var(--ink); background:#f1f5f9; }
.wrap { max-width:760px; margin:0 auto; padding:0 14px; }
header { background:var(--blue); color:#fff; padding:14px 14px 0; position:sticky; top:0; z-index:30;
  box-shadow:0 1px 8px rgba(0,0,0,.12); }
header .wrap { padding:0 14px; }
header h1 { margin:0 0 4px; font-size:17px; line-height:1.32; }
header .meta { font-size:11.5px; color:#bfdbfe; }
.tabs { display:flex; gap:2px; margin-top:10px; overflow-x:auto; }
.tabs button { background:transparent; color:#cbd5e1; border:none; padding:9px 12px;
  font-size:13px; font-weight:700; cursor:pointer; border-bottom:3px solid transparent;
  white-space:nowrap; }
.tabs button.on { color:#fff; border-bottom-color:var(--amber); }
.tabs button .bg { background:var(--red); color:#fff; border-radius:9px; padding:1px 6px;
  font-size:10px; margin-left:4px; font-weight:800; }
.status { background:#0f172a; color:#cbd5e1; padding:7px 14px; font-size:12px;
  display:flex; gap:14px; align-items:center; flex-wrap:wrap; }
.status .item { display:inline-flex; gap:5px; align-items:center; }
.status .item b { color:#fff; font-weight:800; font-size:13px; }
.status .item.score b { color:var(--amber); }
.status .reset { margin-left:auto; background:#334155; color:#94a3b8; border:none;
  border-radius:6px; padding:4px 10px; font-size:11px; cursor:pointer; }
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
.vocab { width:100%; border-collapse:collapse; font-size:13px; }
.vocab td { padding:5px 8px; border:1px solid #f0e6d2; }
.vocab td.nl { font-weight:700; width:46%; }
.vocab td.zh { color:#6b7280; }
.vocab tr:nth-child(even) td { background:#fffdf7; }
.pat { font-size:13px; margin:5px 0; padding-bottom:5px; border-bottom:1px dotted #e5e7eb; }
.pat .pnl { font-weight:700; color:#0f766e; }
.pat .pnote { color:#9ca3af; font-size:11.5px; display:block; }
.dlg-h { font-size:13.5px; font-weight:800; color:var(--blue); margin:14px 15px 4px; }
.dlg-h span { font-size:11px; color:#9ca3af; font-weight:500; }
.line { display:flex; gap:9px; padding:7px 15px; border-bottom:1px solid #f3f4f6;
  cursor:pointer; transition:background .15s, border-color .15s; position:relative;
  border-left:3px solid transparent; scroll-margin-top:80px; scroll-margin-bottom:140px; }
.line:hover { background:#f8fafc; }
.line.playing { background:#fef3c7; border-left-color:#f59e0b;
  box-shadow:inset 0 0 0 1px rgba(245,158,11,0.25); }
.line.playing::before { content:"▶"; position:absolute; left:-2px; top:50%;
  transform:translateY(-50%); color:#f59e0b; font-size:9px;
  width:14px; text-align:center; pointer-events:none; }
.line.playing .lnl { color:#78350f; font-weight:700; }
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
.q-h .qbadge { font-size:9.5px; padding:1px 7px; border-radius:9px; font-weight:800;
  white-space:nowrap; }
.q-h .qbadge.ok { background:var(--green); color:#fff; }
.q-h .qbadge.ng { background:var(--red); color:#fff; }
.q-h .qbadge.srs { background:var(--cyan); color:#fff; }
.q-body { padding:10px 12px; }
.q-zh { font-size:12.5px; color:#6b7280; margin-bottom:8px; }
.opt { padding:7px 9px; margin:4px 0; border:1px solid #e5e7eb; border-radius:7px;
  font-size:13.5px; cursor:pointer; transition:all .12s; }
.opt:hover { background:#f8fafc; }
.opt .ol { font-weight:800; color:#6b7280; margin-right:5px; }
.opt .ozh { color:#9ca3af; font-size:12px; }
.opt.picked { border-color:var(--blue2); background:#eff6ff; }
.q.revealed .opt { cursor:default; }
.q.revealed .opt:hover { background:transparent; }
.q.revealed .opt.correct { border-color:var(--green); background:#dcfce7; }
.q.revealed .opt.correct .ol { color:#15803d; }
.q.revealed .opt.wrongpick { border-color:var(--red); background:#fef2f2; }
.q.revealed .opt.wrongpick .ol { color:#b91c1c; }
.reveal-btn { width:100%; padding:9px; margin-top:6px; border:none; border-radius:8px;
  background:var(--blue); color:#fff; font-size:13.5px; font-weight:700; cursor:pointer; }
.reveal-btn:disabled { background:#cbd5e1; cursor:not-allowed; }
.reveal-btn.danger { background:var(--red); }
.answer { display:none; margin-top:10px; }
.q.revealed .answer { display:block; }
.q.revealed .reveal-btn { display:none; }
.src { background:#f0f9ff; border:1px solid #bae6fd; border-radius:8px; padding:8px 10px; }
.src .sh { font-size:11px; font-weight:800; color:#0369a1; margin-bottom:5px; }
.src .sl { display:flex; gap:8px; padding:3px 0; cursor:pointer; }
.src .sl:hover { background:#e0f2fe; border-radius:5px; }
.src .sl .slnl { font-weight:600; color:#0c4a6e; font-size:13px; }
.src .sl .slzh { color:#64748b; font-size:11.5px; }
.explain { font-size:13px; margin-top:9px; }
.explain .lbl { font-weight:800; color:#1d4ed8; }
.trap { font-size:12.5px; background:#fff7ed; border-left:3px solid #fb923c;
  padding:7px 10px; margin-top:7px; border-radius:5px; color:#7c2d12; }
.trap .lbl { font-weight:800; color:#c2410c; }
.note { background:#fef9c3; border-left:3px solid #ca8a04; padding:9px 12px; margin:12px 15px;
  border-radius:6px; font-size:12.5px; color:#713f12; }
/* exam mode */
.exam-intro, .exam-result { padding:24px 18px; background:#fff; border-radius:14px;
  margin:18px 14px; box-shadow:0 1px 3px rgba(0,0,0,.07); }
.exam-intro h2, .exam-result h2 { color:var(--blue); margin:0 0 12px; font-size:18px; }
.exam-intro ul { padding-left:20px; color:#4b5563; font-size:13px; line-height:1.9; }
.exam-intro .start { margin-top:14px; width:100%; padding:14px; border:none;
  border-radius:10px; background:var(--blue); color:#fff; font-size:15px; font-weight:800;
  cursor:pointer; }
.exam-active .timer { background:var(--ink); color:#fff; padding:10px 14px;
  text-align:center; font:700 22px ui-monospace,Menlo,monospace; }
.exam-active .timer.warn { background:var(--red); }
.exam-active .progress { background:#e5e7eb; height:4px; }
.exam-active .progress > div { background:var(--amber); height:100%; transition:width .2s; }
.result-score { font-size:42px; font-weight:900; text-align:center; color:var(--amber); }
.result-score small { display:block; font-size:14px; color:#94a3b8; font-weight:500;
  margin-top:4px; }
.result-row { display:flex; gap:12px; align-items:center; margin:8px 0;
  padding:8px 10px; background:#f8fafc; border-radius:7px; font-size:13px; }
.result-row .qn { font-weight:800; color:var(--blue); min-width:40px; }
.result-row .qt { flex:1; }
.result-row .qok { color:var(--green); font-weight:800; }
.result-row .qng { color:var(--red); font-weight:800; }
/* mistakes / stats */
.empty { text-align:center; padding:40px 20px; color:#9ca3af; font-size:14px; }
.empty .em { font-size:32px; display:block; margin-bottom:8px; }
.stat-card { background:#fff; padding:16px; border-radius:12px; margin:14px;
  box-shadow:0 1px 3px rgba(0,0,0,.06); }
.stat-card h3 { margin:0 0 10px; font-size:14px; color:var(--blue); }
.chart { width:100%; height:140px; }
.stat-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.stat-grid .cell { text-align:center; padding:10px; background:#f8fafc; border-radius:8px; }
.stat-grid .cell b { display:block; font-size:24px; color:var(--blue); font-weight:800; }
.stat-grid .cell span { font-size:11px; color:#6b7280; }
.srs-row { display:flex; gap:10px; align-items:center; padding:9px 12px; background:#fff;
  border-radius:8px; margin:6px 14px; font-size:13px; cursor:pointer; }
.srs-row:hover { background:#fef3c7; }
.srs-row .due { font-size:11px; color:var(--cyan); font-weight:800; }
.srs-row .due.overdue { color:var(--red); }
.srs-row .qt { flex:1; }
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
.player .tnow { font:700 12px ui-monospace,Menlo,monospace; min-width:78px; text-align:right; }
.player .spd { display:flex; gap:3px; }
.player .spd button { background:#334155; color:#cbd5e1; border:none; border-radius:5px;
  font-size:11px; padding:4px 6px; cursor:pointer; }
.player .spd button.on { background:var(--amber); color:#0f172a; font-weight:700; }
[hidden] { display:none !important; }
"""


JS = r"""
const VID = document.body.dataset.vid;
const KEY = 'examapp:' + VID;
const TOTAL_Q = +document.body.dataset.total;
const EXAM_SEC = 25;  // seconds per question in exam mode

const today = () => new Date().toISOString().slice(0,10);
const addDays = (d, n) => {
  const dt = new Date(d + 'T00:00:00Z'); dt.setUTCDate(dt.getUTCDate() + n);
  return dt.toISOString().slice(0,10);
};
const cmp = (a, b) => a < b ? -1 : a > b ? 1 : 0;

// ── State ──
function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) || {}; }
  catch (e) { return {}; }
}
function save(st) { localStorage.setItem(KEY, JSON.stringify(st)); }
function S() {
  const s = load();
  s.q = s.q || {};           // q[id] = {last_pick, last_correct, attempts: [{date, pick, correct}], srs: {due, interval, reps}}
  s.attempts = s.attempts || []; // mock attempts [{id, started, mode, completed_at, answers, score, total}]
  return s;
}

// ── SRS (Anki-lite) ──
function scheduleSRS(qstate, correct) {
  qstate.srs = qstate.srs || {due: today(), interval: 0, reps: 0};
  if (!correct) {
    qstate.srs.interval = 1; qstate.srs.reps = 0;
    qstate.srs.due = addDays(today(), 1);
  } else {
    qstate.srs.reps += 1;
    const intervals = [1, 3, 7, 14, 30];
    qstate.srs.interval = intervals[Math.min(qstate.srs.reps, intervals.length - 1)];
    qstate.srs.due = addDays(today(), qstate.srs.interval);
    if (qstate.srs.reps >= 4) qstate.srs.graduated = true;
  }
}

// ── Record answer ──
function recordAnswer(qid, pick, correct) {
  const st = S();
  const q = st.q[qid] = st.q[qid] || {attempts: []};
  q.last_pick = pick; q.last_correct = correct;
  q.attempts.push({date: today(), pick, correct});
  scheduleSRS(q, correct);
  save(st);
  updateStatus();
  updateBadges();
}

// ── Status bar ──
function updateStatus() {
  const st = S();
  let answered = 0, correct = 0;
  Object.values(st.q).forEach(q => {
    if (q.attempts && q.attempts.length) {
      answered++;
      if (q.last_correct) correct++;
    }
  });
  document.getElementById('s-answered').textContent = answered;
  document.getElementById('s-total').textContent = TOTAL_Q;
  document.getElementById('s-correct').textContent = correct;
  const pct = answered ? Math.round(correct / answered * 100) : 0;
  document.getElementById('s-pct').textContent = pct + '%';
  // Review queue: due today/overdue + all currently-wrong (most recent attempt)
  const due = Object.entries(st.q).filter(([k,q]) =>
    (q.srs && !q.srs.graduated && q.srs.due <= today()) ||
    q.last_correct === false).length;
  const tab = document.getElementById('tab-review');
  const badge = tab.querySelector('.bg');
  if (due > 0) {
    if (!badge) { const b = document.createElement('span'); b.className = 'bg';
      b.textContent = due; tab.appendChild(b); }
    else badge.textContent = due;
  } else if (badge) badge.remove();
}

// ── Per-question result badges ──
function updateBadges() {
  const st = S();
  document.querySelectorAll('.q').forEach(q => {
    const id = q.dataset.qid;
    const qs = st.q[id]; if (!qs) return;
    let bdg = q.querySelector('.qbadge');
    if (!bdg) {
      bdg = document.createElement('span'); bdg.className = 'qbadge';
      q.querySelector('.q-h').insertBefore(bdg, q.querySelector('.qt').nextSibling);
    }
    if (qs.srs && !qs.srs.graduated && qs.srs.due <= today()) {
      bdg.className = 'qbadge srs'; bdg.textContent = '待複習';
    } else if (qs.last_correct) { bdg.className = 'qbadge ok'; bdg.textContent = '✓ 已答對'; }
    else if (qs.last_correct === false) { bdg.className = 'qbadge ng'; bdg.textContent = '✗ 上次錯'; }
  });
}

// ── Audio (same as v1) ──
const A = document.getElementById('aud');
const pp = document.getElementById('pp'), fill = document.getElementById('fill');
const tnow = document.getElementById('tnow'), bar = document.getElementById('bar');
const fmt = s => (isNaN(s)?'0:00':Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0'));
function play(sec){ if(sec>=0){ A.currentTime=sec; } A.play(); }
function bindTS() {
  document.querySelectorAll('[data-t]:not(.bound)').forEach(el => {
    el.classList.add('bound');
    el.addEventListener('click', e => { e.stopPropagation(); play(parseFloat(el.dataset.t)); });
  });
}
pp.onclick = ()=> A.paused ? A.play() : A.pause();
A.onplay = ()=> pp.textContent='⏸';
A.onpause= ()=> pp.textContent='▶';

// ── Karaoke auto-scroll: keep current line visible during playback ──
// Pause auto-scroll for 4s after user manually scrolls (so they can browse freely).
let _userScrolledAt = 0;
let _autoScrollAt = 0;
window.addEventListener('scroll', () => {
  // Distinguish auto-scroll (we just triggered it) vs user-scroll
  if (Date.now() - _autoScrollAt < 250) return;
  _userScrolledAt = Date.now();
}, { passive: true });
let _lastCur = null;
A.ontimeupdate = ()=>{
  fill.style.width = (A.currentTime/A.duration*100||0)+'%';
  tnow.textContent = fmt(A.currentTime)+' / '+fmt(A.duration);
  let cur=null;
  document.querySelectorAll('.line[data-t]').forEach(l=>{
    if(parseFloat(l.dataset.t)<=A.currentTime) cur=l;
  });
  document.querySelectorAll('.line.playing').forEach(l=>{ if(l!==cur) l.classList.remove('playing'); });
  if(cur && !cur.classList.contains('playing')) cur.classList.add('playing');
  // Auto-scroll only when the current line CHANGES, audio is playing,
  // and user hasn't manually scrolled in the last 4s
  if (cur && cur !== _lastCur && !A.paused && Date.now() - _userScrolledAt > 4000) {
    const rect = cur.getBoundingClientRect();
    const vh = window.innerHeight;
    // Only scroll if the line isn't comfortably in the middle band (25-65% of viewport)
    if (rect.top < vh * 0.2 || rect.bottom > vh * 0.7) {
      _autoScrollAt = Date.now();
      cur.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
  _lastCur = cur;
};
bar.onclick = e=>{ const r=bar.getBoundingClientRect();
  A.currentTime=(e.clientX-r.left)/r.width*A.duration; };
function applySpeed(v) {
  A.playbackRate = v;
  try { localStorage.setItem('lph_playback_speed', String(v)); } catch(e) {}
  document.querySelectorAll('.spd button').forEach(b =>
    b.classList.toggle('on', parseFloat(b.dataset.s) === v));
}
document.querySelectorAll('.spd button').forEach(b=>{
  b.onclick=()=> applySpeed(parseFloat(b.dataset.s));
});
// Restore last chosen speed (shared with echo page via same key)
(function() {
  const v = parseFloat(localStorage.getItem('lph_playback_speed') || '1');
  if (v && v !== 1.0) applySpeed(v);
})();

// ── Question interactions (study mode) ──
function bindQuestions(root) {
  (root || document).querySelectorAll('.q').forEach(q => {
    const ans = parseInt(q.dataset.ans);
    const qid = q.dataset.qid;
    q.querySelectorAll('.opt').forEach((o,i)=>{
      o.onclick=()=>{
        if (q.classList.contains('revealed')) return;
        q.querySelectorAll('.opt').forEach(x=>x.classList.remove('picked'));
        o.classList.add('picked'); q.dataset.pick=i;
      };
    });
    const rb=q.querySelector('.reveal-btn');
    if (rb) rb.onclick=()=>{
      const pick = q.dataset.pick === undefined ? -1 : parseInt(q.dataset.pick);
      if (pick < 0) { alert('請先選一個答案'); return; }
      q.classList.add('revealed');
      q.querySelectorAll('.opt').forEach((o,i)=>{
        if(i===ans) o.classList.add('correct');
        else if(i===pick) o.classList.add('wrongpick');
      });
      recordAnswer(qid, pick, pick === ans);
    };
  });
}

// ── Tab switching ──
document.querySelectorAll('.tabs button').forEach(b => {
  b.onclick = () => {
    document.querySelectorAll('.tabs button').forEach(x => x.classList.remove('on'));
    b.classList.add('on');
    const m = b.dataset.mode;
    document.querySelectorAll('[data-mode-content]').forEach(s =>
      s.hidden = s.dataset.modeContent !== m);
    if (m === 'review') renderReview();
    if (m === 'stats') renderStats();
    if (m === 'exam') resetExam();
    window.scrollTo({top: 0, behavior: 'smooth'});
  };
});

// ── Review mode (SRS) ──
function renderReview() {
  const st = S();
  const root = document.getElementById('review-list'); root.innerHTML = '';
  const due = Object.entries(st.q)
    .filter(([k,q]) =>
      (q.srs && !q.srs.graduated && q.srs.due <= today()) ||
      q.last_correct === false)
    .sort((a,b) => {
      // overdue first, then due today, then upcoming-wrong
      const ad = a[1].srs ? a[1].srs.due : '9999';
      const bd = b[1].srs ? b[1].srs.due : '9999';
      return cmp(ad, bd);
    });
  if (!due.length) {
    root.innerHTML = '<div class="empty"><span class="em">✨</span>沒有待複習的題目！'
      + '<br><span style="font-size:12px">答錯的題目會自動進這裡，'
      + 'SRS 會在 1/3/7/14/30 天安排複習</span></div>';
    return;
  }
  due.forEach(([qid, qs]) => {
    const src = document.querySelector(`.q[data-qid="${qid}"]`);
    if (!src) return;
    const clone = src.cloneNode(true);
    clone.classList.remove('revealed');
    clone.querySelectorAll('.opt').forEach(o =>
      o.classList.remove('picked','correct','wrongpick'));
    delete clone.dataset.pick;
    const dueDate = qs.srs ? qs.srs.due : today();
    const overdue = dueDate < today();
    const dueToday = dueDate === today();
    const head = document.createElement('div');
    const color = overdue ? '#dc2626' : dueToday ? '#0891b2' : '#94a3b8';
    head.style.cssText = `font-size:11px;color:${color};font-weight:800;margin:14px 15px 4px;letter-spacing:.4px`;
    head.textContent = overdue ?
      `⚠️ 過期 ${Math.floor((Date.now() - new Date(dueDate).getTime())/86400000)} 天` :
      dueToday ? `📅 今天到期` : `🔁 上次答錯（${dueDate} 該複習）`;
    root.appendChild(head);
    root.appendChild(clone);
  });
  bindQuestions(root);
  bindTS();
  updateBadges();
}

// ── Stats mode (history + per-question) ──
function renderStats() {
  const st = S();
  const root = document.getElementById('stats-body'); root.innerHTML = '';
  // top stats
  let answered = 0, correct = 0, totalAttempts = 0;
  Object.values(st.q).forEach(q => {
    if (q.attempts) {
      answered++; totalAttempts += q.attempts.length;
      if (q.last_correct) correct++;
    }
  });
  const pct = answered ? Math.round(correct/answered*100) : 0;
  root.innerHTML += `<div class="stat-card"><h3>📊 整體</h3>
    <div class="stat-grid">
      <div class="cell"><b>${answered}/${TOTAL_Q}</b><span>已答題數</span></div>
      <div class="cell"><b>${pct}%</b><span>當前正確率</span></div>
      <div class="cell"><b>${totalAttempts}</b><span>累計嘗試</span></div>
    </div></div>`;
  // history chart
  const mocks = (st.attempts || []).slice(-10);
  if (mocks.length) {
    const W = 320, H = 100, P = 14;
    const xs = mocks.map((_,i) => P + i*((W-2*P)/Math.max(1,mocks.length-1)));
    const ys = mocks.map(m => H-P - (m.score/m.total)*(H-2*P));
    const pts = xs.map((x,i)=>`${x.toFixed(1)},${ys[i].toFixed(1)}`).join(' ');
    const dots = xs.map((x,i) =>
      `<circle cx="${x.toFixed(1)}" cy="${ys[i].toFixed(1)}" r="4" fill="#1e3a8a"/>`
      + `<text x="${x.toFixed(1)}" y="${(ys[i]-8).toFixed(1)}" font-size="9" `
      + `text-anchor="middle" fill="#1e3a8a">${mocks[i].score}/${mocks[i].total}</text>`
    ).join('');
    root.innerHTML += `<div class="stat-card"><h3>📈 模考歷史（最近 ${mocks.length} 次）</h3>
      <svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
        <line x1="${P}" y1="${H-P}" x2="${W-P}" y2="${H-P}" stroke="#cbd5e1"/>
        <polyline points="${pts}" fill="none" stroke="#f59e0b" stroke-width="2"/>
        ${dots}
      </svg></div>`;
  } else {
    root.innerHTML += `<div class="stat-card"><h3>📈 模考歷史</h3>
      <div style="color:#9ca3af;font-size:12.5px">完成一次「考場模式」後，這裡會出現分數曲線</div></div>`;
  }
  // per-q
  const rows = Array.from(document.querySelectorAll('.q')).map(q => {
    const qid = q.dataset.qid;
    const qs = st.q[qid];
    const att = qs && qs.attempts ? qs.attempts.length : 0;
    const ok = qs && qs.attempts ? qs.attempts.filter(a=>a.correct).length : 0;
    const pct = att ? Math.round(ok/att*100) : -1;
    return {qid, title: q.querySelector('.qt').textContent, att, ok, pct,
            last: qs && qs.last_correct};
  });
  const tried = rows.filter(r => r.att > 0);
  if (tried.length) {
    root.innerHTML += '<div class="stat-card"><h3>📝 逐題表現</h3>' +
      tried.map(r => `<div class="result-row">
        <span class="qn">Q${r.qid}</span>
        <span class="qt">${r.title.length>30?r.title.slice(0,30)+'…':r.title}</span>
        <span class="${r.last?'qok':'qng'}">${r.att}次 · ${r.pct}%</span>
      </div>`).join('') + '</div>';
  }
}

// ── Exam mode ──
let examState = null;
function resetExam() {
  document.getElementById('exam-intro').hidden = false;
  document.getElementById('exam-active').hidden = true;
  document.getElementById('exam-result').hidden = true;
}
document.getElementById('start-exam').onclick = () => {
  const qs = Array.from(document.querySelectorAll('[data-mode-content="study"] .q')).map(q => ({
    qid: q.dataset.qid, ans: parseInt(q.dataset.ans),
    html: q.outerHTML, title: q.querySelector('.qt').textContent,
  }));
  examState = {qs, idx: 0, answers: {}, started: new Date().toISOString()};
  document.getElementById('exam-intro').hidden = true;
  document.getElementById('exam-active').hidden = false;
  showExamQ();
};
function showExamQ() {
  const root = document.getElementById('exam-active');
  if (examState.idx >= examState.qs.length) return endExam();
  const q = examState.qs[examState.idx];
  root.innerHTML = `
    <div class="timer" id="ex-timer">${EXAM_SEC}</div>
    <div class="progress"><div style="width:${(examState.idx/examState.qs.length*100)}%"></div></div>
    <div style="padding:14px 14px 0;color:#6b7280;font-size:12px">${examState.idx+1} / ${examState.qs.length}</div>
    <div class="ex-qwrap" style="padding:0">${q.html}</div>`;
  const card = root.querySelector('.q');
  card.classList.remove('revealed');
  card.querySelector('.reveal-btn').textContent = '下一題 →';
  card.querySelector('.reveal-btn').classList.add('danger');
  card.querySelector('.reveal-btn').onclick = () => advanceExam();
  card.querySelectorAll('.answer').forEach(a => a.remove());
  card.querySelectorAll('.qbadge').forEach(b => b.remove());
  card.querySelectorAll('.opt').forEach((o,i)=>{
    o.onclick = () => {
      card.querySelectorAll('.opt').forEach(x=>x.classList.remove('picked'));
      o.classList.add('picked'); card.dataset.pick = i;
    };
  });
  // timer
  let left = EXAM_SEC;
  const t = root.querySelector('#ex-timer');
  const iv = setInterval(() => {
    left--; t.textContent = left;
    if (left <= 5) t.classList.add('warn');
    if (left <= 0) { clearInterval(iv); advanceExam(); }
  }, 1000);
  examState.iv = iv;
}
function advanceExam() {
  clearInterval(examState.iv);
  const card = document.querySelector('#exam-active .q');
  const pick = card.dataset.pick === undefined ? -1 : parseInt(card.dataset.pick);
  const q = examState.qs[examState.idx];
  examState.answers[q.qid] = {pick, correct: pick === q.ans};
  examState.idx++;
  showExamQ();
}
function endExam() {
  document.getElementById('exam-active').hidden = true;
  document.getElementById('exam-result').hidden = false;
  const score = Object.values(examState.answers).filter(a => a.correct).length;
  const total = examState.qs.length;
  // save attempt
  const st = S();
  st.attempts.push({id: 'a' + Date.now(), started: examState.started,
    completed_at: new Date().toISOString(), mode: 'exam',
    answers: examState.answers, score, total});
  // also update per-q (counts as a regular attempt)
  Object.entries(examState.answers).forEach(([qid, a]) => {
    const qs = st.q[qid] = st.q[qid] || {attempts: []};
    qs.last_pick = a.pick; qs.last_correct = a.correct;
    qs.attempts.push({date: today(), pick: a.pick, correct: a.correct, mode: 'exam'});
    scheduleSRS(qs, a.correct);
  });
  save(st);
  // render result
  const pct = Math.round(score/total*100);
  const root = document.getElementById('exam-result');
  const rows = examState.qs.map(q => {
    const a = examState.answers[q.qid] || {pick: -1, correct: false};
    const lbl = a.pick < 0 ? '未答' : 'ABCDEFG'[a.pick];
    return `<div class="result-row"><span class="qn">Q${q.qid}</span>
      <span class="qt">${q.title}</span>
      <span class="${a.correct?'qok':'qng'}">${a.correct?'✓':'✗'} ${lbl}</span></div>`;
  }).join('');
  root.innerHTML = `
    <h2>🎯 考場結果</h2>
    <div class="result-score">${score} / ${total}<small>${pct}% · ${pct>=70?'通過':pct>=50?'再加油':'多練幾次'}</small></div>
    <div style="margin:16px 0">${rows}</div>
    <button class="start" onclick="resetExam()">再考一次</button>`;
  updateStatus(); updateBadges();
}

// ── Reset ──
document.getElementById('reset-btn').onclick = () => {
  if (!confirm('清除所有進度（答題紀錄、錯題池、模考歷史）？')) return;
  localStorage.removeItem(KEY);
  location.reload();
};

// ── Init ──
bindQuestions();
bindTS();
updateStatus();
updateBadges();
// restore last_pick/last_correct visual state for already-answered Qs
(function(){
  const st = S();
  Object.entries(st.q).forEach(([qid, qs]) => {
    if (qs.last_pick === undefined) return;
    const q = document.querySelector(`.q[data-qid="${qid}"]`);
    if (!q) return;
    const ans = parseInt(q.dataset.ans);
    q.classList.add('revealed');
    q.querySelectorAll('.opt').forEach((o,i)=>{
      if(i===ans) o.classList.add('correct');
      else if(i===qs.last_pick) o.classList.add('wrongpick');
    });
  });
})();
"""


def build(exam: dict) -> str:
    parts = []
    total_q = exam['n_questions']
    parts.append(f"""<header><div class="wrap">
      <h1>{esc(exam.get('title',''))}</h1>
      <div class="meta">🎧 {esc(exam.get('exam_type',''))} ·
        {len(exam['scenarios'])} 場景 · {total_q} 題</div>
      <div style="margin-top:8px"><a href="index.html"
        style="display:inline-block;padding:6px 12px;background:#0f766e;color:#fff;
               border-radius:6px;font-size:13px;text-decoration:none;font-weight:600">
        🔊 切換到「逐句跟讀／Echo」模式 →</a></div>
    </div>
    <div class="wrap"><div class="tabs">
      <button class="on" data-mode="study">📖 學習</button>
      <button data-mode="exam">⏱️ 考場模式</button>
      <button data-mode="review" id="tab-review">🎯 錯題複習</button>
      <button data-mode="stats">📊 我的紀錄</button>
    </div></div>
    <div class="status">
      <span class="item score">已答 <b id="s-answered">0</b>/<b id="s-total">{total_q}</b></span>
      <span class="item">對 <b id="s-correct">0</b></span>
      <span class="item">正確率 <b id="s-pct">0%</b></span>
      <button class="reset" id="reset-btn">清除進度</button>
    </div></header>""")

    # study mode (main content) ───────────────────────────
    parts.append('<section data-mode-content="study"><div class="wrap">')
    parts.append('<div class="howto"><b>📖 學習模式</b>：① 每題先選答案再按「對答案」'
                 '——答對／答錯都會記下來、自動排進 SRS 複習。② 點任何<b>藍色時間戳</b>'
                 '聽原音。③ 想模擬真考場壓力，切到「⏱️ 考場模式」。'
                 '④ 隔幾天回來，「🎯 錯題複習」會把該複習的題目推給你。</div>')
    if exam.get('intro'):
        parts.append(f'<div class="howto">{esc(exam["intro"])}</div>')
    parts.append('</div>')

    for sc in exam['scenarios']:
        parts.append('<div class="scene">')
        parts.append(f'<div class="scene-bar"><span class="sn">場景 {sc["n"]}</span>'
                      f'<span class="st">{esc(sc["title_zh"])}</span>'
                      f'<span class="sk">{esc(sc["kind"])}</span></div>')
        parts.append(f'<div class="scene-ctx">{esc(sc["context_zh"])}'
                      f'<br><span class="nl">{esc(sc["title_nl"])}</span></div>')
        vrows = ''.join(f'<tr><td class="nl">{esc(v["nl"])}</td>'
                        f'<td class="zh">{esc(v["zh"])}</td></tr>' for v in sc['vocab'])
        pats = ''.join(f'<div class="pat"><span class="pnl">{esc(p["nl"])}</span> — '
                       f'{esc(p["zh"])}<span class="pnote">{esc(p.get("note",""))}</span></div>'
                       for p in sc['patterns'])
        parts.append(f'<div class="sec"><h3>📚 重點單字</h3><table class="vocab">{vrows}</table>'
                      f'<h3 style="margin-top:12px">🔑 必背句型</h3>{pats}</div>')
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
            parts.append(f"""<div class="q" data-qid="{q['n']}" data-ans="{q['answer']}">
              <div class="q-h"><span class="qn">考題 {q['n']}</span>
                <span class="qt">{esc(q['q_nl'])}</span>{recon}</div>
              <div class="q-body">
                <div class="q-zh">{esc(q['q_zh'])}</div>
                {opts}
                <button class="reveal-btn">對答案 ✓</button>
                <div class="answer">
                  <div class="src"><div class="sh">📍 答案出處（點時間聽原音）</div>{slines}</div>
                  <div class="explain"><span class="lbl">💡 反推：</span>{esc(q['explain'])}</div>
                  {trap}
                </div>
              </div></div>""")
        parts.append('</div>')
    parts.append('</section>')

    # exam mode ───────────────────────────
    parts.append(f"""<section data-mode-content="exam" hidden>
      <div class="exam-intro" id="exam-intro">
        <h2>⏱️ 考場模式</h2>
        <ul>
          <li>共 <b>{total_q} 題</b>、每題 <b>{25} 秒</b>、不能回頭</li>
          <li>不顯示答案／出處／反推——做完才公布</li>
          <li>結果會存進「我的紀錄」變成歷史曲線</li>
          <li>題目錯了會自動進「錯題複習」SRS 排程</li>
        </ul>
        <button class="start" id="start-exam">開始考試</button>
      </div>
      <div class="exam-active" id="exam-active" hidden></div>
      <div class="exam-result" id="exam-result" hidden></div>
    </section>""")

    # review mode ───────────────────────────
    parts.append('<section data-mode-content="review" hidden>'
                 '<div id="review-list"></div></section>')

    # stats mode ───────────────────────────
    parts.append('<section data-mode-content="stats" hidden>'
                 '<div id="stats-body"></div></section>')

    # player ───────────────────────────
    parts.append(f"""<div class="player"><div class="row">
      <button class="pp" id="pp">▶</button>
      <div class="bar" id="bar"><div class="fill" id="fill"></div></div>
      <div class="tnow" id="tnow">0:00 / 0:00</div>
      <div class="spd">
        <button data-s="0.6">0.6×</button>
        <button data-s="0.75">0.75×</button>
        <button data-s="0.85">0.85×</button>
        <button data-s="1" class="on">1×</button>
        <button data-s="1.15">1.15×</button>
      </div>
    </div></div>
    <audio id="aud" src="audio.mp3" preload="metadata"></audio>""")

    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(exam.get("title","聽力講義"))}</title>'
            f'<style>{CSS}</style></head>'
            f'<body data-vid="{esc(exam["video_id"])}" data-total="{total_q}">'
            f'{"".join(parts)}<script>{JS}</script></body></html>')


def main():
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    n = 0
    for d in sorted(p for p in OUT.iterdir() if p.is_dir()):
        if only and d.name not in only: continue
        ej = d / 'exam.json'
        if not ej.is_file(): continue
        exam = json.loads(ej.read_text(encoding='utf-8'))
        html = build(exam)
        out = d / 'exam.html'
        out.write_text(html, encoding='utf-8')
        audio = '✓ audio.mp3' if (d / 'audio.mp3').exists() else '✗ NO audio.mp3'
        print(f"  ✓ {out.relative_to(ROOT)}  ({audio}) — {len(html)//1024} KB")
        n += 1
    print(f"\n🎧 {n} interactive exam apps built")


if __name__ == '__main__':
    main()
