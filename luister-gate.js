/* 聽力播放器存取碼閘門（客戶端）。接受 LUIS-* 與 ALL-* 碼。 */
(function(){
  var KEY='lph_access_code';
  var VALID=new Set([
    "4963cd8dbd6c15d5b2ac35072f23a1c33a269e81da84f078b6158025480469e6",
    "1c00fe02f5433b98e1958eeb315854d7862b614e37ef61bf2d22843eed444560",
    "f8db24ac7548e09cbf8a1b0a50f05fedaed9b9a9996c4fb55d44f1139008b98e",
    "34732a734d76ab370e1d07611e5919c22a129910d111c6487667ac47510ec545",
    "a23e38a4826957db1f9c2b7a061f09f47032f08df388ba91e74748c602caaa40",
    "45c53cf0e8a1324e29f3f407617df6722160b487fbb116e84f5aea0d22d12a8e"
  ]);
  async function sha256(s){var b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(String(s).trim().toUpperCase()));return Array.from(new Uint8Array(b)).map(function(x){return x.toString(16).padStart(2,'0');}).join('');}
  async function ok(c){try{return c&&VALID.has(await sha256(c));}catch(e){return false;}}
  function gate(){
    var d=document.createElement('div');d.id='lph-gate';
    d.innerHTML='<style>#lph-gate{position:fixed;inset:0;z-index:2147483647;background:#050510;color:#f2f2f7;display:flex;align-items:center;justify-content:center;padding:24px;font-family:-apple-system,"Noto Sans TC",sans-serif}#lph-gate .b{width:100%;max-width:360px;text-align:center}#lph-gate h2{font-size:20px;font-weight:900;margin:10px 0 8px}#lph-gate p{font-size:13px;color:#a0a0b8;line-height:1.7;margin-bottom:16px}#lph-gate input{width:100%;padding:13px;border-radius:11px;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.06);color:#f2f2f7;font-size:16px;text-align:center;text-transform:uppercase;letter-spacing:1px;outline:none}#lph-gate button{width:100%;margin-top:10px;padding:13px;border-radius:11px;border:none;cursor:pointer;background:linear-gradient(135deg,#fb923c,#f87171);color:#fff;font-size:15px;font-weight:800}#lph-gate .e{color:#f87171;font-size:12px;margin-top:8px;min-height:15px;font-weight:700}#lph-gate a{color:#5eead4;text-decoration:none}</style><div class="b"><div style="font-size:42px">🔒</div><h2>句句聽力播放器</h2><p>這是付費產品。輸入購買後 email 收到的存取碼，即可解鎖全部聽力模擬考。</p><input id="lph-i" placeholder="LUIS-XXXXXX" autocomplete="off"><button id="lph-go">解鎖</button><div class="e" id="lph-e"></div><p style="margin-top:14px">還沒有碼？<a href="../../aanbod.html">看方案 →</a></p></div>';
    (document.body||document.documentElement).appendChild(d);
    var i=d.querySelector('#lph-i');i.focus();
    async function go(){if(await ok(i.value)){localStorage.setItem(KEY,i.value.trim().toUpperCase());d.remove();}else{d.querySelector('#lph-e').textContent='存取碼無效';i.select();}}
    d.querySelector('#lph-go').onclick=go;i.addEventListener('keydown',function(e){if(e.key==='Enter')go();});
  }
  async function init(){var s=localStorage.getItem(KEY);if(s&&await ok(s))return;if(document.body)gate();else document.addEventListener('DOMContentLoaded',gate);}
  init();
})();