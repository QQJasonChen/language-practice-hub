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
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
ANSWER_GAP = 8.0    # seconds of silence that marks the answering pause
CTX_GAP = 8.0       # max gap between context line and its question

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

INTRO_HINTS = ("voorbeeldexamen", "ad apple", "ad appel", "succes", "het examen",
               "u geeft antwoord", "u hoort en ziet", "geef antwoord op alle")


def is_q(seg):
    return "?" in seg["text"]


def slice_video(vid):
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
        if is_q(segs[i]):
            j = i
            while (j + 1 < len(segs) and is_q(segs[j + 1])
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
        # context: single non-Q segment right before the group, close in time,
        # not part of the intro, not an answer-start (those come after a big gap)
        ctx = None
        ci = qs - 1
        if ci >= 0 and not is_q(segs[ci]):
            gap = segs[qs]["start"] - segs[ci]["end"]
            low = segs[ci]["text"].lower()
            is_intro = any(h in low for h in INTRO_HINTS)
            prev_group_end = groups[g - 1][1] if g > 0 else -1
            if gap < CTX_GAP and not is_intro and ci > prev_group_end:
                # if it directly follows the previous answer with a small gap it's ambiguous;
                # accept anyway — single-context assumption holds for Ad Appel
                ctx = ci

        # answers: non-Q segments after the group, starting after the big pause,
        # ending before the next group's context (or next group)
        nxt_start = groups[g + 1][0] if g + 1 < len(groups) else len(segs)
        # reserve next group's context slot
        nxt_ctx = nxt_start - 1
        if nxt_ctx > qe and not is_q(segs[nxt_ctx]) and g + 1 < len(groups):
            gap_nc = segs[nxt_start]["start"] - segs[nxt_ctx]["end"]
            low = segs[nxt_ctx]["text"].lower()
            if gap_nc < CTX_GAP and not any(h in low for h in INTRO_HINTS):
                nxt_start = nxt_ctx  # answers stop before it

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

        q_idx = ([ctx] if ctx is not None else []) + list(range(qs, qe + 1))
        item = {
            "q_nl": " ".join(segs[x]["text"].strip() for x in q_idx),
            "q_zh": " ".join((segs[x].get("translation") or "").strip() for x in q_idx).strip(),
            "q_start": round(segs[q_idx[0]]["start"] - 0.15, 2),
            "q_end": round(segs[q_idx[-1]]["end"] + 0.2, 2),
            "a_nl": " ".join(segs[x]["text"].strip() for x in ans),
            "a_zh": " ".join((segs[x].get("translation") or "").strip() for x in ans).strip(),
            "a_start": round(segs[ans[0]]["start"] - 0.15, 2),
            "a_end": round(segs[ans[-1]]["end"] + 0.2, 2),
        }
        items.append(item)
    return items


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
