// ===== Theme Toggle (라이트/다크/시스템) =====
const modeBtn = document.getElementById('modeToggle');
const THEME_KEY = 'theme';

function applyTheme(t){
  document.body.classList.remove('light','dark');
  if (t === 'light'){ document.body.classList.add('light'); }
  else if (t === 'dark'){ document.body.classList.add('dark'); }
  // system이면 클래스 없음 => prefers-color-scheme 따름
  document.documentElement.style.colorScheme = (t==='light')?'light':(t==='dark')?'dark':'light dark';
}

(function initTheme(){
  const saved = localStorage.getItem(THEME_KEY) || 'system';
  applyTheme(saved);
})();
modeBtn?.addEventListener('click', () => {
  const curr = localStorage.getItem(THEME_KEY) || 'system';
  const next = curr === 'system' ? 'dark' : curr === 'dark' ? 'light' : 'system';
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
});

// ===== Snapshot Rendering Helpers =====
function setDial(el, pct, from='#7C4DFF', to='#00D4FF'){
  const clamped = Math.max(0, Math.min(1, pct || 0));
  const deg = clamped * 360;
  el.style.background = `
    radial-gradient(circle at 50% 50%, var(--ring-bg) 44%, transparent 45%),
    conic-gradient(${from} 0deg, ${to} ${deg}deg, var(--ring-track) ${deg}deg)
  `;
}
function pct(v){ return (v==null||isNaN(v)) ? '—' : (v*100).toFixed(1)+'%'; }
function signedPct(v){
  if(v==null||isNaN(v)) return '—';
  const p=(v*100).toFixed(1)+'%'; return (v>=0?'↑ ':'')+p;
}
function setKPI(s){
  // values
  document.getElementById('val-r2').textContent = s.r2 ?? '—';
  document.getElementById('val-signal').textContent = signedPct(s.signal_strength);
  document.getElementById('val-var').textContent = pct(s.var_pct);
  document.getElementById('val-pos').textContent = s.position ?? '—';
  document.getElementById('val-dd').textContent = (typeof s.max_drawdown_pct==='number') ? (s.max_drawdown_pct*100).toFixed(1)+'%' : '—';
  document.getElementById('val-upd').textContent = s.updated_at ?? '—';

  // rings (시각화 비율은 전시용 감성에 맞춘 가중)
  setDial(document.getElementById('dial-r2'), Math.min(1, (s.r2||0)/1));
  setDial(document.getElementById('dial-signal'), Math.abs(s.signal_strength||0));
  setDial(document.getElementById('dial-var'), (s.var_pct||0)*4); // VaR 가시성 강조
  setDial(document.getElementById('dial-pos'), 0.6);
  setDial(document.getElementById('dial-dd'), Math.abs(s.max_drawdown_pct||0));
  setDial(document.getElementById('dial-upd'), .75);

  // ticker
  document.getElementById('tk-r2').textContent = s.r2 ?? '—';
  document.getElementById('tk-signal').textContent = signedPct(s.signal_strength);
  document.getElementById('tk-var').textContent = pct(s.var_pct);
  document.getElementById('tk-dd').textContent = (typeof s.max_drawdown_pct==='number') ? (s.max_drawdown_pct*100).toFixed(1)+'%' : '—';
  document.getElementById('tk-upd').textContent = s.updated_at ?? '—';
}

// ===== Data Sources: WebSocket 우선 + 폴백(Polling) =====
const WS_PATH = '/ws/snapshot';
const REST_PATH = '/api/snapshot';
let ws;
let pollTimer = null;

async function fetchSnapshot(){
  const r = await fetch(REST_PATH, { cache:'no-store' });
  if(!r.ok) throw new Error('bad status');
  return await r.json();
}

function startPolling(intervalMs=15000){
  // 즉시 1회 요청
  fetchSnapshot().then(setKPI).catch(console.warn);
  // 주기 폴링
  clearInterval(pollTimer);
  pollTimer = setInterval(async ()=>{
    try{
      const s = await fetchSnapshot();
      setKPI(s);
    }catch(e){
      console.warn('poll failed', e);
    }
  }, intervalMs);
}

function startWebSocket(){
  try{
    const scheme = (location.protocol === 'https:') ? 'wss' : 'ws';
    ws = new WebSocket(`${scheme}://${location.host}${WS_PATH}`);
    ws.onopen = () => {
      // 웹소켓 연결되면 폴링 중지
      if(pollTimer) { clearInterval(pollTimer); pollTimer = null; }
      console.log('WS connected');
    };
    ws.onmessage = (e) => {
      try { setKPI(JSON.parse(e.data)); }
      catch(err){ console.warn('bad WS data', err); }
    };
    ws.onerror = () => {
      console.warn('WS error — fallback to polling');
      ws.close();
    };
    ws.onclose = () => {
      // 닫히면 폴백
      if(!pollTimer) startPolling(15000);
      // 재시도 (전시 환경 대비, 과도하지 않게 10초 후)
      setTimeout(startWebSocket, 10000);
    };
  }catch(e){
    console.warn('WS init failed — use polling', e);
    startPolling(15000);
  }
}

// 초기 부트스트랩: WS 시도 → 실패 시 폴링
startWebSocket();
