MODEL: Claude Sonnet 5 (claude-sonnet-5)   TOOLS: off (no web search / code execution used)   MODE: single-session, answered task-by-task without referencing other answers (closest practical approximation to fresh-chat-per-task inside this tool)

===== MG01 =====
**Backtest specification — monthly top-20 momentum, NIFTY500, 2015–2026, India daily data**

**1. Data requirements & point-in-time (PIT) rules**
- Daily OHLCV per symbol, corporate-action adjusted (splits/bonuses back-adjusted; dividends handled separately — do NOT let a dividend-adjusted "total return" close silently double as the execution price, since you can't transact at an adjusted price).
- A *survivorship-complete* price panel: every symbol that ever traded in the window, including delisted/merged/renamed names, carried to its last traded price and de-listing date. Never build this from a live vendor feed queried today.
- NIFTY500 constituent history as a **snapshot series** (the index provider publishes semi-annual reconstitution files) — not today's constituent list applied backward. Universe on rebalance date *t* = the officially published constituent list in effect on *t*, looked up via `asof(t)`, never a static current-day download.
- Trading/holiday calendar from the exchange (NSE), circuit-limit flags, and a "tradable" flag (halted / ASM-GSM stage / no trades that day) so execution logic can no-fill correctly.
- Corporate-action calendar (ex-dates) so the 6-month return signal isn't computed across an unadjusted split/bonus.

**2. Universe construction**
- At each month-end formation date *t*: take PIT NIFTY500 membership as of *t*. Apply a minimum-history filter (≥ 126 trading days of price history, else momentum is undefined) and a minimum-liquidity filter (e.g., 20-day median traded value above a floor) computed using data available *strictly before t* only. Exclude names under a trading ban / circuit-locked on the signal date.

**3. Signal timing & execution convention**
- Signal = trailing 6-month return, computed using **only** closes through the close of the last trading day of the month (formation date *t*). Rank descending, take top 20.
- Execution: enter next trading session's VWAP or open (state which — VWAP is more realistic for names outside the top-50 by ADV), never the formation-day close. This is the single most common lookahead bug in momentum backtests — flag it explicitly to the junior quant.
- Hold until next rebalance; trade only the *delta* between old and new target weights, not a full liquidate-and-rebuild (this changes the cost estimate by 2–5x if done wrong).

**4. Cost model**
- Per-side: brokerage + STT + exchange transaction charge + stamp duty + GST (all known, deterministic — build a lookup table, don't guess a flat bps) **plus** a market-impact term as a function of order size / ADV (e.g., a square-root impact model, calibrated conservatively — 10–20bps for the top 100 names, materially more for the bottom of a NIFTY500-derived universe). Cap position size as a % of 20-day ADV; if a target position would breach that cap, either partial-fill over multiple days or exclude the name and disclose it.

**5. Control experiments required before believing any result**
- **Placebo/random-basket test**: same universe, same rebalance dates, same turnover, same cost model, random stock selection. The strategy must clear a stated percentile (report the actual percentile, not just "beats average").
- **Lag-sensitivity test**: shift the signal by one extra day; if the edge collapses, you have a lookahead bug, not alpha.
- **Cost-stress test**: 2x and 3x the assumed cost model — does the Sharpe survive?
- **Parameter-stability check**: vary top-N (15/20/25) and formation window (3/6/9/12 months); demand a plateau, not an isolated peak.
- **Era/regime split**: pre-2020 vs 2020–2022 vs 2023–2026; no single sub-period should carry the whole result.
- **Static-vs-PIT-universe test**: rerun with today's NIFTY500 list frozen backward — if the result changes materially, you had survivorship bias.
- **Capacity check**: what AUM does this support before impact costs eat the edge?

**6. Explicit kill criteria (pre-committed, not discovered after the fact)**
- Net-of-2x-cost Sharpe < 0.5, or the placebo-percentile < 90th, or the result fails the one-day-lag test (edge doesn't degrade gracefully — it dies), or the result is driven by <3 sub-periods / a handful of extreme trades (check contribution concentration; if top-5 trades explain >40% of PnL, kill), or the static-universe rerun changes CAGR by more than ~30% relative.

===== MG02 =====
**5 falsifiable alpha hypotheses — Indian equity / index-derivatives, cheap to test**

1. **Post-earnings-drift long, positive surprise, mid/small caps.** *Mechanism*: sell-side and retail attention is slower for names outside NIFTY100; the market underreacts to genuine EPS beats vs a trend extrapolation, and drift closes over 5–10 sessions. Losing side: retail investors who don't update on the print, and index-hugging institutions with no mandate to react to a mid-cap beat. *Cheapest kill test*: is the "drift" indistinguishable from ordinary momentum/size factor exposure? Regress trade returns on contemporaneous size and 12-1 momentum factor returns; if the alpha t-stat drops below ~1.5 after controlling for those, it's dead. *Data*: quarterly EPS with true publication timestamps (not quarter-end), adjusted daily prices. *Kill result*: no residual edge after factor-neutralizing, or the edge doesn't survive a 1-day-lag test.

2. **Index-rebalance front-running (inclusion/exclusion in NIFTY50/NIFTY Next 50).** *Mechanism*: passive AUM tracking these indices must buy/sell on the effective date; a small trader can take the other side of that flow days before/at the event. Losing side: index funds forced to trade regardless of price (inelastic demand). *Cheapest kill test*: measure abnormal return in the announcement-to-effective window across all reconstitutions in the last 5 years — if it's not statistically distinguishable from the ordinary volatility of small/mid caps around random dates, dead. *Data*: index provider's reconstitution announcement history (public), free-float and estimated passive AUM tracking each index. *Kill result*: abnormal-return t-stat < 2 across ≥20 events, or the effect has decayed to near-zero in the last 2 years (a well-known effect that's been arbitraged away).

3. **Weekly-expiry pin risk / gamma-driven index drift into expiry.** *Mechanism*: dealer short-gamma hedging near large open-interest strikes on NIFTY weekly expiry days creates a mechanical pull of spot toward high-OI strikes in the final hours. Losing side: option buyers holding gamma into expiry who get pinned against their favor; dealers systematically hedge in a way that dampens realized moves. *Cheapest kill test*: on expiry days, is |close − max-OI-strike| systematically smaller than on a random matched non-expiry day, controlling for realized vol? *Data*: F&O bhavcopy OI by strike, index 1-minute prints. *Kill result*: no statistically significant pin effect vs matched control days.

4. **Overnight index drift conditional on the day's realized-vol regime.** *Mechanism*: overnight returns partly reflect a risk premium for holding gap risk; that premium is time-varying and higher when realized vol has been low (crowded short-gap positioning unwinds less). Losing side: intraday-only traders who are flat overnight and forgo the premium; nobody is "losing" in a zero-sum sense here — this is closer to a risk premium than an inefficiency, which is itself testable and falsifiable. *Cheapest kill test*: compare overnight return conditional on trailing 20-day realized-vol percentile vs unconditional overnight drift — matched-exposure random-night baseline must be beaten, not just "any overnight long." *Data*: daily OHLC only (cheapest of all five). *Kill result*: conditional edge collapses to the unconditional drift once you control for exposure (nights selected vs random nights of equal count).

5. **Quarterly-results-season liquidity discount on illiquid F&O names.** *Mechanism*: during peak results weeks, market-makers widen spreads/reduce depth on single-stock options with earnings risk; a liquidity-provision strategy selling that temporarily-widened spread (via calendar or vertical spreads, not naked) earns a rent for absorbing event risk that most participants avoid. Losing side: retail/small directional traders paying the wide spread to express an earnings view. *Cheapest kill test*: measure realized bid-ask spread and quoted depth in the 3 days around earnings vs a non-earnings baseline for the same stock; if the spread widening isn't several multiples of normal, the rent isn't there to collect. *Data*: F&O quote/trade data (need at least end-of-day best bid/offer, ideally intraday) for single-stock options — the one hypothesis here that needs data a small team may struggle to get cheaply; flag as the weakest on the "cheap data" criterion.

===== MG03 =====
**Resume-safe daily EOD ingestion pipeline over an unreliable proxy**

**Core invariant**: every file the pipeline ever accepts into the dataset is content-verified and recorded exactly once in an append-only ledger before it is considered "ingested." Nothing downstream ever trusts "the download succeeded" as a signal — it trusts the ledger.

**Mechanisms:**
1. **Manifest-first design.** A daily manifest lists every expected file (per segment/exchange) with its expected filename, and — once known — its expected SHA-256 and byte size, published by the exchange or captured from a prior successful pull. The pipeline's job each day is "make the on-disk state match the manifest," which is naturally idempotent and resumable.
2. **Download to a staging area, atomic promote.** Every file downloads to `staging/<date>/<file>.part`. Only after (a) the download completes without a truncated-connection error, (b) the byte size matches the manifest (or, if unknown ahead of time, is non-zero and stable across a re-stat 2 seconds later), and (c) a checksum/structural validation passes (see #3) — the file is `os.rename()`'d into `landed/<date>/<file>` (atomic on the same filesystem). A crash mid-download leaves only a `.part` file, which is simply ignored/deleted on next run; nothing corrupt ever reaches `landed/`.
3. **Content validation before acceptance, not just transport validation.** A file that downloaded "successfully" over a flaky proxy can still be corrupt (truncated mid-write by the proxy, or an HTML error page saved as if it were the data file). Validate structurally: for a CSV/bhavcopy, check expected header, expected row count within a tolerance band of a trailing-N-day median, and that it parses without exceptions. Files failing this go to `quarantine/<date>/<file>` with a reason string — never silently retried forever, never silently dropped.
4. **Ingestion ledger (append-only, e.g. SQLite/Postgres table, one row per file).** Columns: `date, filename, sha256, byte_size, status(landed/quarantined/ingested), ingested_at, ingested_by_host`. Ingestion into the actual dataset is a transaction that (a) checks the ledger for an existing `ingested` row with the same `(date, filename, sha256)` — if present, no-op (idempotent, handles restarts/reruns), (b) if a *different* sha256 exists for the same `(date, filename)`, that's an anomaly (vendor republished a file) — quarantine and alert, don't silently overwrite history, (c) otherwise writes the data and marks the ledger row `ingested`.
5. **Retry/backoff for the flaky proxy specifically.** Chunked/range-resumable downloads (`Range:` header) so a stall resumes from the last received byte rather than restarting; exponential backoff (say 5 attempts, 10s/30s/90s/5m/15m) per file; a circuit breaker per exchange segment — after N consecutive full-segment failures, stop hammering the blocked IP and escalate instead of retrying into a ban.
6. **A new machine takes over mid-history by reading the ledger, not local state.** The ledger is the single source of truth (kept off the flaky machine, e.g., in the shared DB/S3-compatible store); `staging/` and `landed/` are disposable local caches. A fresh machine's first action is "diff manifest vs ledger for the last N days" and only fetch what's missing — no assumption about what it, personally, has downloaded before.
7. **Alerting only when action is genuinely needed.** Alert on: (a) a file in `quarantine/` older than 2 hours with no automatic resolution, (b) the circuit breaker tripping (proxy/IP block), (c) a manifest entry with no corresponding file after the exchange's stated publish-by time + grace period, (d) a ledger anomaly (mismatched checksum for a previously-ingested date). Do NOT alert on ordinary retries, stalls that self-resolved, or routine backoff — that's noise that trains the human to ignore alerts.

===== MG04 =====
**Pre-mortem risk memo — short-index-options book, one year forward, worst week ever**

**What killed it.** The budget/RBI week delivered a surprise policy combination (e.g., an unexpected rate move plus a fiscal-deficit/tax surprise investors read as negative) that moved the index ~5–7% intraday on the announcement day after weeks of compressed realized and implied vol — exactly the regime in which a short-strangle/short-premium book has maximum negative gamma and minimum cushion (IV had been sold down to multi-year lows going into the event, so premium collected was thin relative to the eventual move). The defined-risk spreads capped loss per structure but at multiples of the credit received (typical short vertical spreads lose 3–6x credit at max pain); the naked strangles have no cap and are the dominant tail contributor.

**Quantify the plausible tail.** If the book runs, say, ₹50cr notional-equivalent short gamma with a blended short strangle width of ~3% OTM each side and the index moves 6% against one side: a naked short strangle sized to a normal ₹1–2 lakh margin-per-lot regime can see per-lot losses of 15–25x the collected premium once the move breaches the short strike by several percent (payoff is roughly linear beyond the strike, and vega expansion on the surviving wing compounds it). A back-of-envelope for a book running ~₹8–12cr of naked strangle notional risk: a plausible single-week loss in the 25–45% of book-capital range is not extreme for this setup — that is the number that should trigger the pre-commitment below, not be discovered after the fact.

**De-risk triggers to pre-commit to (numeric, not vibes):**
- Reduce naked-strangle gross short vega by 50% at least 2 sessions before any pre-scheduled binary event (budget/RBI/election) — mechanical calendar rule, no discretion.
- If realized vol over the trailing 10 sessions is below the 20th percentile of trailing-3-year realized vol AND an event is inside 5 sessions, cap new naked-strangle sales entirely (compressed-vol-into-event is the precise setup that produces tail losses; this is exactly when premium looks "cheapest" and is most dangerous).
- Hard stop-loss at 3x credit received per naked structure, executed same-day, no averaging down / no "it'll mean-revert."
- Daily VaR/stress limit: book must survive a pre-specified index gap (e.g., ±7% overnight) within a pre-committed max drawdown (e.g., 15% of book capital) under a full-reval stress test — recompute weekly, not just at inception.

**What cannot be hedged at acceptable cost.** True tail protection for a scheduled, known-date binary event (buying far OTM protection specifically for budget/RBI week) is expensive precisely because everyone wants it into the same week — the IV term structure kinks up going into the event, so hedge cost eats a large fraction of the strategy's baseline edge if done every single time. The honest answer is: you cannot fully hedge this cheaply and still keep the strategy's baseline return; the correct response is *position sizing and gross-exposure reduction* going into known binaries, not "buy insurance every time," and an explicit acknowledgment that a genuine multi-sigma surprise on a scheduled event is a known, accepted, capital-at-risk scenario, not something the book was flawed for missing.

===== MG05 =====
Draw n times with replacement from {1,...,n}; D = number of distinct values observed.

**Derivation.** For each value i ∈ {1,...,n}, let I_i = 1 if i appears at least once in the n draws, else 0. Then D = Σ I_i, and by linearity of expectation E[D] = Σ E[I_i] = n·P(a fixed value appears at least once).

P(value i never drawn in one trial) = 1 − 1/n. Across n independent draws: P(never drawn) = (1 − 1/n)^n. So P(drawn at least once) = 1 − (1 − 1/n)^n.

**E[D] = n·[1 − (1 − 1/n)^n]** (exact closed form).

**Limit of E[D]/n as n→∞:** E[D]/n = 1 − (1 − 1/n)^n → 1 − e^{-1}, since (1 − 1/n)^n → e^{-1}.

**Final answers:**
- E[D] = n − n(1 − 1/n)^n, exactly.
- lim_{n→∞} E[D]/n = 1 − 1/e ≈ 0.6321.

===== MG06 =====
Draws are i.i.d. uniform over 4 suits; T = number of draws to see all 4 suits at least once (coupon collector, 4 coupons).

**Derivation.** After the 1st draw you have 1 new suit for sure. Let T_k = number of additional draws needed to go from k distinct suits seen to k+1 distinct suits seen. While k suits have been seen, each draw has probability (4−k)/4 of being a new suit, so T_k is geometric with success probability p_k = (4−k)/4, and E[T_k] = 1/p_k = 4/(4−k).

T = T_0 + T_1 + T_2 + T_3 (going from 0→1→2→3→4 distinct suits), and by linearity:
E[T] = 4/4 + 4/3 + 4/2 + 4/1 = 1 + 4/3 + 2 + 4 = 4·(1 + 1/2 + 1/3 + 1/4).

1 + 1/2 + 1/3 + 1/4 = 12/12 + 6/12 + 4/12 + 3/12 = 25/12.

**E[T] = 4 · 25/12 = 25/3 draws (exact fraction).**

**Decimal value: 25/3 ≈ 8.3333.**

===== MG07 =====
**Verification protocol before a third-party quarterly fundamentals dataset (India, 2005–present, ~2000 companies, with announcement dates) is allowed near a backtest**

**1. Sampling and cross-checks against ground truth**
- Stratified random sample of 150–250 (company, quarter) pairs, stratified by market-cap decile, sector, and era (pre-2010 / 2010–2015 / 2015–2020 / 2020–present), since vendor data quality is rarely uniform across time or cap size.
- For each sampled row, pull the actual filed result (exchange filing / annual report / investor presentation) and diff every reported field: revenue, EPS, reported date. Track a field-level error rate, not just a pass/fail per row — some fields (revenue) are usually cleaner than derived ones (adjusted EPS, segment-level numbers).
- Cross-check a subset against a second independent source (a different data vendor, or the company's own investor-relations XBRL filing) to catch systematic vendor-specific errors that a single-source check would rubber-stamp.

**2. Testing that announcement dates are genuinely point-in-time**
- For the sampled rows, find the actual public disclosure date/time from the exchange filing system (NSE/BSE corporate announcements) and compare to the vendor's `available_date`/`announcement_date` field. Flag any row where vendor date is *earlier* than the true public filing date — this is the dangerous failure mode (it manufactures lookahead) versus vendor date being *later* (merely conservative/costly, not corrupting).
- Check for a suspicious pattern: is the vendor's announcement date suspiciously always "quarter-end + fixed N days" for every company (a strong tell they backfilled from a template/estimate rather than tracking the actual filing) rather than the genuinely variable real-world lag (which ranges roughly 15–60 days and varies company to company and quarter to quarter)?
- Explicitly test post-facto restatements: does the vendor overwrite a quarter's historical figures when a company later restates, losing the *originally reported* number? A backtest must use what was known at the time, not the eventually-restated "true" figure — verify the vendor exposes (or at least doesn't silently mutate) as-originally-reported values.

**3. Coverage and survivorship checks**
- Reconcile vendor company count and identifiers, quarter by quarter, against the historical NSE/BSE listed-universe count for that quarter — if the vendor's earliest years show materially fewer companies than the exchange's actual listed count for that period, that's a coverage gap concentrated in the past (classic survivorship signature).
- Explicitly check whether delisted/merged/renamed companies are present with their historical data intact, or whether they silently vanish from the dataset the moment they stop being "current" (query the vendor for 20–30 known-delisted names and confirm their historical quarters are still retrievable).
- Check for "look-ahead-friendly" gaps: quarters with suspiciously fewer NA/missing fields in early years than plausible given actual filing quality at the time (over-clean historical data is a red flag for backfilled/estimated figures).

**4. Quarantine / acceptance rules**
- Quarantine (do not admit to any backtest) any field/era/sector stratum where the sampled error rate exceeds a pre-set threshold (e.g., >2% of numeric fields materially wrong, or any confirmed instance of an `available_date` earlier than the true filing date).
- Accept only strata that pass both the value-accuracy check and the PIT-date check; document acceptance per (field, era, cap-bucket) rather than as a single dataset-wide yes/no, since it is normal for one vendor to be fine post-2015 and unreliable pre-2010.
- Re-run the full sampling check any time the vendor pushes a "data refresh" — a silent methodology change in a refresh is a common way clean data quietly becomes contaminated.

===== MG08 =====
**A published ML strategy claims 2.1 Sharpe out-of-sample, US equities, 2010–2023, 940 features (prices/fundamentals/news sentiment) — 6 most likely reasons the number won't replicate, ranked by probability**

1. **Look-ahead / leakage in the feature set (most likely).** *Mechanism*: with 940 heterogeneous features assembled from multiple vendors, at least some are very likely timestamped or point-in-time-adjusted incorrectly (a classic culprit: fundamentals keyed to fiscal period-end rather than public filing date; sentiment features built from data with a delayed/adjusted timestamp that doesn't match true availability). Any single leaking feature among 940 can single-handedly manufacture a large chunk of an inflated Sharpe. *Check*: rebuild the top 20 features by importance and manually verify the exact availability timestamp of each against the true public-disclosure time; re-run with every feature lagged one extra day and see if the Sharpe survives.

2. **"Out-of-sample" is not actually out-of-sample (feature/hyperparameter selection leakage across the split).** *Mechanism*: with 940 candidate features, if any feature selection, hyperparameter tuning, or even the choice of which 940 features to build was informed by looking at performance on data inside the "out-of-sample" window (common when a research team iterates for years before finalizing a paper), the OOS Sharpe is contaminated by implicit multiple-testing / overfitting to that window. *Check*: is there a genuinely separate, never-touched-during-development holdout (e.g., data after the paper's own analysis concluded) — if the OOS window is the same one used throughout years of iteration, that's the tell.

3. **Backtest doesn't reflect achievable trading costs/capacity.** *Mechanism*: a paper Sharpe of 2.1 on a broad ML strategy touching hundreds of features often implies meaningful turnover concentrated in smaller/less liquid names where the feature signal is strongest (classic ML-momentum-in-microcaps pattern); realistic market impact at any deployable size collapses the number. *Check*: report the strategy's actual capacity curve (Sharpe vs AUM) and the liquidity profile (average ADV%) of the positions actually driving the PnL — if this is absent from the paper, that's itself a red flag.

4. **Survivorship bias in the underlying universe/fundamentals panel.** *Mechanism*: 2010–2023 spans multiple bankruptcies/delistings; if the fundamentals/price panel used quietly drops delisted names or backfills identifiers, the strategy never "experiences" its worst-case losers, inflating Sharpe. *Check*: confirm the universe construction explicitly includes delisted names with realized terminal losses, not a current-day universe applied backward.

5. **Selection bias in what gets published (file-drawer / multiple-comparisons across many candidate models).** *Mechanism*: academic and practitioner research pipelines commonly try dozens of model/feature-set variants and publish the best one; a 2.1 Sharpe may be the max of many attempts rather than the expected performance of "the" method. *Check*: ask whether the paper reports a distribution of results across model variants tried (most don't) — if only the winning configuration is shown, treat the number as an order statistic, not an expectation, and apply a haircut consistent with the number of variants plausibly tried.

6. **Overlapping/autocorrelated return sequences inflate the Sharpe's implied statistical confidence (and sometimes the point estimate itself via return-compounding artifacts).** *Mechanism*: if the model rebalances frequently with overlapping holding periods across many names, naive daily-PnL Sharpe annualization (×√252) assumes i.i.d. daily returns; real strategy PnL is autocorrelated (through shared factor exposure and overlapping signals), so the annualized Sharpe overstates the true risk-adjusted return and — separately — small implementation quirks (mark-to-market timing, using close-to-close on names that don't all close simultaneously) can shift the point estimate directly. *Check*: recompute Sharpe using overlapping-adjusted (Newey-West style) variance and compare; also recompute using a coarser (weekly/monthly) return frequency, which should reduce but not eliminate the reported Sharpe if it's genuine — a large drop on de-frequencing is diagnostic of an inflated daily number.

======================================================================
# PART B

===== T01 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. Vendor timestamp mis-parsed to the wrong calendar date (line: `hf["date"] = hf["ts"].dt.date`).**
The sample stamp given, `2025-03-04 18:30:00+00:00`, is UTC for `2025-03-05 00:00:00+05:30` IST — i.e. this bar's true IST trading date is **2025-03-05**, one day later than the naive `.dt.date` extraction on the UTC-aware timestamp (which yields `2025-03-04`). Taking `.dt.date` directly on a UTC timestamp instead of first converting to IST (`hf["ts"].dt.tz_convert("Asia/Kolkata").dt.date`) mislabels every row's date one day early relative to the true IST session. `bhav_close.parquet`, by contrast, is indexed by naive/true IST calendar date. The result is a systematic one-day misalignment between the signal panel (`sig_close`/`rev1`/`xz`, built off the mislabeled `hf["date"]`) and the return/execution panel (`ret`, built off the true-IST-dated `bhav`). Concretely: the code believes it is forming the signal at the close of day *d* and trading the next session, but the information it's actually using was not available until the close of true day *d+1* — a one-session lookahead baked into every signal date. This alone is enough to manufacture a large chunk of a reported 2.4 Sharpe.
*Fix*: `hf["date"] = hf["ts"].dt.tz_convert("Asia/Kolkata").dt.date` before pivoting, and re-verify the resulting dates line up 1:1 with `bhav`'s IST calendar index.

**2. Execution/return panel's corporate-action adjustment status is unverified, while the signal panel's is explicitly audited.**
`hf.close` is stated "split/bonus adjusted (audited)"; `bhav_close.parquet` is only "spot-checked against exchange prints (94.8% exact match)" — a price-level sanity check, not an adjustment-methodology check. `ret = bhav.pct_change()` computes the actual traded P&L. If `bhav` carries raw (unadjusted) closes, any split/bonus during the sample will show up as a large fake one-day "return" (e.g., a 1:1 bonus prints as ≈ −50%) on exactly the day it lands in `pos`/`exit_d`, corrupting both the mean and the tails of the reported PnL. Given `bhav` is used only for `ret`, this is a live risk, not a hypothetical.
*Fix*: compute `ret` from the same audited-adjusted panel as the signal (or explicitly adjust `bhav_close` for the same corporate actions and re-verify against `hf.close` before using it for PnL).

Numbered claimed material defects:
1. `hf["ts"].dt.date` taken on a UTC timestamp instead of the IST-converted timestamp — mislabels every signal date one session early, injecting a one-day lookahead relative to the true-IST-dated return panel.
2. `bhav_close.parquet` (used for `ret`, i.e. the PnL) has no confirmed split/bonus adjustment, unlike the audited signal panel — risk of corporate-action return spikes corrupting the reported Sharpe.

===== T02 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. Signal and fill both use the same-day close with zero execution lag (`entry = df["close"].iloc[i]`).**
The signal (`ret`, `dma20`) is computed from `close`, which includes day *i*'s own closing print. The code then buys "at the close of the signal day" using that very same print as the fill price. This requires knowing the exact closing value and transacting at it simultaneously — unrealistic for an index-futures dip-buy rule (there is no reliable closing-auction mechanism guaranteeing a fill at the exact settlement print in that instrument), and it eliminates the one bar of timing/slippage risk that a real implementation cannot avoid. This zero-lag construction is a classic source of inflated backtest performance.
*Fix*: enter at the next session's open (or a stated intraday-executable price on day *i+1*), never at the same close used to generate the signal.

**2. Instrument mismatch between the signal/PnL source and the stated cost basis.**
The signal and payoff are computed on `nifty_daily.parquet` — the spot index — which is not directly tradable. The cost line ("3bp per side, index futures") implies the intended vehicle is NIFTY futures, but the return series used for PnL is spot-index close-to-close, not futures close-to-close. Futures returns differ from spot via basis and roll cost around monthly expiry, neither of which is modeled; the strategy is costed as futures but marked-to-market as spot.
*Fix*: either simulate on the actual futures continuous-contract series (including roll effects) or, if using spot as a proxy, disclose and bound the basis-risk approximation error rather than silently mixing the two.

Numbered claimed material defects:
1. Same-bar signal-and-fill (line: `entry = df["close"].iloc[i]`) — zero-lag execution, unrealistic and inflates the reported edge.
2. Signal/PnL computed on non-tradable spot index while costs are quoted for futures — instrument/return-series mismatch, basis and roll effects unmodeled.

===== T03 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

Methodology is generally sound: PIT NIFTY-200 membership via as-of snapshots, signals timestamped on `available_date` (not quarter-end), next-open entry with explicit circuit/zero-volume no-fills disclosed, fixed 10-session exit with no discretionary exceptions, a placebo run through the *identical* exit engine, a one-day-lag decay test, and era splits that don't show one period carrying the whole result. The "denominator check" section is a legitimate pre-emptive defense against a real failure mode seen elsewhere in this battery (mixing %-of-premium with %-of-spot) — not applicable here since it's a cash-equity trade with a clean %-of-spot denominator.

**One material defect: the reported t-stat treats 412 overlapping, seasonally-clustered trades as independent observations, and is internally inconsistent with the memo's own (more honest) placebo result.**
Earnings announcements cluster heavily within results seasons, and with up to 8 concurrent 10-session-hold positions, many of the 412 trades' holding windows overlap in time and share common macro/earnings-season exposure — they are not i.i.d. draws. The stated t-stat (3.4 = 0.42/(2.5/√412)) is computed as if they were, which understates the true standard error and overstates significance. This is directly visible in the memo's own placebo evidence: the strategy sits at only the **92nd percentile of 200 random-basket draws**, i.e. an empirical one-sided p ≈ 0.08 — nowhere near the p < 0.001 implied by a naive t-stat of 3.4. That internal inconsistency is itself the tell that the t-stat's independence assumption is violated.
*Fix*: report significance from the (dependency-robust) placebo/permutation percentile as the authoritative measure, or compute the t-stat with a block-bootstrap / Newey-West-style adjustment for overlapping, seasonally-clustered trades; don't present the naive per-trade t-stat as if it were reconcilable with the placebo result without flagging the discrepancy.

Numbered claimed material defects:
1. t-stat 3.4 computed assuming 412 independent trades, when concurrent/overlapping earnings-season trades are autocorrelated — overstates significance and is inconsistent with the memo's own placebo percentile (92nd/200 ≈ p 0.08).

(No defect found in the PIT membership, signal timing, execution, cost model, or placebo construction — those are correctly built and the memo's own verdict is appropriately conservative.)

===== T04 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. Rebalance timing uses the fiscal quarter-end date, not the actual public disclosure date of the results — a severe look-ahead violation (line: `rebal_day = close.index[close.index.searchsorted(qe, side="right")]`).**
Indian companies typically report quarterly results 30–45+ days after the quarter-end (`quarter_end`). The code selects the top-30 revenue-growth basket using `rev_yoy` computed from the full quarterly revenue figure, then rebalances into that basket on the **very next trading day after the quarter-end calendar date** — weeks before those results would have actually been public. This means the backtest picks stocks using revenue figures that could not possibly have been known at the time of the simulated trade; it is trading on hindsight of the quarter's actual outcome, not a PIT-available signal. This is the same category of bug the codebase elsewhere fixes correctly (e.g. `available_date`/`asof_date` logic in the earnings tasks) — here it's missing entirely.
*Fix*: anchor the rebalance to each company's actual results-announcement/publication date (analogous to `available_date` used correctly in the earnings-drift tasks), and only include a name in the ranking once its relevant quarter's figure is actually public; stagger/lag the rebalance to reflect real disclosure timing rather than the quarter-end.

Numbered claimed material defects:
1. Rebalancing on `quarter_end + 1 trading day` instead of the actual results-publication date — uses revenue data before it could have been known, a direct look-ahead bias that inflates the reported 21.7% vs 12.9% CAGR gap.

===== T05 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. Growth defined as a simple ratio `(new − old) / old`, which is mathematically nonsensical when the base (`ttm_eps_prev`) is negative or near zero — and the provided sample proves it's dominating the ranking.**
Look at the sample output given: `SUNWINDPWR` goes from a loss of −1.20 to a *deeper* loss of −2.55, yet `growth = (−2.55 − (−1.20)) / (−1.20) = 1.13`, ranking it **8th** among "fastest growers." `JPINFRAVENT` similarly deepens its loss (−0.35 → −0.68) and still ranks 9th. Meanwhile `BLUECHIPCO`, with a genuine +24% EPS improvement (98.40 → 122.10, a real, large, high-quality growth number), ranks only **61st** — far outside the top-20 basket. Worst of all, `TURNCORP` turns around from a loss of −5.00 to a profit of +1.00 (an unambiguous improvement) and is scored `growth = (1.00 − (−5.00)) / (−5.00) = −1.20`, ranking **496th, near the very bottom** — a genuine turnaround is treated as one of the worst "growth" outcomes in the universe purely because dividing by a negative base flips the sign. A ratio-based growth metric is not sign-consistent across a base that crosses zero or is negative, so the "top-20 fastest growers" basket is systematically populated by loss-deepening and near-zero-EPS penny names whose ratios blow up or invert (also visible in `ZENVITECH` 0.04→1.62 and `ORBIPHARM` 0.11→2.05, both producing enormous, meaningless ratios off a near-zero base), while genuine growth and turnaround companies are mis-ranked to the bottom. Given this defect is visible directly in the code's own sample output, it — not real fundamental growth exposure — is a highly plausible primary driver of the reported +34% vs 13% CAGR gap.
*Fix*: require `ttm_eps_prev` (and ideally `ttm_eps`) to be positive as an eligibility filter before computing a ratio-based growth score, or replace the raw ratio with a metric that handles sign changes correctly (e.g., a bounded/winsorized transform, or separate "improving profitability" vs "growing profit" screens).

Numbered claimed material defects:
1. `growth = (ttm_eps − ttm_eps_prev) / ttm_eps_prev` is undefined/sign-inverting for negative or near-zero `ttm_eps_prev`; the supplied sample shows deepening-loss names ranked top-10 and a genuine loss-to-profit turnaround ranked near the bottom — this corrupts the top-20 selection and is a very plausible driver of the reported outperformance.

===== T06 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. Backtest cycles run through an expiry (2026-07) beyond the stated data coverage (spot/chain "through 2026-06-30"), with no guard — `spot.asof(exp)` will silently forward-fill a stale price rather than fail.**
`monthly_expiry_calendar("2019-01", "2026-07")` generates a cycle whose expiry falls in July 2026, but the spot/chain dataset is explicitly stated to run only "through 2026-06-30." `settle_spot = spot.asof(exp)` for an `exp` beyond the last available data point returns the **last known (stale) value** rather than raising an error — `.asof()` forward-fills silently. There is no assertion anywhere in this code (unlike the closely related weekly-condor task, which explicitly guards `expiry <= idx_close.index.max()`) preventing a cycle from being scored using a fabricated, stale settlement price instead of an actual expiry-day print. This risks either fabricating a benign payoff for a cycle that never should have been included, or corrupting the "90 cycles" count / the reported "-412 pts worst cycle" if that boundary cycle happens to be an extreme one.
*Fix*: assert `exp <= spot.index.max()` (and equivalently that the entry-day chain prices exist) before including a cycle in `expiries`; drop or explicitly flag any cycle whose expiry falls after the data cutoff rather than letting `.asof()` silently substitute a stale value.

Numbered claimed material defects:
1. The expiry calendar extends to 2026-07 while spot/chain data is stated to end 2026-06-30, and `spot.asof(exp)` will silently forward-fill a stale settlement price for any such cycle instead of erroring — fabricates the payoff for at least the final cycle(s).

===== T07 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

Signal timing (decision after Tuesday's close using Tuesday data), execution (Wednesday open fills with an explicit no-fill skip when a leg didn't trade), the settlement calculation (correctly uses the official index close for cash-settlement intrinsic value on all four legs, with the right sign convention for a net-credit iron condor), and the explicit `expiry <= idx_close.index.max()` guard are all done correctly.

**1. Weeks containing a scheduled major event (budget, RBI, election result) are silently excluded from the backtest — this removes precisely the tail-risk weeks a short-premium condor is most exposed to, understating true worst-case risk.**
The comment "weeks with a scheduled major event... are skipped" is a selection/survivorship bias, not a genuine data or liquidity constraint: it deliberately removes exactly the highest-realized-move weeks for a defined-risk-but-still-short-vol strategy from the sample used to compute hit rate and worst-week loss. The reported "-312 pts (wings capped it)" worst week is therefore not a genuine worst case — an actual live budget/RBI/election week (which the strategy will, in reality, be running through) could produce a materially larger loss than anything in the simulated sample, since those exact weeks were never simulated.
*Fix*: include event weeks in the backtest with the same mechanics (or run them as an explicit separate stress overlay), and report the worst-week figure both with and without those weeks so the true tail is visible rather than hidden by omission.

Numbered claimed material defects:
1. Systematic exclusion of scheduled-event weeks (budget/RBI/election) — a selection bias that hides the short-vol strategy's true tail risk and makes the reported worst-week (-312 pts) unrepresentative.

===== T08 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. `day_open = g.iloc[0]["open"]` takes the chronologically-first print of the day without filtering to the regular trading session — likely capturing a pre-open-session indicative price, not a tradable open.**
The task explicitly notes "the file includes every print the vendor ships for the session," which is a strong signal that the 1-minute file contains NSE's pre-open call-auction prints (order collection ~9:00–9:08, matching ~9:08–9:12, buffer to 9:15) in addition to regular continuous-trading bars. `g.sort_values("ts").iloc[0]["open"]` simply grabs whichever print is chronologically first — if that is a pre-open indicative/auction print rather than the 9:15 regular-session open, both the gap-detection signal (`gap = day_open/prev_close − 1`) and the entry fill price are computed off a price that may not have been genuinely tradable at that moment, or may not represent the same thing session to session.
*Fix*: filter to `t >= time(9, 15)` before taking the first row as `day_open`, ensuring the "open" used for both signal and fill is the actual regular-session opening trade.

Numbered claimed material defects:
1. No filter excluding pre-open/auction prints before selecting the day's first bar as `day_open` — risks using a non-tradable indicative price as both the gap signal and the entry fill.

===== T09 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. `df["adv_dec"] = (df["advances"] / df["declines"]).shift(-1)` — a negative shift pulls the *next* day's breadth ratio into today's row, directly contradicting the stated design ("features... evaluated at day t's close, from data known by that close").**
Every other feature (`mom10`, `vol20`, `above_dma`, `vol_regime_ok`) is correctly trailing/same-day (no forward shift). Only `adv_dec` uses `.shift(-1)`, which in pandas moves *future* values backward in time — the value at row *t* becomes the advances/declines ratio actually observed on day *t+1*. Since `advances`/`declines` for day *t* are already known at the close of day *t* (no shift is needed at all for that feature to be PIT-correct), this `.shift(-1)` is a straightforward one-day look-ahead: the entry signal at day *t* is partly conditioned on breadth data from day *t+1*, which would not exist yet in live trading.
*Fix*: drop the shift entirely — `df["adv_dec"] = df["advances"] / df["declines"]` — so the breadth-confirmation feature uses only same-day (already-known-by-close) data, consistent with the other three features and the stated design.

Numbered claimed material defects:
1. `.shift(-1)` on the advances/declines ratio leaks next-day breadth data into today's signal — a direct one-day look-ahead bias in the breadth-confirmation filter.

===== T10 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. The "near-zero daily correlation" evidence is measured on a series that is an exact zero on ~81% of days (the sleeve is flat outside its ~19% active days) — this mechanically shrinks correlation toward zero regardless of the true relationship, and is contradicted by the memo's own monthly evidence.**
A daily P&L series that is a hard zero four days out of five cannot show much linear correlation with anything on those flat days almost by construction; the reported +0.01 to +0.03 pairwise correlations are not strong evidence of genuine orthogonality, only of the sleeve being inactive most of the time. More importantly, the memo's own worst-5-months table directly contradicts the "uncorrelated stream" conclusion: EVT-1 lost money in **every one of the book's worst 5 months** (Mar-2020, Jun-2022, Jan-2023, Oct-2024, Mar-2025) — exactly when the rest of the book was also having its worst months. A near-zero *average/daily* correlation is masking a real *tail* dependence that shows up precisely in the drawdown months that matter for risk, the opposite of what a diversifier should look like.

**2. The Sharpe-stacking arithmetic ("lifts the projected book Sharpe to ~1.38 via standard root-N combination of independent streams") assumes the same independence the evidence above contradicts.**
Root-sum-of-squares Sharpe combination is only valid for genuinely uncorrelated (and ideally independent, not just linearly-uncorrelated-on-average) return streams; given the tail-correlation shown in the monthly table, this projection is not warranted, especially in exactly the scenarios (large drawdown months) where the diversification benefit is supposed to matter most. The claim that "the diversification benefit does not depend on the sleeve's standalone return staying at backtest levels" is also an overclaim — the benefit depends on the correlation structure holding, which the memo's own data suggests it may not, in the tail.

Numbered claimed material defects:
1. Near-zero daily correlation computed over an ~81%-flat series is a mechanically deflated, misleading measure of true co-dependence.
2. The worst-5-months table shows EVT-1 losing money in every one of the book's worst 5 months — direct evidence against the "uncorrelated return stream" claim that the memo's headline correlation table is built on, undermining the Sharpe-stacking projection derived from it.

======================================================================

===== T11 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. `iv_ma = iv.rolling(11, center=True).mean()` — a centered rolling window leaks future IV into today's "local average," corrupting the richness signal.**
`center=True` on an 11-day rolling window at date *t* uses 5 days *before* **and 5 days after** *t*. The comment framing this as de-noising ("de-noise the series before comparing level vs local average") doesn't change the fact that the resulting `iv_ma[t]` depends on IV observations from *t+1* through *t+5*, which are not known at time *t*. The richness test `rich = iv > 1.15 * iv_ma` and the resulting entry-day selection are therefore computed partly from future data — a straightforward look-ahead bug, and one of the more mechanical/unambiguous ones in this set.
*Fix*: use a trailing-only window, `iv.rolling(11).mean()` (or better, `iv.rolling(11).mean().shift(1)` to be strictly conservative), never `center=True`, for any signal meant to be tradable in real time.

Numbered claimed material defects:
1. `rolling(11, center=True)` on the IV series uses 5 future days of IV in "today's" local average — a direct look-ahead bias in the entry signal.

===== T12 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. Using bhavcopy `SETTLE_PR` directly as the expiry-day exit price, without sanity-checking it against computed intrinsic value, allows corrupted/stale settlement prints to flow straight into P&L — this is almost certainly what's producing the reported four-and-five-digit-point "losses" on weeks the index barely moved.**
The comment defending this choice ("SETTLE_PR is the official settlement and avoids stale last-trade CLOSE prints") is exactly backwards for exchange daily bhavcopy data on options: for illiquid or zero-volume-on-the-day contracts, exchanges commonly carry forward or default the daily settlement field, and it does not automatically equal the true expiry intrinsic value. The reported symptom is the tell: an ATM straddle's payoff at expiry is bounded by roughly how far the index moved past the strike — if "several expiry weeks show four-digit point losses even on weeks the index barely moved," that is *mathematically impossible* for a genuine ATM straddle settling at true intrinsic value (e.g. −23,912 pts on a week the index barely moved cannot be real option payoff). The author's own explanation ("pin risk... add a stop?") is a red herring — pin risk produces small differences near the strike, not five-digit point swings. The actual defect is a data-integrity issue: `SETTLE_PR` is being trusted blindly instead of being cross-checked against `max(settle_spot − K, 0)` / `max(K − settle_spot, 0)` computed from the official index close, exactly as is done correctly elsewhere in this codebase (the weekly-condor task computes cash-settlement intrinsic value directly from the index close rather than trusting a bhavcopy settlement field).
*Fix*: compute the expiry exit value from intrinsic value using the official index close and the known strike, not from `SETTLE_PR`; at minimum, cross-check `SETTLE_PR` against computed intrinsic value and quarantine/exclude any week where they diverge materially rather than booking the raw field into P&L. Retract the "add a stop for pin risk" recommendation — it addresses the wrong problem.

Numbered claimed material defects:
1. Expiry-day exit price taken from bhavcopy `SETTLE_PR` without cross-checking against computed intrinsic value — produces the reported five-digit-point "losses" on weeks with negligible index movement, which are not economically possible for a genuine ATM straddle and indicate corrupted/stale settlement data, not real P&L.

===== T13 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. Universe is a single, present-day (2026-07) constituent list applied uniformly across the entire 2013–2025 backtest, not point-in-time NIFTY500 membership — this defeats the purpose of using a survivorship-complete price panel.**
`universe = pd.read_csv("nifty500_constituents.csv")["Symbol"].tolist()` is explicitly noted as "downloaded from the index provider's website, 2026-07 refresh." `close[[c for c in close.columns if c in universe]]` then restricts the *entire* backtest's tradable universe to that single, current-day list. Even though the underlying price panel is correctly survivorship-complete (includes delisted names), the universe filter itself is not point-in-time: any stock that was a genuine NIFTY500 constituent in, say, 2015 but has since been removed by 2026 (whether delisted or simply dropped from the index) is wrongly **excluded** from the entire 2013–2025 backtest, while a stock that only joined the index in, say, 2023 is wrongly treated as **eligible** for momentum ranking as far back as 2013. This is the same current-membership survivorship/look-ahead bias that this codebase handles correctly elsewhere via `load_pit_membership()` with `.asof()` snapshot logic — that mechanism is simply missing here.
*Fix*: replace the static CSV universe with a point-in-time NIFTY500 constituent history and look up membership `.asof(me)` at each month-end rebalance, exactly as done correctly in the revenue-growth-rotation and mid-cap-momentum tasks elsewhere in this review batch.

Numbered claimed material defects:
1. Static, current-day (2026-07) NIFTY500 constituent list applied across the full 2013–2025 backtest instead of point-in-time historical membership — introduces current-membership survivorship/look-ahead bias despite the underlying price panel being survivorship-complete.

===== T14 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

Overall methodology is careful: inputs computed at 15:00 from data through 14:59 (no lookahead), realistic entry/exit execution windows, an exposure-matched random-nights baseline (not just an unconditional one), a same-exit-engine placebo, a one-day-lag decay test, era splits, and disclosed no-fills on limit-locked nights — all genuinely good practice.

**1. The "selection adds +2.2bp/night over matched exposure" claim mixes a gross figure against a net figure, inflating the isolated selection-effect by roughly the size of the trading cost.**
The memo states unconditional/all-nights drift is "+0.9bp/night" and, separately, that the exposure-matched random-nights baseline "earns +0.9bp/night net of the same costs" — reusing the identical number for what should be two different quantities (a raw drift figure vs. a cost-adjusted baseline), which is only possible if trading costs are treated as zero for one of them despite costs being explicitly modeled at 1.2bp/night round-trip. The stated "+2.2bp/night added by selection" is consistent with 3.1 (gross strategy edge) − 0.9, i.e. comparing the strategy's **gross** figure to a baseline labeled **net** — not a like-for-like comparison. Computed consistently net-to-net, the strategy's net edge (1.9bp) minus the matched-exposure baseline's net edge (0.9bp) gives only **+1.0bp/night** of genuine selection-specific value-add — less than half the claimed +2.2bp. This materially changes how much of the sleeve's return should be attributed to the "selection" logic versus plain unconditional/matched-exposure overnight drift.
*Fix*: recompute the matched-exposure comparison using the same basis (gross-vs-gross or net-vs-net) on both sides, and restate the "selection adds ___" figure consistently; reconcile why the unconditional-drift figure and the net-of-cost random-baseline figure are identical when a nonzero cost is applied to the latter.

Numbered claimed material defects:
1. The "+2.2bp/night added by selection" figure appears to compare a gross strategy number (3.1bp) against a baseline explicitly labeled net-of-costs (0.9bp); a consistent net-vs-net comparison (1.9bp − 0.9bp) gives only +1.0bp/night, less than half the claimed selection-specific edge.

===== T15 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. `mu`/`sd` used to standardize IV are computed over the entire 2015–2025 sample, then used to generate entry signals throughout that same sample — a full-sample look-ahead.**
`mu = hist["iv"].mean(); sd = hist["iv"].std()` are calculated once, using all ten years of data, including years far in the future relative to any given historical entry date. An entry signal generated in, say, 2016 (`iv_z = (iv − mu) / sd`, `entry = 1.0 < iv_z < 2.5`) is therefore evaluated against a mean and standard deviation that could not have been known until 2025 — the "so the rule generalizes across vol regimes" framing is a rationalization for what is actually a lookahead bug, not a robustness feature. Because realized IV regimes shifted meaningfully over this decade, calibrating the z-score threshold against full-sample statistics gives the backtest the benefit of hindsight the live rule would never have had, inflating the apparent hit rate and edge.
*Fix*: compute `mu`/`sd` from only a trailing or expanding window of data strictly available before each date (e.g., a rolling multi-year window, or an expanding window using data only through *t−1*), never from full-sample statistics.

Numbered claimed material defects:
1. IV z-score standardized against full-sample (2015–2025) mean/std rather than a trailing/expanding window — a full-sample look-ahead bias in the entry threshold.

(The "crash filter" excluding `iv_z > 2.5`, and the resulting exclusion of the Mar-2020 episode, is disclosed and intentional — a labeled design choice, not a hidden defect, though it does mean the rule is untested against its most extreme regime by construction.)

===== T16 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. The random-basket "hurdle" is refreshed monthly (≈330%/yr turnover) while the strategy under test rebalances semiannually (38%/yr) — an ~8.7x turnover mismatch that, not genuine selection skill, is the main source of the claimed net outperformance.**
The memo states both arms are "charged the same honest cost model: 45bp per side," and treats that as sufficient for a fair comparison — but an identical cost *rate* does not make the comparison fair when the two arms trade at radically different *frequencies*. The random hurdle's gross-to-net drag (14.7% → 11.5%, ≈3.2pp) is consistent with its stated ~330%/yr turnover, while the strategy's drag (15.0% → 14.6%, ≈0.4pp) is consistent with its much lower ~38%/yr turnover — the cost figures are internally consistent, but the *comparison* is not apples-to-apples: a properly constructed null for testing "does this semiannual quality-tilt rule select stocks better than random" must rebalance the random baskets at the **same** semiannual frequency as the strategy, so that the only difference between strategy and null is stock selection, not trading frequency. As built, most of the claimed "+3.1pp/yr beats even the 95th-percentile hurdle" edge is very plausibly just the cost saved by trading 8.7x less often, not evidence of quality-factor selection skill. This is the same turnover-matching principle this codebase applies correctly elsewhere (e.g., the mid-cap-momentum task explicitly builds its random-basket null with "SAME monthly rebalance dates").
*Fix*: rebuild the random-basket hurdle to rebalance semiannually (same frequency/turnover discipline as the strategy, ~38%/yr), recompute its gross and net CAGR distribution, and re-measure the net-of-cost gap; report both a gross-vs-gross comparison (isolates selection skill) and a frequency-matched net-vs-net comparison before certifying any expected outperformance number.

Numbered claimed material defects:
1. Random-basket hurdle refreshed monthly (~330%/yr turnover) vs. the strategy's semiannual (~38%/yr) rebalance — an unmatched-turnover null whose extra cost drag manufactures most of the claimed +3.1pp/yr net outperformance, rather than genuine stock-selection skill.

===== T17 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. `best = win.loc[win["ff"].idxmax()]` picks the single best-priced day across the *entire* T-30..T-10 window in hindsight — not a rule that could be implemented in real time.**
The stated question the engine is meant to answer is "which day inside the T-30..T-10 window should we enter each cycle" — but the code answers it by first collecting the **whole** window (`win = ff[... lead between 10 and 30]`), including days as close as T-10, and then taking the argmax of `ff` across that whole span. To know on, say, day T-28 that it will turn out to be the best-priced day in the window, you would already need to have observed every day down to T-10 — 18 days in the future relative to T-28. This is a full-window-argmax look-ahead: the "decision" of which day to enter is made with knowledge of days that haven't happened yet relative to the earlier candidate days in the window, and no live trading rule could reproduce this selection in real time.
*Fix*: replace the full-window argmax with a real-time-implementable rule — e.g., enter as soon as `ff` first crosses a pre-committed threshold (evaluated causally, day by day, using only data through that day), or enter at a fixed pre-specified lead time — and re-measure performance under that rule instead of the in-hindsight optimum.

Numbered claimed material defects:
1. `win["ff"].idxmax()` selects the best entry day using the full T-30..T-10 window, including future days relative to earlier candidates in that window — a look-ahead bias; no real-time rule could reproduce this choice.

===== T18 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. The audit script's date-matching against candle timestamps is broken, and the "all 501 legs UNFILLABLE" result — including deep-liquid ATM NIFTY weeklies — is the signature of that bug, not a real liquidity finding.**
The task explicitly flags that "the broker's daily (ONE_DAY) candles are known to be stamped at 00:00 IST" — a strong hint about timestamp convention that the code does not account for. `entry_bar` is located via `if c[0][:10] == leg.entry_date.strftime("%Y-%m-%d")`, a naive string-prefix match against the candle's raw timestamp. If the broker's daily candle for trading day *D* is actually stamped at 00:00 IST of day *D+1* (a common convention — the bar is timestamped at its "close," i.e. the start of the next calendar day — directly analogous to the vendor-timestamp mismatch that appears elsewhere in this review batch), then `c[0][:10]` will equal `D+1`, never `D`, and the match will **never succeed for any leg, regardless of true liquidity**. That is exactly the observed symptom: a 100% UNFILLABLE rate across all 501 legs, including instruments (deep-liquid ATM NIFTY weeklies) that are certainly not illiquid in reality. The correct diagnosis is a systematic date-alignment bug in the audit script, not an untradeable paper book — the recommendation to void the week's paper results is therefore unwarranted as stated.
*Fix*: parse `c[0]` as a real datetime and resolve the actual session it represents according to the broker's documented stamping convention (e.g., compare against `entry_date + 1 day` if bars are stamped at next-midnight, or better, check whether `entry_date`'s session falls inside `[bar_start, next_bar_start)` rather than doing a fragile string-prefix match), then re-run the audit before drawing any conclusion about fillability.

Numbered claimed material defects:
1. Candle-timestamp date matching (`c[0][:10] == entry_date`) does not account for the broker's stated 00:00-IST daily-candle stamping convention, causing every lookup to fail and every leg to be wrongly flagged UNFILLABLE — the "untradeable paper book" conclusion is an artifact of this bug, not a real finding.

===== T19 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

No material defect. This submission is built correctly: point-in-time NIFTY membership via `.asof(me)` snapshot logic, momentum computed strictly from data through the signal date, stale/frozen price runs explicitly masked out of both the signal and return calculations (rather than silently distorting either), delistings marked-to-last-price with the loss realized on the delisting date (no silent drop, which would otherwise flatter results), next-session open-fill execution with an explicit no-fill check, and — importantly — the 10,000-basket random null is drawn from the *same* panel, *same* PIT universe, and *same* monthly rebalance dates as the strategy, which is exactly the turnover/exposure-matching discipline needed for the percentile comparison (93rd percentile vs. random) to be meaningful.

Non-material comment (not a defect): during a stale-masked window, `pd.DataFrame.sum(axis=1)` with `skipna=True` (default) effectively treats that name's allocated weight as contributing nothing to the portfolio during the mask, without explicitly reallocating its capital to the remaining basket or otherwise flagging the reduced invested exposure. Since this masking is applied identically to both the strategy and the random null (same panel), it doesn't bias the reported relative comparison, but tightening the accounting (either reweighting the remaining names or explicitly zero-flooring the masked name's return rather than relying on `skipna`) would make gross-exposure bookkeeping more transparent.

1. None — no material defect identified.

===== T20 =====
Review this. Identify any defects that would make the result wrong or fake. Be specific.

**1. The placebo substitutes a different, simpler fixed-5-session exit instead of the strategy's own adaptive exit engine — this does not isolate the entry signal, and much of the reported outperformance could come from the exit engine's optionality rather than the RSI-dip entry itself.**
The strategy's exit is a first-touch barrier (+2.0% target OR −4.0% stop OR 20-session timeout, intraday touch), which has inherent asymmetric/optionality-driven behavior (a closer profit target than stop tends to mechanically raise win rate and can shape mean/trade independent of whether the entry itself carries real information). The placebo, however, exits every random trade at a **fixed** close of the 5th session, explicitly "chosen to approximate the strategy's typical holding period" rather than using the identical rule. A holding-period *average* match is not the same as using the *same exit engine* — elsewhere in this review set, well-constructed placebos (e.g., the post-earnings-drift and mid-cap-momentum submissions) explicitly reuse the identical exit engine for the null, precisely so that any measured outperformance can be attributed to the entry signal and not to a different payoff shape at exit. As built here, the 99th-percentile placebo comparison is confounded by the exit-engine difference, so "the entry signal carries real selection information" is not properly established by this test.
*Fix*: rerun the placebo with the exact same adaptive exit rule (+2%/−4%/20-session timeout, intraday touch) applied to the 500 random-entry baskets, not a fixed 5-day close exit, before concluding the entry signal itself is validated.

Numbered claimed material defects:
1. Placebo exit engine (fixed 5-session close) differs from the strategy's exit engine (adaptive +2%/−4%/20-session-timeout barrier) — confounds the entry-signal test with an unmatched exit, since the same-exit-engine discipline used correctly elsewhere in this batch is not applied here.

======================================================================
# END OF FILE — all 8 MG tasks and all 20 T tasks completed.
