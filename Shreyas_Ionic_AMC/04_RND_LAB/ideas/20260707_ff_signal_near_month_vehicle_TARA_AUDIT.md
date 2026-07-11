# Companion memo — hedge-leg fill audit + live-signal data check
**Owner:** Tara Singh (Execution & TCA) · **Date:** 2026-07-07 · **File type:** companion to `20260707_ff_signal_near_month_vehicle.md` (Aakash's scoping memo) — that file is NOT edited; this is a separate file per the task's own "your call, note which" instruction. Answers pre-registered kill items **NEW-6→NEW-8** (partially) and CIO-1's direct successor question for Candidate B.

## Headline verdicts
1. **Task 1 (hedge-leg liquidity gate): PASSES, decisively — does NOT inherit K-012's disease.** Signal-day-conditioned drop rate for the near-month OTM hedge leg is **2.1% (14/673) full-sample, 0.5% (1/199) forward** under an 8-strike search rule — nowhere near the back-leg's 59.3%/61.3%. Well inside the CIO's pre-registered <20% kill bar (item 1, §6 of Aakash's memo).
2. **Task 2 (does FF fire today): DATA-BLOCKED, honestly — not computable on the current pipeline, for two independent reasons.** No fabricated signal produced. Flag routed to Kavya/Arjun per Aakash's own NEW-7 item.

---

## TASK 1 — Hedge-leg fill/liquidity audit (structure → costs → fills → verdict)

### Structure audited
Candidate B's long leg: near-month (M1) OTM CE, same expiry as the short ATM CE, at a strike selected by Aakash's pre-registered rule — "nearest OTM strike... searched outward from ATM up to a max distance cap (start at 8 strikes)... if no strike clears the floor within the cap, DROP the signal." I audited **every one of the 673 causal FF-signal dates** in `results/S-03/20260705_resurrection/causal_per_trade.csv` (54 large-cap symbols, entry = `ca_D`/`ca_strike`, the causal first-FF-cross day/strike — NOT the old `ga_D` post-back-leg-gate day, since Candidate B has no back leg to gate on) — this is the exact same population Aakash's memo cites, checked at signal time, not a cross-sectional spot-check.

### Method (byte-reused from my own back-leg audit, `fill_audit.py`)
- Loader/tiering reused verbatim: `fa.load_file`, `fa.day_table`, `fa.leg_eval`, `fa.classify` — NORMAL (day-vol ≥0.5× trailing-20-session median of that exact contract), THIN (0.2–0.5×), THIN-ABRUPT (<0.2×), **UNTRADED** (zero/no row that day).
- For each signal, strike ladder = every CE strike ever printed in that symbol's near-month file (full-life listed set — avoids under-counting distance when an HF-schema day simply has no row for a dead-interest strike). Candidates = the 8 nearest listed strikes **above** the short strike.
- **DROP** = none of the candidate strikes (within the stated distance cap) clear UNTRADED that exact day. Two cap widths reported: 1–3 strikes (task's stated candidate band) and 1–8 (Aakash's pre-registered search cap).
- Standing-OI supplementary check on the drop-cohort's candidate slots, same convention as the back-leg audit (no-row vs zero-vol-with-OI vs genuinely dead).
- Code: `results/S-03/20260705_resurrection/hedge_leg_audit.py`. Output: `hedge_leg_audit_per_trade.csv` (673 rows), `hedge_leg_audit_summary.json`.

### Assumed costs
None new — this is a liquidity/fill gate, not a cost re-price. Cost stack for the surviving leg stays at COST_STANDARDS' single-stock near-ATM tier (0.5–1.5% premium) once Gate-4 build prices it; that's Arjun's job next, not this memo's.

### Realistic fill scenario — the numbers

| Cohort | n | DROP (1–3 strikes) | DROP (1–8 strikes) |
|---|---|---|---|
| Full (673) | 673 | **3.7% (25)** | **2.1% (14)** |
| BUILD | 474 | 3.8% (18) | 2.7% (13) |
| **FWD** | **199** | **3.5% (7)** | **0.5% (1)** |

Per-distance UNTRADED/NO_STRIKE rate (full sample, single-strike-only, i.e. "what if you only ever tried distance d and nothing else"):

| Distance | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Untradeable rate | 8.6% | 7.9% | 13.1% | 12.9% | 17.7% | 21.5% | 28.2% | 32.1% |

Reads exactly like Aakash's own 6-name spot-check, now on the full FF-signal population: gradual degradation out to ~6 strikes, then a real slope from 7 onward — but because the pre-registered rule is a **search** (first strike that clears, not a fixed distance), the OR-across-8-candidates drop rate stays low (2.1%) even though any single fixed distance alone would fail 8–32% of the time. **This is structurally the opposite finding from the back leg**, where the problem was binary (a specific 2nd-forward-month contract either trades or doesn't, with no adjacent-strike escape hatch) — here, adjacent-strike substitutability is exactly what saves the vehicle.

Standing-OI supplementary check on the 14 full-sample drops' candidate slots (of the 8 checked per drop): 14.3% had no data row at all, 85.7% had a row with zero volume **and** zero OI, 0% had OI-but-no-volume. These are genuinely dead slots, not quiet-but-real ones — consistent with (not contradicting) the low overall drop rate; it just means when all 8 candidates fail together (rare), they fail for real reasons, not a data artifact.

### Margin & worst-case MTM
Not re-derived here — Aakash's memo (§3) already correctly routes the SPAN read to me for sign-off separately; this audit answers the liquidity gate only, which was the explicit blocking item before any margin/backtest work proceeds. My prior lesson stands: mid/small-cap tails are fatter in fills than backtests, so once Arjun prices Candidate B, the same-day-close vs D+1 fill-timing convention (Aakash's pre-reg spec, defaulting D+1 per lesson 17) should be honored strictly — this audit was run at `ca_D` (signal day) for the liquidity CHECK only; the actual fill price still belongs at D+1 per spec.

### Sim-vs-paper gap
N/A — no paper/live fills exist yet for Candidate B (pre-1-INTAKE, not on PAPER_LEDGER).

### Verdict: hedge leg SURVIVES the liquidity gate at both distance caps, comfortably inside CIO kill item 1's <20% bar
**Candidate B does not inherit K-012's disease.** The back leg's failure mode was a specific OTHER-EXPIRY contract simply not existing in the market that day (59.3%/61.3% dead, no fix available within the same structure). The new hedge leg's failure mode — SAME-expiry strike distance — is continuous and substitutable: when the nearest OTM strike is thin, the next one over usually isn't. Recommend Arjun proceed to Gate-3/4 build using the ex-ante version of this exact rule (gate on trailing-5-session median per Aakash's spec, not same-day realized volume, since same-day is only knowable in hindsight — this audit deliberately checked same-day to match the "was it real" question, but the PRODUCTION gate must be ex-ante; flag this distinction explicitly to Arjun so it isn't silently conflated).

---

## TASK 2 — Does the FF signal fire right now (Jul-2026), and is it computable?

**Verdict: DATA-BLOCKED. Two independent, catalogued reasons — reported honestly, not forced.**

### Blocker 1 — the signal's own spot-price series is stale since 2026-01-22
`ff_v3_causal.py`'s FF computation calls `dispersion_strategy.atm_iv_asof(df, spot, day, exp)`, and `spot` comes from `dispersion_strategy.stock_close()`, which reads **`swing_momentum/data/hf_stock_minute/day/train-00000.parquet`**. Verified directly (not just per the catalog note): max date in that file = **2026-01-22**, for every symbol including the FF universe (checked CANBK explicitly — last row 2026-01-22). This exact staleness is already catalogued (`05_DATA_OFFICE/DATA_CATALOG.md` §2: "Stock daily (HF) → 2026-01-22 (stale tail)"). **Implied vol back-out needs a spot price; there isn't one past Jan-22 in this pipeline's own source.** I did not find a wired-in fresher substitute on disk under this pipeline (an "Angel bulk 2026" 477–500/500-stock OHLCV through Jul-2026 is referenced in `RESUME_TOMORROW.md` line 155/163 as [books], but I could not locate its file path on disk in this session — Kavya's provenance, not mine to invent a path for).

### Blocker 2 — even with a fresher spot, the back-month (2nd-forward) IV history for the CURRENT front/back pair is too thin for the signal's own lead grid
Checked `intraday_options_strategy/datasets/angel_capture_2026/day/` directly (this is the live-forward capture DATA_CATALOG flags for "Jul-2026 → ongoing"):
- **87/210 F&O symbols captured** (not the full universe) — but **53/54 of the validated large-cap FF universe ARE covered** (only JSWSTEEL missing), so universe breadth is not actually the binding constraint here.
- All checked symbols carry the same expiry pair: **front = 2026-07-28, back = 2026-08-25** (verified across 15 symbols, uniform).
- Front-month file (CANBK sample): 29 trading days, **2026-05-11 → 2026-07-03**.
- **Back-month file (CANBK sample): only 3 trading days, 2026-06-29 → 2026-07-03.** The back-month-of-the-current-pair only started accumulating history when it became "next month" at the June expiry rollover (~Jun 24) — it has under 2 weeks of life.
- The FF signal's frozen spec (`ff_v3_causal.py` LEADS=[30,25,20,15,12] sessions-before-front-expiry) needs `iv2` (back-month ATM IV) at candidate days going back up to 30 sessions before the Jul-28 expiry — i.e., roughly mid-June. **The back-month contract didn't exist in the capture set that far back.** Only the closest 1–2 leads (≈15/20-session marks, landing right around today/late-June) have any chance of both front AND back data overlapping — and the very-near leads (12/15 sessions ≈ mid-July) haven't happened yet as of today (2026-07-07), so there is nothing to compute there either.
- Additionally, capture itself is **~2–4 calendar days stale** (last row 2026-07-03 vs today 2026-07-07) and **carries no `oi` column at all** (schema: timestamp/open/high/low/close/volume/strike/option_type/trading_day) — confirmed by direct read. This matters for the sub-task: even if a signal had fired, **OI cannot be pulled from stored data** — it would require a live Angel SmartAPI quote call, not a file read.

### No signal reported, by design (SUPERSEDED — see correction below)
Given both blockers, I did not run the FF grid computation and report a number — that would be forcing a fake answer through a pipeline I've just shown can't currently produce one honestly. Routed to Kavya (fresher spot source) and Arjun. **This conclusion was based on cached FILES only and was incomplete — corrected same-day below using the live API.** The staleness/thinness diagnosis of the FILES themselves stands (still true, still useful); the "therefore no live signal is computable" inference was wrong for the point-in-time question.

---

## CORRECTION (2026-07-07, same day) — Task 2 redone on the LIVE Angel API, not cached files

My first pass concluded "DATA-BLOCKED" from two stale/thin **files**. Correctly challenged: the firm has a live, working Angel SmartAPI connection (same creds/pattern as `C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\daily_capture.py`) that I hadn't used. Redone properly — logged in live, pulled real spot + FULL quotes (LTP+OI+volume, confirmed field names: `opnInterest`, `tradeVolume`) for all 54/54 FF-universe names, front (2026-07-28) and back (2026-08-25) ATM CE. Code: `results/S-03/20260705_resurrection/live_ff_check.py`. Output: `live_ff_snapshot_20260707.csv` (54 rows).

**Result: the "does it fire right now" question is NOT access-blocked — it never needed historical depth, only today's two IV points.** Live snapshot, computed exactly as `ff_v3_causal.py` does (`implied_vol` + `forward_vol`): **8/54 names show FF≥0.25 today** — COLPAL 0.98, ICICIBANK 0.90, BANDHANBNK 0.64, ULTRACEMCO 0.58, TECHM 0.50, APOLLOHOSP 0.49, TATACONSUM 0.36, TCS 0.30.

**But 7 of those 8 are almost certainly artifacts, not signal — and this is exactly my lane.** Back-month (M2) OI/volume for COLPAL, ICICIBANK, ULTRACEMCO, APOLLOHOSP, TATACONSUM = **0/0** (BANDHANBNK: OI 7,200/vol 0). Their `iv2` is backed by a quoted LTP on a contract with **zero live trading interest today** — a stale/theoretical print feeding the IV back-out, the same "unpriceable garbage in" pattern my charter exists to catch. **Only TCS (FF=0.30) has a back-month leg that is genuinely live-traded right now**: OI 123,750, volume 182,925. That is the one name I'd call a real, tradeable signal today.

**TCS hedge-leg sanity check (live, real numbers) — short ATM + 5 candidate OTM CE strikes, 2026-07-28 expiry:**

| Strike | Distance from ATM | LTP | OI | Volume |
|---|---|---|---|---|
| 2100 (short ATM) | 0 | 65.70 | 3,332,700 | 6,404,850 |
| 2120 | 1 | 56.75 | 679,950 | 1,494,450 |
| 2140 | 2 | 48.00 | 643,500 | 958,275 |
| 2160 | 3 | 40.25 | 1,403,550 | 1,047,600 |
| 2180 | 4 | 33.30 | 215,100 | 490,725 |
| 2200 | 5 | 28.60 | 2,925,225 | 3,011,850 |

Every candidate is deeply liquid — consistent with Task 1's finding that this large-cap name's near-month strike ladder is not the failure mode.

**Structural test (the part that DOES stay blocked, and it's a market-reality gap, not an access gap):** requested the SAME 80-day `ONE_DAY` candle window `daily_capture.py` itself requests, live, for the back-month ATM CE on two names — **ABB: 0 candles returned at all** (despite a live LTP quote existing) — **TCS (the most liquid name in the universe): only 5 candles, 2026-07-01→2026-07-07, all with volume, earliest non-zero-volume day = 2026-07-01.** Even the best-case, most-liquid name has under a week of real trading history on its 2nd-forward-month contract. This is NOT a stale-cache problem — the live API was asked directly and returned the same thinness the cached file showed. **A live snapshot answers "today"; it structurally cannot answer "did it cross 0.25 two/three/four weeks ago" for the back leg, because that contract has not been trading long enough yet, live or cached — this is a market-microstructure fact (2nd-forward-month stock options simply don't get traded interest until they're closer to their own expiry), not a data-access failure.**

**Corrected verdict:** live signal computability is **split, precisely**: (a) point-in-time "does it fire today" — **YES, fully live-computable**, and it does fire for 8 names, but only 1 (TCS) survives a liquidity sanity-check on its own iv2 input; (b) "did it fire in the last few weeks" (the lookback reconstruction) — **structurally blocked**, confirmed by live query, not merely under-resourced. Route to Arjun: any live-signal claim on this vehicle must gate on back-month OI/volume >0 before trusting iv2, exactly as Aakash's NEW-7 item anticipated — TCS today is the one name that would currently pass that gate.

## Files
- `results/S-03/20260705_resurrection/hedge_leg_audit.py` — Task 1 audit code (reuses `fill_audit.py` loaders verbatim).
- `results/S-03/20260705_resurrection/hedge_leg_audit_per_trade.csv` — 673 rows: per-signal short strike, 8 candidate distances × (strike/tier/volume/OI), drop_1_3/drop_1_8 flags.
- `results/S-03/20260705_resurrection/hedge_leg_audit_summary.json` — headline drop-rate numbers by cohort.
- Task 2 (initial, file-based): no artifacts (deliberate) — verified against `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` (max date check) and `intraday_options_strategy/datasets/angel_capture_2026/day/*` (87-symbol listing, CANBK front/back date-range check, schema check).
- Task 2 (corrected, live API): `results/S-03/20260705_resurrection/live_ff_check.py` — live login (`angel_capture/creds.json` pattern) + bulk FULL quotes + FF computation for 54/54 names. `results/S-03/20260705_resurrection/live_ff_snapshot_20260707.csv` — 54 rows: spot/strikes/LTP/OI/volume/iv1/iv2/ff per name, live 2026-07-07. `results/S-03/20260705_resurrection/live_tcs_hedge_check.py` — TCS OTM CE hedge-strike ladder live OI/volume pull.

**Tags:** [DATA] Task 1 drop-rate table; Task 2 all file paths/dates/row counts and the live snapshot numbers (verified directly, this session, both file-based and live-API passes). [INFERENCE] the "7/8 are LTP artifacts" call is a direct read of 0/0 OI+volume, not a guess — flagged as [DATA]-grounded inference. [OPINION] none.
