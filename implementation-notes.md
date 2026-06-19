# 施工日誌：A2 Spreking 講義 PDF 升級（🥇+🥈+🏅）

**SPEC**：把現在的「逐字稿 PDF」升級成主動學習用的「講義」。三個項目：
- 🥇 加考前預習頁（吃 data.json 的 vocabulary）+ 練後自測頁（吃 questions）
- 🥈 自動標記考題結構（"Lees eerst" / "Vertel ook" / `?` 結尾等 → 加色塊）
- 🏅 加 QR Code 跳回該影片的 Echo Dutch 線上練習頁

**開始**：2026-05-20 夜班
**專案**：language-practice-hub @ main
**範圍**：先做 Frederika oefenexamen 1-3 三支驗證，OK 再 batch 全 27 支
**驗收**：兩版（講義版 + 純荷文版）×27 支 = 54 PDF，外加講義版打開能看到預習/結構/自測/QR

---

## 23:55 — 結構偵測規則：用 starts-with / endswith 而非 AI

**類型**：🎯 設計決定

**情境**：要分辨「考題（vraag）/ 第二題（vertel ook）/ 考試 UI 指令」三類

**決定**：純 regex+startswith heuristic：
- `Vertel ook` 開頭 → 🟦 vertel（第二題）
- 句末 `?` + 短句 + 疑問詞 (Wat/Waar/Hoe/...) + 含「u/je/uw」→ 🟧 vraag
- "Volgende vraag" / "Wilt u nog terug" / "Geef antwoord op de vraag" / "Lees eerst de vraag" / "Kijk daarna naar de video" → ⚪ examui

**理由**：A2 考試的 prompt 句模式很固定，AI 反而誤判（會把 setup 句當題目）。Regex 透明、可調

**狀態**：✅ 已自行決定

## 23:56 — QR Code 用線上 API，不裝 library

**類型**：⚖️ 折衷

**情境**：講義版要 QR 跳回 Echo Dutch 線上練習頁

**決定**：用 `https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=<url>` 當 `<img src>`，Chrome 渲染時自動抓圖嵌進 PDF

**理由**：避免裝 python `qrcode` 套件、cross-platform 簡單

**替代方案**：
- 裝 `pip install qrcode[pil]` 並本地生 → 增加依賴
- 不要 QR → 失去紙↔數位橋

**狀態**：✅ 已自行決定。Chrome 印 PDF 時要連網（沒網會空白），可接受

## 隔日 — SPEC 大幅擴充：講義升級成「場景制聽力模擬考冊」

**類型**：🛤 偏離 SPEC

**情境**：用戶看了 v2 講義後回饋三點：(1)「每個新問題影片會重播一次」造成
逐字稿同段對話出現 3 次、很亂；(2) 考題沒標出答案對應原文哪一句；(3) 想
把它做成能賣錢（NT$300）的資源、下一步要加音檔做成網站。並追加「加上常見
單字＋句型分析」。

**決定**：放棄 v2 的「逐字稿＋標色」路線，整套改成 SCENARIO-BASED：
- 偵測場景邊界，每個場景的對話只列一次（重播折疊掉）
- 每題 = ✓答案 + 📍完整出處（問句＋答句，多行 timestamp）+ 💡反推 + ⚠️陷阱
- 每場景加考前預習：重點單字表 + 必背句型
- 兩版：講義版（詳解內嵌）/ 純荷文盲練版（答案集中到最後）

**理由**：v2 還是「逐字稿」思維；用戶要的是「模擬考冊」。場景制把 437 段
壓成 10 場景、22 題，每題都能反推。經 AskUserQuestion 確認用戶選「場景制」。

**狀態**：✅ 已自行決定（編排方式經用戶選擇）

## 隔日 — 用 exam.json 當資料層，與 data.json 分離

**類型**：🎯 設計決定

**情境**：考題結構（答案、出處、反推、單字、句型）要存哪。

**決定**：新增 `output/<id>/exam.json`，由 `make_exam.py` 手工編寫＋從
data.json segments 拉對話原文。make_pdfs.py 只讀 exam.json。

**理由**：用戶明說下一步要「抓音檔做成點擊播放原音的網站」。exam.json 的
每句、每個出處都帶 timestamp，網站可直接用同一份 JSON → 不是丟棄式工作，
是在建產品的資料層。data.json 留給轉錄 pipeline，職責分離。

**狀態**：✅ 已自行決定

## 隔日 — PART 2 缺失題幹的處理：忠實重建並標註

**類型**：⚖️ 折衷

**情境**：PART 2 有 4 題的題目自動轉錄抓不到——因為考試指令是「Lees eerst
de vraag（先『讀』題目）」，題幹是畫面文字、沒念出聲，Whisper 無音可轉。

**決定**：根據選項＋原文忠實重建題幹，並在該題加「題幹重建」標籤公開揭示。

**替代方案**：
- 重新轉錄 → 沒用，題目本來就無聲，再轉也抓不到
- OCR 影片畫面取題幹 → 要下載影片、跑 OCR，scope 太大，留待網站階段
- 略過這些題 → 講義不完整，違背用戶「完整」要求

**狀態**：⚠️ 請用戶確認重建的 4 題（PART 2 考題 3/4/12/13）題幹用詞是否 OK

## 隔日 — 出處改成「問句＋答句」整段，不只答案那一句

**類型**：🛤 偏離 SPEC

**情境**：用戶看到範例「📍出處 0:43 Drie maanden」回饋：「很喜歡，但可以
儘量完整一點，應該也包含問他懷孕多久了那句」。

**決定**：`source` 從單行改成多行 list，收錄問答整段（如 0:38 問句 +
0:43 答句），每行各帶 timestamp。

**理由**：A2 聽力反推的關鍵常是「問句出現 → 下一句就是答案」。只給答案那
一句，學習者看不到觸發點。完整呈現問答對才教得會「怎麼聽」。

**狀態**：✅ 已自行決定（用戶明確要求）

## 23:57 — 兩版維持原本：講義版（完整） + 純荷文版

**類型**：🎯 設計決定

**情境**：升級後是否要保留「純文字稿+ZH」版？

**決定**：不保留。兩版 = 講義版（preview + tagged transcript + self-test + QR）/ 純荷文版（一樣排版但無 ZH、無 vocab 翻譯、自測題答案藏到最後）

**理由**：講義版就是「純文字稿+ZH」的超集；多一版只增加管理成本

**狀態**：⚠️ 用戶可能會想要回到「只有逐字稿、不要 preview/self-test」純粹版 → 看完成品再決定

## 00:08 — Chrome `virtual-time-budget` 8s → 15s

**類型**：🛤 偏離

**情境**：跑 make_pdfs.py 第一次 PDF 出不來；debug 顯示 Chrome 在 budget=8000 下不寫檔，提到 10000 就 OK。QR API 抓圖需要 5-10s

**決定**：把 budget 提到 15000、deadline 提到 120s、settle 1.5→2s

**理由**：QR 是外部 URL fetch，wall-clock 比 virtual time 久，給足時間比快印爛掉強

**狀態**：✅ 已自行決定

## 00:10 — detect_tag 改用 clause-split

**類型**：🎯 設計決定

**情境**：多句段（"Jafar komt te laat... Waarom komt hij te laat?"）整段 endswith `?` 為 False，漏抓 vraag。"Waar maakt u huiswerk? Vertel ook waarom." 也漏（複合句）

**決定**：用 `re.split(r'(?<=[.!?])\s+', t)` 拆每個 clause，找第一個結尾 `?` 的子句判斷

**理由**：A2 影片常一段含 vraag+vertel；clause-level 才能正確抓主問題

**狀態**：✅ 已自行決定

## 2026-05-25 — 模擬考三：用「自錄 MP4 的螢幕 OCR」取代 YouTube 來源

**類型**：🎯 設計決定

**情境**：用戶錄了自己做 OptimumAssessment 平台 mock 3 的螢幕，給的是 `~/Downloads/荷蘭文聽力模擬考三.mp4`（11 分鐘、64MB）。**沒有 YouTube 影片可抓**——但 MP4 同時含 (a) 聽力 audio 和 (b) 螢幕上的題幹／選項／正答 highlight。

**決定**：兩條 pipeline 並行：
1. `ffmpeg -vn` 抽 audio.mp3 → `transcribe.py`（Whisper nl + GPT 翻譯）→ data.json
2. `ffmpeg -vf fps=1/3` 抽 218 張 frame jpg → Claude `Read` 工具直接看圖辨識題幹／選項／正答／使用者選的錯答（紅 highlight）

兩邊資訊在 `make_exam.py` 中合併成 exam.json。

**理由**：用戶想要的不只是「轉錄成文本」——而是把「真實做題經驗」做成講義。錄影過程裡的「我選錯了什麼」是有教學價值的（V8 火車、V17 辦新卡、V21 half twaalf 三題在 exam.json 的 `trap` 欄都標了「⚠️ 這題我原本選了...」）。沒影片就用自己錄的，反而更個人化。

**狀態**：✅ 已自行決定

## 2026-05-25 — Mock 3 的 video_id 用 `mock3_a2_2026`（不是 YouTube ID）

**類型**：⚖️ 折衷

**情境**：既有 mock 1+2 的 video_id 是 YouTube ID（`_iC1Pooi2UA` / `AMVy2zPNLso`）。mock 3 沒 YT URL 怎麼命名？

**決定**：用語義化的 slug `mock3_a2_2026`。HAS_EXAM Set 增加這個 ID；hub 首頁 videos 陣列在最上面加一筆，channel 標「自製模擬考」。

**理由**：未來自製 mock 4+5+6 都會是 slug 命名。用 YT-style 隨機 ID 反而難維護。Capacitor + localStorage key 直接吃這個 slug 就行——無需特殊處理。

**狀態**：✅ 已自行決定

## 2026-05-25 — 5 題答案無法從畫面確認時，用「audio 推論 + reconstructed 標記」

**類型**：⚖️ 折衷

**情境**：218 frames 在 1/3 fps 間距下，用戶滑頁太快時某些 vraag 沒被截到完整。具體缺失：V12 的 question text（Johnny 試衣間第二題）、V24（Bioscoop 普通廳數）等。

**決定**：根據 audio transcript 上下文 + 標準 NT2 mock 題型推論題目，在 exam.json 的該題標 `reconstructed: True`（跟既有 PART 2 的「Lees eerst」題目相同處理）。前端／PDF 會顯示「橘色重建標」。

**理由**：刪掉這些題會讓 mock 不完整；用 OCR 抓影片畫面 scope 太大且只缺 5/25 題。reconstructed 標記公開揭示是「我推論的」，學習者可自行核對。

**狀態**：⚠️ 用戶可校對 5 個 reconstructed 題目（V12、V24 等）

## 2026-05-25 — frames/ + sheets/ 不入 git

**類型**：🎯 設計決定

**情境**：做題目辨識用的 218 個 frame jpg + 6 個 contact sheet 是 ephemeral 中間產物。

**決定**：在 `.gitignore` 加 `output/*/frames/` + `output/*/sheets/`。

**理由**：總共幾十 MB、純為 OCR 工作流而存在、未來不會被讀取。data.json + exam.json 已包含全部資訊。

**狀態**：✅ 已自行決定
