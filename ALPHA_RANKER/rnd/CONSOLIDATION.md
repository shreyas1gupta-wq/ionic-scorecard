# ALPHA_RANKER — R&D Consolidation (money-first, cross-regime honest)

> One research loop: foundation (PIT panels + shared anti-overfit harness) → 50 pre-registered hypotheses
> across 10 workers → money-first re-scoring → 21-yr cross-regime confirmation. This is the honest verdict.

## >>> RED-TEAMED + DSR-CORRECTED SURVIVORS (supersedes in-sample numbers below; see rnd/SURVIVORS.md, scoreboard_v2.csv)
HARNESS FIXED (v2): DSR per-family (not global-318); verdict signed-IC (recovered low-vol H010 & size H028); horizon annualization fixed — earlier ×12 inflation corrected (e.g. EY net LS ~2%/yr, NOT 34%; magnitudes now realistic single-digit %/yr decile spreads, ranking unchanged).
- **EARNINGS YIELD = THE ANCHOR** — robust 1Y & 5Y, bear IC > bull IC, red-team found NO fragility. Value is the backbone.
- **Residual (sector-relative) momentum + MA-65 slope** — real 1Y edge BUT red-team: FRAGILE in high-vol (momentum-crash) → MUST be regime-gated down when vol spikes.
  - CONTINUOUS regime overlay TESTED (21yr): WINS on signal (IC_IR 1.18; bear IC 0.222 vs static 0.038, ~6x) but LOSES net-of-cost.
  - RANK-BAND FIX TESTED & FAILED (corrects earlier "one fix away" claim — that was WRONG): banding cut turnover 0.31→0.19 and kept ~5.5x bear-IC, but net-of-cost got WORSE. ROOT CAUSE (decomposed): the overlay trails static on GROSS return (2.035 vs 2.130) BEFORE cost — cost was never the problem. The defensive-tilt blend lifts full-cross-section & bear IC but DILUTES the extreme top-minus-bottom decile spread that a long-short monetizes. No band fixes a gross-return shortfall. → **PARKED the return-blend overlay (do not churn more variants).**
  - REFRAME (the real lesson): regime info monetizes as RISK/EXPOSURE CONTROL (scale momentum exposure DOWN in bear/high-vol — like the %>200DMA breadth scalar that halved maxDD, + India-VIX regime), NOT as return-blending into the score. Use regime to size, not to select.
- **DCF + reverse-DCF gap** — robust 5Y value (stable across all 24 WACC×g cells).
- **Net-share-issuance (1Y, NEW)** — IC_IR 0.95, era-stable (durable), balance-sheet-only, ORTHOGONAL to momentum/value. Caveat: proxy=equity-capital %chg (bonus/split noise ~8%), not true shares. **Asset-growth (5Y, NEW)** — IC_IR 0.40, strengthening post-2015 (over-investment anomaly). [orthogonality-vs-EY correlation check PENDING before weight-book]
- **Market-state EY-vs-history + small-cap-tier EY** — 5Y exposure/regime signal (M1 rho 0.30/0.25).
- **India-VIX regime** — buy-the-vol-spike 1Y overlay input.
- **Cross-sectional seasonality (NEW, CANDIDATE)** — IC_IR 0.44, +4%/yr, orthogonal, modest; clean on EVENT-TIME lag test (standard +1-rebalance lag mismatched for calendar factors). Composites (Greenblatt/GARP/earn-stability/SMILE) all KILL — none beats plain EY (ROC leg inverted; earn-stability inverted; SMILE net-neg). Plain value wins again.
- **Cumulative CFO/PAT authenticity (NEW, forensic-quality leg)** — IC_IR 1.14 (1Y); BEATS existing accruals(H022) & cash-conv(H045) on incremental bar; orthogonal Marcellus-style "earnings backed by cash over years". 5Y (4.50) = thin-window artifact, directional only. Anti-findings this bucket (honest): ROCE-streak WRONG-SIGN (−0.79, Marcellus longevity fails — priced-for-perfection); deleveraging = dead-cat not repair (killed); under-owned-value doesn't beat EY (+stale 2023 shareholding).
- **QMJ Quality-Minus-Junk composite (NEW, quality backbone)** — PROMOTE* 1Y IC_IR 0.77 / 5Y 1.74, monotone, gates clean, orthogonal to EY (corr 0.08). BEAR-DEFENSIVE (holds bear IC where momentum crashes; matches low-vol in hivol at 5Y). KEY LESSON: raw quality legs (op-profit, ΔROA) are fragile/inverted STANDALONE in the junk-bull — durable only rank-averaged into QMJ (quality+growth+safety+payout). Resolves the "quality inverted" puzzle: it was single-leg fragility, not quality failing. Buffett's-alpha parked (QMJ duplicate). → QMJ = the defensive leg regime-SIZING wants (heavier in bear/hivol).
- **BAB betting-against-beta (NEW, selection leg)** — signed IC_IR 0.45(1M)/1.03(1Y), gates clean, works on gross. General low-risk premium (holds in India via beta-rank, unlike raw low-vol which was inverted). Defensive by construction, not bear-extra. Idio-vol=WEAK(cost); MAX-lottery=parked(1M lag-fail, nets ~0).
- **%>200DMA breadth scalar (RISK layer, NEW)** — conditions forward VOL not return (IC -0.3/-0.4, lag-clean); as a gross-exposure scalar HALVES maxDD (-52%->-26%), Sharpe 0.56->0.62. Stacks ON TOP of alpha factors (scale exposure by breadth). Killed as non-additive: NH-NL, breadth-divergence, dispersion.
- KILLED as bull-only artifacts (21yr sign-flip): Weinstein stage-2 (H009), vol-scaled-mom at 5Y. 1M: structurally unconfirmed (no 21yr intra-month cube).
- Honest magnitudes: these are MODEST edges (low single-digit %/yr net LS spreads). Real, cross-regime, defensible — not the bull-inflated figures.

## RESURRECTION CANDIDATES (real signal, blocked only on data — chase when data lands)
- **Promoter-buying drift** — IC_IR 1.33, mono 0.72, gates CLEAN, correct sign, but only 17% obs coverage (shareholding stale 2023-12). RESURRECT when fresh NSE shareholding/SAST data is pulled (home-network). Strong candidate.
- (FII/DII accumulation KILLED — wrong sign, contrarian, not a drift signal.)

## THE DURABLE MODEL (survives 2008/2011/2020 bears, not just the 2021-26 bull)
Combine by SIMPLE RANK-AVERAGE (ML/ridge overfits; forced interactions destroy strong legs), regime-aware:
- **Residual momentum (12-1, FF-neutralized), PLAIN** — least fragile; positive IC in real bears at 1Y. Core. CORRECTED: peer-relative was a 5yr-BULL-PANEL artifact — on 21yr PLAIN (0.69) BEATS sub-sector peer-relative (0.55). Use plain. (Authoritative model = FINAL_MODEL.md; this older section superseded where they differ.)
- **MA-slope trend (65d; slope > stack > distance out-of-sample)** — holds in bears; slope survives 5Y better than stack.
- **Earnings yield (value)** — holds, and HIGHER IC in bears (0.156) than bulls (0.042); the defensive workhorse. (5Y value tentative: PIT fundamentals thin pre-2012.)
Turnover-banded (rank-band hysteresis) to keep cost drag low. Horizon: this is primarily a **1Y** model; 5Y is genuinely under-determined by available data.

## REGIME MAP (Principal's "regime-gold" thesis — CONFIRMED, causal/lookahead-free)
- Bull / calm / low-vol: momentum + trend win.
- Bear / high-vol / flight-to-quality: value(EY), quality, low-vol, low-beta win; momentum crashes (IC -0.09..-0.17).
- Quality is INVERTED in the 2021-26 junk-bull (mono -0.9) — expected to normalize (+) in bears; it's a regime leg, not dead.
- CAVEAT: the naive DISCRETE regime-switch does NOT beat holding momentum (doubles turnover, eats the gain) and the 5-yr sample has too few bear months (3/61). FIX for wave-3: continuous regime-PROBABILITY overlay (magnitude-preserving) + re-test on the 21-yr panel where bears are plentiful.

## BULL-ONLY ARTIFACTS (unmasked by the 21-yr panel — would have been false promotes)
- Weinstein stage-2: PROMOTE* in-sample → fails gate & negative 5Y on 21-yr. Dead outside 2021-26.
- Vol-scaled momentum: monotonicity 0.99→0.07 at 5Y — a 1Y-only effect.
- 65-vs-50: 65 wins but margin shrinks to 0.007-0.036 OOS — real, marginal; the crowding RATIONALE is not supported (generic longer-MA effect).

## TRAPS (dead across regimes)
Raw growth CAGR (growth-trap, negative), short-term mean-reversion (K confirmed), forced interactions, PEAD at monthly frequency (needs event-time), beta-standalone.

## HARNESS FIXES NEEDED (gates were too academic — Principal directive: money not PhD)
1. **PBO/CSCV** structurally saturated (~1.0) on our monthly, return-overlapping, few-block sample → ADVISORY only, never a hard kill. DONE (money-first scorer).
2. **DSR** uses a GLOBAL cross-family trial count (300+) → crushes every factor to ~0. Fix: per-independent-family trial count, or drop as a hard bar.
3. **verdict() uses UNSIGNED IC_IR** → auto-kills negative-expected-sign factors (size, low-vol, quality-in-bull). Use signed.
4. **1Y net-return annualized ×12 uniformly** → magnitudes inflated (rankings OK).
5. **lag-test full-period shift** mismatched for event-window factors → use event-time test for those.
6. HARD GATES that WORK and stay: one-day-lag lookahead + placebo. They correctly killed mean-reversion & caught event leakage.

## DATA ASSETS BUILT (reusable, quarterly-refreshable)
- `panel.parquet` (5yr, 1M research), `panel_long.parquet` (21yr, 1Y/5Y + bears), cubes (short+long).
- `MASTER_fundamentals_pit.parquet` (4,613 co, FY02-26, ~2,079 fresh) + builder; `sector_map.parquet`.
- Shared harness + money-first scorer + regime-gold scoreboard (259 cards).
- Full NIFTY-750 production scoring engine (`run_universe.py`).

## CLEANUP-REMAINING-UNTESTED PASS (2026-07-17, tick worker)
Confirmed prior IDG-G/IDG-I coverage is near-total (cross-checked cards + FINAL_MODEL §4 rejected-list +
builders_w2_momq/seas/issuance headers) — only 3 genuine stragglers remained buildable from on-disk data,
all now tested, all KILL:
- **W2S-11 sector relative-PE + momentum rotation** — 15 clean-history NSE sector indices (2016-2026), IC_IR
  ~0.03, lag-test fails (small-N=15 IC series unstable), tilt net-of-cost excess -12%/yr vs equal-weight-sector
  benchmark. Dead on both the hard gate and its own pre-registered cost kill.
- **W2S-06 max-pain magnet into expiry** — index-level NIFTY, front-contract max_pain vs spot, near-expiry
  (dte<=2, n=153) pull not distinguishable from a shuffle-null (p=0.134). No magnet effect measurable at this
  sample size. Coverage caveat: source has only 248 distinct trade-dates in 2021-06..2024-07 (~33% density).
- **IDG-I-15 sector-breadth rotation** (participation, not price/valuation) — built off panel_long's own
  22-sector column + cube_close_long 200DMA breadth, harness-evaluated 1M/1Y: IC_IR both horizons <0.20
  AND lag_test_delta fails (0.92 @1M, 0.35 @1Y) — placebo-clean so not raw lookahead, just gate-unstable.
Cards: `rnd/cards/W2S11_sector_relpe_mom_1M.json`, `W2S06_maxpain_magnet.json`, `IDG_I_15_sectorbreadth_{1M,1Y}.json`.
Data-blocked (not attempted, correctly left parked): single-stock options-flow cross-sectional test (thin/patchy
210-symbol coverage, already flagged in `W2_OPT_DATA_COVERAGE.md`), social/alt-data ideas (no feed on disk).

## WAVE-3 REJECTED-SOURCES RESURRECTION PASS (2026-07-17)
- **Event-time PEAD — CONFIRMED DEAD, not a frequency artifact.** Re-tested at true event-time (one row
  per real earnings print, `[+2 trading days, +45 calendar days]` market-adjusted abnormal return vs
  NIFTY500, n=2,642 valid events 2020-2025, from `np_surprise` = actual vs own-trailing-4Q-trend). IC
  -0.003 (p=0.87), non-monotone deciles (-0.15), hit rate 0.515 (coinflip), sub-window drift flat/negative
  across [+2,+10]/[+10,+20]/[+20,+45] (no building drift). Placebo clean but irrelevant — there is no
  signal to placebo-test. The 2026-07 monthly-panel kill (`W2_event_pead_sign_1M`, IC_IR -0.19) was NOT a
  frequency-mismatch artifact; PEAD genuinely does not exist in this data at either grain. Script:
  `rnd/lib/run_w3_pead_eventtime.py`, card `rnd/cards/W3_pead_eventtime.json`. **PARKED for good, no
  further granularity variants** (this closes the "needs event-time" caveat honestly).
- **Quality-in-bear/high-vol GATE — REVIVES the sizing use.** `build_qmj_composite` (unchanged, no re-fit)
  restricted to dates where `regime_trend=='bear' OR regime_vol=='high'` (causal, panel's own trailing
  regime tags), evaluated via the shared harness on `panel_long`: IC_IR 0.44 (1Y, n=33,792/63 dates) / 1.57
  (5Y, n=27,963/55 dates), monotonicity 0.87/0.90, lag_test_delta 0.048/0.023 (clean, <<0.25), placebo_ic
  ~0.0006/0.003 (clean). Both hard gates (lag+placebo) PASS cleanly — the harness's literal verdict string
  says KILL only because of PBO 0.97/1.00, which CONSOLIDATION's harness-fix #1 already disclosed as
  structurally saturated on this sample and ADVISORY, not a hard kill (per this wave's own brief). Net: the
  SIZING framing (heavier quality weight in bear/high-vol, flat otherwise) is a genuine, clean, causal
  result — confirms QMJ's bear-defensiveness is usable as an exposure dial, not just descriptive. Script:
  `rnd/lib/run_w3_qualgate.py`, cards `rnd/cards/W3_qualgate_1Y.json` / `_5Y.json`. Caveat: gross/net returns
  in the card are inflated by the harness's known annualization-on-a-sparse-subset math (few active dates)
  — do not quote the ann_return_LS numbers outside this context; the IC/lag/placebo/monotonicity block is
  the honest part of the result.

## WAVE-3 QUEUE (backlog_scout.json W2S-01..15 + redesigns)
Continuous regime-probability overlay; quality-in-bear gate; event-time (daily) PEAD; FII/DII & promoter-buying drift; sector-momentum + peer-relative fundamentals (re-run — eval didn't complete); market-state 5Y valuation layer (running); DSR per-family fix; relative PIT cap-tiers everywhere (microcap 4th lens).

## ADOPTION GATE (not yet crossed)
Nothing enters production weights until: OOS-survivor + red-team pass + IC memo (CIO+FM). The durable core above is the CANDIDATE set for that memo — pending the DSR-fix re-score and the continuous-overlay regime test. Do NOT deploy on in-sample shine.
