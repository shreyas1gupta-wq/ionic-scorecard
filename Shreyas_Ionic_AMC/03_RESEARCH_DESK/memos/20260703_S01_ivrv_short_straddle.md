# IC MEMO — S-01: IV/RV Short Straddle — **SEND-BACK**
`Date:` 2026-07-03 · `Chair:` Rajan Mehta (CIO) · `Members:` Rao (Quant), Shah (FM-Deriv), Singh (TCA), Bose (Red Team) · `Protocol:` R1 blind-parallel → R2 red-team → CIO verdict · `First formal IC of the firm.`

## 1. VERDICT
**SEND-BACK** — returns to Research Desk (Gate-3/backfill), NOT to sizing. No live capital.
Paper-tracking: APPROVED, small, firewalled (see §3a). Registered edge: **+11.4pts incremental** (see §3b).

## 2. Evidence assembled (all verified from disk)
**Round 1 (blind):**
- **Quant (Arjun Rao):** slice n=1,583 (195 syms, 2021-06→2026-05); mean +37.6%/premium, hit 90.5%, build +38.0 ≈ fwd +37.4; no concentration (top-5 removed → 37.4); accounting CLEAN (exit-booked, premium denominator, no terminal-theta, none of the firm's 3 historical artifacts). Flag: **no vol crash in sample** (2020 absent, 2022 n=7). [DATA]
- **FM (Vikram Shah):** conditional top-up to S-04 base-load; 4-6 concurrent inverse-IV names ~10-12% book margin inside shared short-vol VaR; event rule: never carry earnings naked (large-caps route to S-02). [DATA/OPINION]
- **TCA (Tara Singh):** regulatory stack 0.44% of premium (trivial); survives 2× on the mean (~33% residual). BUT backtest slippage (2%/side combined) thinner than approved per-leg floors for the 147 mid-caps; EOD/bhavcopy closes flatter a short seller on illiquid strikes; **live feed IV-cap unconfirmed** (INFY 132.7% in a live file); empirical tails −239%/−213% of premium, clip at −300% = blindness beyond. [DATA]
- Two independent provenance checks: two-stage pipeline (rv_iv_vol.py → build_final_docs.py) airtight; slippage-only cost model confirmed. [DATA]

**Round 2 (Red Team, Nikhil Bose): FRAGILE.**
Within-entry-month shuffle of the signal still earns **+26.8%** → **71% of the headline is unconditional short-vol regime beta**. True incremental selection alpha **+11.4pts** (bootstrap 5th pctile +10.3, significant; ~+8.8 net of 2× costs). In 2022 — the only stress year (n=10) — the signal was **worse than random by −10.1pts**. 96.2% of sample in the 2024-04→2026-05 low-vol block. [DATA]

**Formal battery (results/S-01/20260703_validation/):** walk-forward OOS +0.364 avg (hollow — validates on same regime) · plateau **FAIL** (+35.6% spike) · **DSR 0.687 FAIL** (<0.95, 13 honest trials) · **PBO 55.3% FAIL** (<25% required) · bootstrap PASS (5th pctile +0.363) · crash-proxy: 18% book hit under 1%/pos sizing but trips the 3% single-day halt. 90.5% win = 2024-25 artifact (72-78% in 2021-23). iv<1.0 grid dimension = no-op (max iv 0.986). **Arjun Rao WITHDREW his R1 support: NOT-CERTIFIED.** [DATA]

## 3. CIO rulings
**(a) Paper-tracking:** APPROVED — small, paper-only, through the next vol event, expressly to collect live-IV/gap behaviour. Conditions: LIVE feed only after the IV-cap question is settled (INFY 132.7% must be impossible in the live scanner); per-trade marks; **FIREWALLED — paper P&L must not anchor any future size**; event-gated (never carry earnings naked).
**(b) Registered edge:** **+11.4pts incremental** (~+8.8 after 2× costs) — NOT the +37.6% headline, which is regime beta we don't pay alpha for. S-01 is registered as a low-conviction, unproven-in-stress selection overlay.
**(c) Resurrection conditions (reopen full sizing):** (i) backfill 2018 + 2020 vol-crash option data and re-run; (ii) size per-trade, not monthly-averaged, and re-derive DSR; (iii) fix the IV-cap so the grid is genuine 3×3; AND (iv) positive incremental through a genuine vol-spike with the edge re-registering at ~+11pts.

## 4. Reasoning (tail first — CIO charter)
PBO 55.3% + DSR 0.687 = more likely overfit than not; bars capital outright. A short-vol book that has never met a vol spike is an unpriced left tail — the calm-looking setup our own KNOWLEDGE_BASE says kills us. Empirical −239% tails with a −300% clip are fiction under a real gap. The headline decomposes to 71% beta; we do not pay alpha rates for beta.

## 5. Dissents / final positions
Rao: NOT-CERTIFIED, aligned. Bose: FRAGILE, aligned. Singh: conditions unmet, concurs with hold. Shah: support-with-conditions presupposed certification; consistent with paper-only, no standing dissent.

## 6. AlphaPoints (Chair's recommendation — posted to ledger)
Bose +30 (pre-capital halt +15, regime-beta bias catch +15) · Rao +20 (formal battery +15, honest self-withdrawal/decision-useful +5) · Singh +5 · Shah +5.

## 7. Review
Paper-tracking review at first vol event (India VIX >20) or 8 weeks, whichever first. Owner: Vikram Shah (paper), Arjun Rao (resurrection work).
