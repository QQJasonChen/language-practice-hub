#!/usr/bin/env python3
# 為 spreken-templates.html 的範例句 + 反射小詞預生成 nl-NL 神經語音（OpenAI nova）。
# 檔名 = FNV-1a(UTF-8) 8 hex，與頁面 say() 的 hashKey 一致；輸出 audio/templates/<hash>.mp3
import os
from openai import OpenAI

ROOT = os.path.expanduser("~/Projects/language-practice-hub")
OUT = os.path.join(ROOT, "audio", "templates")
os.makedirs(OUT, exist_ok=True)
MODEL = "gpt-4o-mini-tts-2025-12-15"
VOICE = "nova"
INSTR = ("Speak in clear, natural Netherlands Dutch (nl-NL), calm and slightly slow "
         "for A2 language learners. Neutral, friendly tone.")

def hashkey(s):
    h = 0x811c9dc5
    for b in s.encode("utf-8"):
        h ^= b; h = (h * 0x01000193) & 0xffffffff
    return format(h, "08x")

# 13 句「立刻能說」範例（與頁面 .nl 逐字一致）
examples = [
    "Zij loopt op straat. Haar auto is kapot.",
    "Hij gaat met de fiets naar zijn werk.",
    "Ik ga liever naar een concert dan naar de bioscoop, want dat is gezelliger.",
    "Ik kook graag pasta. Ik vind dat lekker.",
    "Ik sport twee keer per week.",
    "Ik eet het liefst thuis. / Ik werk in een ziekenhuis.",
    "Ik houd van popmuziek. Bijvoorbeeld Coldplay.",
    "Ik fiets graag, want dat is gezond.",
    "Ik begin om negen uur. / Ik werk het liefst in de ochtend.",
    "Ik ben schoonmaker. / Ik maak het liefst Aziatisch eten.",
    "Ik ga met de fiets. / Ik kook eerst de pasta, dan doe ik er groente bij.",
    "Ik eet meestal samen met mijn familie.",
    "Ja, ik vind cadeautjes ook leuk. Ik krijg graag bloemen.",
]

# 反射小詞（詞卡）——簡單、口說好用；zoals 為新增的簡單版「例如」
vocab = [
    # 頻率/程度
    "het liefst", "graag", "meestal", "vaak", "soms", "bijna altijd", "nooit",
    # 連接（zoals 排前面，最簡單）
    "want", "zoals", "bijvoorbeeld", "en", "maar", "ook", "dan",
    # 表態形容詞
    "leuk", "mooi", "lekker", "gezond", "handig", "gezellig", "duur", "goedkoop",
    # 萬用理由（整句）
    "want dat is gezond", "want dat is handig", "want dat is goedkoop",
    "want dat is belangrijk", "want dat is rustig",
]

texts = examples + vocab
print(f"共 {len(texts)} 段（範例 {len(examples)} + 詞 {len(vocab)}）")
c = OpenAI()
made = skip = fail = 0
for i, raw in enumerate(texts, 1):
    path = os.path.join(OUT, hashkey(raw) + ".mp3")
    if os.path.exists(path) and os.path.getsize(path) > 200:
        skip += 1; continue
    spoken = raw.replace(" / ", ", ").replace("/", ", ")  # 斜線→停頓，讀起來自然
    try:
        r = c.audio.speech.create(model=MODEL, voice=VOICE, input=spoken,
                                  instructions=INSTR, response_format="mp3")
        with open(path, "wb") as f:
            f.write(r.read())
        made += 1
        if made % 10 == 0:
            print(f"  …已生成 {made}/{len(texts)}")
    except Exception as e:
        fail += 1
        print(f"  ✗ {e}  「{raw[:40]}」")
print(f"完成：新生成 {made}、跳過 {skip}、失敗 {fail} → audio/templates/")
