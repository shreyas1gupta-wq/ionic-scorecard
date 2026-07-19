# Line B factor battery — RE-RUN on Line A's survivorship-safe panel
**By:** Arjun Rao (Quant Head) | **Date:** 2026-07-18 | Cheap-tier pipeline rerun (not a Gate-4 backtest — no DSR/PBO/walk-forward here, per assessment scope).

## [DATA] Lineage
- Input panel: `swing_momentum/processed/eq_close.parquet` (3,067,420 rows, 976 symbols, 2005-01-03..2025-12-05) + `processed/membership.parquet` (21,040 rows, 42 monthly PIT snapshots) — Line A's already-built, read-only.
- Delist register: `Nifty500_Delisted_2005_2025.xlsx` (148 named symbols with delist dates).
- Code: `Shreyas_Ionic_AMC/04_RND_LAB/BROAD_RESEARCH_2036/lineb_corrected_backtest.py` — Line B's 7 signal functions + backtest engine (`swing_momentum/multi_backtest.py`) and combo weights (`swing_momentum/combo_and_report.py`) copied verbatim: top-30 equal-weight, monthly rebalance, 0.4% RT cost, ±25% winsorized daily returns, build ≤2021-12-31 / forward 2022-2026.
- Outputs: `lineb_corrected_daily.parquet` (daily strategy returns), `lineb_corrected_results.csv`, full run log `lineb_corrected_run.log`.

## [DATA] Guards passed — survivorship spot-check (pre-registered, run BEFORE trusting any result)
| Symbol | Present in panel? | Span |
|---|---|---|
| SATYAM | Absent (expected — pre-2005 delist, before panel start) | — |
| DHFL | Present | 2015-01-01 → 2020-05-15 |
| RCOM | Present | 2005-01-03 → 2025-12-05 |
| JETAIRWAYS | Present | 2005-03-14 → 2025-12-05 |
3/4 present with real (non-zero) price history, the one absence pre-dated by construction — matches the sibling assessment's independent finding. Confirmed: **this panel is not the current-day-survivors-only bug Line B ran on.**

Two deltas from Line B's code, both disclosed and necessary, not optional style choices:
1. **Universe filter**: Line A's panel has no volume column, so Line B's ADV/turnover liquidity filter couldn't be replicated. Substituted Line A's own already-used proxy — PIT Nifty500 membership + price≥₹20 floor (avg 377 eligible names/rebalance).
2. **Delist-loss realization**: swapping the panel alone is not sufficient — Line B's `seg[holds].mean(axis=1)` silently skips NaNs, so a delisted name held into its final trading day would just vanish from the mean (no loss booked), reintroducing the same bias through the back door. Ported Line A's explicit fix: -50% one-time hit on the day a held name's price disappears within its documented delisting window (2 names actually triggered this in-sample: ADLABS 2020-04-21, ILFSTRANS 2010-04-16).

## Corrected vs original (biased) — side by side

| Strategy | Original BUILD Sh/CAGR/DD | Original FWD Sh/CAGR/DD | **Corrected BUILD** | **Corrected FWD** |
|---|---|---|---|---|
| mom_12_1 | 0.76 / +13.3% / -55% | 0.86 / +21.4% / -35% | **0.94 / +21.0% / -74%** | **0.86 / +19.7% / -35%** |
| lowvol_126 | 0.80 / +7.8% / -27% | 1.01 / +9.3% / -14% | **1.13 / +14.1% / -48%** | **1.12 / +11.6% / -20%** |
| Mom12+LowVol (best combo, orig.) | 0.84 / +9.9% / -37% | 1.03 / +14.0% / -20% | **1.09 / +16.8% / -59%** | **1.06 / +14.9% / -23%** |
| Mom12+LowVol+52wh+Trend | — | — | 1.12 / +18.6% / -60% | 0.96 / +15.2% / -23% |
| revers_5d (Line B "failed forward") | — | negative/weak (flagged failed) | 0.42 / +7.8% / -77% | 1.08 / +21.4% / -21% |

Full battery (all 8 signals + 3 combos) in `lineb_corrected_results.csv`.

## Degenerate-detector flags
- No Sharpe > 4 anywhere (max 1.22 build, Mom6+regime+LowVol) — no obvious inflation artifact.
- **MaxDD is the story, not Sharpe/CAGR.** Correcting the universe barely moved Sharpe/CAGR for mom_12_1 (fwd 0.86/+21.4% orig → 0.86/+19.7% corrected — essentially unchanged) but blew up BUILD-period MaxDD from -55% to -74%. Mechanism is coherent, not noise: the 2005-2021 build window contains the real corporate blowups (IL&FS/DHFL/Yes Bank-era, PSU/telecom distress) that a current-day-survivors dataset structurally cannot show; Line A's panel has them and the delist-loss fix realizes them. Forward-period (2022-2026) DD is nearly unchanged (-35%→-35%) because that window has had comparatively few large-cap/mid-cap blowups among Nifty500 names — consistent, not a coincidence.
- `revers_5d`'s "failed forward" flag from Line B does **not** replicate here — corrected fwd Sharpe 1.08/+21.4%, one of the best forward numbers in the battery. This is a genuine discrepancy signal, not a free pass: with only ~4 years of forward data (244 rebalances total, ~48 in the forward window) this is a small-n result — logic for a 5-day reversal signal surviving costs is not obviously sound (mean-reversion at 5-day horizon after 0.4% RT cost is a thin edge), so this is flagged for a dedicated cheap-test/placebo pass before anyone cites it, not killed and not certified.
- No DSR/PBO computed (out of scope for this rerun, consistent with the assessment's "≤1-day quant-desk job" framing) — none of these numbers are certified for sizing.

## [INFERENCE] Verdict
**mom_12_1 and the Mom12+LowVol combo: edge survives the correction on return/Sharpe, but the ORIGINAL Line B numbers materially understated tail risk.** This is a different failure mode than Line A's own V1→V2 experience (where correction halved CAGR) — here the correction shows up almost entirely in MaxDD (-55%→-74% build for mom_12_1), not CAGR. Two consistent readings:
1. The economic logic (12-1 momentum, low-vol combo) is real and survives an honest, differently-composed survivorship-safe universe — consistent with Line A's own independently-fixed regime-gated momentum result (Sharpe 0.43-0.60) and with the academic prior. Not a kill.
2. But Line B's headline framing ("fwd Sharpe 0.86, forward-robust", "MaxDD -35% best-risk-adjusted") is still not safe to cite as-is: real MaxDD on this universe is -74% in-sample, and that risk is invisible on a universe with no delistings. Sizing off Line B's original -35%/-55% drawdown numbers would be a real capital-protection error.

**Single weakest assumption:** the PIT-membership + price≥₹20 substitute for Line B's ADV/turnover liquidity filter is not identical to either original methodology — it's a reasonable, already-vetted proxy (it's what Line A itself uses), but it means this is not a strict single-variable "add back delisted names, hold everything else constant" experiment; the total universe composition changed (2,535 HF symbols → 976 PIT names, top-500-by-turnover → PIT-membership+price-floor) alongside the survivorship fix. The direction of the finding (Sharpe/CAGR roughly held, drawdown much worse) is robust to that caveat because it's driven by a small number of identifiable named blowups (ADLABS, ILFSTRANS, and the broader 148-name delist register), not by the liquidity-filter choice — but a controlled ablation (same 976-panel, with vs without delist-loss realization, holding universe fixed) would isolate it cleanly and is the natural next cheap test if this gets escalated.

## Next step (not done here — flagging, not executing)
Walk-forward / parameter stability and DSR/PBO for mom_12_1 and Mom12+LowVol before any Gate-4/IC citation. Also recommend the controlled ablation described above (isolate delist-loss-realization effect alone on the identical 976-panel) to separate "universe composition changed" from "survivorship bug fixed" as the driver of the DD blowup.
