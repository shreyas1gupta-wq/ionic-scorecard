# PRE-REGISTRATION — PLEDGE_SAFE_20260802
Written before running. Question: Rs 50L gov bond (8%) + Rs 50L equity MF (12% assumed) held as a
base portfolio, BOTH pledged as collateral, and the resulting margin used to run the firm's one
real-fill-validated NIFTY short-vol edge (S1-F) as a yield overlay. Does the combined portfolio stay
genuinely capital-protected?

## This is NOT a new options-edge search
S1-F's edge (0DTE NIFTY ATM short straddle, +10.7 pts/day net, t=3.92, PF 1.79, n=259, frozen D-030,
`06_TRADING_DESK/specs/S1F_SPEC.md`) is reused UNCHANGED — no re-tuning of entry/exit/veto rules
(that would violate the forward-test freeze). The ONLY new variable is the CAPITAL SOURCE and
resulting lot-sizing. The frozen spec itself flags this exact question as out of its own scope:
*"Pledged-collateral margin (liquid funds) is the legitimate lever to lift capital efficiency —
Principal decision, not part of this spec."* (S1F_SPEC.md, sizing section). This backtest is that
Principal decision being tested.

## Sizing model
- **Book equity** = Rs 50L bond + Rs 50L MF = Rs 1cr, held throughout (never sold, only pledged).
- **Haircuts [ASSUMPTION, external-search attempted, no single citable 2026 rate exists — VaR-based,
  scheme-specific, published only in the live NSE-approved-securities list]:** G-sec 10% (search
  found ~5% for gov-sec/liquid-fund growth plans; 10% used as a conservative round number) / equity
  MF 30% (no exact figure found; industry-typical VaR-based range for diversified equity funds is
  ~20-40%; 30% used as a mid-range conservative estimate). **Available margin (haircut basis) =
  Rs 45L + Rs 35L = Rs 80L.**
- **RISK_LIMITS.md book-level rule (already firm policy, not invented here): aggregate short-vol
  margin <= 40% of book equity; free cash/buffer >= 30% at all times.** Applied dynamically:
  margin_budget(t) = 0.40 x current(bond(t)+MF(t)). At Rs 1cr this is Rs 40L <= the Rs 80L haircut
  ceiling, so **the firm's own risk rule binds, not the haircut assumption** — the result is
  therefore fairly insensitive to the exact haircut % chosen, PROVIDED haircuts stay under ~60%
  blended (a robustness point, checked, not assumed).
- Per-lot margin, veto rules (F1/F2), and the 3-day-vol crash-halving rule are reused VERBATIM from
  S1F_SPEC.md (spot x 75 x 0.15; RSI5 D-1 >=80/<=20; |D-1 ret|>1.5%). Crash rule approximated on
  DAILY realized vol (3d vs 1yr trailing median, D-1 values) rather than 1-min bars — [ASSUMPTION,
  disclosed: tractability, expected to be similarly conservative not looser].
- Realized options P&L accumulates as cash, NOT reinvested into more lots — margin budget is always
  anchored to the SAFE base assets only, never to trading gains (prevents pyramiding the risky sleeve).

## Two base-return variants (flat assumption is a known firm anti-pattern elsewhere — tested both ways)
1. **FLAT**: bond @ 8%/yr, MF @ 12%/yr, both daily-compounded — Principal's literal numbers.
2. **REAL**: bond @ 8%/yr (unchanged, G-secs are genuinely close to deterministic), MF replaced with
   actual NIFTY 500 daily price-index returns 2021-05-27..2026-07-03 (`datasets/index_daily/
   nifty500.parquet`) — shows real sequencing/drawdown risk a flat 12% hides. [DATA, price return not
   total return — understates real fund NAV by roughly the dividend yield, ~1-1.5%/yr, disclosed not
   corrected for].

## What "very very safe" will be judged on
Max drawdown of the COMBINED portfolio (bond+MF+options, not options alone), worst single expiry-day
loss as % of total book, whether margin utilization ever approaches the 40%/80L ceilings, and an
approximate COVID-stress rescaling from the existing `SELLSIDE_20260710/covid_backcast` result
(spec's own stress MDD ~-16% at 75%-of-Rs10L reference sizing) — noted as an [INFERENCE] scaling by
relative margin-to-book ratio (40% vs the spec's 75%), not a fresh stress rerun; flagged for the
red-team pass, not presented as verified.

## Kill / caveat criteria
Not a new-edge gate-4 (edge is already frozen/proven) — this is a CAPITAL-STRUCTURE evaluation.
Flag (not silently pass) if: margin utilization ever exceeds the 40% book cap; combined MaxDD at
FLAT assumption differs materially from combined MaxDD at REAL MF returns (sequencing risk exists if
so); worst-day loss exceeds what "very very safe" could honestly claim without a defined-risk (wing)
overlay — in which case a defined-risk variant is recommended as a follow-on, not silently substituted.
