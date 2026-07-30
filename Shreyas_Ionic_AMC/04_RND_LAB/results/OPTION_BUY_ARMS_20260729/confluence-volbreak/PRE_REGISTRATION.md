# PRE-REGISTRATION — ARM 3: CONFLUENCE STACKING + VOLATILITY BREAKOUT (option-buying)

Written **2026-07-29, BEFORE any result in this folder was computed.** Binding under firm
order D-035. Any amendment must be appended below with a timestamp and a reason — never
a silent rewrite.

Requested output path was the literal string `undefined/OPTION_BUY_ARMS_undefined/...`
(variable-interpolation bug in the orchestrator). Using the firm convention
`04_RND_LAB/results/OPTION_BUY_ARMS_20260729/confluence-volbreak/`.

---

## 1. THE QUESTIONS (fixed before running)

**Q1 (structural, the Principal's core question).** Does stacking conditions BUY
MAGNITUDE, or only SHRINK n? Measured as: signed spot move AND real option net P&L as a
function of the NUMBER of stacked conditions k = 1, 2, 3, 4.

**Q2.** Does `volbrk_orb_volfilter` (+5.60 pts, t=2.23 on spot) survive as its own option
arm after real 1-min option fills and binding costs? Same for the two other volatility-
state triggers (ATR expansion, Keltner squeeze release).

**Q3 (the honest mechanism question).** When you enter on a volatility EXPANSION, are you
buying already-elevated IV? Measured as: real entry IV percentile — derived from REAL
1-min option prices, never assumed — vs the subsequent realized move and vs the actual
option net P&L.

## 2. DATA AND ENGINE (no new machinery)

* Spot: `hf_index_options_1m/index/NIFTY.parquet`, pre-open 09:00–09:07 removed.
* Options: `hf_index_options_1m/options/NIFTY/{expiry}.parquet`, real 1-min prints.
* Signal generators: **reused verbatim** from
  `04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py`
  (`supertrend_flips`, `atr_expansion`, `keltner_squeeze_release`, `orb_vol_filter`,
  `sweep_signals`, `level_breakout_reject`, `round_number_levels`, `confluence_buckets`).
  No re-derivation, no re-tuning of any generator parameter.
* Option P&L: **reused verbatim** from `OPTION_PL_HARNESS_20260729/opt_pl.py`
  (UNIT-1..4 / REG-1 / SANITY-6 validated). No fill logic is rewritten here.
* Costs: `cost_model="cost_standards"` (STT 0.1%, exch 0.035%, GST 18%, brokerage ₹20/order,
  stamp, SEBI) + 0.5%/leg slippage with the harness's dynamic multiplier.
  COST_STANDARDS.md is APPROVED (D-021) and binding.
* Entry fill = the option's first 1-min bar **strictly after** the signal bar. Never same-bar.
* Indicators computed **per day**; no cross-session state.

## 3. SPLIT (frozen)

* **BUILD: 2021-05-24 .. 2025-12-31.** All selection happens here.
* **FORWARD (HELD OUT): 2026-01-01 .. 2026-06-03.** Reported, never selected on.
* Nothing in section 5 may be changed after looking at forward numbers.

## 4. THE CONFIG GRID (fixed; no config outside this list will be run and reported as a result)

Option configs (all `lots=1` so per-trade % returns are comparable; all intraday
`max_hold_days=0`, mandatory flat 15:25):

| id | strike | DTE window | exits |
|---|---|---|---|
| C1 | ATM (`strike_offset=0`) | 1–7 | none (pure directional, flat 15:25) |
| C2 | ATM | 1–7 | target +50% / stop −30% |
| C3 | 2 steps ITM (`strike_offset=-2`) | 1–7 | none, flat 15:25 |
| C4 | ATM | 0–7, `expiry_handling="trade_out"` | none, flat 15:25 (0DTE allowed) |

Signal cells:

* Confluence: `stack1, stack2, stack3, stack4` — "exactly k distinct condition families
  agree on the same 15-min bar in the same direction". Also reported cumulatively (≥k) as
  a robustness view, because that is how retail designs are actually specified.
  Two stack definitions:
  * **STACK-A** (primary, zero selection): condition families exactly as the sibling
    script built them — supertrend(15m,ATR10x3), atr_expansion(15m), sweep (ALL four
    variants unioned), S-R (weekly+monthly+round, breakout+reject unioned).
  * **STACK-B** (robustness, FLAGGED as in-sample-informed): sweep family restricted to
    the two variants that measured positive on the build set. This uses build-set
    knowledge and will be labelled as such; it is never the headline.
* Volatility breakout: `volbrk_orb_volfilter`, `volbrk_atr_expansion`,
  `volbrk_keltner_squeeze_release`.

Total pre-registered cells × configs = (4 stack + 3 volbreak) × 4 configs = 28 runs,
plus the STACK-B robustness set and the two IV-conditioned runs in §6. Every one of these
counts as a trial for multiple-comparison honesty and will be stated in the summary.

**Compute rule (declared now, not after seeing anything):** a cell whose BUILD signal
count exceeds 4,000 is uniformly subsampled to 4,000 with `numpy.default_rng(0)`. This is
a runtime measure only; it is applied identically across configs so the k-comparison stays
apples-to-apples, and the FORWARD set is never subsampled. Subsampled cells will be
labelled with their true n.

## 5. KILL / PASS CRITERIA (the pass bar, fixed)

A config PASSES only if **all four** hold:

1. **NET-POSITIVE after real costs on the BUILD set** (`net_total > 0`).
2. **Sign does not invert on the held-out 2026 H1 forward set** (forward `net_total >= 0`,
   or forward n < 10 in which case the cell is reported as UNDERPOWERED, not as a pass).
3. **No single trade > 30% of gross profit** (`top1_profit_share <= 0.30`).
4. **Fills credible**: zero-volume entry fill fraction <= 5%, and the cell's fill rate is
   reported alongside so a low-fill cell cannot masquerade as a strategy.

If no config in §4 passes, the arm is **KILLED** and reported as such, plainly, with no
softening and no post-hoc search for a variant that survives.

**Anti-tuning clause.** I will not add a config, a strike, an exit rule, a DTE window, a
time-of-day filter or a volatility filter after seeing results. The only conditional test
is the single pre-specified one in §6.

## 6. THE ONE PRE-SPECIFIED CONDITIONAL TEST (IV mechanism, Q3)

IV is derived from REAL option prices only:

* At each entry, read the real ATM CE and ATM PE 1-min prices → ATM straddle premium.
* Price-derived vol proxy `sig_straddle = (straddle / spot) / sqrt(DTE_cal/365)`.
  This is a normalisation of an observed price, not an assumed vol level.
* Also solve Black–Scholes IV from the real ATM CE price by bisection, r=0, q=0,
  T = calendar DTE/365. **Assumption declared:** r=0/q=0 and spot-not-forward make this a
  monotone approximation, adequate for a PERCENTILE, not for a quoted vol level.
* IV percentile = rank of that entry's IV within all entries of that same cell on the
  BUILD set (expanding-history rank is not used; the full-cell rank is a descriptive
  statistic, and I will say so rather than present it as tradeable at the time).
  A **strictly PIT expanding-window percentile** is additionally computed and is the only
  version used for the conditioned trade test below.

Conditioned runs (exactly two, no search):

* **IV-LOW**: same cells/configs but keeping only entries whose PIT-expanding IV
  percentile <= 33.3 (bottom tercile).
* **IV-HIGH**: complement (> 66.7) — run as the falsification: if buying is a vol-cheapness
  trade, IV-HIGH must be worse. If IV-LOW and IV-HIGH are indistinguishable, the
  "buy cheap vol" mechanism is absent and I will say so.

Tercile cut fixed at 33.3/66.7 in advance. No other cut will be tried.

## 7. WHAT COUNTS AS AN HONEST NEGATIVE

* A flat magnitude-vs-k curve with collapsing n **is the answer to Q1** and is a valuable
  result, not a failure of the study.
* Every cell reports GROSS and NET separately, and positive-month fraction on BOTH
  (an under-costed backtest fakes exactly the "consistent returns" claim).
* Concentration >30% of profit in one trade/day ⇒ labelled FRAGILE regardless of headline.
* Any metric that is genuinely undefined (e.g. CAGR on a negative equity path) gets a
  sentinel and a sentence, never an invented number.
* PCR: index volume is 0 and option OI is unusable (~64% zeros 2025+, 32% of validated
  entries). **No PCR / OI-based condition will be used anywhere in this arm.** If a
  volume-based chain statistic is reported at all it will be option-chain traded volume
  with its sample stated.

---

## 8. TWO FURTHER ITEMS DECLARED NOW (not amendments — written before any run)

1. **`no_overlap=True` diagnostic.** The grid runs allow heavy simultaneous positions
   (stack1 fires ~16x/day), so per-trade % return is the honest metric there. I will
   additionally run C1 with `no_overlap=True` on the highest-magnitude confluence cell and
   on the ORB cell, as a single-position-book diagnostic. It is a diagnostic only: it
   cannot rescue a cell that fails §5 net-positivity.
2. **Scope of the §6 IV-conditioned runs:** the ORB cell and the ATR-expansion cell only —
   the two genuine volatility-state triggers, which is where Q3's mechanism lives. This
   reduces, not increases, the trial count.

---

## AMENDMENTS

**A1 — 2026-07-30, after the three volatility-breakout cells finished, before the control
was run. Reason:** every volatility cell's held-out 2026 H1 forward set came out
NET-POSITIVE (ORB +0.08%/trade, ATR-expansion +4.55%, Keltner +6.14%) while every build
set was deeply negative. A uniform forward sign across mechanically unrelated triggers is
the signature of a favourable REGIME, not of signal validity. So I am adding one test:

* **RANDOM-2026H1 CONTROL** — 1,500 uniformly random timestamps and random directions in
  the forward window only, run through config C1. Same must-fail logic as the harness's
  build-window random control.
  * If random signals are ALSO net-positive in 2026 H1, then "forward net-positive" carries
    no information in this window and no cell may claim credit for it.
  * If random signals are net-negative while a cell is net-positive, that cell's forward
    result is worth something.

This control can only make the verdict more conservative — it cannot rescue a cell, because
pass criterion §5.1 (build net-positive) is untouched. Adding a must-fail control after
seeing a suspicious pattern is diagnosis, not tuning; the pass bar is unchanged.

*(no other amendments)*
