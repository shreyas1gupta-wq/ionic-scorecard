# FnO REPLAY GAME — ROADMAP (v1.0 FINAL, Principal-approved 2026-07-05)

**Mission:** Intraday NIFTY weekly-options paper-trading simulator replaying a RANDOM HIDDEN historical day
bar-by-bar from our real 1-min data. Training tool for the Principal. 100% local, offline after one-time setup.
**Location:** `Shreyas_Ionic_AMC/09_PRODUCT/fno_game/`. Data read (read-only) from legacy folders — copy nothing.
**Design provenance:** 4-agent design workflow 2026-07-05 (architecture / F&O realism / features / red-team),
digest archived at `docs/design_digest.md`. Principal rulings via Q&A same day.

---

## 1. LOCKED DECISIONS (Principal-approved — do not relitigate)

| # | Decision | Ruling |
|---|---|---|
| L1 | Day selection | Random, uniform, hidden date; no-repeat (played-days registry); NO re-roll button; abandoned day counts as played |
| L2 | Blinding | Hide date only. Real strikes & prices shown. Date revealed only at session end. Era-guess via spot level = accepted residual |
| L3 | Instruments | NIFTY weekly options, 2 nearest expiries, strikes within ±200 pts of CURRENT spot; BUY and SELL |
| L4 | Margin | Approx-SPAN with hedge/spread benefit (formulas §4.3); recomputed every bar; RMS behavior §4.5 |
| L5 | Costs | Today's exchange rates uniform across all eras (§4.2). Net P&L is the only P&L displayed |
| L6 | Fills | **Spread-aware** (red-team upgrade, approved 2026-07-05): modeled half-spread by moneyness/DTE/volume/range/ToD (§4.1); no-fill on zero-volume; trade-through limits; gap-through stops can MISS |
| L7 | Contract regime | **Today's mechanics uniform**: lot = 65 on every replayed day, today's freeze qty (1800 units → 27 lots/order), today's costs. Historical prices, current frictions. Historical lot shown only in reveal screen |
| L8 | Capital | Start ₹10,00,000. Bankroll persists across sessions. Reset = NEW SEASON (append-only history, never deletion). Blow-up (equity ≤ 0) freezes career until explicit reset |
| L9 | Speed | 1 sim-min per 1–60 real-sec, adjustable mid-session; pause; intraday only, forced square-off 15:25 |
| L10 | Loss lockout | SKIPPED in v1 (Principal ruling, against red-team advice — revisit at v2 with mistake-detection data) |
| L11 | V1 scope | Core + post-session review + option chain w/ IV+Greeks + journal tags & analytics + feature set §6 |

---

## 2. ARCHITECTURE

- **Stack:** Python ASGI — FastAPI + uvicorn (fallback: pure-Python Starlette + uvicorn if cp314 wheels fail; decide in P0 with one pip attempt). Vanilla-JS frontend, no build step. TradingView **lightweight-charts** standalone JS bundled locally (one-time download via truststore). pyarrow/pandas/scipy/websockets already installed on Python 3.14.
- **Transport:** One WebSocket per session for tick frames (`{bar, vix_band, marks, margin, fills, clock}`) + control (`pause/resume/set_speed`). REST for `session/start`, `order` (idempotency key), `chain`, `payoff`, `review`, `analytics`, `journal`. WS disconnect → server auto-pauses; reconnect → full resync of released bars (refresh-safe).
- **Anti-leak (server-authoritative clock):** browser NEVER possesses a bar/quote/OI row beyond sim-now. State machine: IDLE→PICKING→LOADING→BRIEFING→RUNNING→PAUSED→SQUAREOFF→REVEAL→ARCHIVED. All outbound payloads pass ONE choke-point sanitizer (`blinding.py`): timestamps rebased to fake anchor (sim day → 2000-01-03; D-1 → 2000-01-02), metadata stripped, contracts labeled `NIFTY <strike> CE · ATM+100 · 2 DTE`, hard assert `max(ts) <= sim_clock` on every payload. Acceptance test: devtools dump of every response + window object shows nothing beyond sim-now, no real dates.
- **Replay engine:** asyncio tick loop; whole-minute clock 09:15→15:30 (wall-minutes, not row count — gaps render as gaps, never interpolate). At sim time t only bars ≤ t−1 render (forming bar never shown — intrabar lookahead structurally impossible). Candle aggregation CLIENT-side from released 1-min bars, buckets anchored 09:15 (unit test: candle(t) == aggregate(bars ≤ t)).
- **Chain serving:** expiry parquet loaded once per session → per-minute dict `{minute: {(strike,cp): (o,h,l,c,vol,oi)}}` + last-trade carry-forward state. IV/Greeks cached per (minute,strike,cp).

## 3. DATA FOUNDATION (P0)

`tools/build_index.py` (idempotent) produces into `fno_game/data/`:
1. **eligible_days.json** — day D in pool iff: spot ≥360 bars in [09:15,15:29] + bar ≥15:25; first regular bar 09:15 (kills Muhurat/special); front-weekly file has ≥8 strikes ±200 of open with ≥60% minute coverage AND ≥5 strikes with volume>0; D-1 exists ≥360 bars; ≥5 prior sessions (PWH/PWL); VIX coverage (1-min, else daily fallback tag, else exclude); consistent lot row.
2. **lot_sizes.json** — per (trading_day, expiry) from 402 bhavcopies. Old schema: median of `VAL_INLAKH*1e5/(CONTRACTS*(STRIKE_PR+CLOSE))` over OPTIDX NIFTY rows (CONTRACTS>50, CLOSE>0), snap {25,50,65,75} @12% tol; UDiFF schema: read `NewBrdLotQty` directly. Cross-check FUTIDX. VERIFIED eras: 75→50 (Aug-2021)→25 (Apr-2024, mid-life on far contracts)→75 (Nov-2024 new contracts)→65 (Jan-2026). Gameplay uses 65 (L7); table used for validation + reveal screen.
3. **coverage_gaps.json** — every excluded day + reason. Human-review once (honest pool size before Principal expects "any random day").
- **Expiry calendar = the parquet file list**, NEVER weekday rules (Thu→Tue Sep-2025; holiday-shifted Wed 2021-08-18…2025-04-30, Mon 2026-03-02/03-30/04-13). Front weekly for D = min(expiry ≥ D with rows for trading_day==D). DTE = calendar days. Validate expiry column inside file vs filename.
- **Landmine enforcement at loader boundary** (`data_loader.py`, one shared function, no bypass path): tz-convert IST + hard filter ts ≥ 09:15 for spot, options, VIX. Unit test asserts no loaded frame contains <09:15 bar.

## 4. MARKET MECHANICS SPEC

### 4.1 Fills (spread-aware, L6)
- **Half-spread model:** `hs = clamp(max(0.05, 0.0010 * premium) * M, 0.05, 0.02*premium + 2.0)` where multiplier M = product of: ×2 if fill-bar volume in bottom quartile of that strike's day; ×2 if bar range > 3× that strike's rolling ATR(20); ×2 if expiry day after 15:00; ×1.5 if 09:15–09:20; capped M ≤ 4. **Calibrate against live Angel-terminal spreads (Tara spot-check) before P2 sign-off.**
- **Market order** at t → fills at NEXT bar (t+1) open ± hs (adverse). No bar / zero-volume at t+1 → look forward ≤3 min for first volume>0 bar, fill at its open ± (hs + 1 extra tick per minute waited). ENTRY with no qualifying bar in 3 min → REJECT "no liquidity" (D-031 doctrine). EXIT stays queued, fills at first traded bar ± (hs + 1 tick).
- **Limit order:** fills only on volume>0 bar with strict trade-THROUGH (low < L for buy; high > L for sell), or open crosses → fill at open (price improvement). Touch ≠ fill.
- **SL-M:** triggers on bar extreme crossing; fills at max(trigger, next open) + hs for buy-stops (min/− for sell-stops) — gaps fill at the worse next open, never at trigger. **SL-Limit gapped through = MISS** → open position + alert (the missed-stop lesson ships in v1).
- **Freak prints:** candidate fill bar open deviating >30% from strike's previous traded close → skip to next qualifying bar (logged). Marks: median-of-3 filter only when newest close >3× both neighbors. Chart draws raw.
- **Freeze qty:** max 27 lots (1800 units @65) per order; bigger intent = multiple orders, each ₹20 + own fill bar.
- **Tick:** all fills rounded to ₹0.05 AFTER spread; costs in separate charges column. Per-trade identity test: net = (sell − buy) − charges.

### 4.2 Costs (today's rates, uniform; on premium turnover V per order)
₹20 brokerage | STT 0.1%·V SELL only | NSE txn 0.03503%·V both | IPFT 0.0005%·V both | SEBI 0.0001%·V both | stamp 0.003%·V BUY only | GST 18% on (brokerage+txn+IPFT+SEBI) | exercise STT 0.125%·intrinsic, long ITM only. Full breakdown per trade in review screen.

### 4.3 Margin (approx-SPAN; label "approximate" in UI — real SPAN deviates ±10–20% in stress)
- Long option: premium debit, zero margin.
- **Naked short/lot:** `65 * [P + max(0.045*S − OTM, 0.025*S)]` (ATM @S=25,000, P=160 → ₹83.5k/lot ✓).
- **Credit vertical:** `65 * max(width − net_credit, 0.005*S)`; debit vertical: 0 (max loss prepaid).
- **Short straddle/strangle pair:** `max(M_CE, M_PE) + 65*P_mark_other`.
- **Portfolio = greedy pairing** per expiry after every fill AND every bar: shorts→cheapest covering same-type long (verticals) → largest CE×largest PE pairs → leftovers naked, additive. Reject order if margin + debits > cash + credits.
- Expiry day: ×1.3 on all short-leg margin from 09:15. Closing a hedge leg re-margins the short instantly (blocked if insufficient — live RMS behavior).

### 4.4 Settlement & square-off
- New entries blocked 15:20; forced market exits 15:25 via normal fill engine (queued-exit, stressed spread — square-off is NOT free). Non-expiry unfilled at 15:29: settle at last mark − 2 ticks, tagged `forced-settle` (exit-liquidity mistake in analytics).
- **Expiry day:** settlement spot = mean of NIFTY 1-min closes 15:00–15:29. OTM → 0 (shorts keep premium, no exit cost); ITM long → intrinsic credit − 0.125% STT; ITM short → intrinsic debit. Banner at 15:15: "ITM held to close settles at 30-min average; longs pay exercise STT — selling usually cheaper."

### 4.5 Live risk behavior
- Marks: `close` of strike's most recent completed bar ≤ t−1, freak-filtered; staleness badge >5 min; ONE mark function imported by MTM/margin/RMS (no second definition).
- Chain rows: >10 min stale → greyed, entries blocked; >30 min → price/IV shows "—"; zero rows all day → hidden.
- Margin utilization each bar: >100% → warning + block margin-increasing orders; >110% for 5 bars → RMS-liquidate the highest-margin position at market, tagged `RMS-forced` (mistake-class in analytics).

### 4.6 Greeks/IV
Bisection IV ∈ [0.01, 5.00] on Black-Scholes; T = max(minutes_to_expiry,1)/525600, expiry moment 15:30 IST; r = 6.5%; q = 0; **forward from ATM put-call parity at current timestamp** (not S·e^rT — red-team fix). Mark < intrinsic−0.05 → IV "—", |delta|=1. Stale >5 min → IV greyed, excluded from smile & ATM-IV headline. Display cap 400% with ">".

## 5. BLINDING SPEC
- UI timestamps HH:MM only; x-axis/tooltip/exports date-free until reveal (exports use session UUID).
- Never render: sim weekday, expiry weekday/date, real contract codes (reveal screen shows them).
- **VIX shown as BAND during play** (<13 / 13–17 / 17–25 / >25) + %change from day open + sparkline (no absolute axis); exact VIX at reveal. (Red-team: exact VIX+spot pair pins the exact day.)
- OI shown as within-day chain percentile bars during play; raw OI at reveal.
- Lot leak eliminated by L7 (always 65). Spot-level era leak accepted (L2).
- Iconic-day blacklist (~10–15 dates: 2024-06-04, 2022-02-24, budget days…) excluded from pool, documented in config.
- **Pre-reveal recognition prompt (MANDATORY v1):** "Did you recognize this day? Date guess:" → near-correct guess sets RECOGNIZED flag → session default-excluded from career analytics.
- Trade-log rows buffered in memory during play; real-dated records written only at reveal. Played-days ledger stores hashed dates.
- Pause-and-lookup = honor system (accepted): pause count/duration logged, "pause profile" shown in session report.
- `tests/test_leak.py`: scripted full session asserts every captured payload ≤ sim-clock and date-free.

## 6. V1 FEATURES (beyond core replay/trading/review/chain/journal)
**Chart spec (Principal order 2026-07-05, implemented):** previous day's FULL chart rendered on the MAIN chart
in continuation ahead of the sim day (both fake-anchored 09:15→09:15, 86400s apart so all timeframe buckets
stay 09:15-aligned); session always opens at sim-day 09:15 with the D-1 tail visible. Indicators pinned to
their own timeframes regardless of displayed TF (values sampled onto displayed candles): session-anchored
VWAP on typical price (index has NO volume — labeled), EMA 9/21 computed on 5-min, RSI(14) Wilder on 15-min
in a sub-pane (30/70 lines). VIX chip = band + intraday %chg from open (band per blinding §5). D-1/EMA/RSI
warm-up seeded from D-1 bars. Bottom panel = selected-position premium chart with TP/SL zones.
| Feature | Effort |
|---|---|
| Indicator pack: VWAP(TP), EMA 9/21 @5m, RSI14 @15m — DONE; CPR + floor pivots, opening-range box | S |
| Bracket orders (SL + target OCO, attached at entry; edits logged for later moved-SL detection) | M |
| Position-sizing calculator: risk % + SL distance → lots, margin-checked, one-click to ticket | S |
| Hotkeys: Space pause, B/S market, F2 flatten, ± speed, ← → step-1-bar (paused), 1–6 timeframe, ? cheatsheet | S |
| Bar-by-bar step mode (paused arrow key advances one bar — chart/chain/margin tick together) | S |
| VIX band strip (per §5) | S |
| One-click ATM straddle/strangle presets w/ combined margin preview, atomic legs | M |
| Sound cues: fill / SL hit / target / margin warning / square-off countdown (bundled WAVs, mute) | S |
| Trade-log export to Excel/CSV — schema FROZEN in v1 (contract for all future analytics/AI-coach) | S |
| Analytics guardrails: Wilson CI on win-rate, bootstrap CI on expectancy, min-N=30 grey-out, regime-segmented views default (VIX band × day-type × era), R only from stated risk (undefined-R excluded), MAE/MFE from bar extremes labeled "≥bounds", speed-band segmentation, RECOGNIZED-flag exclusion | (in P5) |

**V2 backlog:** daily max-loss lockout (L10) + auto-suspension; mistake auto-detection (revenge/overtrade/oversize/moved-SL); multi-leg builder (verticals/condors/4-leg); trailing SL + auto-breakeven; persistent drawing tools (carry into review); forward-only jump-to-time; **OI flow tape + max-pain drift (moat feature — minute-level OI)**; career mode (streaks/milestones/seasons view); day-type classification + opportunity-capture score; **live Greeks P&L attribution ticker (delta/gamma/theta/vega decomposition per bar)**; **counterfactual exit engine** (your exits vs hold/1R/2R/trail policies on real remaining bars); guess-the-regime endgame quiz; AI persona coach report (Dhruv entries / Tara execution / Nikhil red-team, .docx per Principal format); probabilistic partial fills; "manual close only" hard mode; sizing analytics in %/R primary.
**V3:** challenge gauntlets + prop-firm evaluation mode; spaced-repetition retake of failed days; BANKNIFTY mode; shareable session card.

## 7. RED-TEAM REGISTER (30 flaws; key items and their disposition)
BAKED INTO V1: spread-aware fills (was #1 HIGH); server-authoritative clock + devtools acceptance test; client-side aggregation only (pre-aggregated candles = 59-min future leak); timestamp rebasing + hashed ledger + deferred log writes; resume-at-exact-bar (refresh hole); VIX banding; OI percentiles; iconic-day blacklist; recognition prompt + flag; reset=season append-only (survivorship); Wilson/bootstrap CI + min-N; regime segmentation; MAE/MFE as bounds; R-from-stated-risk; single-path counterfactual framing (MFE-capture % is the headline exit metric); parity forward for IV; expiry settlement at 30-min average; per-bar margin + RMS; controlled journal tag vocabulary; speed-band stat segmentation; stressed square-off costs.
ACCEPTED RESIDUALS (documented in-app methodology note): no real-money pain (game stats = upper bound on live); era-guess from spot level; pause-and-lookup honor system; 1-min bar granularity floor; learning-the-tape vs learning-the-market (mitigation: rolling-window stats; ultimate OOS = firm paper desk on live data — game is drill, not proof).
DEFERRED (Principal ruling): loss lockout → v2.

## 8. BUILD PHASES
| Phase | Delivers | Sessions |
|---|---|---|
| **P0 Data foundation** | build_index.py run + gap report reviewed; data_loader.py landmine-enforced; stack decision closed; lightweight-charts fetched | 1 |
| **P1 Replay core** (watchable) | ASGI app + WS tick loop + SimClock pause/speed; blinding.py; live blinded chart 1m–1h + D-1 + PDH/PDL/PWH/PWL + VIX band; hidden-day pick; hotkeys; resync | 2 |
| **P2 Trading** (playable) | Chain endpoint; order ticket + spread-aware fill engine + full cost stack; position book + MTM push; margin + RMS; 15:25 square-off; SQLite persistence + bankroll + registry; **spread calibration vs Angel terminal** | 2–3 |
| **P3 Reveal & review** | Date reveal + entries/exits overlay + what-happened-after; recognition prompt; position_marks → MAE/MFE rollup; expiry settlement path | 1 |
| **P4 Chain intelligence** | IV + Greeks in chain (parity forward); payoff diagram; margin preview in ticket | 1 |
| **P5 Journal & analytics** | Tag UI (controlled vocab); dashboard w/ all §6 guardrails; export; equity curves + season views | 1–2 |
| **P6 Hardening** | test_leak green; test_engine green (fills/costs/margin/settlement/aggregation hand-checked); disconnect QA; OneDrive/WAL check; README; supervised first play-through | 1 |

Total ~10–12 focused sessions. Playable game after P2.

## 9. MODULES & PERSISTENCE
Modules: `config.py` (paths absolute→legacy read-only, capital, cost table, tick, squareoff 15:25, margin params, r, blacklist), `tools/build_index.py`, `tools/fetch_libs.py`, `server/{app,replay,data_loader,blinding,chain,margin,orders,persistence,analytics}.py`, `static/{index.html,app.js,chart.js,chain.js,lib/lightweight-charts...js}`, `run_game.ps1` (sets PYTHONIOENCODING=utf-8, full python path — alias broken; ASCII-only logs, cp1252), `tests/{test_leak,test_engine}.py`, `README.md`.
SQLite `data/fno_game.db` (WAL + busy_timeout; folder "Always keep on this device" — OneDrive lock risk): bankroll, bankroll_resets(seasons), played_days(hashed), sessions, orders(full cost components), trades(MAE/MFE rolled up, exit_reason), position_marks(per-minute, batch-insert per minute), journal, equity_snapshots. events.jsonl = append-only audit (never read by analytics). Crash mid-session = session voided, bankroll reverts, day stays PLAYED.

## 10. RISKS (standing)
cp314 wheels (fallback ready) | OneDrive-SQLite locks | pool size honesty via coverage_gaps | approx-SPAN ±10–20% (labeled) | thin-strike stale marks (badged) | costs-realism drift documented in README | eligible-pool exhaustion → explicit new "season" with disclosure.

## CHANGELOG
- 2026-07-05 (P3/P4/P5 server pass, DESK-100): `server/greeks.py` NEW — Black-76 IV bisection (math.erf, no scipy),
  parity forward, greeks (theta/calendar-day, vega/vol-pt); cached per (ci,strike,cp,hm) in app.
  `server/app.py`: MAE/MFE + risk_rs + r_mult + hold_min + dte per trade (trades-table migration via
  try/ALTER-ADD-COLUMN, additive — old rows null); intraday eq_hist → reveal `equity[]` + `session_id`;
  /api/chain rows extended {iv,delta,theta,vega,oi_pct} (OI as blinded within-window percentile);
  NEW endpoints: POST /api/margin_preview (no-mutation sim), POST /api/basket (ATM straddle/strangle,
  combined-margin precheck, atomic pending legs), POST /api/step (paused single-bar advance),
  GET /api/payoff (expiry+t0 lines, BE, max P/L w/ null=unbounded), GET /api/tags + POST /api/journal
  (controlled vocab, REVEALED-only, journal table), GET /api/analytics (Wilson CI, recognized-exclusion,
  min-N=30 low_n flags, by_hour/dte/reason/tag, seasons), GET /api/export (CSV, post-reveal real dates).
  All existing payloads unchanged; blinding intact (no real dates pre-reveal). Smoke: 44/44 TestClient checks.
