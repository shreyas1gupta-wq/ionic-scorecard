# FnO Replay Game

Intraday NIFTY weekly-options paper-trading simulator. Replays a **random hidden historical
day** bar-by-bar from our real 1-min data (2019+). Training drill for the Principal — 100%
local, offline, no real money anywhere near it. Full spec: `ROADMAP.md` (v1.0 FINAL).

---

## Setup (one-time)

Everything runs on the already-installed Python 3.14 (`fastapi`, `uvicorn`, `pandas`,
`pyarrow`, `pytest` are present). If a fresh machine ever needs it:

```
C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pip install fastapi uvicorn pandas pyarrow pytest httpx
```

Rebuild the day-pool index after any change to the underlying option/spot parquet data
(idempotent, writes `data/eligible_days.json`, `data/lot_sizes.json`, `data/coverage_gaps.json`):

```
cd fno_game
C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe tools\build_index.py
```

Market data is read **read-only** from the legacy `intraday_options_strategy/` folders —
nothing is copied or modified there.

## Launch

```
powershell -ExecutionPolicy Bypass -File run_game.ps1
```

Opens `http://127.0.0.1:8787` and starts uvicorn (foreground). Equivalent manual line:

```
cd fno_game\server
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUNBUFFERED="1"
C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8787
```

(`python` alias is broken on this machine — always use the full path.)

## Controls & hotkeys

| Key / control | Action |
|---|---|
| `Space` | Pause / resume |
| `ArrowRight` | Step one bar (only while paused) — chart, chain, fills, margin all tick together |
| `B` / `S` | Market BUY / SELL the contract currently in the ticket |
| `F2` | Flatten all positions |
| `+` / `-` | Faster / slower replay (1–60 s per sim-minute) |
| Timeframe buttons | 1m / 3m / 5m / 15m / 30m / 1h (client-side aggregation from released bars) |
| Chain cell click | Loads that strike+side into the ticket |
| Position row click | Shows its premium chart with TP/SL zones in the bottom panel |
| `Straddle` / `Strangle ±` | One-click ATM basket presets (combined margin pre-check, atomic legs) |
| Risk% + `use` | Position-sizing calculator: risk % of equity + SL distance -> lots |
| `HLine` / `Trend` / `Clear` | Drawing tools |
| Indicator chips | VWAP(TP) · EMA 9/21 (pinned 5m) · RSI14 (pinned 15m) · CPR · OR15 |

New entries are blocked after 15:20; everything is force-squared-off at 15:25 through the
normal (stressed) fill engine.

## Game rules — blinding & honor system

- The date is **hidden**. Timestamps are rebased to a fake epoch; the UI shows HH:MM only.
  VIX shows as a band, OI as within-day percentiles. Real strikes and prices are shown (L2).
- **No pausing-to-Google.** Pauses are logged; the honor system is the only enforcement.
- At session end you get the **recognition prompt** ("did you recognize this day?"). Answer
  honestly — recognized sessions are excluded from career analytics by default. Gaming this
  only corrupts your own stats.
- One bankroll, persistent across sessions (start Rs 10,00,000). Reset = a **new season**;
  history is append-only, never deleted. An abandoned day still counts as played.

## Methodology notes (read before trusting any number)

- **VWAP is typical-price VWAP** — the index has no volume; it is labeled as such.
- **Margin is approximate SPAN** (formulas in ROADMAP §4.3). Real exchange SPAN deviates
  ±10–20% in stress. Expiry day carries a 1.3x short-leg multiplier.
- **Costs are today's exchange rates applied uniformly across all eras** (L5/L7), lot size
  is always 65, freeze qty 27 lots/order. Historical prices, current frictions.
- **1-min bar granularity floor**: fills model spread/adverse selection at bar level
  (ROADMAP §4.1); no intrabar path exists. Market orders fill at NEXT bar open +/- modeled
  half-spread; zero-volume bars don't fill; gapped-through SL-limits MISS.
- **MAE/MFE are bounds, not truths** — computed from per-minute marks, labeled ">= bounds".
- **Stats guardrails**: Wilson 95% CI on win rate; buckets with n < 30 are greyed out
  (`low_n`); R-multiples only from *stated* risk (no SL = excluded from R stats);
  recognized sessions excluded by default.
- Game stats are an **upper bound** on live skill: no real-money pain, and repeated play
  learns this tape. Ultimate out-of-sample = the firm paper desk on live data.

## Data provenance

Spot/options/VIX 1-min parquet from the HF `hf_index_options_1m` dataset (tz-fixed to IST,
pre-open auction bars dropped at the loader boundary — see `server/data_loader.py`); lot-size
history cross-checked against 402 NSE bhavcopies; eligible-day pool and exclusion reasons in
`data/coverage_gaps.json`.

## Tests

```
cd fno_game
C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest tests -q
```

- `test_engine.py` — hand-computed costs / margin (naked, vertical, straddle, expiry-day
  multiplier) / Wilson CI / Black-76 parity + IV round-trip / tick rounding.
- `test_leak.py` — scripted full session; asserts no ISO date or weekday name in ANY
  pre-reveal payload, released-bar count == steps taken, chain window +-200 with blinded
  OI only, export hides the just-ended session until reveal.
- `test_frontend.py` — static serving + every element id referenced in app.js exists.
- Tests write to a **scratch DB** (`app.DB` redirected before `db_init`); the production
  `data/fno_game.db` is never touched by test sessions.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `database is locked` / stale reads | OneDrive is syncing the DB. Right-click `fno_game/data` -> "Always keep on this device". WAL sidecar files (`-wal`, `-shm`) are normal — never delete while the server runs. |
| Port 8787 busy | `Get-NetTCPConnection -LocalPort 8787 \| Select OwningProcess` then `Stop-Process -Id <pid>`. |
| "eligible pool exhausted" | Every day in the pool has been played. Deliberate design (no-repeat). Start a new season: reset the bankroll, then clear the `played` table ONLY if the Principal explicitly wants to re-play days (stats from replays are tainted). |
| Blown-up career (equity <= 0) | Career freezes by design. Click "Reset bankroll (new season)" — history is kept, season counter increments. |
| Chain rows all "—" / greyed | Thin strikes: mark older than 10 min blocks entries, older than 30 min blanks price/IV. Not a bug — exit-liquidity realism. |
| `python` not found | The bare alias is broken on this machine; always use the full `pythoncore-3.14-64\python.exe` path (run_game.ps1 does). |
| cp1252 UnicodeEncodeError in console | Set `$env:PYTHONIOENCODING="utf-8"` (run_game.ps1 does). |
