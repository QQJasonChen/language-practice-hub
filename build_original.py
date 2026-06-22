#!/usr/bin/env python3
"""PRODUCT B — 原創精華版 (clean, sellable).

Author-written original A2 dialogues (one per major scenario from the 場景圖鑑),
voiced with macOS `say -v Xander` (nl_NL) → mp3, written into the existing
exam.json pipeline so make_pdfs.py renders the handout PDFs for free.

Script = mine, voice = Apple TTS → no third-party content. Safe to sell.

Run:  python3 build_original.py          # TTS + build output/orig_NN/
then: python3 make_pdfs.py orig_01 ... orig_10
"""
import json, os, re, subprocess, shutil, pathlib, tempfile
ROOT = pathlib.Path(__file__).parent
OUT = ROOT / 'output'
VOICE = 'Xander'      # nl_NL
RATE = 168            # words/min — a touch slower for A2 clarity
PAUSE = 0.7           # seconds between lines

def mmss(s): return f"{int(s)//60}:{int(s)%60:02d}"

# ---- content: list of original mocks --------------------------------------
# each: theme, kind, title_zh, title_nl, context_zh,
#   dialogue: [[nl, zh], ...]
#   vocab:    [[nl, zh], ...]
#   patterns: [[nl, zh, note], ...]
#   questions:[ {q_nl,q_zh, opts:[[nl,zh],...], answer:idx, src:[line_idx...],
#                explain, trap} ]
MOCKS = [
 {"theme":"醫療・預約","kind":"電話對話","title_zh":"打電話跟家醫預約","title_nl":"Een afspraak bij de huisarts",
  "context_zh":"Anna 打電話到家醫診所預約，因為她頭痛又發燒。",
  "dialogue":[
   ["Huisartsenpraktijk De Linden, goedemorgen. Waarmee kan ik u helpen?","林登家醫診所，早安。請問需要什麼協助？"],
   ["Goedemorgen. Ik wil graag een afspraak maken. Ik heb al een paar dagen hoofdpijn en koorts.","早安。我想預約。我已經頭痛發燒好幾天了。"],
   ["Dat is vervelend. Kunt u vandaag om half drie komen?","真不舒服。您今天兩點半能來嗎？"],
   ["Half drie is lastig, want dan werk ik nog. Kan het ook later?","兩點半不方便，因為那時我還在上班。能晚一點嗎？"],
   ["Om kwart over vier is er ook plek.","四點十五分也有空檔。"],
   ["Ja, dat is goed.","好，那可以。"],
   ["Mag ik uw naam en geboortedatum?","可以給我您的名字和出生日期嗎？"],
   ["Ik ben Anna de Vries, twaalf maart negentienhonderdnegentig.","我是 Anna de Vries，1990 年 3 月 12 日。"],
   ["Dank u wel. Tot vanmiddag, mevrouw De Vries.","謝謝。下午見，de Vries 女士。"]],
  "vocab":[["een afspraak maken","預約"],["de hoofdpijn","頭痛"],["de koorts","發燒"],["vervelend","難受、麻煩"],
   ["lastig","不方便"],["de plek","空檔、位置"],["de geboortedatum","出生日期"],["de huisarts","家庭醫生"]],
  "patterns":[["Ik wil graag een afspraak maken.","我想預約。","wil + graag 表禮貌的「想要」，主要動詞 maken 放句尾。"],
   ["Kunt u vandaag om half drie komen?","您今天兩點半能來嗎？","疑問句助動詞 Kunt 放最前，主要動詞 komen 丟到句尾。"],
   ["Kan het ook later?","能晚一點嗎？","het 當抽象主詞「這件事」。"]],
  "questions":[
   {"q_nl":"Waarom belt Anna de huisartsenpraktijk?","q_zh":"Anna 為什麼打給家醫診所？",
    "opts":[["Om een afspraak af te zeggen.","為了取消預約。"],["Om een afspraak te maken.","為了預約。"],["Om de uitslag te vragen.","為了問檢查結果。"]],
    "answer":1,"src":[1],"explain":"她直說 “Ik wil graag een afspraak maken”，並說頭痛發燒——是要約看診。","trap":"afzeggen(取消)、uitslag(結果) 都沒出現，別被沒聽到的字嚇到。"},
   {"q_nl":"Hoe laat komt Anna naar de praktijk?","q_zh":"Anna 幾點到診所？",
    "opts":[["Om half drie.","兩點半。"],["Om kwart over vier.","四點十五。"],["Om kwart voor drie.","兩點四十五。"]],
    "answer":1,"src":[4,5],"explain":"兩點半她要上班 → 改成 kwart over vier，她回 “dat is goed”。","trap":"half drie 是她拒絕的時間，不是答案。"},
   {"q_nl":"Waarom kan Anna niet om half drie komen?","q_zh":"Anna 為什麼兩點半不能來？",
    "opts":[["Ze moet dan werken.","那時她要上班。"],["Ze ligt dan in bed.","那時她臥床。"],["Ze heeft dan een andere afspraak.","那時她有別的約。"]],
    "answer":0,"src":[3],"explain":"“want dan werk ik nog” = 因為那時我還在工作。","trap":"她生病沒錯，但「不能來」的原因是工作。"}]},

 {"theme":"工作・職場","kind":"電話對話","title_zh":"跟公司請病假","title_nl":"Je ziek melden op het werk",
  "context_zh":"Mark 打電話到公司請病假，因為他感冒喉嚨痛。",
  "dialogue":[
   ["Met de receptie van Bouwbedrijf Jansen.","顏森營造公司櫃台，您好。"],
   ["Hallo, met Mark Bakker. Ik bel om me ziek te melden. Ik ben verkouden en heb keelpijn.","您好，我是 Mark Bakker。我打來請病假。我感冒又喉嚨痛。"],
   ["Wat naar. Kun je vandaag echt niet komen?","真糟。你今天真的不能來嗎？"],
   ["Nee, ik blijf liever thuis. Morgen ga ik naar de dokter.","不行，我寧願待在家。明天我去看醫生。"],
   ["Goed. Zal ik het tegen je chef zeggen?","好。要我跟你主管說嗎？"],
   ["Ja, graag. En kan iemand mijn dienst van vanmiddag overnemen?","好，麻煩了。今天下午我的班有人能接嗎？"],
   ["Ik regel het. Beterschap, Mark.","我來安排。早日康復，Mark。"]],
  "vocab":[["zich ziek melden","請病假"],["verkouden","感冒的"],["de keelpijn","喉嚨痛"],["de dienst","班、值勤"],
   ["overnemen","接手"],["de chef","主管"],["beterschap","早日康復"],["liever","寧願"]],
  "patterns":[["Ik bel om me ziek te melden.","我打來請病假。","om … te + 原形 = 為了…；me 是反身代名詞。"],
   ["Zal ik het tegen je chef zeggen?","要我跟你主管說嗎？","Zal ik …? 用來提議幫忙。"],
   ["Kan iemand mijn dienst overnemen?","有人能接我的班嗎？","可分動詞 overnemen，原形整體放句尾。"]],
  "questions":[
   {"q_nl":"Waarom belt Mark naar zijn werk?","q_zh":"Mark 為什麼打給公司？",
    "opts":[["Hij komt later op het werk.","他會晚點到。"],["Hij is ziek en komt niet.","他生病不來。"],["Hij wil een dag vrij vragen.","他想請一天休假。"]],
    "answer":1,"src":[1,3],"explain":"“om me ziek te melden” + verkouden + keelpijn + 待在家。","trap":"vrij vragen 是休假，不是病假。"},
   {"q_nl":"Wat gaat Mark morgen doen?","q_zh":"Mark 明天要做什麼？",
    "opts":[["Naar de dokter gaan.","去看醫生。"],["Weer gaan werken.","回去上班。"],["Zijn chef bellen.","打給主管。"]],
    "answer":0,"src":[3],"explain":"“Morgen ga ik naar de dokter”。","trap":"主管是櫃台幫忙轉達，不是 Mark 明天打。"},
   {"q_nl":"Wat vraagt Mark aan de receptie?","q_zh":"Mark 拜託櫃台什麼？",
    "opts":[["Of zij de dokter belt.","她是否打給醫生。"],["Of iemand zijn dienst overneemt.","是否有人接他的班。"],["Of hij eerder naar huis mag.","他能否提早回家。"]],
    "answer":1,"src":[5],"explain":"“kan iemand mijn dienst van vanmiddag overnemen?”","trap":"沒提到要櫃台打給醫生。"}]},

 {"theme":"交通・出行","kind":"櫃台對話","title_zh":"車站：火車誤點","title_nl":"Op het station: de trein is vertraagd",
  "context_zh":"Sara 在車站詢問處問往 Utrecht 的火車。",
  "dialogue":[
   ["Goedemiddag, kan ik u helpen?","午安，需要幫忙嗎？"],
   ["Ja, ik wil naar Utrecht. Welk spoor is dat?","是的，我要去 Utrecht。在第幾月台？"],
   ["Normaal spoor vijf, maar de trein van tien over twee heeft vertraging.","平常是 5 號月台，但兩點十分那班誤點了。"],
   ["O nee. Hoeveel later vertrekt hij?","不會吧。會晚多久發車？"],
   ["Ongeveer twintig minuten. U kunt ook de bus nemen, die gaat zo.","大約 20 分鐘。您也可以搭巴士，馬上就開。"],
   ["Met de bus duurt het langer, denk ik. Ik wacht wel op de trein.","我想搭巴士比較久。我還是等火車好了。"],
   ["Prima. Houd dan spoor vijf in de gaten.","好的。那請留意 5 號月台。"]],
  "vocab":[["het spoor","月台、軌道"],["de vertraging","誤點"],["vertrekken","出發"],["ongeveer","大約"],
   ["de bus nemen","搭巴士"],["duren","持續、花時間"],["in de gaten houden","留意"],["zo","馬上"]],
  "patterns":[["Welk spoor is dat?","那是幾號月台？","Welk 接中性名詞 spoor。"],
   ["Hoeveel later vertrekt hij?","會晚多久發車？","hij 指 de trein。"],
   ["Ik wacht wel op de trein.","我還是等火車吧。","wachten op = 等候；wel 緩和語氣。"]],
  "questions":[
   {"q_nl":"Wat is er met de trein van tien over twee?","q_zh":"兩點十分那班火車怎麼了？",
    "opts":[["Hij is vertraagd.","誤點了。"],["Hij is al weg.","已經開走了。"],["Hij rijdt vandaag niet.","今天停駛。"]],
    "answer":0,"src":[2],"explain":"“heeft vertraging”。","trap":"不是停駛，只是晚點。"},
   {"q_nl":"Hoe gaat Sara naar Utrecht?","q_zh":"Sara 怎麼去 Utrecht？",
    "opts":[["Met de bus.","搭巴士。"],["Met de trein.","搭火車。"],["Met de taxi.","搭計程車。"]],
    "answer":1,"src":[5],"explain":"“Ik wacht wel op de trein”。","trap":"櫃台建議巴士，但她選擇等火車。"},
   {"q_nl":"Hoeveel later vertrekt de trein ongeveer?","q_zh":"火車大約晚多久？",
    "opts":[["Tien minuten.","十分鐘。"],["Twintig minuten.","二十分鐘。"],["Veertig minuten.","四十分鐘。"]],
    "answer":1,"src":[4],"explain":"“Ongeveer twintig minuten”。","trap":""}]},

 {"theme":"購物・商店","kind":"店內對話","title_zh":"在店裡換一件毛衣","title_nl":"Een trui ruilen in de winkel",
  "context_zh":"Tom 想換一件毛衣，因為太小了。",
  "dialogue":[
   ["Goedemiddag, kan ik u helpen?","午安，需要幫忙嗎？"],
   ["Ja, ik heb deze trui gekregen, maar hij is te klein. Kan ik hem ruilen?","我收到這件毛衣，但太小了。可以換嗎？"],
   ["Natuurlijk. Heeft u de bon bij u?","當然。您有帶收據嗎？"],
   ["Ja, hier. Ik wil graag een grotere maat.","有，在這。我想要大一號。"],
   ["Welke maat heeft u nodig?","您需要哪個尺碼？"],
   ["Medium, denk ik. De small is te strak.","我想是 M。S 太緊了。"],
   ["We hebben medium in het blauw en in het zwart.","我們 M 號有藍色和黑色。"],
   ["Doe maar de blauwe, die vind ik mooier.","那給我藍色的，我比較喜歡。"]],
  "vocab":[["de trui","毛衣"],["ruilen","換貨"],["de bon","收據"],["de maat","尺碼"],
   ["groter","較大的"],["te strak","太緊"],["krijgen","收到、得到"],["doe maar","就要…(口語)"]],
  "patterns":[["Kan ik hem ruilen?","我可以換嗎？","hem 指陽性名詞 de trui。"],
   ["Welke maat heeft u nodig?","您需要哪個尺碼？","nodig hebben = 需要。"],
   ["Doe maar de blauwe.","給我藍色那件。","購物/點餐常用 doe maar「就要…」。"]],
  "questions":[
   {"q_nl":"Waarom wil Tom de trui ruilen?","q_zh":"Tom 為什麼要換毛衣？",
    "opts":[["Hij is te klein.","太小。"],["Hij is kapot.","壞了。"],["De kleur is lelijk.","顏色醜。"]],
    "answer":0,"src":[1],"explain":"“hij is te klein”。","trap":"顏色是他後面才挑，不是換貨原因。"},
   {"q_nl":"Wat heeft Tom nodig om te ruilen?","q_zh":"Tom 換貨需要什麼？",
    "opts":[["Zijn paspoort.","護照。"],["De bon.","收據。"],["Niets.","不用。"]],
    "answer":1,"src":[2,3],"explain":"店員問 “Heeft u de bon?”，他說有。","trap":""},
   {"q_nl":"Welke trui kiest Tom?","q_zh":"Tom 選了哪件？",
    "opts":[["De zwarte medium.","黑色 M。"],["De blauwe medium.","藍色 M。"],["De blauwe small.","藍色 S。"]],
    "answer":1,"src":[5,7],"explain":"medium + “Doe maar de blauwe”。","trap":"small 太緊已被排除。"}]},

 {"theme":"餐飲・餐廳","kind":"電話對話","title_zh":"餐廳訂位","title_nl":"Een tafel reserveren",
  "context_zh":"Lisa 打電話到餐廳訂週六的位子。",
  "dialogue":[
   ["Restaurant De Tuin, goedenavond.","花園餐廳，晚安。"],
   ["Goedenavond. Ik wil graag een tafel reserveren voor zaterdag.","晚安。我想訂這週六的位子。"],
   ["Voor hoeveel personen?","幾位？"],
   ["Voor vier personen, om zeven uur.","四位，七點。"],
   ["Zeven uur is helaas vol. Acht uur kan wel.","七點很抱歉滿了。八點可以。"],
   ["Acht uur is ook prima.","八點也好。"],
   ["Op welke naam mag ik reserveren?","用什麼名字訂位？"],
   ["Op naam van Lisa Smit. En we zitten graag bij het raam.","用 Lisa Smit。我們想坐窗邊。"],
   ["Ik noteer het. Tot zaterdag!","我記下了。週六見！"]],
  "vocab":[["een tafel reserveren","訂位"],["voor hoeveel personen","幾位"],["helaas","很遺憾"],["vol","客滿"],
   ["bij het raam","窗邊"],["noteren","記下"],["op naam van","用…的名字"],["prima","很好"]],
  "patterns":[["Ik wil graag een tafel reserveren.","我想訂位。","reserveren 原形放句尾。"],
   ["Voor hoeveel personen?","幾位？","訂位固定問法。"],
   ["We zitten graag bij het raam.","我們想坐窗邊。","graag 表偏好。"]],
  "questions":[
   {"q_nl":"Voor wanneer wil Lisa reserveren?","q_zh":"Lisa 想訂哪天？",
    "opts":[["Voor vrijdag.","週五。"],["Voor zaterdag.","週六。"],["Voor zondag.","週日。"]],
    "answer":1,"src":[1],"explain":"“voor zaterdag”。","trap":""},
   {"q_nl":"Hoe laat krijgt Lisa een tafel?","q_zh":"Lisa 訂到幾點？",
    "opts":[["Om zeven uur.","七點。"],["Om acht uur.","八點。"],["Om negen uur.","九點。"]],
    "answer":1,"src":[4,5],"explain":"七點客滿 → 八點 → “ook prima”。","trap":"七點是原本想要但客滿。"},
   {"q_nl":"Wat vraagt Lisa nog extra?","q_zh":"Lisa 還多要求什麼？",
    "opts":[["Een tafel bij het raam.","窗邊的桌子。"],["Een kinderstoel.","兒童椅。"],["Het menu.","菜單。"]],
    "answer":0,"src":[7],"explain":"“we zitten graag bij het raam”。","trap":""}]},

 {"theme":"市政府・登記","kind":"櫃台對話","title_zh":"市政府辦遷入登記","title_nl":"Bij de gemeente: verhuizing doorgeven",
  "context_zh":"Ahmed 到市政府登記新地址（搬家）。",
  "dialogue":[
   ["Goedemorgen, waarvoor komt u?","早安，您來辦什麼？"],
   ["Ik ben verhuisd en wil mijn nieuwe adres doorgeven.","我搬家了，想登記新地址。"],
   ["Heeft u een afspraak gemaakt?","您有預約嗎？"],
   ["Nee, dat wist ik niet.","沒有，我不知道要預約。"],
   ["Geen probleem, het is rustig. Heeft u uw identiteitsbewijs bij u?","沒關係，現在不忙。您帶證件了嗎？"],
   ["Ja, mijn paspoort. En hier is mijn huurcontract.","帶了，我的護照。這是我的租約。"],
   ["Prima. Vanaf welke datum woont u er?","好。您從哪天開始住那裡？"],
   ["Vanaf één juni.","從 6 月 1 日。"],
   ["Ik verwerk het meteen. U krijgt een bevestiging per post.","我馬上處理。您會收到郵寄確認信。"]],
  "vocab":[["verhuizen","搬家"],["het adres doorgeven","登記地址"],["de afspraak","預約"],["het identiteitsbewijs","身分證件"],
   ["het paspoort","護照"],["het huurcontract","租約"],["de bevestiging","確認"],["per post","郵寄"]],
  "patterns":[["Ik wil mijn nieuwe adres doorgeven.","我想登記新地址。","可分動詞 doorgeven，原形整體放句尾。"],
   ["Heeft u uw identiteitsbewijs bij u?","您帶證件了嗎？","bij u = 隨身帶著。"],
   ["Vanaf welke datum woont u er?","從哪天起住那？","vanaf = 從…起；er 指那地方。"]],
  "questions":[
   {"q_nl":"Waarvoor komt Ahmed naar de gemeente?","q_zh":"Ahmed 來市政府辦什麼？",
    "opts":[["Om een paspoort aan te vragen.","申請護照。"],["Om zijn verhuizing door te geven.","登記搬家。"],["Om te trouwen.","結婚登記。"]],
    "answer":1,"src":[1],"explain":"“verhuisd … nieuwe adres doorgeven”。","trap":"他出示護照不代表是來辦護照。"},
   {"q_nl":"Wat is het probleem aan het begin?","q_zh":"一開始有什麼問題？",
    "opts":[["Ahmed heeft geen afspraak.","沒預約。"],["Ahmed heeft geen paspoort.","沒護照。"],["De gemeente is gesloten.","關門了。"]],
    "answer":0,"src":[2,4],"explain":"問有沒有預約，他說沒有；但因 rustig 不成問題。","trap":"他有護照；也沒關門。"},
   {"q_nl":"Hoe krijgt Ahmed de bevestiging?","q_zh":"Ahmed 怎麼收到確認？",
    "opts":[["Per e-mail.","email。"],["Per post.","郵寄。"],["Per telefoon.","電話。"]],
    "answer":1,"src":[8],"explain":"“een bevestiging per post”。","trap":""}]},

 {"theme":"學校・課程","kind":"電話對話","title_zh":"報名語言課程","title_nl":"Je inschrijven voor een cursus",
  "context_zh":"Fatima 打電話報名荷蘭文課程。",
  "dialogue":[
   ["Taalschool Centraal, goedemiddag.","中央語言學校，午安。"],
   ["Hallo, ik wil me inschrijven voor de cursus Nederlands.","您好，我想報名荷蘭文課。"],
   ["Welk niveau zoekt u, A1 of A2?","您要哪個級別，A1 還是 A2？"],
   ["A2. Ik heb A1 vorig jaar gehaald.","A2。我去年通過了 A1。"],
   ["Mooi. De lessen zijn op dinsdag- en donderdagavond.","很好。課在週二和週四晚上。"],
   ["Donderdag is moeilijk voor mij. Is er ook een andere groep?","週四對我有點難。有別的班嗎？"],
   ["Er is ook een groep op zaterdagochtend.","也有週六早上的班。"],
   ["Dat is perfect. Wat kost de cursus?","太好了。課程多少錢？"],
   ["Tweehonderd euro voor tien weken.","十週兩百歐元。"]],
  "vocab":[["zich inschrijven","報名"],["de cursus","課程"],["het niveau","級別"],["halen","通過(考試)"],
   ["de les","課"],["de groep","班級"],["de ochtend","早上"],["kosten","花費"]],
  "patterns":[["Ik wil me inschrijven voor de cursus.","我想報名課程。","zich inschrijven voor = 報名…。"],
   ["Welk niveau zoekt u?","您找哪個級別？","Welk + 中性名詞 niveau。"],
   ["Wat kost de cursus?","課程多少錢？","Wat kost …? 問價格。"]],
  "questions":[
   {"q_nl":"Welk niveau wil Fatima volgen?","q_zh":"Fatima 想上哪個級別？",
    "opts":[["A1.","A1。"],["A2.","A2。"],["B1.","B1。"]],
    "answer":1,"src":[3],"explain":"“A2. Ik heb A1 … gehaald”。","trap":"A1 是她已通過的。"},
   {"q_nl":"Wanneer gaat Fatima naar de les?","q_zh":"Fatima 哪時上課？",
    "opts":[["Dinsdagavond.","週二晚上。"],["Donderdagavond.","週四晚上。"],["Zaterdagochtend.","週六早上。"]],
    "answer":2,"src":[5,6],"explain":"週四對她難 → 改週六早上 “perfect”。","trap":"週二/週四是原本的班。"},
   {"q_nl":"Wat kost de cursus?","q_zh":"課程多少錢？",
    "opts":[["Honderd euro.","一百歐元。"],["Tweehonderd euro.","兩百歐元。"],["Driehonderd euro.","三百歐元。"]],
    "answer":1,"src":[8],"explain":"“Tweehonderd euro voor tien weken”。","trap":""}]},

 {"theme":"住房・居住","kind":"電話對話","title_zh":"暖氣壞了打給房東","title_nl":"De verwarming is kapot",
  "context_zh":"Nour 打電話給房東，因為暖氣壞了。",
  "dialogue":[
   ["Met Pietersen Verhuur.","彼得森租屋，您好。"],
   ["Goedemiddag, met Nour uit de Bloemstraat twaalf. Mijn verwarming doet het niet.","午安，我是花街 12 號的 Nour。我的暖氣不能動。"],
   ["Sinds wanneer is dat?","從什麼時候開始的？"],
   ["Sinds gisteren. Het is nu echt koud in huis.","從昨天。家裡現在真的很冷。"],
   ["Ik stuur morgenochtend een monteur. Bent u dan thuis?","我明天早上派維修工。您那時在家嗎？"],
   ["Ja, tot twaalf uur ben ik thuis.","在，我十二點前都在家。"],
   ["Goed, hij komt rond tien uur.","好，他大約十點到。"],
   ["Dank u. Kunt u hem mijn telefoonnummer geven?","謝謝。可以把我電話給他嗎？"],
   ["Doe ik. Tot morgen.","沒問題。明天見。"]],
  "vocab":[["de verwarming","暖氣"],["kapot","壞掉"],["het doet het niet","壞了、不動了"],["sinds","自從"],
   ["de monteur","維修工"],["thuis","在家"],["rond","大約(時間)"],["het telefoonnummer","電話號碼"]],
  "patterns":[["Mijn verwarming doet het niet.","我的暖氣壞了。","“het doet het niet” = 機器不動了的固定說法。"],
   ["Sinds wanneer is dat?","從什麼時候開始？","sinds = 自從。"],
   ["Bent u dan thuis?","您那時在家嗎？","dan 指前面提到的時間。"]],
  "questions":[
   {"q_nl":"Waarom belt Nour de verhuurder?","q_zh":"Nour 為什麼打給房東？",
    "opts":[["De verwarming is kapot.","暖氣壞了。"],["De huur is te hoog.","房租太高。"],["De buren maken lawaai.","鄰居很吵。"]],
    "answer":0,"src":[1],"explain":"“verwarming doet het niet”。","trap":""},
   {"q_nl":"Wanneer komt de monteur?","q_zh":"維修工什麼時候來？",
    "opts":[["Vandaag.","今天。"],["Morgenochtend.","明天早上。"],["Volgende week.","下週。"]],
    "answer":1,"src":[4,6],"explain":"“morgenochtend … rond tien uur”。","trap":""},
   {"q_nl":"Wat vraagt Nour aan het eind?","q_zh":"Nour 最後拜託什麼？",
    "opts":[["Een nieuwe verwarming.","一台新暖氣。"],["Haar telefoonnummer doorgeven.","把她電話轉給維修工。"],["Korting op de huur.","房租打折。"]],
    "answer":1,"src":[7],"explain":"“Kunt u hem mijn telefoonnummer geven?”","trap":""}]},

 {"theme":"銀行・金錢","kind":"電話對話","title_zh":"金融卡不見了打給銀行","title_nl":"Mijn pinpas is kwijt",
  "context_zh":"Daan 打電話給銀行，因為金融卡不見了。",
  "dialogue":[
   ["Goedemorgen, met de bank. Waarmee kan ik u helpen?","早安，銀行您好。需要什麼協助？"],
   ["Ik ben mijn pinpas kwijt. Kunt u hem blokkeren?","我的金融卡不見了。可以幫我停卡嗎？"],
   ["Ja, dat doe ik meteen. Mag ik uw rekeningnummer?","好，我馬上處理。可以給我帳號嗎？"],
   ["Ja, het staat op mijn telefoon, momentje.","好，在我手機上，稍等。"],
   ["De pas is nu geblokkeerd. Wilt u een nieuwe?","卡片已停用。您要新卡嗎？"],
   ["Graag. Hoelang duurt dat?","好的。要多久？"],
   ["Ongeveer vijf werkdagen. Hij komt per post.","大約五個工作天。會郵寄到。"],
   ["Prima, dank u wel.","好，謝謝您。"]],
  "vocab":[["de pinpas","金融卡"],["kwijt zijn","弄丟"],["blokkeren","停卡、凍結"],["het rekeningnummer","帳號"],
   ["geblokkeerd","已停用"],["een nieuwe","一張新的"],["de werkdag","工作天"],["per post","郵寄"]],
  "patterns":[["Ik ben mijn pinpas kwijt.","我的卡不見了。","kwijt zijn = 遺失，固定搭配。"],
   ["Kunt u hem blokkeren?","能幫我停卡嗎？","hem 指 de pinpas。"],
   ["Hoelang duurt dat?","要多久？","問所需時間。"]],
  "questions":[
   {"q_nl":"Waarom belt Daan de bank?","q_zh":"Daan 為什麼打給銀行？",
    "opts":[["Hij wil geld lenen.","想借錢。"],["Zijn pinpas is kwijt.","卡不見了。"],["Hij wil een rekening openen.","想開戶。"]],
    "answer":1,"src":[1],"explain":"“mijn pinpas kwijt … blokkeren”。","trap":""},
   {"q_nl":"Wat doet de medewerker eerst?","q_zh":"行員先做什麼？",
    "opts":[["De pas blokkeren.","停卡。"],["Geld overmaken.","轉帳。"],["Een afspraak maken.","預約。"]],
    "answer":0,"src":[2,4],"explain":"馬上 blokkeren → “nu geblokkeerd”。","trap":""},
   {"q_nl":"Hoe krijgt Daan de nieuwe pas?","q_zh":"Daan 怎麼拿到新卡？",
    "opts":[["Hij haalt hem op.","自己去拿。"],["Per post.","郵寄。"],["Via e-mail.","email。"]],
    "answer":1,"src":[6],"explain":"“Hij komt per post”。","trap":"email 不能寄實體卡。"}]},

 {"theme":"休閒・活動","kind":"櫃台對話","title_zh":"報名健身房","title_nl":"Je aanmelden bij de sportschool",
  "context_zh":"Eva 想加入健身房會員。",
  "dialogue":[
   ["Hoi, welkom bij FitPlus. Kan ik je helpen?","嗨，歡迎來到 FitPlus。需要幫忙嗎？"],
   ["Ja, ik wil graag lid worden. Wat kost een abonnement?","是的，我想加入會員。會員多少錢？"],
   ["Dertig euro per maand. Daarmee kun je elke dag sporten.","每月三十歐元，可以每天來運動。"],
   ["Zijn er ook lessen, zoals yoga?","也有課嗎，像瑜珈？"],
   ["Ja, yoga is op maandag en woensdag. Die zit bij het abonnement.","有，瑜珈在週一和週三，包含在會員裡。"],
   ["Mooi. Kan ik vandaag al beginnen?","太好了。我今天就能開始嗎？"],
   ["Zeker. Neem je een handdoek en sportschoenen mee?","當然。你有帶毛巾和運動鞋嗎？"],
   ["Schoenen heb ik bij me, een handdoek niet.","鞋子有帶，毛巾沒有。"],
   ["Geen zorgen, die kun je hier huren.","別擔心，這裡可以租。"]],
  "vocab":[["lid worden","入會"],["het abonnement","會員、月票"],["per maand","每月"],["sporten","運動"],
   ["de les","課程"],["bij iets zitten","包含在內"],["de handdoek","毛巾"],["de sportschoenen","運動鞋"]],
  "patterns":[["Ik wil graag lid worden.","我想入會。","lid worden = 成為會員。"],
   ["Wat kost een abonnement?","會員多少錢？","Wat kost …? 問價格。"],
   ["Kan ik vandaag al beginnen?","我今天就能開始嗎？","al = 就/已經，強調早。"]],
  "questions":[
   {"q_nl":"Wat kost het abonnement?","q_zh":"會員多少錢？",
    "opts":[["Dertien euro per maand.","每月十三歐元。"],["Dertig euro per maand.","每月三十歐元。"],["Veertig euro per maand.","每月四十歐元。"]],
    "answer":1,"src":[2],"explain":"“Dertig euro per maand”。","trap":"dertien(13) 和 dertig(30) 發音很像，注意聽 -tien / -tig。"},
   {"q_nl":"Wanneer is er yoga?","q_zh":"瑜珈在哪幾天？",
    "opts":[["Maandag en woensdag.","週一和週三。"],["Dinsdag en donderdag.","週二和週四。"],["In het weekend.","週末。"]],
    "answer":0,"src":[4],"explain":"“yoga is op maandag en woensdag”。","trap":""},
   {"q_nl":"Wat heeft Eva niet bij zich?","q_zh":"Eva 沒帶什麼？",
    "opts":[["Sportschoenen.","運動鞋。"],["Een handdoek.","毛巾。"],["Geld.","錢。"]],
    "answer":1,"src":[7],"explain":"“Schoenen heb ik bij me, een handdoek niet”。","trap":"鞋子有帶。"}]},
]

# ---- TTS + assembly --------------------------------------------------------
def tts_line(text, wav_path):
    aiff = wav_path.with_suffix('.aiff')
    subprocess.run(['say','-v',VOICE,'-r',str(RATE),'-o',str(aiff),text],check=True)
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(aiff),
                    '-ar','22050','-ac','1',str(wav_path)],check=True)
    aiff.unlink()
    dur=float(subprocess.run(['ffprobe','-i',str(wav_path),'-show_entries','format=duration',
                    '-v','quiet','-of','csv=p=0'],capture_output=True,text=True).stdout.strip())
    return dur

def build_mock(idx, m, tmp):
    vid=f'orig_{idx:02d}'
    d=OUT/vid; d.mkdir(parents=True,exist_ok=True)
    # silence clip
    sil=tmp/'sil.wav'
    if not sil.exists():
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','lavfi',
            '-i','anullsrc=r=22050:cl=mono','-t',str(PAUSE),str(sil)],check=True)
    wavs=[]; times=[]; t=0.0
    for li,(nl,zh) in enumerate(m['dialogue']):
        w=tmp/f'{vid}_{li}.wav'; dur=tts_line(nl,w)
        times.append(t); wavs.append(w); t+=dur+PAUSE
    total=t
    # concat
    listf=tmp/f'{vid}.txt'
    with open(listf,'w') as f:
        for i,w in enumerate(wavs):
            f.write(f"file '{w}'\n")
            if i<len(wavs)-1: f.write(f"file '{sil}'\n")
    joined=tmp/f'{vid}_join.wav'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0',
        '-i',str(listf),'-c','copy',str(joined)],check=True)
    mp3=d/f'{idx:02d} {m["title_nl"]}.mp3'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(joined),
        '-b:a','96k',str(mp3)],check=True)
    # build exam.json
    dialogue=[{'t':mmss(times[i]),'nl':nl,'zh':zh} for i,(nl,zh) in enumerate(m['dialogue'])]
    questions=[]
    for qi,q in enumerate(m['questions'],1):
        src=[{'t':dialogue[s]['t'],'nl':dialogue[s]['nl'],'zh':dialogue[s]['zh']} for s in q['src']]
        questions.append({'n':qi,'t':src[0]['t'] if src else '0:00',
            'q_nl':q['q_nl'],'q_zh':q['q_zh'],
            'options':[{'nl':o[0],'zh':o[1]} for o in q['opts']],
            'answer':q['answer'],'source':src,'explain':q['explain'],
            **({'trap':q['trap']} if q.get('trap') else {})})
    scenario={'n':1,'title_zh':m['title_zh'],'title_nl':m['title_nl'],'kind':m['kind'],
        'context_zh':m['context_zh'],'start':'0:00',
        'dialogue':dialogue,
        'vocab':[{'nl':v[0],'zh':v[1]} for v in m['vocab']],
        'patterns':[{'nl':p[0],'zh':p[1],'note':p[2]} for p in m['patterns']],
        'questions':questions}
    exam={'video_id':vid,'title':f'原創模擬 {idx:02d}：{m["title_zh"]}（{m["theme"]}）',
        'channel':'原創 · 可商用 A2 模擬','duration':int(total),
        'exam_type':'A2 Luisteren 原創模擬','intro':m['context_zh'],
        'n_questions':len(questions),'scenarios':[scenario]}
    (d/'exam.json').write_text(json.dumps(exam,ensure_ascii=False,indent=1),encoding='utf-8')
    return vid,mp3.name,total

def main():
    with tempfile.TemporaryDirectory() as td:
        tmp=pathlib.Path(td); ids=[]
        for i,m in enumerate(MOCKS,1):
            vid,mp3,dur=build_mock(i,m,tmp)
            ids.append(vid)
            print(f'  ✓ {vid}  {m["theme"]:6} {mmss(dur)}  → {mp3}')
    print(f'\n✓ {len(ids)} original mocks built: {" ".join(ids)}')
    print('next: python3 make_pdfs.py '+' '.join(ids))

if __name__=='__main__':
    main()
