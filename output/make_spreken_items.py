"""Slice Ad Appel spreken mock videos into Q/A items for spreken.html.

Ad Appel format per item:
  [context statement] -> [question line(s) ending with ?] -> ~20s answer pause -> [model answer lines]

Detection:
  - Q-segment: text contains '?'
  - Q-group: consecutive Q-segments (gap < 8s between them)
  - answers: non-Q segments after the Q-group, starting after a gap > ANSWER_GAP
  - context: the single non-Q segment right before a Q-group (gap < 8s), excluded from
    the previous item's answers
Output: output/spreken_items.json
"""
import difflib
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)
PROJECTS_ROOT = os.path.dirname(PROJECT_ROOT)
ANSWER_GAP = 8.0    # seconds of silence that marks the answering pause
CTX_GAP = 8.0       # max gap between context line and its question
CTX_LEAD_GAP = 2.2  # min gap before a context line; answer continuations are tighter

# Ad Appel spreekvaardigheid videos (regular Q->pause->model-answer format)
VIDS = [
    ("_tkoK4nhpVU", "Oefenexamen 1"),
    ("Oe2mXQSvrIc", "Oefenexamen 2"),
    ("LpmHcxO1GIE", "Oefenexamen 3"),
    ("_JVTi1vheeg", "Oefenexamen 4"),
    ("cqzgh_uaT0w", "Oefenexamen 5"),
    ("uK6B2WPV5ac", "Oefenexamen 6"),
    ("cPwEoHUGwnE", "Oefenexamen 7"),
    ("b0zrI7QOGcc", "Oefenexamen 8"),
    ("FM7AOEA-Ddw", "Oefenexamen 9"),
    ("jqzUZtV16g4", "Oefenexamen 10"),
    ("H-ZYqDGAfwM", "Oefenexamen 11"),
    ("BkaibOsg3hc", "Oefenexamen 12"),
    ("5L1Zv6n2pkU", "Oefenexamen 13"),
    ("eo9Dx17g8BE", "Oefenexamen 14"),
    ("QCSexczXI8o", "Oefenexamen 15"),
    ("xrcgcN30YVg", "Oefenexamen 16"),
    # 17-19 (2016 format) excluded: question-only videos, no spoken model answers
]

INTRO_HINTS = ("voorbeeldexamen", "voorbeeld examen", "ad apple", "ad appel", "succes", "het examen",
               "u geeft antwoord", "u hoort en ziet", "geef antwoord op alle")
OUTRO_HINTS = ("dit was een voorbeeldexamen", "succes bij het echte examen",
               "tv gelderland", "ondertitels")
DROP_SAMPLE_PREFIXES = ("加長版", "替代回答", "用 moeten")
PROMPT_TAIL_HINTS = (
    "vertel ook", "zeg ook", "gebruik alle plaatjes", "kies een",
    "kies één", "kies 1"
)
BAD_Q_PHRASES = (
    "wat wilt u later in singapore gaan wonen",
    "wat wil u later in singapore gaan wonen",
)
QUESTION_START_RE = re.compile(
    r"^(wat|waar|wanneer|welk|welke|wie|hoe|waarom|in welk|naar welk|"
    r"met wie|waarmee|houdt u|hebt u|bent u|vindt u|doet u|kookt u|"
    r"ontvangt u|gebruikt u|reist u)\b",
    re.I,
)

# A separate React project contains hand-cleaned questions/answers for the first
# nine Ad Appel mock exams. Use it when available, then align those texts back to
# this repo's local audio segments so the simulator plays the original audio.
CURATED_DIR = os.path.join(PROJECTS_ROOT, "spreken-ace", "src", "data", "speakingExams")
CURATED_SETS = {
    "_tkoK4nhpVU": "set1.ts",
    "Oe2mXQSvrIc": "set02.ts",
    "LpmHcxO1GIE": "set03.ts",
    "_JVTi1vheeg": "set04.ts",
    "cqzgh_uaT0w": "set05.ts",
    "uK6B2WPV5ac": "set06.ts",
    "cPwEoHUGwnE": "set07.ts",
    "b0zrI7QOGcc": "set08.ts",
    "FM7AOEA-Ddw": "set09.ts",
}


def is_prompt_tail(text):
    low = (text or "").lower()
    return any(h in low for h in PROMPT_TAIL_HINTS)


def is_q(seg):
    text = seg.get("text", "")
    low = text.lower()
    if any(p in low for p in BAD_Q_PHRASES) and "ik wil later" in low:
        return False
    if "?" in text or is_prompt_tail(text):
        return True
    return bool(QUESTION_START_RE.search(text.strip()))


def question_remainder(text):
    text = text or ""
    if "?" in text:
        return text.split("?")[-1].strip()
    if "？" in text:
        return text.split("？")[-1].strip()
    if "?" not in text:
        return ""


def is_answer_echo_segment(segs, idx):
    if idx <= 0 or "?" not in segs[idx].get("text", ""):
        return False
    gap = segs[idx]["start"] - segs[idx - 1]["end"]
    return gap > ANSWER_GAP and is_q(segs[idx - 1])


def is_answer_echo_only(seg):
    text = seg.get("text", "")
    return "?" in text and not question_remainder(text)


def preceded_by_answer_pause(segs, idx):
    if idx <= 0:
        return False
    return segs[idx]["start"] - segs[idx - 1]["end"] > ANSWER_GAP


def has_context_lead_gap(segs, idx):
    if idx <= 0:
        return True
    gap = segs[idx]["start"] - segs[idx - 1]["end"]
    return CTX_LEAD_GAP <= gap <= ANSWER_GAP


def context_block_start(segs, group_start, prev_group_end):
    ci = group_start - 1
    if ci <= prev_group_end or is_q(segs[ci]):
        return None
    if segs[group_start]["start"] - segs[ci]["end"] >= CTX_GAP:
        return None
    start = ci
    while start - 1 > prev_group_end and not is_q(segs[start - 1]):
        gap_to_next = segs[start]["start"] - segs[start - 1]["end"]
        if gap_to_next >= CTX_GAP:
            break
        start -= 1
    while start <= ci:
        low = segs[start].get("text", "").lower()
        if (not is_outro(segs[start].get("text", ""))
                and not any(h in low for h in INTRO_HINTS)
                and not preceded_by_answer_pause(segs, start)
                and has_context_lead_gap(segs, start)):
            break
        start += 1
    if start > ci:
        return None
    return start


def is_outro(text):
    low = text.lower()
    return any(h in low for h in OUTRO_HINTS)


def clean_join(segs, key="text"):
    vals = []
    for seg in segs:
        text = (seg.get(key) or "").strip()
        if not text or is_outro(text):
            continue
        vals.append(text)
    return " ".join(vals).strip()


def clean_answer_join(segs, key="text"):
    vals = []
    for seg in segs:
        text = (seg.get(key) or "").strip()
        if not text or is_outro(text):
            continue
        if "?" in text or "？" in text:
            text = question_remainder(text)
        if text:
            vals.append(text)
    return " ".join(vals).strip()


def strip_outro_text(text):
    text = text or ""
    text = re.sub(r"^\s*Succes!\s*", "", text, flags=re.I)
    text = re.sub(r"^\s*祝你好運！?\s*", "", text)
    for pat in (
        r"\s*Dit was een voorbeeldexamen.*$",
        r"\s*Succes bij het echte examen.*$",
        r"\s*TV Gelderland.*$",
        r"\s*Ondertitels ingediend.*$",
        r"\s*這是.*(?:範例|模擬).*考試.*$",
        r"\s*祝.*考試.*$",
    ):
        text = re.sub(pat, "", text, flags=re.I)
    return text.strip()


def normalize(text):
    text = unicodedata.normalize("NFKD", (text or "").lower())
    text = text.replace("€", " euro ").replace("één", "een")
    text = re.sub(r"\b5\s*km\b", "vijf kilometer", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def score_window(target, text):
    nt, nw = normalize(target), normalize(text)
    if not nt or not nw:
        return 0
    ratio = difflib.SequenceMatcher(None, nt, nw).ratio()
    target_words = set(nt.split())
    window_words = set(nw.split())
    coverage = len(target_words & window_words) / max(1, len(target_words))
    extra = len(window_words - target_words) / max(1, len(window_words))
    return ratio * 0.65 + coverage * 0.45 - extra * 0.12


def best_window(segs, target, start, max_len=8, limit=80):
    best = (-1, None, None)
    end_lim = min(len(segs), start + limit)
    for i in range(start, end_lim):
        text = ""
        for j in range(i, min(end_lim, i + max_len)):
            text = (text + " " + segs[j]["text"]).strip()
            score = score_window(target, text)
            if score > best[0]:
                best = (score, i, j)
    return best


def read_curated_set(filename):
    if not filename:
        return None
    path = os.path.join(CURATED_DIR, filename)
    if not os.path.isfile(path):
        return None
    text = open(path, encoding="utf-8").read()
    match = re.search(r"export const \w+: ExamSet = (.*);\s*$", text, re.S)
    if not match:
        return None
    return json.loads(match.group(1))


def curated_question_text(q):
    return " ".join(x.strip() for x in (q.get("contextDutch"), q.get("questionDutch")) if x and x.strip())


def curated_question_zh(q):
    return " ".join(x.strip() for x in (
        q.get("contextChinese") or q.get("contextJapanese"),
        q.get("questionChinese") or q.get("questionJapanese"),
    ) if x and x.strip())


def curated_answer_text(q):
    answers = []
    for sample in q.get("sampleAnswers", []):
        dutch = (sample.get("dutch") or "").strip()
        if not dutch or dutch.startswith(DROP_SAMPLE_PREFIXES):
            continue
        # Many sets store a long coached answer after the real video answer.
        if answers and len(dutch) > 100 and dutch.count(".") >= 2:
            break
        answers.append(dutch)
    return " ".join(answers).strip()


def curated_answer_zh(q):
    answers = []
    for sample in q.get("sampleAnswers", []):
        dutch = (sample.get("dutch") or "").strip()
        zh = (sample.get("chinese") or sample.get("japanese") or "").strip()
        if not dutch or dutch.startswith(DROP_SAMPLE_PREFIXES):
            continue
        if answers and len(dutch) > 100 and dutch.count(".") >= 2:
            break
        answers.append(zh)
    return " ".join(answers).strip()


def image_paths_for_video(vid):
    folder = os.path.join(PROJECT_ROOT, "spreken-examen", vid)
    if not os.path.isdir(folder):
        return []
    files = []
    for name in os.listdir(folder):
        if re.match(r"q\d+\.jpe?g$", name, re.I):
            files.append(name)
    return [f"spreken-examen/{vid}/{name}" for name in sorted(files)]


def needs_image(text):
    low = (text or "").lower()
    return "kijk naar" in low or "plaatje" in low or "plaatjes" in low


def slice_video_curated(vid):
    curated = read_curated_set(CURATED_SETS.get(vid, ""))
    if not curated:
        return None
    data_path = os.path.join(ROOT, vid, "data.json")
    if not os.path.exists(data_path):
        return None
    segs = json.load(open(data_path, encoding="utf-8"))["ai_data"].get("segments", [])
    segs = [s for s in segs if s.get("text", "").strip()]
    if not segs:
        return None

    items = []
    cursor = 0
    image_paths = image_paths_for_video(vid)
    image_i = 0

    for q in curated.get("questions", []):
        q_nl = curated_question_text(q)
        a_nl = curated_answer_text(q)
        if q_nl:
            q_best = best_window(segs, q_nl, cursor, max_len=8, limit=80)
            if q_best[1] is None:
                continue
            a_best = best_window(segs, a_nl, q_best[2] + 1, max_len=6, limit=80)
            if a_best[1] is None:
                continue
            q_slice = segs[q_best[1]:q_best[2] + 1]
        else:
            a_best = best_window(segs, a_nl, cursor, max_len=6, limit=80)
            if a_best[1] is None or a_best[1] <= cursor:
                continue
            q_best = (1, cursor, a_best[1] - 1)
            q_slice = segs[cursor:a_best[1]]
        a_slice = [s for s in segs[a_best[1]:a_best[2] + 1] if not is_outro(s.get("text", ""))]
        if not a_slice:
            continue

        # If a curated set has a blank question, fall back to the aligned source text.
        final_q_nl = q_nl or clean_join(q_slice, "text")
        final_q_zh = curated_question_zh(q) or clean_join(q_slice, "translation")
        final_a_nl = a_nl or clean_join(a_slice, "text")
        final_a_zh = curated_answer_zh(q) or clean_join(a_slice, "translation")

        item = {
            "q_nl": strip_outro_text(final_q_nl),
            "q_zh": strip_outro_text(final_q_zh),
            "q_start": round(q_slice[0]["start"] - 0.15, 2),
            "q_end": round(q_slice[-1]["end"] + 0.2, 2),
            "a_nl": strip_outro_text(final_a_nl),
            "a_zh": strip_outro_text(final_a_zh),
            "a_start": round(a_slice[0]["start"] - 0.15, 2),
            "a_end": round(a_slice[-1]["end"] + 0.2, 2),
        }
        if needs_image(item["q_nl"]) and image_i < len(image_paths):
            item["img"] = image_paths[image_i]
            image_i += 1
        items.append(item)
        cursor = a_best[2] + 1

    return items or None


def build_item_from_segments(q_segs, a_segs):
    while a_segs and is_answer_echo_only(a_segs[0]):
        a_segs = a_segs[1:]
    if not q_segs or not a_segs:
        return None
    return {
        "q_nl": strip_outro_text(clean_join(q_segs, "text")),
        "q_zh": strip_outro_text(clean_join(q_segs, "translation")),
        "q_start": round(q_segs[0]["start"] - 0.15, 2),
        "q_end": round(q_segs[-1]["end"] + 0.2, 2),
        "a_nl": strip_outro_text(clean_answer_join(a_segs, "text")),
        "a_zh": strip_outro_text(clean_answer_join(a_segs, "translation")),
        "a_start": round(a_segs[0]["start"] - 0.15, 2),
        "a_end": round(a_segs[-1]["end"] + 0.2, 2),
    }


def apply_specific_fixes(vid, items, segs):
    if vid == "H-ZYqDGAfwM":
        for item in items:
            q = item.get("q_nl", "")
            if "Wat wilt u later in Singapore gaan wonen" in q:
                item["q_nl"] = (
                    "Ik wil later in Singapore gaan wonen. Dat is mijn ideale stad. "
                    "Wat is uw ideale plaats en vertel ook waarom."
                )
                item["q_zh"] = "我以後想住在新加坡。那是我理想中的城市。您的理想地點是哪裡？也請說說為什麼。"
            elif "muesli en fruit" in q and "ontbijt" in q:
                item["q_nl"] = (
                    "Ik eet elke dag muesli en fruit bij mijn ontbijt. "
                    "En ik drink ook thee. Wat neemt u bij uw ontbijt?"
                )
                item["q_zh"] = "我每天早餐吃麥片和水果，也喝茶。您早餐吃什麼？"
    if vid == "eo9Dx17g8BE":
        for i, item in enumerate(items):
            q = item.get("q_nl", "")
            if "Ik werk ook het liefst met anderen" in q and "Het strand is leuk" in q:
                work_item = build_item_from_segments(segs[27:29], segs[29:31])
                beach_item = build_item_from_segments(segs[31:33], segs[35:37])
                if work_item and beach_item:
                    beach_item["a_nl"] = (
                        "Het strand is leuk want ik houd van de zee. "
                        "Het strand is niet altijd leuk want soms is het heel druk."
                    )
                    beach_item["a_zh"] = "海灘很棒，因為我喜歡大海。海灘並非總是很棒，因為有時候很擁擠。"
                    items = items[:i] + [work_item, beach_item] + items[i + 1:]
                break
    return items


def slice_video(vid):
    curated_items = slice_video_curated(vid)
    if curated_items:
        return curated_items

    path = os.path.join(ROOT, vid, "data.json")
    if not os.path.exists(path):
        return None
    segs = json.load(open(path))["ai_data"].get("segments", [])
    segs = [s for s in segs if s.get("text", "").strip()]
    if not segs:
        return None

    # 1) find Q-groups: runs of Q-segments (small gaps between them allowed)
    groups = []  # list of (start_idx, end_idx) inclusive
    i = 0
    while i < len(segs):
        if is_q(segs[i]) and not is_answer_echo_segment(segs, i):
            j = i
            while (j + 1 < len(segs) and is_q(segs[j + 1])
                   and not is_answer_echo_segment(segs, j + 1)
                   and segs[j + 1]["start"] - segs[j]["end"] < CTX_GAP):
                j += 1
            groups.append((i, j))
            i = j + 1
        else:
            i += 1
    if not groups:
        return None

    items = []
    for g, (qs, qe) in enumerate(groups):
        # context: one or more non-Q lead-in segments right before the group.
        prev_group_end = groups[g - 1][1] if g > 0 else -1
        ctx_start = context_block_start(segs, qs, prev_group_end)

        # answers: non-Q segments after the group, starting after the big pause,
        # ending before the next group's context (or next group)
        nxt_start = groups[g + 1][0] if g + 1 < len(groups) else len(segs)
        if g + 1 < len(groups):
            nxt_ctx_start = context_block_start(segs, nxt_start, qe)
            if nxt_ctx_start is not None:
                nxt_start = nxt_ctx_start  # answers stop before next context block

        ans = []
        k = qe + 1
        started = False
        while k < nxt_start:
            gap = segs[k]["start"] - segs[k - 1]["end"]
            if not started:
                if gap > ANSWER_GAP:
                    started = True
                    ans.append(k)
                # else: stray segment inside the pause window — skip
            else:
                ans.append(k)
            k += 1
        # fallback: no big gap found (timing noise) -> everything after group is answer
        if not ans and qe + 1 < nxt_start:
            ans = list(range(qe + 1, nxt_start))

        if not ans:
            continue  # unusable item

        q_idx = (list(range(ctx_start, qs)) if ctx_start is not None else []) + list(range(qs, qe + 1))
        q_segs = [segs[x] for x in q_idx]
        a_segs = [segs[x] for x in ans if not is_outro(segs[x].get("text", ""))]
        while a_segs and is_answer_echo_only(a_segs[0]):
            a_segs = a_segs[1:]
        if not a_segs:
            continue
        item = build_item_from_segments(q_segs, a_segs)
        if item:
            items.append(item)
    return apply_specific_fixes(vid, items, segs)


def main():
    out = {"videos": []}
    total = 0
    for vid, label in VIDS:
        items = slice_video(vid)
        if not items:
            print(f"✗ {label} ({vid}): no items")
            continue
        out["videos"].append({"vid": vid, "label": label, "items": items})
        total += len(items)
        print(f"✓ {label}: {len(items)} items")
    out["count"] = total
    dst = os.path.join(ROOT, "spreken_items.json")
    json.dump(out, open(dst, "w"), ensure_ascii=False, indent=1)
    print(f"\n→ {dst}  ({total} items, {len(out['videos'])} videos)")


if __name__ == "__main__":
    main()
