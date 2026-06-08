#!/usr/bin/env python3
"""Render vragen.html (expanded) to PDF using Playwright + local HTTP server.

Output: transcripts/問句速查/A2 luisteren 問句速查.pdf
"""
import http.server, socketserver, threading, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
PORT = 8765
OUT = ROOT / 'transcripts' / '問句速查' / 'A2 luisteren 問句速查.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)

# Print-friendly CSS overrides (light theme + remove interactive UI noise)
PRINT_CSS = """
  @page { size: A4; margin: 14mm 12mm; }
  body { background: #ffffff !important; color: #18181b !important;
         font-size: 11.5px !important; line-height: 1.55 !important; }
  /* Hide interactive elements that don't print well */
  .search, .q-play, .expand-cue, .d-link, .src-line, .q-row { cursor: default !important; }
  .search { display: none !important; }
  .q-play { display: none !important; }
  .expand-cue { display: none !important; }
  .d-link { display: none !important; }
  /* Layout tweaks */
  .wrap { max-width: none !important; padding: 0 !important; }
  header { margin-bottom: 6px !important; }
  header a { display: none !important; }
  h1 { font-size: 22px !important; }
  .lede { font-size: 12.5px !important; color: #52525b !important; margin: 6px 0 14px !important; }
  .lede b { color: #0891b2 !important; }
  /* TOC: cleaner light style */
  .toc { background: #f4f4f5 !important; border: 1px solid #e4e4e7 !important; padding: 8px !important; }
  .toc a { background: #ffffff !important; color: #18181b !important;
           border: 1px solid #d4d4d8 !important; font-size: 11px !important; }
  .toc a .n { color: #71717a !important; }
  /* Group headers */
  .group { margin: 16px 0 12px !important; break-inside: avoid-page; }
  .g-head { background: #fef3c7 !important; border-left: 4px solid #f59e0b !important; }
  .g-head .nl { color: #18181b !important; font-size: 18px !important; }
  .g-head .zh { color: #52525b !important; }
  .g-head .cnt { color: #71717a !important; }
  .g-meta { background: #ffffff !important; border: 1px solid #e4e4e7 !important;
            color: #18181b !important; font-size: 11.5px !important; line-height: 1.6 !important; }
  .g-meta .lbl { color: #d97706 !important; }
  .g-meta .trap { color: #be123c !important; }
  /* Question rows */
  .q { background: #ffffff !important; border: 1px solid #e4e4e7 !important;
       break-inside: avoid; margin-bottom: 5px !important; }
  .q.expanded { background: #ffffff !important; border-color: #d4d4d8 !important; }
  .q-nl { color: #18181b !important; font-size: 12.5px !important; }
  .q-zh { color: #52525b !important; font-size: 11.5px !important; }
  .q-src { color: #71717a !important; }
  .iw { background: #fef08a !important; color: #18181b !important; font-weight: 800 !important; }
  /* Detail panel — always visible in print */
  .q-detail { display: block !important; padding: 0 12px 12px 12px !important;
              border-top: 1px dashed #d4d4d8 !important; }
  .d-h { color: #52525b !important; font-size: 10.5px !important; }
  .d-body { color: #18181b !important; font-size: 12px !important; }
  .d-section.trap .d-body { color: #be123c !important; }
  .opt { background: #fafafa !important; color: #18181b !important;
         border: 1px solid #e4e4e7 !important; }
  .opt.correct { background: #dcfce7 !important; border-color: #86efac !important; }
  .opt-letter { background: #e4e4e7 !important; color: #18181b !important; }
  .opt.correct .opt-letter { background: #16a34a !important; color: #ffffff !important; }
  .opt-nl { color: #18181b !important; }
  .opt-zh { color: #52525b !important; }
  .opt-mark { color: #16a34a !important; }
  .src-line { background: #f4f4f5 !important; border-left: 3px solid #0891b2 !important;
              color: #18181b !important; cursor: default !important; }
  .src-t { color: #0891b2 !important; }
  .src-nl { color: #18181b !important; }
  .src-zh { color: #52525b !important; }
  /* Per-group accent color resets */
  .em-wat .g-head, .em-waarom .g-head, .em-waar .g-head, .em-wanneer .g-head,
  .em-hoelaat .g-head, .em-hoe .g-head, .em-welke .g-head, .em-wie .g-head,
  .em-hoeveel .g-head {
    background: #fef3c7 !important; border-left-color: #f59e0b !important;
  }
  .em-wat .g-meta .lbl, .em-waarom .g-meta .lbl, .em-waar .g-meta .lbl,
  .em-wanneer .g-meta .lbl, .em-hoelaat .g-meta .lbl, .em-hoe .g-meta .lbl,
  .em-welke .g-meta .lbl, .em-wie .g-meta .lbl, .em-hoeveel .g-meta .lbl {
    color: #d97706 !important;
  }
"""

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kw): super().__init__(*args, directory=str(ROOT), **kw)
    def log_message(self, *a, **kw): pass

httpd = socketserver.TCPServer(('127.0.0.1', PORT), Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
time.sleep(0.3)

print(f'▶ rendering vragen.html → {OUT.name}')
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f'http://127.0.0.1:{PORT}/vragen.html', wait_until='networkidle')
    page.wait_for_selector('.q', timeout=20000)
    # Expand every question row
    expanded = page.evaluate("""
      (() => {
        const els = document.querySelectorAll('.q.has-detail');
        els.forEach(el => el.classList.add('expanded'));
        return els.length;
      })()
    """)
    print(f'  expanded {expanded} questions')
    page.add_style_tag(content=PRINT_CSS)
    # Give animations a moment to settle
    page.wait_for_timeout(300)
    page.pdf(path=str(OUT), format='A4', print_background=True,
             margin={'top':'14mm','bottom':'14mm','left':'12mm','right':'12mm'},
             display_header_footer=True,
             header_template='<div style="font-size:9px;color:#71717a;padding:0 12mm;width:100%;text-align:right">A2 luisteren · 問句速查</div>',
             footer_template='<div style="font-size:9px;color:#71717a;padding:0 12mm;width:100%;text-align:center"><span class="pageNumber"></span> / <span class="totalPages"></span></div>')
    browser.close()

httpd.shutdown()
size_kb = OUT.stat().st_size // 1024
print(f'✓ {OUT.relative_to(ROOT)}  ({size_kb} KB)')
