#!/usr/bin/env python3
"""為口說衝刺包的「題目+範例答案」預生成 nl-NL 神經語音 mp3。
檔名 = FNV-1a(UTF-8 文字) 8 hex，與 spreken-sprint.html 的 hashKey() 一致。
輸出到 audio/spreken/<hash>.mp3，已存在則跳過（可重複執行只補缺的）。

用法（擇一 provider）：
  Azure（推薦，nl-NL FennaNeural）：
    export AZURE_SPEECH_KEY=xxxx
    export AZURE_SPEECH_REGION=westeurope        # 看你的資源在哪區
    python3 gen_spreken_tts.py --provider azure --voice nl-NL-FennaNeural

  Google Cloud TTS：
    export GOOGLE_API_KEY=xxxx
    python3 gen_spreken_tts.py --provider google --voice nl-NL-Neural2-D
"""
import os, sys, json, time, argparse, base64, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(ROOT, 'audio', 'spreken')

def hashkey(s: str) -> str:
    h = 0x811c9dc5
    for byte in s.encode('utf-8'):
        h ^= byte
        h = (h * 0x01000193) & 0xffffffff
    return format(h, '08x')

def collect_texts():
    texts = set()
    for fn in ('output/sprint_bank.json', 'output/picture_bank.json'):
        p = os.path.join(ROOT, fn)
        if not os.path.exists(p):
            continue
        for b in json.load(open(p)):
            for field in ('q', 'a'):
                t = (b.get(field) or '').strip()
                if t:
                    texts.add(t)
    return sorted(texts)

# ---- Azure ----
def tts_azure(text, voice, key, region):
    url = f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1'
    ssml = (f"<speak version='1.0' xml:lang='nl-NL'>"
            f"<voice name='{voice}'><prosody rate='-8%'>{_xml(text)}</prosody></voice></speak>")
    req = urllib.request.Request(url, data=ssml.encode('utf-8'), method='POST', headers={
        'Ocp-Apim-Subscription-Key': key,
        'Content-Type': 'application/ssml+xml',
        'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3',
        'User-Agent': 'spreken-tts',
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def _xml(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;').replace("'", '&apos;'))

# ---- Google ----
def tts_google(text, voice, key):
    url = f'https://texttospeech.googleapis.com/v1/text:synthesize?key={key}'
    body = json.dumps({
        'input': {'text': text},
        'voice': {'languageCode': 'nl-NL', 'name': voice},
        'audioConfig': {'audioEncoding': 'MP3', 'speakingRate': 0.92},
    }).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST',
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return base64.b64decode(json.loads(r.read())['audioContent'])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--provider', choices=['azure', 'google'], required=True)
    ap.add_argument('--voice', required=True)
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    texts = collect_texts()
    print(f'共 {len(texts)} 句、總 {sum(len(t) for t in texts)} 字元')

    if args.provider == 'azure':
        key = os.environ.get('AZURE_SPEECH_KEY'); region = os.environ.get('AZURE_SPEECH_REGION')
        if not key or not region:
            sys.exit('缺 AZURE_SPEECH_KEY / AZURE_SPEECH_REGION 環境變數')
        synth = lambda t: tts_azure(t, args.voice, key, region)
    else:
        key = os.environ.get('GOOGLE_API_KEY')
        if not key:
            sys.exit('缺 GOOGLE_API_KEY 環境變數')
        synth = lambda t: tts_google(t, args.voice, key)

    made = skip = fail = 0
    for i, t in enumerate(texts, 1):
        path = os.path.join(OUT, hashkey(t) + '.mp3')
        if os.path.exists(path) and os.path.getsize(path) > 200:
            skip += 1; continue
        try:
            audio = synth(t)
            with open(path, 'wb') as f:
                f.write(audio)
            made += 1
            if made % 20 == 0:
                print(f'  …已生成 {made}（{i}/{len(texts)}）')
            time.sleep(0.05)
        except urllib.error.HTTPError as e:
            fail += 1
            print(f'  ✗ HTTP {e.code}: {e.read()[:200]!r}  「{t[:40]}…」')
            if e.code in (401, 403):
                sys.exit('金鑰/權限錯誤，停止。')
        except Exception as e:
            fail += 1
            print(f'  ✗ {e}  「{t[:40]}…」')
    print(f'\n完成：新生成 {made}、已存在跳過 {skip}、失敗 {fail}。輸出在 audio/spreken/')

if __name__ == '__main__':
    main()
