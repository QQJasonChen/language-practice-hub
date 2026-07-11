/* 存取碼閘門（客戶端，casual-proof）。
   進站需輸入購買後 email 收到的存取碼；驗證用 SHA-256 hash，明碼不進前端。
   注意：靜態站無法真正鎖死原始檔，這只擋一般使用者；付費王牌 AI 批改另有後端真鎖。 */
(function () {
  var KEY = 'lph_access_code';
  var VALID = new Set([
    "d46b8116e5793f930cdec241405dfeec78a341b84b23b0b37e63b94e99c67cb7",
    "f48281ffc94b652ed722fe41cfd4438a3f7b737a2427666af988404a6aae81e2",
    "7f8d7a4e38218160ee54cec127a85fcebeb991f239e52c51328ac25f6ff754fd"
  ]);
  async function sha256(s) {
    var buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(String(s).trim().toUpperCase()));
    return Array.from(new Uint8Array(buf)).map(function (x) { return x.toString(16).padStart(2, '0'); }).join('');
  }
  async function valid(code) { try { return code && VALID.has(await sha256(code)); } catch (e) { return false; } }

  function showGate() {
    var d = document.createElement('div');
    d.id = 'lph-gate';
    d.innerHTML =
      '<style>' +
      '#lph-gate{position:fixed;inset:0;z-index:2147483647;background:#050510;color:#f2f2f7;' +
      'display:flex;align-items:center;justify-content:center;padding:24px;' +
      'font-family:-apple-system,"Noto Sans TC",system-ui,sans-serif}' +
      '#lph-gate .gb{width:100%;max-width:360px;text-align:center}' +
      '#lph-gate .lk{font-size:44px;margin-bottom:12px}' +
      '#lph-gate h2{font-size:20px;font-weight:900;margin-bottom:8px}' +
      '#lph-gate p{font-size:13px;color:#a0a0b8;line-height:1.7;margin-bottom:18px}' +
      '#lph-gate input{width:100%;padding:14px;border-radius:12px;border:1px solid rgba(255,255,255,.15);' +
      'background:rgba(255,255,255,.06);color:#f2f2f7;font-size:16px;text-align:center;letter-spacing:1px;' +
      'text-transform:uppercase;outline:none}' +
      '#lph-gate button{width:100%;margin-top:10px;padding:14px;border-radius:12px;border:none;cursor:pointer;' +
      'background:linear-gradient(135deg,#fb923c,#f87171);color:#fff;font-size:15px;font-weight:800}' +
      '#lph-gate .err{color:#f87171;font-size:12.5px;margin-top:10px;min-height:16px;font-weight:700}' +
      '#lph-gate a{color:#5eead4;text-decoration:none}' +
      '</style>' +
      '<div class="gb"><div class="lk">🔒</div>' +
      '<h2>輸入存取碼</h2>' +
      '<p>這是付費學習資源。<br>購買後你的 email 會收到一組存取碼，輸入一次即可全站解鎖。</p>' +
      '<input id="lph-gate-in" placeholder="ECHO-XXXXXX" autocomplete="off" autocapitalize="characters">' +
      '<button id="lph-gate-go">解鎖</button>' +
      '<div class="err" id="lph-gate-err"></div>' +
      '<p style="margin-top:16px">還沒有碼？<a href="unlock/all.html">看方案 →</a></p></div>';
    (document.body || document.documentElement).appendChild(d);
    var inp = d.querySelector('#lph-gate-in');
    var err = d.querySelector('#lph-gate-err');
    inp.focus();
    async function submit() {
      var v = inp.value;
      if (await valid(v)) {
        localStorage.setItem(KEY, String(v).trim().toUpperCase());
        d.remove();
      } else {
        err.textContent = '存取碼無效，請確認購買後收到的碼';
        inp.select();
      }
    }
    d.querySelector('#lph-gate-go').addEventListener('click', submit);
    inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') submit(); });
  }

  async function init() {
    var stored = localStorage.getItem(KEY);
    if (stored && await valid(stored)) return; // 已解鎖
    if (document.body) showGate();
    else document.addEventListener('DOMContentLoaded', showGate);
  }
  init();
})();
