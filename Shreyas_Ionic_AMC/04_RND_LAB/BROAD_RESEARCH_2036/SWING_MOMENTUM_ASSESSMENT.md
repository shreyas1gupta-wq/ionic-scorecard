# swing_momentum/ — Honest Current-State Assessment
**By:** Devika Menon (FM, Equities & Momentum) | **Date:** 2026-07-18 | **Scope:** read-only review of legacy `swing_momentum/` folder, no files in it touched.

## [DATA] What was planned (`swing_momentum/PLAN.md`)
A ≤₹10Cr Minervini/CANSLIM-style leadership swing system: PIT survivorship-safe universe →
RS/trend-template/VCP leader score → regime-gated entries → weekly rebalance → walk-forward
validation → paper → live. 7 phases, `GOD_TIER_EXPANSION.md` / `FRONTIER_DIMENSIONS_2026_2040.md`
sketch 10 further capacity-limited sleeves and 2026-40 thematic tailwinds (unbuilt, narrative only).

## [DATA] What's actually built and run — TWO SEPARATE RESEARCH LINES
**Line A (2026-06-17, `RESULTS.md`, `data/build_panel.py`+`run_swing.py`):** survivorship-safe
976-symbol PIT panel (`processed/eq_close.parquet`, verified below to correctly include known
delistees). First pass (V1) reported +21%/34.4% OOS CAGR; author caught the bug and fixed it —
**V2 (honest, delist loss realized, price≥₹20 floor, regime tightened):**

| segment | CAGR | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|
| Regime-gated full 2005-25 | +11.6% | 0.43 | 23.0% | 0.51 |
| OOS ~2019-2025 | +16.1% | 0.60 | 23.0% | 0.70 |
| Always-on (no regime) | +21.7% | 0.66 | 73.4% | 0.30 |

Regime filter is the entire edge (halves MaxDD 73%→23-36%); episodic bull years (+76% 2014,
+62% 2021) drive the return, chop years flat/negative — an honest "skill+regime bet," not a
stationary alpha. A second test in the same file (`run_multistrat.py`) found stacking a
mean-reversion sleeve on top FAILS (ρ+0.57, risk-parity combo worse than momentum alone) —
correctly concluded that two long-only equity sleeves under the same regime gate aren't a real
diversifier; only a different-driver sleeve (short-vol carry, market-neutral L/S) would be.

**Line B (2026-07-02, `multi_backtest.py`+`combo_and_report.py` → `Backtest_Results_India.xlsx`):**
a broader 7-signal factor battery (mom 3/6/12-1, low-vol, hi-52w, reversal, trend+mom) plus
combos, on a **different, broader universe**: 2,535 symbols from a HuggingFace daily dataset,
liquidity-filtered to top-500 by 60d turnover, build ≤2021 / forward 2022-2026:

| strategy | Build Sharpe/CAGR/MaxDD | Fwd Sharpe/CAGR/MaxDD |
|---|---|---|
| mom_12_1 (winner) | 0.76 / +13.3% / -55% | 0.86 / +21.4% / -35% |
| lowvol_126 | 0.80 / +7.8% / -27% | 1.01 / +9.3% / -14% |
| Mom12+LowVol combo (best combo) | 0.84 / +9.9% / -37% | 1.03 / +14.0% / -20% |
| Episodic Pivot / short reversal | — | negative/weak OOS (flagged as "failed forward" in the file itself) |

## [DATA] Honesty check — Line B repeats the exact landmine Line A already found and fixed
I verified this directly rather than trust the file's own caveat. The HF day parquet
(`swing_momentum/data/hf_stock_minute/day/train-00000.parquet`, 2,535 symbols) contains **zero**
of a sample of 11 classic NSE delisting/blowup names (8KMILES, ABGSHIP, ADLABS, SATYAM,
JPASSOCIAT, RCOM, DHFL, JETAIRWAYS, VIDEOCON, KINGFISHER, ADVANTA) — checked by direct symbol-set
membership, not inference. By contrast, `processed/eq_close.parquet` (Line A's 976-symbol PIT
panel) **does** contain 6 of 7 of the same names (all but SATYAM, pre-2005 delist). This is a
clean, load-bearing confirmation: **Line B's universe is current-day-survivors only** — the same
bug Line A's own V1→V2 fix (documented in `RESULTS.md`) found HALVES CAGR when corrected (+21%→
+11.6% full, and MaxDD understated 35.7%→ fixed-23%). `combo_and_report.py`'s own "Next to fix"
note flags this ("re-run on the 976 PIT universe... broader universe leans optimistic") but it
was never acted on. **Conclusion: the Backtest_Results_India.xlsx headline numbers (mom_12_1
+21.4% fwd CAGR / Sharpe 0.86; Mom12+LowVol combo +14.0%/Sharpe 1.03) are not trustworthy as
stated — expect a materially lower, though not necessarily zero, edge once survivorship is fixed.**
This is NOT a reason to kill the underlying momentum-factor logic (economic rationale is sound,
consistent with Line A's independently-fixed result) — it is a data-pipeline defect to correct
before citing Line B's numbers anywhere.

No other landmine from CLAUDE.md's list was found to clearly apply here on this pass: HF
timestamps ARE correctly tz-converted (`tz_convert('Asia/Kolkata')`) in both scripts; pre-open
auction bug doesn't apply (daily bars, not 1-min); no fundamentals/earnings lookahead in the
momentum engine itself (price-only signals); `earnings_strategies.py`'s PEAD/Episodic-Pivot work
does use `datasets/nse_earnings_dates/earnings_dates.csv` announcement dates with a liquidity gate
and winsorized forward returns — reasonable PIT discipline on a quick read, not independently
re-verified here. Line B still has no volume/circuit-lock fill realism (flat 0.4% RT cost
regardless of liquidity) — a secondary, smaller optimism source on top of survivorship.

## [DATA/INFERENCE] What's untested / open
1. Line A and Line B have never been reconciled — no run of the broader 7-signal battery (mom,
   low-vol, combos) on the survivorship-safe 976-symbol PIT panel. This is the single most
   valuable next step (see below).
2. No walk-forward / parameter-stability pass on either line (PLAN.md 6.1, 6.4 unchecked).
3. No liquidity/ADV fill realism or circuit-lock handling in Line B.
4. No DSR/PBO computed for either line — per this firm's discipline that alone is not a kill
   reason, but it means neither result carries a certified confidence number yet.
5. `MULTIBAGGER_DNA.md`/`FORWARD_WATCHLIST.md`/`GOD_TIER_EXPANSION.md`/`FRONTIER_DIMENSIONS_...`
   are narrative synthesis (qualitative multibagger patterns, 2026-40 theme baskets) — genuinely
   useful for a quality/momentum overlay idea (RoE+low-debt gate suggested), but 0% operationalized
   into code; no fundamentals or sector-map data has been fetched to test it.
6. `Qullamaggie_Playbook.xlsx`, `Minervini_Playbook.xlsx`, `VVV_Rohit_Playbook.xlsx`,
   `SwingPositional_Setups_India.xlsx` are reference/knowledge-base material (not opened in this
   pass — filenames + folder position indicate playbook notes, not backtest output; flagged here
   only so no one mistakes them for results).

## Single most valuable next step
**Re-run the Line B factor battery (`multi_backtest.py`'s signal set: mom_12_1, lowvol_126,
hi_52w, trend+mom, and the Mom12+LowVol combo) on Line A's survivorship-safe 976-symbol PIT panel
(`processed/eq_close.parquet` + `processed/membership.parquet`), with the same delist-loss
realization and ≥₹20 price floor V2 already used in Line A.** This directly answers the open
question the file itself raises, reuses 100% of existing code/data (no new fetch, no new
approval needed), and will tell us whether the more diversified factor combo (which looked
better risk-adjusted than plain momentum: Sharpe 1.03 vs 0.76 build) survives the fix or was
itself an artifact of the same bias — a ≤1-day quant-desk job, not a full Gate-4 backtest.
I have not done this myself in this pass (scope was assessment, not new backtesting); routing to
Quant Head (Arjun Rao) as a cheap-tier pipeline item is the correct next action, since it's a
rerun of existing harnesses on existing data, not new research.

## Bottom line
Real, honestly-caveated edge exists in Line A (~12-16% CAGR, Sharpe 0.4-0.6, MaxDD~23%, OOS
Calmar 0.70) — modest but genuine, regime-dependent, correctly NOT oversold as "100% CAGR."
Line B's more attractive headline numbers (mom_12_1, Mom12+LowVol combo) are compromised by an
unfixed survivorship-bias universe and should not be cited or sized until reconciled with Line
A's methodology. Diversification value: as a momentum-swing sleeve this remains the firm's
non-short-vol equity diversifier (see Track-2/S-06 book logic) — the mean-reversion-stacking
test in Line A is a useful negative result confirming that within-equity diversification doesn't
work here; the diversification case must be made against the derivatives book, not internally.
