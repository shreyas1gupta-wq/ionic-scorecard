/* FnO Replay Game frontend. Blinded: times are fake-anchored, HH:MM only. */
const $ = id => document.getElementById(id);
const LWC = LightweightCharts;
const FAKE = t => t; // times already fake-anchored server-side
let S = null;             // latest snapshot
let bars = [];            // released 1-min spot bars (sim day only)
let tf = 1;               // active timeframe (minutes)
let markHist = {};        // position premium history {posKey: [{time,value}]}
let selPos = null;        // selected position key for bottom chart
let lastChain = null;     // last /api/chain payload (for sizing calc + ATM)
const ind = { vwap: true, ema: true, rsi: true, cpr: false, or15: true };   // indicator toggles
const allBars = () => ((S && S.d1) || []).concat(bars);  // D-1 + sim day, one continuous series
let autoFit = true; // keep complete D-1 + sim day in view; user zoom/pan takes over until next session
for (const ev of ['wheel', 'pointerdown']) $('chart').addEventListener(ev, () => { autoFit = false; }, { passive: true });

/* ---------- charts ---------- */
const chartOpts = {
  layout: { background: { color: '#131722' }, textColor: '#d1d4dc' },
  grid: { vertLines: { color: '#1e222d' }, horzLines: { color: '#1e222d' } },
  timeScale: { timeVisible: true, secondsVisible: false },
  crosshair: { mode: 0 },
};
const chart = LWC.createChart($('chart'), chartOpts);
const candles = chart.addCandlestickSeries({ upColor: '#26a69a', downColor: '#ef5350', wickUpColor: '#26a69a', wickDownColor: '#ef5350', borderVisible: false });
const lineOpts = { lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false };
const vwapS = chart.addLineSeries({ color: '#64b5f6', ...lineOpts });
const e9S = chart.addLineSeries({ color: '#ffd54f', ...lineOpts });
const e21S = chart.addLineSeries({ color: '#f06292', ...lineOpts });
const rsiS = chart.addLineSeries({ color: '#ba68c8', priceScaleId: 'rsi', ...lineOpts, lastValueVisible: true });
chart.priceScale('rsi').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
chart.priceScale('right').applyOptions({ scaleMargins: { top: 0.05, bottom: 0.24 } });
rsiS.createPriceLine({ price: 70, color: '#363a45', lineWidth: 1, lineStyle: 2, title: '70' });
rsiS.createPriceLine({ price: 30, color: '#363a45', lineWidth: 1, lineStyle: 2, title: '30' });
const bChart = LWC.createChart($('d1chart'), chartOpts);
let bLine = null; // line series for position premium mode
new ResizeObserver(() => { chart.resize($('chart').clientWidth, $('chart').clientHeight); bChart.resize($('d1chart').clientWidth, $('d1chart').clientHeight); }).observe($('left'));

/* ---------- TP/SL red-green zones (TradingView-style) primitive ---------- */
class ZonePrimitive {
  constructor() { this.zones = []; this._s = null; this._c = null; }
  attached(p) { this._s = p.series; this._c = p.chart; }
  setZones(z) { this.zones = z; }
  updateAllViews() {}
  paneViews() {
    const self = this;
    return [{ renderer: () => ({ draw(target) {
      target.useBitmapCoordinateSpace(scope => {
        const ctx = scope.context, w = scope.bitmapSize.width, vr = scope.verticalPixelRatio;
        for (const z of self.zones) {
          const y1 = self._s.priceToCoordinate(z.p1), y2 = self._s.priceToCoordinate(z.p2);
          if (y1 == null || y2 == null) continue;
          ctx.fillStyle = z.color;
          ctx.fillRect(0, Math.min(y1, y2) * vr, w, Math.abs(y2 - y1) * vr);
        }
      });
    } }) }];
  }
}
let zonePrim = null;

/* ---------- timeframe folding (anchored 09:15) ---------- */
function fold(b1, tfm) {
  if (tfm === 1) return b1;
  const out = []; const t0 = b1.length ? b1[0].time : 0;
  for (const b of b1) {
    const k = Math.floor((b.time - t0) / (tfm * 60));
    const last = out[out.length - 1];
    if (last && last._k === k) { last.high = Math.max(last.high, b.high); last.low = Math.min(last.low, b.low); last.close = b.close; }
    else out.push({ _k: k, time: t0 + k * tfm * 60, open: b.open, high: b.high, low: b.low, close: b.close });
  }
  return out;
}
/* ---------- indicators (computed on pinned TFs, sampled onto the displayed TF) ---------- */
function ema(cds, n) {
  const k = 2 / (n + 1); let e = null; const out = [];
  for (const b of cds) { e = e == null ? b.close : b.close * k + e * (1 - k); out.push({ time: b.time, value: e }); }
  return out.slice(n); // drop unconverged head (D-1 bars provide the warm-up)
}
function rsi(cds, n) {
  const out = []; let ag = 0, al = 0;
  for (let i = 1; i < cds.length; i++) {
    const ch = cds[i].close - cds[i - 1].close, g = Math.max(ch, 0), l = Math.max(-ch, 0);
    if (i <= n) { ag += g / n; al += l / n; if (i < n) continue; }
    else { ag = (ag * (n - 1) + g) / n; al = (al * (n - 1) + l) / n; }
    out.push({ time: cds[i].time, value: al < 1e-12 ? 100 : 100 - 100 / (1 + ag / al) });
  }
  return out;
}
function vwapTP(b1) { // session-anchored, typical price (index has no volume) - resets each day
  const out = []; let day = null, s = 0, c = 0;
  for (const b of b1) {
    const d = Math.floor(b.time / 86400);
    if (d !== day) { day = d; s = 0; c = 0; }
    s += (b.high + b.low + b.close) / 3; c++;
    out.push({ time: b.time, value: s / c });
  }
  return out;
}
function sampleAt(cds, pts, tfm) { // value as of each displayed candle's last covered point
  const out = []; let j = 0;
  for (const cd of cds) {
    const end = cd.time + tfm * 60;
    while (j < pts.length && pts[j].time < end) j++;
    if (j > 0) out.push({ time: cd.time, value: pts[j - 1].value });
  }
  return out;
}
function redraw() {
  const all = allBars(), cds = fold(all, tf);
  candles.setData(cds);
  vwapS.setData(ind.vwap && all.length ? sampleAt(cds, vwapTP(all), tf) : []);
  if (ind.ema && all.length) {
    const f5 = fold(all, 5);
    e9S.setData(sampleAt(cds, ema(f5, 9), tf));
    e21S.setData(sampleAt(cds, ema(f5, 21), tf));
  } else { e9S.setData([]); e21S.setData([]); }
  rsiS.setData(ind.rsi && all.length ? sampleAt(cds, rsi(fold(all, 15), 14), tf) : []);
}

/* ---------- level lines ---------- */
let levelLines = [];
function setLevels(lv) {
  levelLines.forEach(l => candles.removePriceLine(l)); levelLines = [];
  const defs = [['pdh', '#f59e0b', 'PDH'], ['pdl', '#f59e0b', 'PDL'], ['pwh', '#8b5cf6', 'PWH'], ['pwl', '#8b5cf6', 'PWL']];
  for (const [k, color, title] of defs) if (lv[k]) levelLines.push(candles.createPriceLine({ price: lv[k], color, lineWidth: 1, lineStyle: 2, title }));
}

/* ---------- CPR + opening-range indicator lines ---------- */
let cprLines = [], orLines = [];
function clearCpr() { cprLines.forEach(l => candles.removePriceLine(l)); cprLines = []; }
function clearOr() { orLines.forEach(l => candles.removePriceLine(l)); orLines = []; }
function updateCpr() {
  clearCpr();
  const d1 = (S && S.d1) || [];
  if (!ind.cpr || !d1.length) return;
  let H = -Infinity, L = Infinity;
  for (const b of d1) { if (b.high > H) H = b.high; if (b.low < L) L = b.low; }
  const C = d1[d1.length - 1].close;
  const P = (H + L + C) / 3, BC = (H + L) / 2, TC = 2 * P - BC;
  const defs = [[P, 'CPR-P'], [BC, 'CPR-BC'], [TC, 'CPR-TC'], [2 * P - L, 'CPR-R1'], [2 * P - H, 'CPR-S1'], [P + (H - L), 'CPR-R2'], [P - (H - L), 'CPR-S2']];
  for (const [pr, title] of defs) cprLines.push(candles.createPriceLine({ price: pr, color: '#4dd0e1', lineWidth: 1, lineStyle: 2, title, axisLabelVisible: false }));
}
function updateOr() { // first 15 min of the SIM day; appears once 09:30 is reached
  if (!ind.or15 || bars.length < 15) { if (orLines.length && !ind.or15) clearOr(); return; }
  if (orLines.length) return; // OR is fixed after the first 15 bars
  const f = bars.slice(0, 15);
  let orh = -Infinity, orl = Infinity;
  for (const b of f) { if (b.high > orh) orh = b.high; if (b.low < orl) orl = b.low; }
  orLines.push(candles.createPriceLine({ price: orh, color: '#90a4ae', lineWidth: 1, lineStyle: 2, title: 'ORH', axisLabelVisible: false }));
  orLines.push(candles.createPriceLine({ price: orl, color: '#90a4ae', lineWidth: 1, lineStyle: 2, title: 'ORL', axisLabelVisible: false }));
}

/* ---------- drawing tools ---------- */
let drawMode = null, trendPts = [], userLines = [], trendSeries = [];
$('dHline').onclick = () => setDraw('h');
$('dTrend').onclick = () => setDraw('t');
$('dClear').onclick = () => { userLines.forEach(l => candles.removePriceLine(l)); userLines = []; trendSeries.forEach(s => chart.removeSeries(s)); trendSeries = []; };
function setDraw(m) { drawMode = drawMode === m ? null : m; trendPts = []; $('dHline').classList.toggle('on', drawMode === 'h'); $('dTrend').classList.toggle('on', drawMode === 't'); }
chart.subscribeClick(p => {
  if (!drawMode || !p.point) return;
  const price = candles.coordinateToPrice(p.point.y);
  if (price == null) return;
  if (drawMode === 'h') {
    userLines.push(candles.createPriceLine({ price, color: '#2962ff', lineWidth: 1, title: price.toFixed(1) }));
  } else if (drawMode === 't' && p.time != null) {
    trendPts.push({ time: p.time, value: price });
    if (trendPts.length === 2) {
      trendPts.sort((a, b) => a.time - b.time);
      if (trendPts[0].time !== trendPts[1].time) {
        const s = chart.addLineSeries({ color: '#2962ff', lineWidth: 2, lastValueVisible: false, priceLineVisible: false });
        s.setData(trendPts); trendSeries.push(s);
      }
      trendPts = [];
    }
  }
});

/* ---------- bottom panel: selected-position premium chart (D-1 now lives on the main chart) ---------- */
function renderBottom() {
  const have = selPos && markHist[selPos] && markHist[selPos].length;
  $('bHint').style.display = have ? 'none' : 'flex';
  if (!have) { if (bLine) { bChart.removeSeries(bLine); bLine = null; zonePrim = null; } return; }
  {
    if (!bLine) bLine = bChart.addLineSeries({ color: '#d1d4dc', lineWidth: 2 });
    bLine.setData(markHist[selPos]);
    if (!zonePrim) { zonePrim = new ZonePrimitive(); bLine.attachPrimitive(zonePrim); }
    const pos = (S.positions || []).find(p => pkey(p) === selPos);
    const zones = []; const pls = [];
    bLine.priceLines ??= [];
    (bLine._pl || []).forEach(l => bLine.removePriceLine(l)); bLine._pl = [];
    if (pos) {
      bLine._pl.push(bLine.createPriceLine({ price: pos.entry, color: '#d1d4dc', lineWidth: 1, title: 'ENTRY' }));
      const better = pos.dir === 'L' ? 1 : -1;
      if (pos.tp != null) { zones.push({ p1: pos.entry, p2: pos.tp, color: 'rgba(38,166,154,0.18)' }); bLine._pl.push(bLine.createPriceLine({ price: pos.tp, color: '#26a69a', lineWidth: 1, title: 'TP' })); }
      if (pos.sl != null) { zones.push({ p1: pos.entry, p2: pos.sl, color: 'rgba(239,83,80,0.18)' }); bLine._pl.push(bLine.createPriceLine({ price: pos.sl, color: '#ef5350', lineWidth: 1, title: 'SL' })); }
    }
    zonePrim.setZones(zones); bChart.timeScale().fitContent();
  }
}
const pkey = p => `${p.ci}-${p.strike}-${p.cp}`;

/* ---------- timeframe buttons ---------- */
for (const m of [1, 3, 5, 15, 30, 60]) {
  const b = document.createElement('button'); b.className = 'tfbtn'; b.textContent = m < 60 ? m + 'm' : '1h';
  if (m === 1) b.classList.add('on');
  b.onclick = () => { tf = m; document.querySelectorAll('.tfbtn').forEach(x => x.classList.remove('on')); b.classList.add('on'); redraw(); };
  $('tfs').appendChild(b);
}

/* ---------- indicator toggles ---------- */
function bindInd(id, key) {
  $(id).onclick = () => {
    ind[key] = !ind[key];
    $(id).classList.toggle('on', ind[key]);
    chart.priceScale('right').applyOptions({ scaleMargins: { top: 0.05, bottom: ind.rsi ? 0.24 : 0.05 } });
    redraw();
  };
}
bindInd('iVwap', 'vwap'); bindInd('iEma', 'ema'); bindInd('iRsi', 'rsi');
$('iCpr').onclick = () => { ind.cpr = !ind.cpr; $('iCpr').classList.toggle('on', ind.cpr); updateCpr(); };
$('iOr').onclick = () => { ind.or15 = !ind.or15; $('iOr').classList.toggle('on', ind.or15); if (ind.or15) updateOr(); else clearOr(); };

/* ---------- sound cues (WebAudio, synthesized, lazy ctx) ---------- */
let actx = null;
let muted = localStorage.getItem('fno_muted') === '1';
function initAudio() { if (!actx) { try { actx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {} } }
document.addEventListener('pointerdown', initAudio, { once: true });
document.addEventListener('keydown', initAudio, { once: true });
function beep(freq, dur, type, vol, delay) {
  if (muted || !actx) return;
  const t = actx.currentTime + (delay || 0);
  const o = actx.createOscillator(), g = actx.createGain();
  o.type = type || 'sine'; o.frequency.value = freq;
  g.gain.setValueAtTime(vol || 0.12, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g); g.connect(actx.destination);
  o.start(t); o.stop(t + dur + 0.02);
}
const snd = {
  fill: () => beep(660, 0.09),
  sl: () => beep(180, 0.25, 'square', 0.15),
  tp: () => beep(880, 0.18),
  reject: () => beep(150, 0.15, 'sawtooth', 0.16),
  marginWarn: () => { beep(300, 0.1); beep(300, 0.1, 'sine', 0.12, 0.16); },
  sqoff: () => { beep(520, 0.09); beep(520, 0.09, 'sine', 0.12, 0.18); beep(520, 0.09, 'sine', 0.12, 0.36); },
};
let prevFillSet = new Set(), prevWarn = '', prevClock = '';
function soundDiff(m, newSession) {
  const cur = (m.fills || []).map(f => f.hm + '|' + f.msg);
  if (!newSession) {
    const rank = { sl: 4, tp: 3, reject: 2, fill: 1 };
    let best = null;
    for (const s of cur) {
      if (prevFillSet.has(s)) continue;
      const msg = s.slice(s.indexOf('|') + 1);
      const c = (msg.indexOf('REJECTED') === 0 || msg.includes('CANCEL')) ? 'reject' : msg.includes('SL') ? 'sl' : msg.includes('TP') ? 'tp' : 'fill'; // pending LMT/SLM fills arrive as fills msgs and classify here; cancels/rejects → thud
      if (!best || rank[c] > rank[best]) best = c;
    }
    if (best) snd[best]();
    if (m.warn && m.warn !== prevWarn && m.warn.includes('MARGIN')) snd.marginWarn();
    if (m.clock === '15:20' && prevClock !== '15:20' && m.state === 'RUNNING') snd.sqoff();
  }
  prevFillSet = new Set(cur); prevWarn = m.warn || ''; prevClock = m.clock;
}
function renderMute() { $('muteBtn').textContent = muted ? 'Sound OFF' : 'Sound ON'; $('muteBtn').classList.toggle('on', !muted); }
$('muteBtn').onclick = () => { muted = !muted; localStorage.setItem('fno_muted', muted ? '1' : '0'); renderMute(); };

/* ---------- WS + state ---------- */
let ws, wsOpen = false;
function pauseBanner(m) { // pause_reason: '' | 'user' | 'disconnect' (absent on old server → generic pause text)
  if (!wsOpen) return 'CONNECTION LOST — reconnecting…';
  if (m && m.paused && m.state === 'RUNNING')
    return m.pause_reason === 'disconnect' ? 'PAUSED (reconnected) — Space to resume' : 'PAUSED — Space resume · → step 1 bar';
  return '';
}
function connect() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => { // after a drop: never auto-resume — show the reconnect banner, user decides
    wsOpen = true;
    try {
      if (S && S.pause_reason === 'disconnect') $('warn').textContent = 'PAUSED (reconnected) — Space to resume';
      else if (S) $('warn').textContent = S.warn || pauseBanner(S);
    } catch (e) { console.error('reopen banner failed:', e); }
  };
  ws.onmessage = ev => { try { onSnap(JSON.parse(ev.data)); } catch (e) { console.error('snap failed:', e); } };
  ws.onclose = () => {
    wsOpen = false;
    try { $('warn').textContent = 'CONNECTION LOST — reconnecting…'; } catch (e) {}
    setTimeout(connect, 1500);
  };
}
function onSnap(m) { // each subsection isolated: one failure must never freeze the rest of the UI
  const newSession = !S || m.bars.length < bars.length;
  try { soundDiff(m, newSession); } catch (e) { console.error('sound cues failed:', e); }
  S = m; bars = m.bars;
  try { // chart: levels, OR/CPR, candles + indicators, autofit
    if (newSession) { markHist = {}; selPos = null; editPos = null; editVals = null; setLevels(m.levels); renderBottom(); candles.setMarkers([]); clearOr(); updateCpr(); }
    updateOr();
    redraw();
    if (newSession) autoFit = true;
    if (autoFit) chart.timeScale().fitContent(); // COMPLETE D-1 + full sim day always in view until the user zooms/pans
  } catch (e) { console.error('chart render failed:', e); }
  try { updateChips(m); } catch (e) { console.error('chip update failed:', e); }
  try { // positions: mark history + table
    const t = bars.length ? bars[bars.length - 1].time : null;
    for (const p of (m.positions || [])) {
      const k = pkey(p); (markHist[k] ??= []);
      const h = markHist[k];
      if (t && (!h.length || h[h.length - 1].time !== t)) h.push({ time: t, value: p.mark });
    }
    renderPositions(m.positions || []);
  } catch (e) { console.error('positions render failed:', e); }
  try { renderTabs(m, newSession); } catch (e) { console.error('tabs render failed:', e); }
  try { if (newSession) schedPayoff(); } catch (e) { console.error('payoff refresh failed:', e); }
  try { if (selPos) renderBottom(); } catch (e) { console.error('bottom chart failed:', e); }
  try { if (m.state === 'ENDED' && !window._revealAsked) { window._revealAsked = true; askReveal(); } } catch (e) { console.error('reveal prompt failed:', e); }
}
function updateChips(m) {
  $('clock').textContent = m.clock; $('vix').textContent = m.vix;
  $('dte').textContent = (m.dte || []).join('/');
  $('equity').textContent = fmt(m.equity); $('margin').textContent = fmt(m.margin);
  $('warn').textContent = m.warn || pauseBanner(m);
  $('pauseBtn').textContent = m.paused ? 'Resume' : 'Pause';
  $('lot').textContent = m.lot;
  if (m.day_realized != null || m.open_pnl != null) { // Day P&L = realized + open (new-server fields; hidden when absent)
    const dr = m.day_realized || 0, op = m.open_pnl || 0, tot = dr + op;
    $('dayPnlChip').style.display = '';
    $('dayPnlChip').title = `realized ${fmt(dr)} · open ${fmt(op)}`;
    $('dayPnl').textContent = (tot > 0 ? '+' : '') + fmt(tot);
    $('dayPnl').className = tot >= 0 ? 'pos' : 'neg';
  } else $('dayPnlChip').style.display = 'none';
  if (m.free_margin != null) {
    $('freeChip').style.display = '';
    $('freeM').textContent = fmt(m.free_margin);
    $('freeM').className = m.free_margin < 0 ? 'neg' : '';
  } else $('freeChip').style.display = 'none';
  let cm = null; // entry-cutoff countdown — sim-minutes only, derived from the blinded HH:MM clock string
  if (typeof m.clock === 'string' && /^\d{1,2}:\d{2}$/.test(m.clock)) { const [h, mi] = m.clock.split(':').map(Number); cm = h * 60 + mi; }
  const CUT = 15 * 60 + 20;
  if (cm != null && m.state === 'RUNNING' && cm >= 15 * 60 && cm < CUT) {
    $('cutChip').style.display = '';
    $('cut').textContent = `cutoff in ${CUT - cm}m`;
    $('cut').style.color = CUT - cm <= 5 ? '#ff9800' : '';
  } else $('cutChip').style.display = 'none';
}
const hm = x => `${String(Math.floor(x / 60)).padStart(2, '0')}:${String(x % 60).padStart(2, '0')}`;
const fmt = x => x == null ? '-' : Number(x).toLocaleString('en-IN', { maximumFractionDigits: 0 });

let editPos = null, editVals = null; // open TP/SL inline editor: position key + typed values (survive 1s re-renders)
function renderPositions(ps) {
  const tb = $('posT').querySelector('tbody');
  if (editPos) { // preserve what the user typed before the snapshot re-render wipes the DOM
    const tpi = tb.querySelector('.tpEdit'), sli = tb.querySelector('.slEdit');
    if (tpi && sli) editVals = { tp: tpi.value, sl: sli.value };
  }
  tb.innerHTML = ps.map(p => {
    const k = pkey(p), cls = p.pnl >= 0 ? 'pos' : 'neg', st = p.stale > 5 ? ' class="stale"' : '';
    let row = `<tr${st} data-k="${k}"><td>${p.strike}${p.cp} ${p.dir} ${p.tp != null ? 'T' : ''}${p.sl != null ? 'S' : ''}</td><td>${p.lots}</td><td>${p.entry}</td><td>${p.mark}</td><td class="${cls}">${fmt(p.pnl)}</td><td><button data-e="${k}" title="edit TP/SL" style="padding:0 4px;font-size:11px">✎</button><button data-x="${k}" style="padding:0 5px">×</button></td></tr>`;
    if (editPos === k) {
      const v = editVals || { tp: p.tp != null ? p.tp : '', sl: p.sl != null ? p.sl : '' };
      row += `<tr class="editrow"><td colspan="6" style="text-align:left">TP <input class="tpEdit" type="number" step="0.5" min="0" value="${v.tp}" style="width:64px"> SL <input class="slEdit" type="number" step="0.5" min="0" value="${v.sl}" style="width:64px"> <button class="brkSet" data-k="${k}" style="padding:1px 8px;font-size:11px">set</button> <span style="color:var(--dim);font-size:10px">blank = clear</span></td></tr>`;
    }
    return row;
  }).join('');
  const tot = ps.reduce((s, p) => s + (p.pnl || 0), 0); // footer total row
  $('posT').querySelector('tfoot').innerHTML = ps.length
    ? `<tr><td colspan="4"><b>Total</b></td><td class="${tot >= 0 ? 'pos' : 'neg'}"><b>${fmt(tot)}</b></td><td></td></tr>` : '';
  tb.querySelectorAll('tr').forEach(tr => tr.onclick = e => {
    if (e.target.classList.contains('tpEdit') || e.target.classList.contains('slEdit')) { e.stopPropagation(); return; }
    if (e.target.classList.contains('brkSet')) { e.stopPropagation(); setBracket(e.target.dataset.k); return; }
    if (e.target.dataset.x) { e.stopPropagation(); closePos(e.target.dataset.x); return; }
    if (e.target.dataset.e) { // toggle the inline TP/SL editor
      e.stopPropagation();
      editPos = editPos === e.target.dataset.e ? null : e.target.dataset.e; editVals = null;
      renderPositions((S && S.positions) || []);
      return;
    }
    if (tr.classList.contains('editrow')) return; // clicks inside the editor row never change chart selection
    selPos = tr.dataset.k; renderBottom();
  });
}
async function setBracket(k) {
  const [ci, strike, cp] = k.split('-');
  const row = $('posT').querySelector('tr.editrow'); if (!row) return;
  const tpv = row.querySelector('.tpEdit').value.trim(), slv = row.querySelector('.slEdit').value.trim();
  const tp = tpv === '' ? null : Number(tpv), sl = slv === '' ? null : Number(slv);
  if ((tp != null && !(tp > 0)) || (sl != null && !(sl > 0))) { alert('TP/SL must be positive (blank clears)'); return; }
  try {
    const r = await api('/api/bracket', { ci: Number(ci), strike: Number(strike), cp, tp, sl });
    if (r && r.error) { alert(r.error); return; }
  } catch (e) { console.error('bracket set failed:', e); return; }
  editPos = null; editVals = null;
  renderPositions((S && S.positions) || []);
}
async function closePos(k) {
  const [ci, strike, cp] = k.split('-');
  const p = (S.positions || []).find(x => pkey(x) === k); if (!p) return;
  await api('/api/order', { ci, strike, cp, side: p.dir === 'L' ? 'S' : 'B', lots: p.lots });
}

/* ---------- log-area tabs: Orders | Trades | Log ---------- */
let activeTab = 'log', tradesUnread = 0, prevTradesN = 0;
const escAttr = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
function setTab(t) {
  activeTab = t;
  $('tabOrders').classList.toggle('on', t === 'orders');
  $('tabTrades').classList.toggle('on', t === 'trades');
  $('tabLog').classList.toggle('on', t === 'log');
  $('ordersPane').style.display = t === 'orders' ? '' : 'none';
  $('tradesPane').style.display = t === 'trades' ? '' : 'none';
  $('fills').style.display = t === 'log' ? '' : 'none';
  if (t === 'trades') { tradesUnread = 0; renderTradesBadge(); }
}
$('tabOrders').onclick = () => setTab('orders');
$('tabTrades').onclick = () => setTab('trades');
$('tabLog').onclick = () => setTab('log');
function renderTradesBadge() {
  const b = $('tradesBadge');
  b.style.display = tradesUnread > 0 ? 'inline-block' : 'none'; // inline override needed: CSS default is display:none
  b.textContent = tradesUnread;
}
function renderTabs(m, newSession) {
  $('fills').innerHTML = (m.fills || []).map(f => `<div>[${hm(f.hm)}] ${f.msg}</div>`).reverse().join('');
  const pend = m.pending || []; // pending orders (new-server field; empty list on old server)
  $('ordersPane').innerHTML = pend.length
    ? `<table><thead><tr><th>Contract</th><th>Side</th><th>Lots</th><th>Type</th><th>Px/Trig</th><th>Placed</th><th></th></tr></thead><tbody>${pend.map(o =>
      `<tr${o.note ? ` title="${escAttr(o.note)}"` : ''}><td>${o.strike}${o.cp}</td><td class="${o.side === 'B' ? 'pos' : 'neg'}">${o.side === 'B' ? 'BUY' : 'SELL'}</td><td>${o.lots}</td><td>${o.type}</td><td>${o.type === 'LMT' ? (o.price != null ? o.price : '—') : (o.trigger != null ? o.trigger : '—')}</td><td>${hm(o.placed_hm)}</td><td><button data-cancel="${o.id}" style="padding:0 5px;font-size:11px">Cancel</button></td></tr>`).join('')}</tbody></table>`
    : '<div style="color:var(--dim)">no pending orders</div>';
  $('ordersPane').querySelectorAll('button[data-cancel]').forEach(b => b.onclick = () => cancelOrder(b.dataset.cancel));
  const tds = m.trades_today || []; // closed trades today (new-server field)
  $('tradesPane').innerHTML = tds.length
    ? `<table><thead><tr><th>Contract</th><th>Lots</th><th>Px</th><th>Time</th><th>Net</th><th>Chg</th><th>Exit</th></tr></thead><tbody>${tds.map(t =>
      `<tr><td>${t.strike}${t.cp} ${t.dir}</td><td>${t.lots}</td><td>${t.entry_px}→${t.exit_px}</td><td>${hm(t.entry_hm)}→${hm(t.exit_hm)}</td><td class="${t.net >= 0 ? 'pos' : 'neg'}">${fmt(t.net)}</td><td>${fmt(t.chg)}</td><td>${t.reason}</td></tr>`).join('')}</tbody></table>`
    : '<div style="color:var(--dim)">no closed trades yet</div>';
  if (newSession) { prevTradesN = tds.length; tradesUnread = 0; renderTradesBadge(); }
  else if (tds.length > prevTradesN) { // unread badge: new trades landed while another tab is active
    if (activeTab !== 'trades') { tradesUnread += tds.length - prevTradesN; renderTradesBadge(); }
    prevTradesN = tds.length;
  } else prevTradesN = tds.length;
}
async function cancelOrder(id) {
  try {
    const r = await api('/api/cancel', { id: /^\d+$/.test(id) ? Number(id) : id }); // dataset gives strings; send numeric ids as numbers
    if (r && r.error) alert(r.error);
  } catch (e) { console.error('cancel failed:', e); }
}

/* ---------- chain ---------- */
async function pollChain() {
  try {
    await pollChainOnce();
  } catch (e) { console.error('chain poll failed:', e); }
  setTimeout(pollChain, 4000);
}
function chainSideCells(r, cp) {
  const o = cp === 'CE' ? r.ce : r.pe;
  const at = ` data-s="${r.strike}" data-cp="${cp}"`;
  if (!o || o.ltp == null) { const e = `<td${at}>—</td>`; return e + e + e; }
  const st = o.stale > 5 ? ' class="stale"' : '';
  const bar = o.oi_pct != null ? ` style="background:linear-gradient(90deg,rgba(41,98,255,.28) ${o.oi_pct}%,transparent ${o.oi_pct}%)"` : '';
  const ltp = `<td${st}${bar}${at}>${o.ltp}</td>`;
  const iv = `<td${st}${at}>${o.iv != null ? Number(o.iv).toFixed(1) : '—'}</td>`;
  const dl = `<td${st}${at}>${o.delta != null ? (o.delta > 0 ? '+' : '') + Number(o.delta).toFixed(2) : '—'}</td>`;
  return cp === 'CE' ? ltp + iv + dl : dl + iv + ltp;
}
async function pollChainOnce() {
  if (S && S.state === 'RUNNING') {
    const c = await (await fetch('/api/chain')).json();
    if (c.chains) {
      lastChain = c;
      const ci = Number($('oExp').value || 0), ch = c.chains[ci] || c.chains[0];
      const rows = ch ? ch.rows : [];
      let atm = null; // strike closest to spot
      if (c.spot != null) for (const r of rows) if (atm == null || Math.abs(r.strike - c.spot) < Math.abs(atm - c.spot)) atm = r.strike;
      $('chainT').querySelector('tbody').innerHTML = rows.map(r =>
        `<tr${r.strike === atm ? ' class="atm"' : ''}>${chainSideCells(r, 'CE')}<td><b>${r.strike}</b></td>${chainSideCells(r, 'PE')}</tr>`
      ).join('');
      $('chainT').querySelectorAll('td[data-s]').forEach(td => td.onclick = () => { $('oStrike').value = td.dataset.s; $('oCp').value = td.dataset.cp; ticketChanged(); });
      const sel = $('oStrike'), cur = sel.value;
      sel.innerHTML = rows.map(r => `<option>${r.strike}</option>`).join('');
      if ([...sel.options].some(o => o.value === cur)) sel.value = cur;
      const eSel = $('oExp');
      if (eSel.options.length !== c.chains.length) eSel.innerHTML = c.chains.map((x, i) => `<option value="${i}">${x.dte} DTE</option>`).join('');
      updateSizing();
      schedMarginPreview(); // keep free-cash line fresh as the day moves
    }
  }
}

/* ---------- margin preview / position sizing / basket presets ---------- */
let previewSide = 'B', mprevTimer = null, sizeSug = 0;
function ticketChanged() { schedMarginPreview(); updateSizing(); schedPayoff(); }
function schedMarginPreview() { clearTimeout(mprevTimer); mprevTimer = setTimeout(marginPreview, 400); }
function enableSides() { $('oBuy').disabled = false; $('oSell').disabled = false; }
async function marginPreview() {
  if (!S || S.state !== 'RUNNING' || !$('oStrike').value) { $('mprev').textContent = ''; enableSides(); return; }
  try {
    const r = await api('/api/margin_preview', {
      ci: Number($('oExp').value || 0), strike: Number($('oStrike').value),
      cp: $('oCp').value, side: previewSide, lots: Number($('oLots').value || 1),
    });
    if (!r.ok) { $('mprev').textContent = r.error || ''; enableSides(); return; }
    const bad = r.free_cash < 0;
    $('mprev').innerHTML = `margin after: ${fmt(r.margin_after)} · free: <span class="${bad ? 'neg' : ''}">${fmt(r.free_cash)}</span>`;
    $('oBuy').disabled = bad && previewSide === 'B';
    $('oSell').disabled = bad && previewSide === 'S';
    if (!bad) enableSides();
  } catch (e) { /* endpoint unreachable - leave quiet */ }
}
$('oBuy').addEventListener('mouseenter', () => { if (previewSide !== 'B') { previewSide = 'B'; schedMarginPreview(); schedPayoff(); } });
$('oSell').addEventListener('mouseenter', () => { if (previewSide !== 'S') { previewSide = 'S'; schedMarginPreview(); schedPayoff(); } });

function ticketLtp() { // selected contract's ltp from the last chain poll
  if (!lastChain || !lastChain.chains) return null;
  const ch = lastChain.chains[Number($('oExp').value || 0)] || lastChain.chains[0];
  if (!ch) return null;
  const r = (ch.rows || []).find(x => x.strike === Number($('oStrike').value));
  if (!r) return null;
  const o = $('oCp').value === 'CE' ? r.ce : r.pe;
  return o ? o.ltp : null;
}
function updateSizing() {
  const el = $('sizeOut');
  const ltp = ticketLtp(), sl = Number($('oSl').value), risk = Number($('riskPct').value);
  const lot = (S && S.lot) || 65;
  sizeSug = 0;
  if (!S || ltp == null || $('oSl').value === '' || !(risk > 0) || Math.abs(ltp - sl) < 0.05) { el.textContent = 'size: — (need ltp + SL)'; return; }
  const perLot = Math.abs(ltp - sl) * lot;
  sizeSug = Math.min(27, Math.floor((S.equity * risk / 100) / perLot));
  el.textContent = sizeSug < 1 ? `size: 0 lots (1 lot risks ₹${fmt(Math.round(perLot))})` : `size: ${sizeSug} lots · risk ₹${fmt(Math.round(perLot * sizeSug))}`;
}
$('sizeUse').onclick = () => { if (sizeSug >= 1) { $('oLots').value = sizeSug; ticketChanged(); } };

function flashLog() { const f = $('fills'); f.style.background = 'rgba(41,98,255,.35)'; setTimeout(() => { f.style.background = ''; }, 350); }
async function basket(kind) {
  const side = $('pSide').textContent === 'BUY' ? 'B' : 'S';
  const lots = Number($('oLots').value || 1), width = Number($('pWidth').value || 100);
  const w = kind === 'strangle' ? ` width ±${width}` : '';
  if (!confirm(`${kind.toUpperCase()} — ${side === 'B' ? 'BUY' : 'SELL'} ${lots} lot(s)${w}. Place?`)) return;
  const r = await api('/api/basket', { ci: Number($('oExp').value || 0), kind, side, lots, width });
  if (r.error || r.ok === false) { alert(r.error || 'basket failed'); return; }
  flashLog();
}
$('pStraddle').onclick = () => basket('straddle');
$('pStrangle').onclick = () => basket('strangle');
$('pSide').onclick = () => {
  const sell = $('pSide').textContent !== 'BUY' ? false : true; // toggle
  $('pSide').textContent = sell ? 'SELL' : 'BUY';
  $('pSide').classList.toggle('sell', sell); $('pSide').classList.toggle('buy', !sell);
};

/* ---------- payoff diagram ---------- */
let payoffDebounce = null;
function schedPayoff() { clearTimeout(payoffDebounce); payoffDebounce = setTimeout(() => { fetchPayoff().catch(() => {}); }, 250); }
async function pollPayoff() {
  try { await fetchPayoff(); } catch (e) { /* endpoint not up yet */ }
  setTimeout(pollPayoff, 5000);
}
async function fetchPayoff() {
  if (!S || S.state !== 'RUNNING') return;
  const base = await (await fetch('/api/payoff')).json();
  let hypo = null;
  const st = Number($('oStrike').value);
  if (st) {
    const q = new URLSearchParams({ ci: $('oExp').value || 0, strike: st, cp: $('oCp').value, side: previewSide, lots: $('oLots').value || 1 });
    try { hypo = await (await fetch('/api/payoff?' + q)).json(); } catch (e) { hypo = null; }
  }
  drawPayoff(base, hypo);
}
function drawPayoff(base, hypo) {
  const cv = $('payoff'), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H);
  ctx.font = '10px system-ui';
  // grid: prefer the book's, else the hypothetical ticket's (empty book + hovered ticket still draws)
  const xs = (base && base.xs && base.xs.length > 1) ? base.xs
    : (hypo && hypo.xs && hypo.xs.length > 1 ? hypo.xs : null);
  if (!xs) { ctx.fillStyle = '#787b86'; ctx.fillText('payoff: no data', 10, 20); return; }
  const haveBook = !!(base && base.xs && base.xs.length > 1);
  const mpSrc = haveBook ? base : (hypo || {});
  const series = [base.expiry, base.t0, hypo && hypo.expiry].filter(a => a && a.length);
  let lo = Infinity, hi = -Infinity;
  for (const a of series) for (const v of a) { if (v < lo) lo = v; if (v > hi) hi = v; }
  if (!isFinite(lo)) { lo = -1; hi = 1; }
  if (hi - lo < 1) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.08; hi += pad; lo -= pad;
  const L = 8, R = 8, T = 14, B = 14;
  const xAt = px => L + (W - L - R) * (px - xs[0]) / (xs[xs.length - 1] - xs[0]);
  const Y = v => T + (H - T - B) * (hi - v) / (hi - lo);
  ctx.strokeStyle = '#363a45'; ctx.lineWidth = 1;               // zero line
  ctx.beginPath(); ctx.moveTo(L, Y(0)); ctx.lineTo(W - R, Y(0)); ctx.stroke();
  ctx.fillStyle = '#787b86';                                     // x-axis labels (spot grid)
  ctx.fillText(String(Math.round(xs[0])), L, H - 3);
  const xr = String(Math.round(xs[xs.length - 1]));
  ctx.fillText(xr, W - R - ctx.measureText(xr).width, H - 3);
  const plot = (arr, color, dash, wdt) => {
    ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = wdt; ctx.setLineDash(dash);
    ctx.beginPath();
    for (let i = 0; i < arr.length && i < xs.length; i++) { const x = xAt(xs[i]), y = Y(arr[i]); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); }
    ctx.stroke(); ctx.restore();
  };
  if (haveBook && base.t0 && base.t0.length) plot(base.t0, '#64b5f6', [4, 3], 1);
  if (haveBook && base.expiry && base.expiry.length) plot(base.expiry, '#ffffff', [], 1.5);
  if (!haveBook && hypo && hypo.t0 && hypo.t0.length) plot(hypo.t0, '#64b5f6', [4, 3], 1);
  if (hypo && hypo.expiry && hypo.expiry.length) plot(hypo.expiry, '#ffd54f', [2, 3], 1);
  for (const b of (mpSrc.be || [])) {                            // breakevens: dots + labels
    const x = xAt(b);
    if (x < L || x > W - R) continue;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath(); ctx.arc(x, Y(0), 2.5, 0, 6.3); ctx.fill();
    ctx.fillStyle = '#d1d4dc';
    const lbl = String(Math.round(b));
    ctx.fillText(lbl, Math.min(W - R - ctx.measureText(lbl).width, Math.max(L, x - ctx.measureText(lbl).width / 2)), Y(0) - 5);
  }
  ctx.fillStyle = '#787b86';                                     // max P/L + legend (text in dim, swatch in series color)
  const mv = v => v == null ? 'unl.' : (v > 0 ? '+' : '') + fmt(v);
  ctx.fillText(`max ${mv(mpSrc.max_profit)} / ${mv(mpSrc.max_loss)}`, L, 10);
  let lx = W - R - 4;
  const legend = [['#ffd54f', '+ticket', !!(hypo && hypo.expiry && hypo.expiry.length)],
    ['#64b5f6', 't0', true], ['#ffffff', 'expiry', haveBook]];
  for (const [color, label, on] of legend) {
    if (!on) continue;
    lx -= ctx.measureText(label).width; ctx.fillStyle = '#787b86'; ctx.fillText(label, lx, 10);
    lx -= 12; ctx.strokeStyle = color; ctx.beginPath(); ctx.moveTo(lx, 7); ctx.lineTo(lx + 9, 7); ctx.stroke();
    lx -= 10;
  }
}

/* ---------- controls ---------- */
const api = (u, body) => fetch(u, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) }).then(r => r.json());
$('startBtn').onclick = async () => { window._revealAsked = false; const r = await api('/api/session/start'); if (r.error) alert(r.error); };
$('pauseBtn').onclick = () => api('/api/ctl', { paused: !(S && S.paused) });
$('speed').oninput = e => { $('spdLbl').textContent = e.target.value + 's/bar'; api('/api/ctl', { speed: Number(e.target.value) }); };
$('oFlat').onclick = () => api('/api/flatten');
$('resetBtn').onclick = async () => { if (confirm('Start a NEW SEASON at Rs.10,00,000? History is kept.')) { await api('/api/reset'); career(); } };
async function order(side) {
  const tp = $('oTp').value, sl = $('oSl').value, typ = $('oType').value; // 'MKT' | 'LMT' | 'SLM'
  const body = { ci: Number($('oExp').value || 0), strike: Number($('oStrike').value), cp: $('oCp').value, side, lots: Number($('oLots').value), tp: tp ? Number(tp) : null, sl: sl ? Number(sl) : null, type: typ };
  if (typ === 'LMT') {
    const px = Number($('oPrice').value);
    if (!(px > 0)) { alert('LMT order needs a positive limit price'); return; }
    body.price = px;
  } else if (typ === 'SLM') {
    const tg = Number($('oTrigger').value);
    if (!(tg > 0)) { alert('SL-M order needs a positive trigger price'); return; }
    body.trigger = tg;
  }
  const r = await api('/api/order', body);
  if (r.error) alert(r.error);
}
$('oBuy').onclick = () => order('B');
$('oSell').onclick = () => order('S');
$('oType').onchange = () => { // LMT shows price, SL-M shows trigger; MKT shows neither
  const t = $('oType').value;
  $('oPriceWrap').style.display = t === 'LMT' ? '' : 'none';
  $('oTrigWrap').style.display = t === 'SLM' ? '' : 'none';
};
for (const id of ['oStrike', 'oCp']) $(id).onchange = ticketChanged;
$('oExp').onchange = () => { pollChainOnce().catch(() => {}); ticketChanged(); };
$('oLots').oninput = ticketChanged;
$('oSl').oninput = updateSizing;
$('riskPct').oninput = updateSizing;
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  if (e.code === 'Space') { e.preventDefault(); $('pauseBtn').click(); }
  else if (e.key === 'ArrowRight') { if (S && S.paused && S.state === 'RUNNING') api('/api/step'); }
  else if (e.key === 'b' || e.key === 'B') order('B');
  else if (e.key === 's' || e.key === 'S') order('S');
  else if (e.key === 'F2') api('/api/flatten');
  else if (e.key === '+') { $('speed').value = Math.max(1, Number($('speed').value) - 2); $('speed').dispatchEvent(new Event('input')); }
  else if (e.key === '-') { $('speed').value = Math.min(60, Number($('speed').value) + 2); $('speed').dispatchEvent(new Event('input')); }
});

/* ---------- reveal + journal ---------- */
function askReveal() {
  $('modalBody').innerHTML = `<h3>Session over — net will be revealed</h3>
    <p style="margin:10px 0">Did you recognize this day? Enter a date guess (YYYY-MM-DD) or leave blank. Honest answers keep your stats clean — recognized sessions are excluded from career analytics.</p>
    <div class="row"><input id="guess" style="width:140px" placeholder="YYYY-MM-DD"><button id="revealBtn">Reveal</button></div>`;
  $('modal').style.display = 'flex';
  $('revealBtn').onclick = async () => {
    const r = await api('/api/reveal', { guess: $('guess').value.trim() });
    if (r.error) { alert(r.error); return; }
    bars = r.full_day; tf = 1; // 1-min for the review so trade markers align exactly
    document.querySelectorAll('.tfbtn').forEach((x, i) => x.classList.toggle('on', i === 0));
    redraw(); chart.timeScale().fitContent();
    const mk = [];
    for (const t of r.trades) {
      mk.push({ time: barT(t.entry_hm), position: 'belowBar', color: '#2962ff', shape: 'arrowUp', text: `${t.dir === 'L' ? 'B' : 'S'} ${t.strike}${t.cp}` });
      mk.push({ time: barT(t.exit_hm), position: 'aboveBar', color: t.gross - t.chg >= 0 ? '#26a69a' : '#ef5350', shape: 'arrowDown', text: t.reason });
    }
    candles.setMarkers(mk.sort((a, b) => a.time - b.time));
    const rows = r.trades.map(t => `<tr><td>${t.strike}${t.cp} ${t.dir}</td><td>${t.lots}</td><td>${t.entry_px}→${t.exit_px}</td><td>${hm(t.entry_hm)}→${hm(t.exit_hm)}</td><td class="${t.gross - t.chg >= 0 ? 'pos' : 'neg'}">${fmt(t.gross - t.chg)}</td><td>${fmt(t.chg)}</td><td>${t.r_mult != null ? Number(t.r_mult).toFixed(2) : '—'}</td><td>${t.reason}</td></tr>`).join('');
    $('modalBody').innerHTML = `<h3>${r.real_date} (${r.weekday}) ${r.recognized ? '— RECOGNIZED (excluded from stats)' : ''}</h3>
      <p style="margin:8px 0">Net P&L: <b class="${r.net >= 0 ? 'pos' : 'neg'}">${fmt(r.net)}</b> · New bankroll: <b>${fmt(r.cash)}</b> · Expiries: ${r.expiries.join(', ')}</p>
      <table><thead><tr><th>Contract</th><th>Lots</th><th>Px</th><th>Time</th><th>Net</th><th>Charges</th><th>R</th><th>Exit</th></tr></thead><tbody>${rows}</tbody></table>
      <div id="journal"></div>
      <p style="margin:10px 0"><button onclick="document.getElementById('modal').style.display='none'">Close — trades stay on chart</button></p>`;
    renderJournal(r.trades).catch(e => console.error('journal ui failed:', e));
    career();
  };
}
const barT = h => (bars.length ? bars[0].time - 0 : 946890900) + (h - 555) * 60;

async function renderJournal(trades) {
  let tg;
  try { tg = await (await fetch('/api/tags')).json(); } catch (e) { return; } // tags endpoint unavailable - skip journal UI
  const selOf = t => `<select class="jsel" data-t="${t}" style="width:88px;font-size:11px;padding:2px 3px"><option value="">${t}…</option>${(tg[t] || []).map(x => `<option>${x}</option>`).join('')}</select>`;
  const jrows = trades.map((t, i) => `<div class="row" data-ti="${i}" style="margin:3px 0">
      <span style="width:92px;color:var(--dim);font-size:11px">${t.strike}${t.cp} ${t.dir}</span>
      ${selOf('setup')}${selOf('mistake')}${selOf('emotion')}
      <input class="jnote" placeholder="note" style="width:150px;font-size:11px"></div>`).join('');
  $('journal').innerHTML = `<h4 style="margin-top:12px">Journal — tag your trades</h4>${jrows}
    <div class="row" data-ti="s" style="margin:6px 0 3px;border-top:1px solid #2a2e39;padding-top:6px">
      <span style="width:92px;color:var(--dim);font-size:11px">SESSION</span>
      ${selOf('mistake')}<input class="jnote" placeholder="session note" style="width:246px;font-size:11px"></div>
    <button id="jSave" style="margin-top:4px">Save journal</button>`;
  $('jSave').onclick = async () => {
    const btn = $('jSave'); btn.disabled = true;
    const posts = [];
    for (const row of $('journal').querySelectorAll('[data-ti]')) {
      const ti = row.dataset.ti === 's' ? null : Number(row.dataset.ti);
      const note = (row.querySelector('.jnote') || { value: '' }).value.trim();
      for (const sel of row.querySelectorAll('.jsel')) {
        if (!sel.value) continue;
        posts.push(api('/api/journal', { trade_idx: ti, tag_type: sel.dataset.t, tag: sel.value, note }));
      }
    }
    try { await Promise.all(posts); btn.textContent = 'saved'; }
    catch (e) { btn.disabled = false; alert('journal save failed'); }
  };
}

/* ---------- analytics ---------- */
$('analyticsBtn').onclick = () => { $('modalBody').innerHTML = '<p>loading…</p>'; $('modal').style.display = 'flex'; renderAnalytics(false); };
async function renderAnalytics(inclRec) {
  const closeBtn = `<p style="margin:10px 0 0"><button onclick="document.getElementById('modal').style.display='none'">Close</button></p>`;
  let a;
  try { a = await (await fetch('/api/analytics?include_recognized=' + (inclRec ? 1 : 0))).json(); }
  catch (e) { $('modalBody').innerHTML = `<h3>Analytics</h3><p style="margin:8px 0;color:var(--dim)">analytics unavailable</p>${closeBtn}`; return; }
  const c = a.career || {}, minN = a.min_n != null ? a.min_n : 30;
  const pc = v => v == null ? '—' : Math.round(v <= 1 ? v * 100 : v); // tolerate fraction or percent
  const chip = (k, v) => `<span class="chip"><span>${k} </span><b>${v}</b></span>`;
  const chips = [
    chip('Sessions', c.sessions != null ? c.sessions : '—'),
    chip('Trades', c.trades != null ? c.trades : '—'),
    chip('WR', c.win_rate != null ? `${pc(c.win_rate)}% [${pc(c.wr_lo)}-${pc(c.wr_hi)}]` : '—'),
    chip('R:R', c.rr != null ? Number(c.rr).toFixed(2) : '—'),
    chip('Expectancy', c.expectancy != null ? fmt(c.expectancy) : '—'),
    chip('Total net', `<span class="${(c.total_net || 0) >= 0 ? 'pos' : 'neg'}">${fmt(c.total_net)}</span>`),
    chip('Charges', fmt(c.total_charges)),
    chip('Undef-R', c.undefined_r != null ? c.undefined_r : '—'),
  ].join(' ');
  const tbl = (title, kh, rows) => `<div style="flex:1 1 45%;min-width:150px"><h4>${title}</h4>
    <table><thead><tr><th>${kh}</th><th>n</th><th>net</th></tr></thead><tbody>${(rows || []).map(r =>
      `<tr${r.low_n ? ` class="lown" title="n&lt;${minN} — insufficient sample"` : ''}><td>${r.k}</td><td>${r.n}</td><td class="${r.net >= 0 ? 'pos' : 'neg'}">${fmt(r.net)}</td></tr>`).join('')}</tbody></table></div>`;
  $('modalBody').innerHTML = `<h3>Career analytics</h3>
    <div class="row" style="margin:10px 0">${chips}</div>
    <div class="row" style="margin:6px 0;color:var(--dim);font-size:12px">
      <label style="cursor:pointer"><input id="acInc" type="checkbox" ${inclRec ? 'checked' : ''}> include recognized sessions</label>
      <button id="acExport" style="font-size:11px">Export CSV</button></div>
    <h4>Equity curve (bankroll by session)</h4>
    <canvas id="acEq" width="640" height="140" style="background:var(--bg);border:1px solid #2a2e39;border-radius:4px"></canvas>
    <div class="row" style="align-items:flex-start;margin-top:8px">
      ${tbl('By entry hour', 'hour', a.by_hour)}${tbl('By DTE', 'dte', a.by_dte)}
      ${tbl('By exit reason', 'reason', a.by_reason)}${tbl('By tag', 'tag', a.by_tag)}
    </div>${closeBtn}`;
  $('acInc').onchange = e => renderAnalytics(e.target.checked);
  $('acExport').onclick = () => { location = '/api/export'; };
  drawEquityCurve($('acEq'), a.equity_curve || [], a.seasons || []);
}
function drawEquityCurve(cv, pts, seasons) {
  const ctx = cv.getContext('2d'), W = cv.width, H = cv.height;
  ctx.clearRect(0, 0, W, H); ctx.font = '10px system-ui';
  if (!pts.length) { ctx.fillStyle = '#787b86'; ctx.fillText('no sessions yet', 10, 20); return; }
  let lo = Infinity, hi = -Infinity;
  for (const p of pts) { if (p.cash < lo) lo = p.cash; if (p.cash > hi) hi = p.cash; }
  if (hi - lo < 1) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.1; hi += pad; lo -= pad;
  const L = 6, R = 6, T = 6, B = 14;
  const n0 = pts[0].n, n1 = pts[pts.length - 1].n;
  const X = n => n1 === n0 ? W / 2 : L + (W - L - R) * (n - n0) / (n1 - n0);
  const Y = v => T + (H - T - B) * (hi - v) / (hi - lo);
  let cum = 0;                                                   // season boundaries
  for (let i = 0; i < seasons.length - 1; i++) {
    cum += seasons[i].sessions || 0;
    const x = X(n0 + cum - 0.5);
    ctx.strokeStyle = '#363a45'; ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(x, T); ctx.lineTo(x, H - B); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = '#787b86'; ctx.fillText('S' + (seasons[i + 1].season != null ? seasons[i + 1].season : i + 2), x + 3, T + 9);
  }
  ctx.strokeStyle = '#64b5f6'; ctx.lineWidth = 1.5;              // curve
  ctx.beginPath();
  pts.forEach((p, i) => { const x = X(p.n), y = Y(p.cash); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
  ctx.stroke(); ctx.lineWidth = 1;
  ctx.fillStyle = '#787b86';
  ctx.fillText(fmt(pts[pts.length - 1].cash), W - R - 60, Y(pts[pts.length - 1].cash) - 4);
  ctx.fillText(`sessions 1–${pts.length}`, L, H - 3);
}

/* ---------- career + init ---------- */
async function career() {
  const c = await (await fetch('/api/career')).json();
  $('career').textContent = `Season ${c.season} · bankroll ${fmt(c.cash)} · ${c.sessions} sessions · total P&L ${fmt(c.total_pnl)}`;
}
renderMute();
connect(); pollChain(); pollPayoff(); career();
