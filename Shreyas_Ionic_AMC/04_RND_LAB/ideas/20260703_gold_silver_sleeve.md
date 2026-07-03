# Hypothesis one-pager — Gold/Silver ETF sleeve (crash diversifier)
_Intake 2026-07-03 · R&D (Aditya Verma) · RESEARCH_SOP §template · stage 1-INTAKE_

- **Name:** `gold_silver_sleeve` — GOLDBEES/SILVERBEES crisis/inflation hedge + trend overlay.
- **One-line edge:** Hold a small, trend-gated GOLDBEES (+ optionally SILVERBEES) position as the **book's crash diversifier** — not because gold has alpha, but because our entire live book is short-vol and gold's payoff is *uncorrelated-to-negatively-correlated* with equity/vol crashes, so it pays exactly when the option sleeves bleed.

- **Economic WHY (who loses money to us, why do they keep doing it?):**
  This one is honest: it is **not primarily an alpha trade — it is a correlation trade.** The "WHY" is portfolio-structural, not a counterparty who overpays us. KNOWLEDGE_BASE is explicit — **every profitable sleeve we run is short-vol** (IV/RV, earnings-crush, FF-calendar-CE, managed strangle), and KNOWLEDGE_BASE lesson 4 says tails are survivable only at the *portfolio* level. In an equity/vol crash all four sleeves lose together (correlated short-vol) while gold typically catches a flight-to-safety bid. To the extent there IS a return premium: the losers are forced sellers in a crisis (leveraged holders liquidating) and disinflation-fearing real-money — a **structural/behavioral** flow that bids gold when it hurts equities most. We keep the position small; its job is to reduce book drawdown, and any positive carry is a bonus.

- **Factor sleeve:** Commodity sleeve (FACTOR_LIBRARY §Commodity — ETF route, no MCX; one-pager was the pending item, this closes it).
- **Universe:** GOLDBEES, SILVERBEES (NSE ETFs). Overlay reference: NIFTY for the crisis-correlation and trend-regime context.
- **Holding period:** Strategic/regime — weeks-to-months; trend overlay (e.g. price vs 200-DMA) flips it on/off. Not a trading signal, a sizing/hedge sleeve.
- **Expected decay horizon:** Very long / structural — the diversification property of gold vs equities is a macro constant, not a crowded factor that decays on publication. The *trend overlay's* timing edge, if any, can decay; the correlation benefit does not.
- **Capacity estimate:** Effectively **unconstrained** for our size — GOLDBEES/SILVERBEES are among the most liquid ETFs on NSE; a small book sleeve is a rounding error on their ADV. (Confirm exact ADV at cheap-test.)

- **Data needed (on disk? Y/N per DATA_CATALOG):**
  - Angel instrument tokens for GOLDBEES/SILVERBEES — `datasets/angel_instrument_list.json` — **Y**, **verified on disk 2026-07-03** (grep confirms both symbols present in the 281KB file; DATA_CATALOG §6 [books]).
  - ETF **daily price history series** — **PARTIAL/N** — the *tokens* are on disk, but a clean multi-year GOLDBEES/SILVERBEES daily OHLC series is **not yet catalogued as a dataset**. Pulling the history (Angel historical API or NSE bhavcopy for the ETF) is a small **Data Officer fetch** — flag as the one true data gap here.
  - NIFTY daily for the crisis-correlation test — **Y** (equity daily 2005-2026 long history, §2).

- **Cheap-test design (the single cheapest falsification):**
  Correlation-in-crashes study — no strategy backtest needed first. Pull GOLDBEES (and SILVERBEES) daily since inception, align to NIFTY, and measure **gold's return specifically in the worst equity-decile days / drawdown episodes** (2018 smallcap crash, 2020 COVID, 2022 rate shock, 2024 election vol, 2026 YTD — the RESEARCH_SOP regime slices). The sleeve is justified iff gold's conditional return in equity crashes is **≥ 0 and its correlation to NIFTY in those tails is ≤ 0**. The trend overlay is a *second* test only if the diversification holds.

- **Pre-registered KILL criteria:**
  1. GOLDBEES's mean return **in the worst equity-return decile days is negative** (i.e. it sells off *with* equities) across the regime slices → KILL as a crash diversifier (its whole reason to exist fails).
  2. GOLDBEES/NIFTY correlation **in tail (crash) windows > +0.3** → KILL (not a diversifier when it matters, even if unconditional corr looks low).
  3. Trend overlay (if tested) does **not reduce the sleeve's own max drawdown vs buy-and-hold gold** → drop the overlay, keep at most a static small allocation (overlay adds no value).
  4. Data gap: if a clean ETF price series cannot be obtained PIT-clean → HOLD for Data Officer, do not proxy with MCX/LBMA spot and claim ETF behavior.

- **Trials run so far on this family:** **0** (new sleeve; commodity sleeve had no prior variant — one-pager was the pending gate-1 item per FACTOR_LIBRARY).

- **Cheapest falsification (closing line):** Align GOLDBEES daily to NIFTY, and kill it as a crash diversifier if gold's mean return on the worst equity-decile days is **negative** or its tail-window correlation to NIFTY is **> +0.3** across the five regime slices — because a "hedge" that falls with the book is not a hedge.
