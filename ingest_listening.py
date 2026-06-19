#!/usr/bin/env python3
"""Batch-ingest every listening video from @Inburgeren.examen.A2 into the app as a
QUIZ-LESS transcript study page (full listening tools + 💡 AI 詳解).

Per video, resumable:
  generate.py (audio+transcript) → make_exam_auto.py (exam.json, no quiz)
  → make_web.py (exam.html) → analyze_sentences.py (analysis.json)

Run:  python3 ingest_listening.py            # all
      python3 ingest_listening.py <id> ...   # subset
Then patch index.html (videos[] + HAS_EXAM) and deploy.
"""
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / 'output'

# (id, title) — listening content only (speaking / reading / ONA excluded)
VIDS = [
    ("EAsLs_1HyG8", "Luisteren examen A2 (nieuw systeem) 5 vragen"),
    ("2K-cXgASSew", "Listening exam A2 (new system) 3 questions"),
    ("iEm-I_gVb9s", "Luisteren examen A2 (nieuw systeem) 3 vragen"),
    ("lk7UF1vn8a4", "Listening exam A2 (new system) 5 questions"),
    ("ogyJB2xEaUs", "Luisteren examen A2 (nieuw systeem) 3 vragen (b)"),
    ("J4yroaYw1SQ", "Luisteren examen A2 (nieuw systeem) 3 vragen (c)"),
    ("VhFT2yDaMjg", "Luisteren examen A2 (nieuw systeem) 3 vragen (d)"),
    ("gIqFonNsQZ8", "Luisteren examen A2 (nieuw systeem) 4 vragen"),
    ("DLKjW7fqyDU", "Listening exam A2 (new system) 5 questions (b)"),
    ("oS9ZMdbDffE", "Luisteren examen A2 (nieuw systeem) 8 vragen"),
    ("aLBxYurJGE0", "Luisteren examen A2 (nieuw systeem) 7 vragen"),
    ("S1Jkiew7ovQ", "Listening exam A2"),
    ("6IPSJbEwluw", "Listening exam A2 (b)"),
    ("4Bp2X6lj1Tw", "Sample question from the Listening exam 2025"),
    ("oAcYTBuHhT8", "Luisteren examen A2 Oefenen 1"),
    ("lb0q-sk82TA", "Listening exam A2 Practice 2"),
    ("BQnidD3sb0g", "Listening exam A2 Practice 3"),
    ("3EyfPWAy57w", "Listening exam A2 Practice 4"),
    ("tYbjAE3F4H0", "Listening exam A2 Practice 5"),
    ("jkm2z_f5oMk", "Luisteren examen A2 Oefenen 6"),
    ("MXsNK9j4PNQ", "Luisteren examen A2 Oefenen 7"),
    ("WqQRYFLxoDc", "Luisteren examen A2 Oefenen 8"),
    ("jc7V08Xc9IQ", "Listening exam A2 Practice 9"),
    ("WDcdn8N_oRk", "Listening exam A2 Practice 10"),
    ("cqXgUkucsvc", "Luisteren examen A2 Oefenen 11"),
    ("BJ3WH-kSAxI", "Listening exam A2 Practice 12"),
    ("0HenRw6__u8", "Luisteren examen A2 Oefenen 13"),
    ("5VRuRmDJURY", "Luisteren examen A2 Oefenen 14"),
    ("c0fBLov2nKk", "Luisteren examen A2 Oefenen 15"),
    ("Z0iOzLatpz4", "luisteren examen inburgeren A2"),
    ("QZ37MHN3NyE", "luisteren examen 2021"),
    ("f53OW6p7l-8", "listening exam A2 practice 2021"),
    ("yQLIwMeSE5c", "Exercise listening exam Level A2"),
    ("KO7Z5_85490", "Listening exam 2021 part 1"),
    ("l4MewuaqxTE", "Listening exam 2021 part 2"),
    ("hCh3xz_BDWo", "Listening exam 2021 part 3"),
    ("FIO4cZ0jCug", "Listening exam 2021"),
    ("Sy926KPXwV0", "Oefenen het luisteren met 10 Nederlandse teksten"),
    ("_--osX9sKB8", "100 Dutch Sentences to Practice for the Listening Exam"),
    ("CYPKuPAZt9E", "Luister naar de woorden"),
    ("J-VCgNpy9p8", "Listening and reading A2 (to the market)"),
    ("-tYNqvvOsU0", "Luisteren en Lezen (Piet met zijn moeder in ziekenhuis)"),
]

def run(cmd, timeout=1800):
    print('   $', ' '.join(cmd[:6]), '…')
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print('     ✗', (r.stderr or r.stdout)[-300:])
    return r.returncode == 0

def main():
    only = sys.argv[1:]
    vids = [(i, t) for i, t in VIDS if not only or i in only]
    print(f'Ingesting {len(vids)} listening videos\n')
    done, failed = [], []
    for n, (vid, title) in enumerate(vids, 1):
        d = OUT / vid
        print(f'[{n}/{len(vids)}] {vid}  {title}')
        try:
            if not (d / 'data.json').is_file():
                if not run(['python3', 'generate.py', f'https://www.youtube.com/watch?v={vid}',
                            '--whisper-api', '--title', title]):
                    failed.append(vid); print('     ⚠ transcript failed, skip'); continue
            if not (d / 'data.json').is_file():
                failed.append(vid); continue
            if not (d / 'exam.json').is_file():
                run(['python3', 'make_exam_auto.py', vid, '--title', title], timeout=300)
            if not (d / 'exam.json').is_file():
                failed.append(vid); continue
            # analyze BEFORE make_web — make_web embeds the 💡 panels from analysis.json
            run(['python3', 'analyze_sentences.py', vid], timeout=1200)
            run(['python3', 'make_web.py', vid], timeout=300)
            done.append(vid)
            print('     ✓ done')
        except Exception as e:
            print('     ✗', e); failed.append(vid)
    print(f'\n=== {len(done)} done, {len(failed)} failed ===')
    if failed: print('failed:', failed)
    (ROOT / 'ingest_done.json').write_text(json.dumps({'done': done, 'failed': failed}, ensure_ascii=False))

if __name__ == '__main__':
    main()
