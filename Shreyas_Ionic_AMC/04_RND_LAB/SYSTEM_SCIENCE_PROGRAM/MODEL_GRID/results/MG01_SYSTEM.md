＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝
CIO-CONSOLIDATED BACKTEST SPECIFICATION — v1.0 (FROZEN ON ADOPTION)
6-Month Momentum · Top-20 · NIFTF500 (NIFTY500) · 2015–2026 · Indian daily
＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝
Consolidated by: Rajan Mehta (E-001), CIO
Inputs merged: Draft (Arjun Rao, Head of Quant, DESIGN) + Red-team review (Nikhil Bose, E-014)
Status: DESIGN — not run. Guards: lib/guards.py mandatory in the entry point.

────────────────────────────────────────────────────────
CIO VERDICT (firm memo format)
────────────────────────────────────────────────────────
VERDICT: APPROVE-WITH-AMENDMENTS — this becomes the frozen v1.0 spec a junior implements verbatim; it is NOT a capital-allocation decision and confers no sizing rights.

RATIONALE (3 lines):
1. The draft's pre-registration, PIT/survivorship, execution and lookahead hygiene are above bar; I adopt them wholesale.
2. Nikhil is correct and his catch is decisive: as written, every kill criterion can PASS on a pure equal-weight small/mid tilt handicapped by a turnover-mismatched null — zero momentum content. That hole is closed here by making EQUAL-WEIGHT-OF-ELIGIBLE the primary hurdle and by fixing the null. All his valid catches are folded in as binding, not optional.
3. Costs stay DRAFT; every headline number is guilty until the full control battery clears it net of 2× cost at a FIXED deployment notional.

TAIL-RISK ASSESSMENT (the part the draft under-weighted — this is a long-only, unhedged, beta-≈1 book):
- Worst single day [INFERENCE]: an equal-weight 20-name book carries ~1.0–1.15 beta. A limit-down macro day (2020-03-23; 2024-06-04 election result, NIFTY −5.9% intraday to ~-8% in high-beta momentum names) is a −8% to −13% NAV day. There is no hedge in this design — that is a deliberate scope limit, and it means this sleeve is a beta amplifier on the left tail, not a diversifier.
- Worst month [INFERENCE]: the 2020 momentum crash is the single most likely blow-up. A 126-day-formation book in Apr–May 2020 holds pre-COVID winners into a junk/low-quality rebound; global momentum lost 15–25% in weeks. Expected drawdown through that rebound: 20–35%. This MUST be reported as a standalone regime slice, not averaged away.
- Correlated-blowup scenario (my firm lesson, binding): "20 names" is NOT 20 bets. Unconstrained Indian momentum routinely stacks 8–10 names into ONE theme (defence/PSU/realty 2023–24; IT 2020–21). A single-theme reversal is a correlated one-week crater dressed as diversification. Our worst historical single-trade losses came from CALM-looking books that were secretly one concentrated bet. Sector concentration is therefore elevated from "report" to a KILL gate (K13).

SIZING RULING: none — design stage. FIREWALL (IC-1 precedent, binding): no number produced by this paper backtest may ever anchor a live position size. Only the INCREMENTAL edge — net alpha OVER equal-weight-of-eligible, after 2× cost, at fixed notional — may be registered, and only if it survives §7–§8. Headline CAGR/Sharpe are decomposition artifacts and are banned from the register (Lessons Learned 2026-07).

KILL CRITERIA + REVIEW DATE: see §9 (K1–K14). Design review checkpoint: on first full battery run, back to CIO + FM before any register entry or Gate-4 claim.

DISSENTS: none recorded. Red-team downgrade to FRAGILE is ACCEPTED as correct against the draft-as-written; the amendments in §2.6, §5.0, §7.1, §7.2, §7.11–§7.13 are precisely what flips it to a spec that CAN certify.

Governing principle for the implementer (unchanged from draft, reinforced): this result is GUILTY until proven innocent. Every parameter below is pre-registered. You do not change a number after seeing an equity curve. Ambiguous rule → STOP and flag. Never "reasonably assume."

────────────────────────────────────────────────────────
0. FROZEN PARAMETERS (pre-register + git-hash BEFORE writing any loop)
────────────────────────────────────────────────────────
Mandate-fixed for THIS study (fixed by design, not claimed to be optimal — robustness reported, never optimized):
- Universe: NIFTY500, point-in-time membership.
- Holdings N = 20.
- Rebalance frequency = monthly.
- Direction = long-only.
  [CIO note, adopting Nikhil #1] N=20 and "monthly" are CHOICES, not laws of nature. They are frozen to keep the trials count honest, but the result's robustness to them is unknown, so §7.14 reports a REPORT-ONLY sensitivity across N∈{15,20,30,50} and frequency∈{monthly, quarterly}. These are NEVER selected on; the headline is always N=20/monthly.

Free parameters (the ENTIRE tuning budget — ≤5; we use 2):
- P1 Formation length L = 126 trading days (≈6m). Grid: {105, 126, 147}.
- P2 Skip S = 21 trading days (skip the most recent month; short-term reversal contaminates raw 6m). Grid: {0, 10, 21}.

Fixed standards (pre-registered constants; perturbed ONLY in the control battery, never optimized on). Each carries a PROVENANCE note asserting it was set ex-ante, not chosen on results [adopting Nikhil #1]:
- Liquidity floor: 20-day median traded value ≥ ₹5 cr. Provenance: firm liquidity standard, not tuned here.
- Min raw price: ₹20. Provenance: firm microcap exclusion, not tuned here.
- Weighting: equal, 5.00% target each.
- Deployment notional: FIXED (see §5.0) — this is a hard input, not left open.

[OPINION] Two free params on a 3×3 grid is deliberately tiny. A momentum book that needs more knobs than that to work is telling you something.

────────────────────────────────────────────────────────
1. DATA REQUIREMENTS + POINT-IN-TIME RULES
────────────────────────────────────────────────────────
Every input needs a DATA_CATALOG entry and a lineage row (exact path, row count, min/max date, spot-check) BEFORE use. No lineage table, no run.

1.1 PIT universe membership — [DATA]
- Source: NIFTY500_TICKER_2005_2025_Final.xlsx (42 PIT snapshots). Extend post-2025 from NSE index-membership archives.
- GATE ON available_date, NOT effective_date [adopting Nikhil, D-028 T-membership]. NSE publishes reconstitution lists ~4 weeks ahead of the effective date. A name is SELECTABLE at rebalance T0 only if the reconstitution list making it a constituent was PUBLISHED (available_date) ≤ T0. Using effective_date silently lets a list "known to the future" drive selection. Store BOTH dates; gate on available_date; assert available_date ≤ effective_date for every row.
- Formation-window prices may pre-date a name's index entry — fine. Membership is gated at selection date only; price history is not.
- NEVER use today's constituent list (Landmine 6: survivorship).

1.2 Prices — daily OHLCV, two series per name — [DATA]. NAME THE EXACT CATALOG ENTRY for each [adopting Nikhil concreteness gap]; do not proceed on "a vendor series."
- (a) TR-adjusted close (splits + bonus + dividends) → used ONLY for return/signal computation.
- (b) RAW (unadjusted) OHLC + RAW volume → used for tradable price levels, the ₹20 filter, ₹5cr traded-value, and circuit checks.
- ADJUSTMENT PIT RULE — RESTATED CORRECTLY [adopting Nikhil, D-028 T-adjustment; the draft's §1.2 wording was self-contradictory]. A standard back-adjusted vendor snapshot bakes LATER ex-date factors into EARLIER prices by construction, so "every adjustment factor has ex-date ≤ the date" is unsatisfiable and is NOT what protects us. What actually protects the SIGNAL is within-window ratio invariance: a corporate action with ex-date AFTER T0 (or between the two window endpoints but applied to both) scales both endpoints of the formation ratio equally and cancels. The binding requirement is: "no corporate action may DIFFERENTIALLY affect the two endpoints of the formation window." REQUIRED LEAK TEST: for a sample of ≥5 split/bonus names, reconstruct the adjusted series AS-OF each T0 (using only actions with ex-date ≤ T0) and confirm the top-20 ranking is unchanged versus the today-snapshot series. If ranking changes materially, the vendor adjustment is leaking — halt.
- PRICE AND VOLUME MUST SHARE ONE ADJUSTMENT BASIS [adopting Nikhil concreteness]. Vendors frequently split-adjust volume independently. Assert raw price × raw volume for traded-value; a mismatched basis makes traded-value wrong around every corporate action. Spot-check across ≥3 known splits.
- DIVIDEND DOUBLE-COUNT GUARD: returns come from the TR series (dividends embedded). Do NOT also credit cash dividends to NAV. Assert ONE dividend treatment once.
- Verify (a) by spot-checking ≥5 known corporate actions (a known 1:1 bonus, a 1:5 split) against raw exchange data.

1.3 Corporate actions + delisting/merger/suspension calendar — [DATA]
- Splits, bonuses, dividends, symbol changes, mergers, delistings, SUSPENSIONS — all with ex-dates/effective dates.
- DELISTING / SUSPENSION HANDLING — TIGHTENED [adopting Nikhil, the survivorship back-door]. Momentum HOLDS WINNERS; the dangerous tail is a winner that ran up then got SUSPENDED (fraud/regulatory — India has a real small/midcap history of this). Concrete rule:
  · Held name delists/merges cleanly → book to merger cash/exchange ratio on the effective date, convert to cash, hold to next rebalance.
  · Held name SUSPENDED with no realizable exit → mark to the EVENTUAL recovery/relisting value (often ≈0), NOT the last pre-suspension print. "Book to last reliable price" is BANNED here because it manufactures free alpha on exactly the names that blow up.
  · "Last reliable price" is defined precisely: the last bar with actual traded volume/CONTRACTS>0. A run of zero-volume bars is NOT a price.
- A name that vanishes must NEVER silently disappear from the P&L.

1.4 Trading calendar — [DATA]. NSE holiday calendar. All offsets (T+1, 126-day, 21-skip) are TRADING days, never calendar days. Assert the date index == NSE session index.

1.5 Benchmarks / hurdles — [DATA]. FOUR, in priority order:
- PRIMARY HURDLE: EQUAL-WEIGHT-OF-ELIGIBLE — an equal-weight portfolio of the SAME post-liquidity-filter eligible universe, same timing, same costs, same turnover treatment [adopting Nikhil, THE attack]. This is the honest "did the RANKING add anything over just equal-weighting the liquid names?" bar. It is the long-only analog of the IC-1 within-signal decomposition. Beating cap-weighted NIFTY500 only proves the small/mid tilt exists.
- NIFTY 500 TRI (cap-weighted): the passive bar; proves the tilt, not the ranking.
- NIFTY 200 Momentum 30 TRI: the LIVE investable momentum index. VALID ONLY ON ITS LIVE PORTION (~Aug-2020 →) [adopting Nikhil]. Pre-2020 is NSE-BACKFILLED/simulated with hindsight; using the backhistory as a live hurdle is itself a lookahead. Report K3 only on the live window.
- Risk-free: 91-day T-bill / MIBOR for Sharpe/Sortino.

1.6 Global PIT rule. At any decision timestamp, only data with available_date ≤ that timestamp may enter — no vendor restatement, no future adjustment factor, no future membership. Auditable via §7.8 one-day-lag AND the §1.2 as-of-reconstruction test.

────────────────────────────────────────────────────────
2. UNIVERSE CONSTRUCTION (evaluated fresh at each T0)
────────────────────────────────────────────────────────
Eligible set at T0 = names satisfying ALL of:
a) NIFTY500 member as-of T0 by available_date (§1.1).
b) ≥ (L+S) valid daily closes in the formation window ending T0 — full history, no NaN-stuffing (excludes recent IPOs; PIT-honest, not survivorship).
c) 20-day median traded value at T0 ≥ ₹5 cr, on RAW price × RAW volume (§1.2 same-basis assertion).
d) Raw close at T0 ≥ ₹20. Apply on the PRICE ACTUALLY OBSERVED at T0, never the back-adjusted level (a later-split stock looks like a penny stock in the adjusted series — a filter leak).
e) Not suspended/delisted/on an ex-date corporate event on T0 or T+1.

[INFERENCE] (c)+(d) are the single biggest silent-inflation risk in a NIFTY500 momentum book — the tail of the 500 is thin, and illiquid winners are where fake momentum alpha lives. Thresholds are pre-registered and swept ONLY in §7.5, never chosen to maximize Sharpe.

2.6 EQUAL-WEIGHT-OF-ELIGIBLE construction [the primary hurdle — build it as a first-class portfolio, NEW]. At each T0, form an equal-weight book of the ENTIRE eligible set (all names passing a–e), run it through the IDENTICAL execution, cost, turnover, dividend, and accounting machinery as the strategy. Its NAV series is the primary net hurdle (K2new) and a §7.2 regressor. Any strategy alpha must survive AFTER this is removed.

────────────────────────────────────────────────────────
3. SIGNAL DEFINITION + TIMING
────────────────────────────────────────────────────────
3.1 Signal date T0 = last NSE session of each calendar month, 2015-01 … last complete month of 2026. Signal uses data through T0 CLOSE.
3.2 Formation return (primary L=126, S=21), on TR-adjusted close:
  R_i = P_adj,i[T0 − S] / P_adj,i[T0 − S − L] − 1
i.e., a 126-day return measured to 21 days before T0 (6m momentum skipping the last month).
3.3 Ranking + selection: rank eligible set by R_i descending; select top-20. Deterministic tie-break: higher 20-day median traded value first (never alphabetical, never index order).
3.4 Weighting: equal, 5.00% target each at rebalance; weights DRIFT with prices intra-month (buy-and-hold within month); do not re-peg daily.

────────────────────────────────────────────────────────
4. EXECUTION CONVENTION (anti-lookahead core)
────────────────────────────────────────────────────────
4.1 Signal→fill separation: signal on T0 close → orders after close → fills at NEXT session open T+1 (raw price). NEVER form the signal and fill at the same T0 close.
4.2 Fill realism (COST_STANDARDS §Dynamic slippage; execution_realism.py):
- Circuit-locked / no-trade at T+1 open → NO FILL → drop the name, hold that 5% in cash to next rebalance (D-031: no-fill = DROP). Do NOT substitute the 21st name (hindsight backfill).
- UPPER-CIRCUIT-AT-OPEN unfillable-WINNER drag — MEASURED SEPARATELY [adopting Nikhil]. Momentum winners are exactly the names that gap up and lock UPPER circuit at the T+1 open — you systematically cannot buy the strongest names. Report the upper-circuit-miss RATE and its P&L drag as a standalone diagnostic; in Indian small/midcaps this quietly guts live-vs-sim.
- Participation cap: fill ≤ 10% of T+1 traded volume; residual at T+2 open, same cap. Report the bind-rate (high bind-rate = capacity problem, §7 + §5.0).
4.3 Turnover: trade only the DELTA (entries, exits, reweight survivors to 5%). Cost charged on both legs of every share. No "costless" survivor rebalance.

────────────────────────────────────────────────────────
5. COST MODEL + DEPLOYMENT NOTIONAL
────────────────────────────────────────────────────────
5.0 DEPLOYMENT NOTIONAL — FIXED [adopting Nikhil: the single biggest implementability hole]. The ≤10%-of-volume cap and the entire impact/cost/capacity model are UNDEFINED without a base capital figure — a ₹1cr and a ₹500cr book fill completely differently.
- HEADLINE notional (frozen): ₹10 cr (top of the D-031 personal-trading capacity band).
- CAPACITY CURVE (mandatory, D-031): re-run the frozen spec at ₹1cr / ₹10cr / ₹100cr / ₹500cr and report net edge vs notional. This is not optional colour — it feeds K14.

5.1 Source: 06_TRADING_DESK/COST_STANDARDS.md — [DATA, flagged DRAFT until Principal-approved]. Every headline carries a "costs = DRAFT" caveat until then.
5.2 Components per executed leg (equity delivery): brokerage, STT, exchange txn charge, SEBI fee, GST, stamp duty, plus slippage. Slippage = max(fixed floor, dynamic component scaled by that day's spread/thin-volume per execution_realism.py); 2–3× on thin days.
5.3 MANDATORY reporting at 1× AND 2× cost (2× stress is firm law); also report a 3× point. HEADLINE Sharpe = the 2×-cost NET number, never gross.
5.4 Turnover→drag sanity: report realized monthly turnover; annual drag ≈ turnover × 12 × round-trip cost. If drag is a large fraction of gross return, the strategy is cost-fragile regardless of gross Sharpe.

────────────────────────────────────────────────────────
6. ACCOUNTING / P&L BOOKING
────────────────────────────────────────────────────────
6.1 Daily-MTM long-only equity book. Daily NAV = cash + Σ(shares_i × raw_close_i); corporate actions on ex-date. Compute returns from ACTUAL NAV changes only — no smoothing, no interpolation over gaps, no monthly averaging. Report BOTH daily and per-rebalance (monthly) return series.
6.1a SHARPE — AUTOCORRELATION-HARDENED [adopting Nikhil, elevated to a gate]. The illiquid-tail risk manifests on the MEASUREMENT side as stale closing marks → positive daily-return autocorrelation → understated vol → INFLATED daily Sharpe, and it can survive the ADV sweep (even "liquid" midcaps get a close set by one late trade). Therefore:
  · Report the lag-1..lag-5 daily-return autocorrelation.
  · HEADLINE Sharpe = the Newey-West / autocorrelation-adjusted Sharpe (daily, √252), NOT the naive daily Sharpe.
  · Cross-check against monthly Sharpe (√12). Material disagreement between adjusted-daily and monthly = accounting/staleness bug → find it before reporting (this is now a gate, not a "note").
6.2 Denominator = portfolio NAV (stable base). Never normalize by anything that can approach zero.
6.3 Daily reconciliation assertion: NAV(t) − NAV(t−1) == Σ position P&L + dividends(if separate) − costs, to the paisa. Fails → HALT (accounting-leak detector).
6.4 Metrics: CAGR (reported but NEVER registered as the edge — Lessons Learned), ann. vol, autocorr-adjusted Sharpe (net, headline), Sortino, max drawdown, Calmar, monthly turnover, hit-rate, avg win/avg loss, beta to NIFTY500, net alpha vs ALL FOUR hurdles, tracking error + information ratio vs each, sector-weight time series (§7.12), and capacity curve (§5.0).

────────────────────────────────────────────────────────
7. CONTROL EXPERIMENTS — DEMANDED BEFORE BELIEVING ANY RESULT
(Run ALL on the FROZEN primary spec, net of 2× cost, ₹10cr notional, fixed logged seeds. This battery runs BEFORE §8 validation — fail here, nothing to validate.)
────────────────────────────────────────────────────────
7.1 Random-portfolio null — TURNOVER-MATCHED / GROSS [FIXED per Nikhil]. The draft's monthly random top-20 turns over ~90%+ (expected overlap ≈ 20×20/250 ≈ 1.6 names) vs momentum's ~30–50%, so a NET comparison lets momentum "win" merely by trading a third as much — a cost artifact, not selection. Fix BOTH ways and report both: (i) evaluate the null GROSS; (ii) build a PERSISTENCE-MATCHED random null (random names held to match momentum's realized monthly turnover). Strategy must exceed the 95th percentile of the FIXED null on a like-for-like turnover basis. N=1000. Fail → it is universe/beta/cost-frequency, not selection. KILL.
7.2 Incremental-vs-base regression [IC-1 rule, EXPANDED per Nikhil, THE attack]. Regress strategy daily returns on: (a) NIFTY500 return, (b) EQUAL-WEIGHT-OF-ELIGIBLE return (§2.6), and (c) a size/small-mid factor. The intercept (alpha), NET of 2× cost, must be significantly positive AFTER all three regressors. The edge is what survives market beta AND the equal-weight tilt AND size — not the raw return. This is the decisive test; run it before anything is celebrated.
7.3 Reverse/anti-momentum — REGIME-CONDITIONAL [FIXED per Nikhil]. Bottom-20 by the same signal should underperform the null OVER NON-CRASH regimes. Evaluate EX the momentum-crash window (2020 junk rebound and comparable junk rallies), because there low-momentum/high-beta names are EXPECTED to outperform — an unconditional test produces a false KILL. If bottom-20 also makes money outside crash windows, the "edge" is universe/beta.
7.4 Timing-perturbation (microstructure/illiquidity): move execution to T+2, T+5, T+10 opens. Medium-horizon momentum should survive a few days' lag with mild decay. Most of the edge dying within days → microstructure/illiquidity (PEAD-contamination), not a factor. Also re-run S∈{0,10,21}: edge only at S=0 → short-term reversal noise, not momentum.
7.5 Liquidity/threshold sensitivity: sweep ADV floor {₹2cr, ₹5cr, ₹10cr, ₹25cr} and min price. Edge concentrated entirely in the thinnest bucket → uninvestable. Report edge AS A FUNCTION of liquidity, not one number.
7.6 Universe-scramble: repeatedly draw random 250-of-eligible subsets, re-run. Edge must be robust across subsets, not carried by a handful of names.
7.7 Survivorship — GATED, not just reported [elevated per Nikhil, D-028 T-membership as the PRIMARY leak probe]. Run current-constituents-only (WRONG) vs available_date-PIT (CORRECT). Report the survivorship premium (the gap). The PIT number is the only real one; if the strategy's certifiable edge exists ONLY in the wrong survivorship-biased run → KILL.
7.8 One-day-lag / lookahead audit (D-028, lib/lookahead_audit.py): re-run all inputs lagged one extra trading day. NOTE [Nikhil]: with a 21-day skip this is NEAR-AUTOMATIC to pass and is therefore WEAK evidence on its own — it is necessary, not sufficient. The strong leak probes for THIS design are §7.7 (membership) and the §1.2 as-of-reconstruction test (adjustment). >40% collapse here = a leak; MUST pass, but do not treat passing as proof of no-leak.
7.9 P&L concentration: contribution of top-5 names and top-3 calendar months to total P&L. >50% from 3 months or 5 names → FRAGILE.
7.10 Regime slices: 2015–17, 2018, 2020 (COVID crash + rebound — report the drawdown THROUGH the rebound explicitly; this is the most likely blow-up), 2022 (rate hikes), 2024 (election-result day), 2026.
7.11 EQUAL-WEIGHT-OF-ELIGIBLE hurdle test [NEW, primary]. Strategy must beat §2.6 EW-of-eligible NET of 2× cost, on the untouched OOS window. This is the honest hurdle; failing it means the ranking added nothing over equal-weighting the liquid names. Tie to K2new.
7.12 SECTOR CONCENTRATION report + SECTOR-NEUTRAL variant [NEW, per Nikhil + CIO tail lesson]. Pure top-20 Indian momentum routinely loads 8–10 names into one theme (defence/PSU/realty 2023–24; IT 2020–21) — a great Sharpe that is secretly one sector's regime, and it SURVIVES the market-beta regression. Report sector weights over time (max single-sector weight, Herfindahl). Run a sector-capped variant (e.g., ≤3 names or ≤25% per sector). If the edge is entirely in the uncapped concentration → it is a single-theme bet, not a factor.
7.13 POST-HOC SELECTION FORBIDDEN [NEW, per Nikhil]. This battery runs ~40+ variants (3×3 grid × timing × ADV × regime × nulls × sector × capacity). You may NOT choose which ADV floor / skip / horizon / regime slice / notional to headline after seeing results. The frozen primary spec (L=126, S=21, ₹5cr, ₹20, ₹10cr, uncapped) is the headline; everything else is diagnostic. All variants count toward the DSR trials tally (§8).
7.14 N / frequency sensitivity — REPORT-ONLY [per Nikhil #1]. Re-run N∈{15,20,30,50} and frequency∈{monthly,quarterly} for robustness disclosure only; never selected on. A lone spike at N=20 = fragile.

────────────────────────────────────────────────────────
8. VALIDATION BATTERY (only if §7 passes)
────────────────────────────────────────────────────────
- Walk-forward: 3y train / 1y test, roll 6 months. Grid on {L,S} ≤ 3×3. Exactly ONE untouched final OOS window, opened once, never re-fit.
- Plateau rule: the {L,S} surface must be a plateau, not an isolated spike. A lone winning cell = overfit.
- DSR > 0.95 with an HONEST trials count — count EVERY {L,S} cell, EVERY §7 control run, the §7.14 sensitivity runs, and any abandoned variant. Undercounting trials is how DSR lies.
- PBO < 25% (combinatorially-symmetric CV).
- ≥30 distinct entries per parameter (trivially met; count distinct entries, not name-months).
- ≤5 parameters (2 free + fixed standards).
- Degenerate detectors, auto-flag [Sharpe-prior REFRAMED per Nikhil #3]: the magnitude prior is NOT the defense — a 2015–24 Indian bull can genuinely print 1.0–1.3 gross Sharpe from beta + small-cap tilt and look "believable" while containing no momentum. The DEFENSE is §7.2 (EW-eligible + size regression) and §7.11 (EW-eligible hurdle). Still flag: any Sharpe >4 (artifact, full stop); autocorr-adjusted vs monthly Sharpe disagreement (§6.1a); win-rate >75% with W/L<0.5; equity-line R²>0.98 (too smooth = leak/smoothing); any ADV/participation violation; any NAV reconciliation break.

────────────────────────────────────────────────────────
9. EXPLICIT KILL CRITERIA (pre-registered — meet any one → die or demote)
────────────────────────────────────────────────────────
K1.  Final untouched-OOS net-of-2×-cost autocorr-adjusted Sharpe < 0.4 → KILL.
K2.  Does not beat NIFTY 500 TRI net of cost on OOS → KILL.
K2new. Does not beat EQUAL-WEIGHT-OF-ELIGIBLE net of cost on OOS (§7.11) → KILL. [PRIMARY hurdle — the ranking added nothing.]
K3.  Does not beat NIFTY 200 Momentum 30 TRI net of cost on OOS (LIVE portion only, ~2020→) → DEMOTE/KILL.
K4.  Fails the TURNOVER-MATCHED/GROSS random null (§7.1, not above 95th pct like-for-like) → KILL.
K5.  One-day-lag test loses >40% (§7.8) OR the §1.2 as-of-reconstruction ranking changes materially → LEAK; KILL and forensically audit.
K6.  PBO ≥ 25% OR DSR ≤ 0.95 (honest trials incl. all controls) → NOT CERTIFIED.
K7.  2×-cost run turns net-negative, or edge exists only below ₹5cr ADV (§7.5) → cost/liquidity-fragile → KILL.
K8.  >50% of total P&L from top-3 months or top-5 names (§7.9) → FRAGILE, not certifiable at size.
K9.  Edge exists only at skip S=0, or dies by T+5 execution lag (§7.4) → reversal/microstructure artifact → KILL.
K10. NAV reconciliation break, or autocorr-adjusted vs monthly Sharpe disagreement (§6.1a) that cannot be root-caused, or any unexplained degenerate flag → HALT, do not report.
K11. Net alpha does NOT survive the §7.2 regression on {NIFTY500 + EW-eligible + size} at 2× cost → KILL. [It is a tilt, not momentum.]
K12. Certifiable edge exists ONLY in the survivorship-biased run (§7.7) → KILL.
K13. Sector concentration is the edge — i.e., the sector-capped variant (§7.12) loses the edge while the uncapped keeps it → single-theme bet, not a factor → NOT certifiable at size (CIO tail gate; my correlated-blowup lesson).
K14. Net edge disappears within the mandated capacity band (§5.0 curve, ₹10L–₹10cr per D-031) → uninvestable at size → KILL.

────────────────────────────────────────────────────────
10. DELIVERABLES
────────────────────────────────────────────────────────
- Entry point importing lib/guards.py; fixed seeds logged; git hash of the frozen spec pinned before the first run.
- Data-lineage table (exact paths, row counts, min/max dates, 5 corporate-action spot-checks, same-basis price/volume assertion) — produced BEFORE the run.
- Results in firm memo format: Result → data lineage → guards passed? → §7 control battery table → §8 validation table → degenerate flags → capacity curve → sector-weight series → verdict REAL / FRAGILE / FAKE + the single weakest assumption.
- Register ONLY the incremental edge (net alpha over EW-eligible, 2× cost, ₹10cr) if it survives; headline CAGR/Sharpe are banned from the register (firewall).
- Costs labeled DRAFT until COST_STANDARDS is Principal-approved.

────────────────────────────────────────────────────────
11. THE SINGLE WEAKEST ASSUMPTION (tested hardest)
────────────────────────────────────────────────────────
[CIO adjudication of the draft-vs-red-team disagreement.] The draft nominated "are the top-20 tradable" (defended by §7.4/§7.5). Nikhil correctly argued that attack is already prosecuted, and that the UNDEFENDED hole is benchmark/null mis-specification letting an equal-weight small/mid tilt (plus a turnover-handicapped null) masquerade as momentum. I RULE FOR NIKHIL: the single weakest assumption is that the momentum RANKING adds anything OVER simply equal-weighting the liquid NIFTY500 names. It is now defended by three binding gates — K2new (§7.11 EW-eligible hurdle), K4 (§7.1 turnover-matched/gross null), and K11 (§7.2 EW-eligible + size regression). Tradability (§7.4/§7.5, K7/K9) remains the SECOND weakest assumption and stays in force. Treat any positive output as FAKE until BOTH sets pass. And even then, remember the tail: this is an unhedged beta-≈1 book whose "diversification" is an illusion if it is secretly 2–3 sector bets (K13) — a great Sharpe here still buys you the 2020-class drawdown, so this sleeve is sized as a beta amplifier, never as a diversifier.
