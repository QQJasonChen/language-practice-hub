#!/usr/bin/env python3
"""
YouTube → Language Practice Generator
把任意 YouTube 影片變成完整的語言練習頁面（AB Loop + Echo 迴音法 + 聽寫模式）

Usage:
  python generate.py <youtube_url> [options]

Options:
  --lang       目標語言 (default: nl)
  --native     母語 (default: zh-TW)
  --title      自訂標題
  --output     輸出資料夾 (default: ./output/<video_id>)
  --whisper    Whisper 模型 (default: large)
  --skip-ai    跳過 AI 處理（只做轉錄）
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Config ──
LANG_NAMES = {
    'nl': {'name': 'Nederlands', 'zh': '荷蘭文', 'en': 'Dutch'},
    'en': {'name': 'English', 'zh': '英文', 'en': 'English'},
    'de': {'name': 'Deutsch', 'zh': '德文', 'en': 'German'},
    'fr': {'name': 'Français', 'zh': '法文', 'en': 'French'},
    'es': {'name': 'Español', 'zh': '西班牙文', 'en': 'Spanish'},
    'ja': {'name': '日本語', 'zh': '日文', 'en': 'Japanese'},
    'ko': {'name': '한국어', 'zh': '韓文', 'en': 'Korean'},
    'it': {'name': 'Italiano', 'zh': '義大利文', 'en': 'Italian'},
    'pt': {'name': 'Português', 'zh': '葡萄牙文', 'en': 'Portuguese'},
}

NATIVE_NAMES = {
    'zh-TW': '繁體中文',
    'zh-CN': '简体中文',
    'en': 'English',
    'ja': '日本語',
    'ko': '한국어',
}


def run(cmd, **kwargs):
    """Run a shell command and return output."""
    print(f"  → {' '.join(cmd[:4])}{'...' if len(cmd) > 4 else ''}")
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"  ✗ Error: {result.stderr[:200]}")
    return result


def extract_video_id(url):
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def get_video_info(url):
    """Get video title and metadata."""
    result = run(['yt-dlp', '--cookies-from-browser', 'chrome', '--print', '%(title)s\n%(channel)s\n%(duration)s', '--no-download', url])
    if result.returncode != 0:
        return {'title': 'Unknown', 'channel': 'Unknown', 'duration': 0}
    lines = result.stdout.strip().split('\n')
    return {
        'title': lines[0] if len(lines) > 0 else 'Unknown',
        'channel': lines[1] if len(lines) > 1 else 'Unknown',
        'duration': int(lines[2]) if len(lines) > 2 and lines[2].isdigit() else 0,
    }


def download_audio(url, output_path):
    """Download audio from YouTube as mp3."""
    result = run([
        'yt-dlp', '--cookies-from-browser', 'chrome',
        '-x', '--audio-format', 'm4a',
        '--audio-quality', '3',
        '-o', str(output_path),
        url
    ])
    return result.returncode == 0


def download_subtitles(url, lang, output_dir):
    """Try to download auto-generated subtitles."""
    srt_path = os.path.join(output_dir, 'subs')
    result = run([
        'yt-dlp', '--cookies-from-browser', 'chrome',
        '--write-auto-sub', '--sub-lang', lang,
        '--sub-format', 'srt', '--skip-download',
        '-o', srt_path,
        url
    ])
    # Find the actual file
    for f in Path(output_dir).glob('subs*.srt'):
        return str(f)
    return None


def transcribe_whisper(audio_path, lang, model='large'):
    """Transcribe audio using Whisper."""
    # Try local whisper first, fallback to API
    try:
        result = run([
            'whisper', str(audio_path),
            '--model', model,
            '--language', lang,
            '--output_format', 'srt',
            '--output_dir', str(Path(audio_path).parent),
        ])
        srt_path = str(audio_path).rsplit('.', 1)[0] + '.srt'
        if os.path.exists(srt_path):
            return srt_path
    except FileNotFoundError:
        pass

    # Fallback: OpenAI Whisper API via curl
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("  ✗ No whisper CLI and no OPENAI_API_KEY. Cannot transcribe.")
        return None

    print("  → Using OpenAI Whisper API...")

    # Compress to 16kHz mono — but SKIP if already 16kHz (avoid double-compression!)
    import shutil
    sr_check = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'stream=sample_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
        capture_output=True, text=True).stdout.strip()

    if sr_check == '16000':
        print(f"  ✓ Already 16kHz, skipping compression")
    else:
        compressed = str(audio_path).rsplit('.', 1)[0] + '_compressed.mp3'
        print(f"  → Compressing {sr_check}Hz → 16kHz mono...")
        comp_result = run([
            'ffmpeg', '-y', '-i', str(audio_path),
            '-ac', '1', '-ab', '64k', '-ar', '16000', compressed
        ])
        if comp_result.returncode == 0 and os.path.exists(compressed):
            comp_size = os.path.getsize(compressed)
            print(f"  ✓ Compressed: {os.path.getsize(audio_path)//(1024*1024)}MB → {comp_size//(1024*1024)}MB")
            original_backup = str(audio_path).rsplit('.', 1)[0] + '_original.mp3'
            if not os.path.exists(original_backup):
                shutil.move(str(audio_path), original_backup)
            else:
                os.remove(str(audio_path))
            shutil.move(compressed, str(audio_path))
            print(f"  ✓ audio.mp3 replaced (Whisper + player use same file)")
        else:
            print(f"  ⚠ Compression failed, using original")

    file_size = os.path.getsize(audio_path)
    if file_size > 25 * 1024 * 1024:
        print(f"  ⚠ Still {file_size//(1024*1024)}MB > 25MB, splitting...")
        return transcribe_whisper_chunked(audio_path, lang, api_key)

    # Try verbose_json first for precise segment timestamps
    json_path = str(audio_path).rsplit('.', 1)[0] + '.whisper.json'
    result = subprocess.run([
        'curl', '-s', 'https://api.openai.com/v1/audio/transcriptions',
        '-H', f'Authorization: Bearer {api_key}',
        '-F', f'file=@{audio_path}',
        '-F', 'model=whisper-1',
        '-F', f'language={lang}',
        '-F', 'response_format=verbose_json',
        '-F', 'timestamp_granularities[]=word',
        '-F', 'timestamp_granularities[]=segment',
    ], capture_output=True, text=True, timeout=180)

    if result.returncode != 0:
        print(f"  ✗ Whisper API error: {result.stderr[:200]}")
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  ✗ Whisper API returned invalid JSON: {result.stdout[:200]}")
        return None

    if 'segments' not in data:
        print(f"  ✗ No segments in Whisper response")
        return None

    # Save raw Whisper data
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Split long segments using word-level timestamps
    if data.get('words'):
        print(f"  ✓ Word-level timestamps available, splitting long segments...")
        data['segments'] = split_long_segments(data['segments'], data['words'])
        print(f"  ✓ {len(data['segments'])} segments after splitting")

    # Convert to SRT format for compatibility
    srt_path = str(audio_path).rsplit('.', 1)[0] + '.srt'
    srt_lines = []
    for i, seg in enumerate(data['segments']):
        start = seg['start']
        end = seg['end']
        text = seg['text'].strip()
        if not text:
            continue
        sh, sm, ss = int(start//3600), int((start%3600)//60), start%60
        eh, em, es = int(end//3600), int((end%3600)//60), end%60
        srt_lines.append(f"{i+1}")
        srt_lines.append(f"{sh:02d}:{sm:02d}:{ss:06.3f} --> {eh:02d}:{em:02d}:{es:06.3f}".replace('.', ','))
        srt_lines.append(text)
        srt_lines.append('')

    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(srt_lines))

    print(f"  ✓ {len(data['segments'])} segments with precise timestamps")
    return srt_path


def transcribe_whisper_chunked(audio_path, lang, api_key):
    """Split large audio and transcribe in chunks."""
    chunk_dir = tempfile.mkdtemp()
    # Split into 10-minute chunks
    run([
        'ffmpeg', '-i', str(audio_path),
        '-f', 'segment', '-segment_time', '600',
        '-c', 'copy',
        os.path.join(chunk_dir, 'chunk_%03d.mp3')
    ])

    all_srt = ''
    offset = 0
    chunk_idx = 1

    for chunk in sorted(Path(chunk_dir).glob('chunk_*.mp3')):
        print(f"  → Transcribing chunk {chunk.name}...")
        srt_path = transcribe_whisper(str(chunk), lang)
        if srt_path and os.path.exists(srt_path):
            with open(srt_path, 'r') as f:
                chunk_srt = f.read()
            # Adjust timestamps by offset
            all_srt += offset_srt(chunk_srt, offset, chunk_idx)
            # Get chunk duration
            dur_result = run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                            '-of', 'default=noprint_wrappers=1:nokey=1', str(chunk)])
            if dur_result.returncode == 0:
                offset += float(dur_result.stdout.strip())
            chunk_idx += len(chunk_srt.strip().split('\n\n'))

    final_srt = str(audio_path).rsplit('.', 1)[0] + '.srt'
    with open(final_srt, 'w', encoding='utf-8') as f:
        f.write(all_srt)
    return final_srt


def offset_srt(srt_text, offset_seconds, start_idx):
    """Offset all timestamps in SRT by given seconds."""
    if offset_seconds == 0 and start_idx == 1:
        return srt_text

    def offset_ts(match):
        h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        total_ms = (h * 3600 + m * 60 + s) * 1000 + ms + int(offset_seconds * 1000)
        h2 = total_ms // 3600000
        m2 = (total_ms % 3600000) // 60000
        s2 = (total_ms % 60000) // 1000
        ms2 = total_ms % 1000
        return f"{h2:02d}:{m2:02d}:{s2:02d},{ms2:03d}"

    result = re.sub(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', offset_ts, srt_text)
    return result


def split_long_segments(segments, words, max_duration=6):
    """Split segments longer than max_duration using word-level timestamps.

    Uses sentence-ending punctuation (。？！.?!) as split points.
    Falls back to natural pauses (gaps between words) if no punctuation found.
    """
    # Build a lookup: for each time range, find the words in it
    result = []

    for seg in segments:
        duration = seg['end'] - seg['start']
        text = seg.get('text', '').strip()

        if duration <= max_duration or not text:
            result.append(seg)
            continue

        # Find words belonging to this segment
        seg_words = [w for w in words
                     if w['start'] >= seg['start'] - 0.1
                     and w['end'] <= seg['end'] + 0.1]

        if not seg_words:
            result.append(seg)
            continue

        # Find sentence-ending punctuation positions
        sentence_ends = []  # indices where sentences end
        for i, w in enumerate(seg_words):
            word_text = w.get('word', '')
            if any(word_text.rstrip().endswith(p) for p in ['。', '？', '！', '.', '?', '!', '、']):
                sentence_ends.append(i)

        if not sentence_ends:
            # No punctuation — try splitting at the largest gap between words
            if len(seg_words) >= 4:
                gaps = [(seg_words[i+1]['start'] - seg_words[i]['end'], i)
                        for i in range(len(seg_words)-1)]
                gaps.sort(reverse=True)
                # Use the biggest gap as split point
                mid = gaps[0][1]
                sentence_ends = [mid]
            else:
                result.append(seg)
                continue

        # Split at sentence boundaries
        prev_start = seg['start']
        prev_word_idx = 0

        for end_idx in sentence_ends:
            if end_idx + 1 >= len(seg_words):
                continue  # last word, will be handled below

            split_end = seg_words[end_idx]['end']
            split_text = ''.join(w.get('word', '') for w in seg_words[prev_word_idx:end_idx+1]).strip()

            sub_duration = split_end - prev_start
            if sub_duration < 1.0 and result:
                # Too short, merge with previous
                result[-1]['end'] = split_end
                result[-1]['text'] += split_text
            elif split_text:
                result.append({
                    'id': seg.get('id', 0),
                    'start': round(prev_start, 2),
                    'end': round(split_end, 2),
                    'text': split_text,
                })

            prev_start = seg_words[end_idx + 1]['start'] if end_idx + 1 < len(seg_words) else split_end
            prev_word_idx = end_idx + 1

        # Remaining words after last split
        if prev_word_idx < len(seg_words):
            remaining_text = ''.join(w.get('word', '') for w in seg_words[prev_word_idx:]).strip()
            if remaining_text:
                remaining_dur = seg['end'] - prev_start
                if remaining_dur < 1.0 and result:
                    result[-1]['end'] = seg['end']
                    result[-1]['text'] += remaining_text
                else:
                    result.append({
                        'id': seg.get('id', 0),
                        'start': round(prev_start, 2),
                        'end': round(seg['end'], 2),
                        'text': remaining_text,
                    })

    return result


def parse_srt(srt_path):
    """Parse SRT file into segments with timestamps."""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    segments = []
    blocks = content.strip().split('\n\n')

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        # Parse timestamp
        ts_match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})', lines[1])
        if not ts_match:
            continue
        start = int(ts_match.group(1)) * 3600 + int(ts_match.group(2)) * 60 + int(ts_match.group(3)) + int(ts_match.group(4)) / 1000
        end = int(ts_match.group(5)) * 3600 + int(ts_match.group(6)) * 60 + int(ts_match.group(7)) + int(ts_match.group(8)) / 1000
        text = ' '.join(lines[2:]).strip()
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        if text:
            segments.append({'start': round(start, 2), 'end': round(end, 2), 'text': text})

    return merge_segments(segments)


def merge_segments(segments, min_duration=3, max_duration=6):
    """Merge SRT segments into sentence-sized chunks for language practice.

    Target: 3-8 seconds per segment, roughly one natural sentence.
    Also fixes overlapping timestamps from YouTube auto-subs.
    """
    if not segments:
        return []

    # Step 1: Fix overlapping timestamps — each segment starts where previous ends
    fixed = []
    for i, seg in enumerate(segments):
        s = {**seg}
        if fixed and s['start'] < fixed[-1]['end']:
            s['start'] = fixed[-1]['end']
        if s['start'] >= s['end']:
            # Segment fully overlapped, skip or merge into previous
            if fixed:
                fixed[-1]['text'] += ' ' + s['text']
                fixed[-1]['end'] = max(fixed[-1]['end'], seg['end'])
            continue
        fixed.append(s)

    # Step 2: Merge short segments
    merged = []
    current = {**fixed[0]} if fixed else None

    for seg in fixed[1:]:
        duration = current['end'] - current['start']
        combined_dur = seg['end'] - current['start']

        if duration < min_duration and combined_dur <= max_duration:
            current['end'] = seg['end']
            current['text'] += ' ' + seg['text']
        else:
            current['text'] = dedupe_text(current['text'])
            merged.append(current)
            current = {**seg}

    if current:
        current['text'] = dedupe_text(current['text'])
        merged.append(current)
    return merged


def dedupe_text(text):
    """Remove obviously repeated phrases from auto-sub merging."""
    words = text.split()
    if len(words) < 6:
        return text
    # Simple dedup: if the second half starts the same as the first half
    mid = len(words) // 2
    if words[:3] == words[mid:mid+3]:
        return ' '.join(words[:mid])
    return text


def ai_process(segments, lang, native, video_info, skip_ai=False):
    """Use AI to generate translations, quiz questions, and vocabulary."""
    if skip_ai:
        return {
            'segments': [{'nl': s['text'], 'zh': '', 'start': s['start'], 'end': s['end']} for s in segments],
            'questions': [],
            'vocabulary': [],
        }

    api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("  ⚠ No API key found. Skipping AI processing.")
        return ai_process(segments, lang, native, video_info, skip_ai=True)

    lang_name = LANG_NAMES.get(lang, {}).get('en', lang)
    native_name = NATIVE_NAMES.get(native, native)

    # NEW APPROACH: Keep Whisper segments untouched, AI only translates
    # This guarantees timestamps are never corrupted
    all_segments = [{'text': s['text'], 'translation': '', 'start': s['start'], 'end': s['end']} for s in segments]

    # Batch translate (text only, no segment structure changes)
    batch_size = 50  # can be bigger since we only send text
    all_questions = []
    all_vocabulary = []

    for batch_idx in range(0, len(segments), batch_size):
        batch = segments[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        total_batches = (len(segments) + batch_size - 1) // batch_size
        is_first = batch_idx == 0
        print(f"  → Translating batch {batch_num}/{total_batches} ({len(batch)} segments)...")

        texts = [s['text'] for s in batch]
        texts_str = '\n'.join([f"{i+1}. {t}" for i, t in enumerate(texts)])

        quiz_section = f"""
Also generate:
"questions": [4-6 comprehension questions about the full video, each with "question", "question_native", "options" (3 choices), "answer"]
"vocabulary": [12-15 key words with "word" and "meaning"]""" if is_first else ""

        prompt = f"""You have {len(texts)} {lang_name} sentences from speech recognition. Do TWO things for each:
1. CLEAN the text: fix missing spaces, punctuation, capitalization, obvious typos
2. TRANSLATE to {native_name} (繁體中文台灣用語 if zh-TW)

{texts_str}

Return ONLY valid JSON:
{{"cleaned": ["cleaned text 1", "cleaned text 2", ...], "translations": ["translation 1", "translation 2", ...]{', ' + quiz_section.strip() if quiz_section else ''}}}

CRITICAL: Return EXACTLY {len(texts)} items in each array. Same order as input. Do NOT merge or skip any."""

        if os.environ.get('ANTHROPIC_API_KEY'):
            result = ai_process_anthropic(prompt, os.environ['ANTHROPIC_API_KEY'])
        else:
            result = ai_process_openai(prompt, api_key)

        if result:
            cleaned = result.get('cleaned', [])
            translations = result.get('translations', [])
            for j in range(len(batch)):
                idx = batch_idx + j
                if idx < len(all_segments):
                    if j < len(cleaned) and cleaned[j]:
                        all_segments[idx]['text'] = cleaned[j]
                    if j < len(translations) and translations[j]:
                        all_segments[idx]['translation'] = translations[j]
            if is_first:
                all_questions = result.get('questions', [])
                all_vocabulary = result.get('vocabulary', [])

    # Filter out empty segments
    all_segments = [s for s in all_segments if s.get('text', '').strip()]

    print(f"  ✓ {len(all_segments)} segments (timestamps from Whisper, untouched)")
    print(f"  ✓ {len(all_questions)} questions generated")
    print(f"  ✓ {len(all_vocabulary)} vocabulary items")

    return {
        'segments': all_segments,
        'questions': all_questions,
        'vocabulary': all_vocabulary,
    }


def _ai_process_batch(segments_for_ai, transcript, lang_name, native_name, video_info, api_key, include_quiz, include_vocab):

    quiz_section = f"""
  "questions": [
    // 4-6 comprehension questions about the FULL video content
    {{"question": "question in {lang_name}", "question_native": "question in {native_name}", "options": ["A","B","C"], "answer": "correct option"}}
  ],
  "vocabulary": [
    // 12-15 key vocabulary items useful for learners
    {{"word": "{lang_name} word", "meaning": "{native_name} meaning"}}
  ]""" if include_quiz else ""

    prompt = f"""You are a language learning assistant. Process this {lang_name} transcript for a speaking practice tool.

Video: {video_info.get('title', 'Unknown')}
Target language: {lang_name}
User's native language: {native_name}

CRITICAL RULES:
- Output EXACTLY {len(segments_for_ai)} segments, one per input. Do NOT split or merge.
- Keep the EXACT same start and end timestamps from input. Do NOT change them.
- Only clean up the text (fix errors, add punctuation) and add translation.
- If a segment is pure noise/music, set text to "" (empty string).
- Translations MUST be in {native_name} (if zh-TW, use 繁體中文台灣用語, not 简体)

Transcript ({len(segments_for_ai)} segments):
{transcript}

Return ONLY valid JSON with EXACTLY {len(segments_for_ai)} segments:
{{
  "segments": [
    {{"text": "cleaned text with punctuation", "translation": "翻譯", "start": 10.0, "end": 13.0}}
  ]{quiz_section}
}}"""

    if os.environ.get('ANTHROPIC_API_KEY'):
        return ai_process_anthropic(prompt, os.environ['ANTHROPIC_API_KEY'])
    else:
        return ai_process_openai(prompt, api_key)


def ai_process_anthropic(prompt, api_key):
    """Process with Claude API via curl."""
    print("  → AI processing with Claude...")
    body = json.dumps({
        'model': 'claude-sonnet-4-20250514',
        'max_tokens': 8000,
        'messages': [{'role': 'user', 'content': prompt}],
    })
    result = subprocess.run([
        'curl', '-s', 'https://api.anthropic.com/v1/messages',
        '-H', f'x-api-key: {api_key}',
        '-H', 'anthropic-version: 2023-06-01',
        '-H', 'content-type: application/json',
        '-d', body,
    ], capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"  ✗ curl error: {result.stderr[:200]}")
        return None

    data = json.loads(result.stdout)
    if 'content' not in data:
        print(f"  ✗ Claude API error: {json.dumps(data)[:200]}")
        return None

    text = data['content'][0]['text']
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
        print(f"  ✗ Could not parse AI response")
        return None


def ai_process_openai(prompt, api_key):
    """Process with OpenAI API via curl."""
    print("  → AI processing with GPT-4o...")
    body = json.dumps({
        'model': 'gpt-4.1-mini',
        'messages': [{'role': 'user', 'content': prompt}],
        'response_format': {'type': 'json_object'},
    })
    result = subprocess.run([
        'curl', '-s', 'https://api.openai.com/v1/chat/completions',
        '-H', f'Authorization: Bearer {api_key}',
        '-H', 'Content-Type: application/json',
        '-d', body,
    ], capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"  ✗ curl error: {result.stderr[:200]}")
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  ✗ OpenAI returned invalid JSON (empty or timeout), retrying...")
        # Retry once
        result2 = subprocess.run([
            'curl', '-s', '--max-time', '120',
            'https://api.openai.com/v1/chat/completions',
            '-H', f'Authorization: Bearer {api_key}',
            '-H', 'Content-Type: application/json',
            '-d', body,
        ], capture_output=True, text=True, timeout=140)
        try:
            data = json.loads(result2.stdout)
        except json.JSONDecodeError:
            print(f"  ✗ Retry also failed: {result2.stdout[:100]}")
            return None

    if 'choices' not in data:
        print(f"  ✗ OpenAI API error: {json.dumps(data)[:200]}")
        return None

    text = data['choices'][0]['message']['content']
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re as _re
        match = _re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
        print(f"  ✗ Could not parse AI response")
        return None


def generate_html(data, video_info, lang, native, output_dir):
    """Generate the complete practice HTML page."""
    template_path = Path(__file__).parent / 'template.html'
    if not template_path.exists():
        print("  ✗ template.html not found! Run this from the project directory.")
        return None

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    lang_info = LANG_NAMES.get(lang, {'name': lang, 'zh': lang, 'en': lang})
    native_name = NATIVE_NAMES.get(native, native)

    # Prepare data for template
    segments_json = json.dumps(data.get('segments', []), ensure_ascii=False)
    questions_json = json.dumps(data.get('questions', []), ensure_ascii=False)
    vocabulary_json = json.dumps(data.get('vocabulary', []), ensure_ascii=False)

    html = template
    html = html.replace('{{TITLE}}', video_info.get('title', 'Language Practice'))
    html = html.replace('{{CHANNEL}}', video_info.get('channel', ''))
    html = html.replace('{{LANG_NAME}}', lang_info['name'])
    html = html.replace('{{LANG_ZH}}', lang_info['zh'])
    html = html.replace('{{NATIVE_NAME}}', native_name)
    html = html.replace('{{SEGMENTS_JSON}}', segments_json)
    html = html.replace('{{QUESTIONS_JSON}}', questions_json)
    html = html.replace('{{VOCABULARY_JSON}}', vocabulary_json)
    html = html.replace('{{AUDIO_FILE}}', 'audio.mp3')

    output_html = os.path.join(output_dir, 'index.html')
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_html


def main():
    parser = argparse.ArgumentParser(description='YouTube → Language Practice Generator')
    parser.add_argument('url', help='YouTube URL')
    parser.add_argument('--lang', default='nl', help='Target language code (default: nl)')
    parser.add_argument('--native', default='zh-TW', help='Native language (default: zh-TW)')
    parser.add_argument('--title', help='Custom title')
    parser.add_argument('--output', help='Output directory')
    parser.add_argument('--whisper', default='large', help='Whisper model (default: large)')
    parser.add_argument('--skip-ai', action='store_true', help='Skip AI processing')
    parser.add_argument('--whisper-api', action='store_true', help='Force Whisper API (better segmentation, ~$0.006/min)')
    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    if not video_id:
        print("✗ Could not extract video ID from URL")
        sys.exit(1)

    print(f"\n🎬 YouTube Practice Generator")
    print(f"{'=' * 50}")

    # 1. Get video info
    print("\n📋 Step 1: Getting video info...")
    info = get_video_info(args.url)
    if args.title:
        info['title'] = args.title
    print(f"  ✓ {info['title']} ({info['channel']})")
    duration_min = info['duration'] // 60 if info['duration'] else '?'
    print(f"  ✓ Duration: {duration_min} min")

    # 2. Setup output dir
    output_dir = args.output or os.path.join('output', video_id)
    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, 'audio.mp3')
    print(f"  ✓ Output: {output_dir}/")

    # 3. Download audio
    print(f"\n🔊 Step 2: Downloading audio...")
    if os.path.exists(audio_path):
        print(f"  ✓ Audio already exists, skipping")
    else:
        if not download_audio(args.url, audio_path):
            print("  ✗ Failed to download audio")
            sys.exit(1)
        print(f"  ✓ Audio downloaded")

    # 4. Get transcript
    print(f"\n📝 Step 3: Getting transcript...")
    srt_path = None

    if args.whisper_api:
        print(f"  → Using Whisper API (better quality)...")
        srt_path = transcribe_whisper(audio_path, args.lang, args.whisper)
        if srt_path:
            print(f"  ✓ Whisper transcription complete")
    else:
        # Try auto-subs first
        srt_path = download_subtitles(args.url, args.lang, output_dir)
        if srt_path:
            print(f"  ✓ Auto-subtitles found")

    if not srt_path:
        print(f"  ⚠ No subtitles, falling back to Whisper...")
        srt_path = transcribe_whisper(audio_path, args.lang, args.whisper)
        if srt_path:
            print(f"  ✓ Whisper transcription complete")
        else:
            print(f"  ✗ Transcription failed")
            sys.exit(1)

    # 5. Parse transcript
    print(f"\n🔍 Step 4: Parsing transcript...")
    segments = parse_srt(srt_path)
    print(f"  ✓ {len(segments)} segments parsed")

    # 6. AI processing
    print(f"\n🤖 Step 5: AI processing ({len(segments)} segments, batched)...")
    ai_data = ai_process(segments, args.lang, args.native, info, skip_ai=args.skip_ai)
    if not ai_data or not ai_data.get('segments'):
        print("  ⚠ AI processing failed, using raw transcript")
        ai_data = {
            'segments': [{'text': s['text'], 'translation': '', 'start': s['start'], 'end': s['end']} for s in segments],
            'questions': [],
            'vocabulary': [],
        }

    # 7. Generate HTML
    print(f"\n🏗️  Step 6: Generating practice page...")
    html_path = generate_html(ai_data, info, args.lang, args.native, output_dir)
    if html_path:
        print(f"  ✓ {html_path}")

    # 8. Save data
    data_path = os.path.join(output_dir, 'data.json')
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump({
            'video_id': video_id,
            'video_info': info,
            'lang': args.lang,
            'native': args.native,
            'ai_data': ai_data,
        }, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {data_path}")

    print(f"\n{'=' * 50}")
    print(f"✅ Done! Open {output_dir}/index.html in your browser")
    print(f"   or deploy with: gh-pages -d {output_dir}")
    print()


if __name__ == '__main__':
    main()
