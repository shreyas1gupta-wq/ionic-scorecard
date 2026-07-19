# H1 — Dealer Gamma / GEX Regime Gate: Cheap-Test Result
**By:** Aakash Jain (Derivatives Structurer), running the pre-registered spec from
`Shreyas_Ionic_AMC/04_RND_LAB/ideas/20260703_dealer_gamma_gex.md` · 2026-07-18 ·
[DATA]/[INFERENCE]/[OPINION] tagged throughout · Script: `Shreyas_Ionic_AMC/04_RND_LAB/BROAD_RESEARCH_2036/h1_gex_cheaptest.py`
· Full console log: `Shreyas_Ionic_AMC/04_RND_LAB/BROAD_RESEARCH_2036/h1_gex_cheaptest_log.txt`

## 0. What this is testing
**[DATA]** Not a standalone signal — a proposed REGIME GATE on the short-vol sleeves (S-01..S-04).
Theory: dealers net long gamma → hedging dampens moves (mean-reversion, calmer realized range,
good for short-vol); dealers net short gamma → hedging amplifies moves (higher realized range,
bad for short-vol). Indian dealer positioning sign was explicitly **unverified** at intake — the
one-pager pre-registered two candidate sign conventions and designed the cheap-test to let the
data reveal which (if either) is correct, before any IV-solve/engineering spend.

## 1. Blocker resolution (confirmed this session)
**[DATA]** The one-pager's stated blocker — "no spot/underlying price column" — is false as of
today. `datasets/index_daily/nifty50.parquet` (2,581 rows, 2016-01-04→2026-07-03) joins cleanly
to the OI surface's 402 snapshot dates: **400/402 matched** (the 2 misses are Jan-1 non-trading
days that shouldn't be in the OI surface — flagged to Data Officer separately, not fixed here).

**[DATA] Self-caught bug, worth recording:** my first join attempt used
`pd.to_datetime(timestamp).dt.tz_convert(None)` on the nifty50.parquet IST-local
`00:00:00+05:30` stamps. Verified empirically that this is the **exact L1 timezone landmine**
from firm CLAUDE.md — `tz_convert(None)` treats the stamp as needing UTC conversion and
silently shifts every date back one day (`2016-01-04T00:00:00+05:30` → `2016-01-03 18:30`),
which dropped the match rate to 307/402 and would have quietly reshuffled which OI snapshot
maps to which spot day. Fixed with `.dt.tz_localize(None)` (strip the tz label, keep the IST
wall date) — re-ran, got the expected 400/402. Flagging because this is a second, subtly
different flavor of the same landmine family (L1 is documented for *HF 1-min* bars; this hit a
*daily* file with local-midnight stamps) — worth a note to the Data Officer to broaden the L1
guard's applicability language beyond "HF timestamps."

## 2. Method (exactly per one-pager, no new criteria invented)
1. NIFTY OI surface (377,034 rows, 402 dates) joined to spot (400 dates usable).
2. Dropped `dte==0` (gamma ill-defined at T→0), `oi<=0`, `close<=0` rows → 252,171 rows.
3. IV back-solved per strike/expiry/date via vectorized Newton-Raphson + bisection fallback
   (European BS, flat r=6.5%). **[DATA]** Solved for 206,202/252,171 rows (81.8%); firm
   IV<100% sanity cap (2026-07 INFY-blowup lesson) dropped a further 3,003 rows → 203,199
   usable option-legs.
4. BS gamma per leg → net GEX per `trade_date` under **both** pre-registered conventions:
   - **Convention A (US-standard):** `GEX_A = (Σ call_OI·Γ − Σ put_OI·Γ) × S²`
   - **Convention B (India-both-short):** `GEX_B = −(Σ call_OI·Γ + Σ put_OI·Γ) × S²` (always
     negative by construction — tests whether *magnitude* of assumed short-gamma still ranks
     realized range correctly, since India retail is a heavy net option-seller base)
   - Contract multiplier and the standard ×0.01 GEX scaling constant **omitted** (documented
     simplification — both are per-date-constant positive scalars that cannot change sign or
     within/cross-date rank order, which is all a sign/quintile test needs; flagged since lot
     size changed multiple times 2021-2026 and would need real handling for a live $-GEX dashboard).
5. Quintile-bucketed the 400 dates by GEX per convention (descriptive full-sample quantiles —
   this is characterization, not a live PIT gate; the one-pager's own kill criterion #4 blocks
   any live-gate build regardless of this result, given the 31%-coverage sparse cadence).
6. Compared next-trading-day NIFTY realized range `(high−low)/prev_close` across quintiles
   (Mann-Whitney extreme-quintile spread + 2,000-draw bootstrap CI).
7. Joined S-04 short-strangle per-trade `strangle_managed` P&L (5,031 trades, 209 stocks,
   `FINAL_STRATEGY_FORWARD_CHECK/04_Short_Strangle/strangle_trades.csv`) via `merge_asof`
   **backward** on entry date (PIT-safe: only the most recent GEX snapshot at/before entry is
   used) — 100% of trades matched.
8. Placebo: shuffled the GEX-quintile labels across dates 2,000 times, rebuilt the null
   distribution of the extreme-quintile spread.

## 3. Results

### 3a. Next-day realized range by GEX quintile (q0 = most-negative-GEX / deep short-gamma)
| Convention | q0 mean range | q4 mean range | spread (q0−q4) | Mann-Whitney p | Bootstrap 95% CI | Placebo shuffle p |
|---|---|---|---|---|---|---|
| A (US-standard) | 1.022% | 0.884% | **+0.138%** (correct sign) | 0.135 (n.s.) | [−0.0001%, +0.282%] | 0.035 |
| B (India-both-short) | 0.843% | 1.241% | **−0.398%** (WRONG sign) | <0.0001 | [−0.544%, −0.242%] | 0.000 |

**[DATA]** Convention A points the theoretically-correct direction (short-gamma → higher range)
but is statistically fragile: Mann-Whitney says not significant, the bootstrap CI barely misses
zero, and it clears the placebo shuffle only at the 0.035 one-sided level — borderline, not clean.
Convention B is the mirror image: a strong, monotonic-ish, highly significant effect that runs
**backwards** from the theory (its "deepest short-gamma" bucket shows the *calmest* next-day
market, not the most volatile).

### 3b. S-04 short-strangle P&L (`strangle_managed`) by the same GEX buckets at trade entry
| Convention | q0 mean P&L | q4 mean P&L | diff (q0−q4) | Mann-Whitney p |
|---|---|---|---|---|
| A | +0.409% | +0.224% | **+0.185%** (WRONG sign) | <0.0001 |
| B | +0.259% | +0.309% | −0.050% (correct sign, trivial size) | <0.0001 |

**[DATA]** Under Convention A — the convention whose range-direction matched theory — the
strangle result flips: the "deep short-gamma" bucket shows the **best** P&L, not the worst.
Under Convention B — whose range-direction was backwards — the strangle P&L direction matches
theory but the economic size is negligible (0.05%, likely just riding the large-n significance
of 2,370 trades rather than a real edge).

### 3c. Placebo
Convention A's observed range spread (+0.138%) sits at the 96.5th percentile of the shuffled
null (p=0.035) — a real but marginal departure from noise. Convention B's spread (−0.398%) is
far outside its null (p<0.0005) — a real, non-noise pattern, just signed the wrong way.

## 4. Kill-criteria evaluation (verbatim from the one-pager, no new criteria added)
- **#1 "Neither sign convention produces the theoretically-expected monotonic relationship →
  KILL":** **Triggered.** Convention A is directionally right but not monotonic (q1 > q0) and
  statistically marginal. Convention B is monotonic-ish and strongly significant but runs
  opposite the theory. No convention delivers a clean theory-consistent range result — this is
  precisely the "can't even identify the correct sign" scenario the one-pager warned would make
  further engineering spend a coin-flip bet.
- **#2 "Correct sign identifiable but CI overlaps zero → KILL or HOLD pending denser data":**
  Also applicable to Convention A on its own (CI = [−0.0001%, +0.282%], essentially touching
  zero) — independently supports not proceeding on sample-size grounds alone even before #1.
- **#3 "Real range effect but S-04 P&L doesn't differ by bucket → KILL as a gate for S-04
  specifically":** **Triggered, in the sharper form of an internal contradiction.** Whichever
  convention is provisionally treated as "the real one," its own strangle-P&L cross-check
  contradicts either the theory's sign (Convention A) or is economically trivial (Convention B).
  A genuine dealer-hedging mechanism should move realized range and short-vol P&L in the *same*
  coherent direction under the *same* sign convention — it does not, on this data.
- **#4 (sparse-cadence gate):** Moot given #1/#3, but independently true regardless — 400/1,300
  trading days (~31% coverage), 3-16 day gaps between snapshots, cannot support a live daily gate.
- **#5 (linear-baseline-before-ML rule):** N/A — the baseline itself fails, so no ML variant
  (HMM regime-switch, etc.) is warranted on this family.

## 5. Verdict
**KILL** — H1 dealer-gamma/GEX regime gate, as specified, fails its own pre-registered kill
criterion #1 (neither candidate sign convention produces a coherent, theory-consistent
relationship between GEX and next-day realized range), reinforced by criterion #3 (the S-04
strangle P&L cross-check contradicts whichever convention's range result you'd provisionally
accept). This is **not** a low-t/small-n dismissal — per firm SOP I checked explicitly whether
this was "wrong-sign-under-both-conventions or genuinely-flat" before killing, since low-t alone
must never kill a sound-logic idea. It clears that bar: Convention B is a strong, non-noise,
significant, *wrong-signed* result (not just weak); Convention A's own significant result
(the strangle P&L) is *also* wrong-signed. The one internally-coherent-looking leg (Convention
A's range direction) is itself statistically marginal (placebo p=0.035, bootstrap CI grazing
zero) and does not survive contact with the strangle-P&L cross-check. Two independent outcome
variables under two pre-registered conventions produce four data points, and none of the four
combinations (A-range, A-P&L, B-range, B-P&L) delivers a theory-consistent, robust, and
mutually-coherent pair.

**[INFERENCE]** My reading, as structurer: the mechanical SpotGamma/SqueezeMetrics story is a
US-market-structure artifact (options-dealer intermediation of a broad, well-hedged
institutional options book). NIFTY's options market is dominated by retail/prop option
*writers*, thin index-option OI concentration relative to notional, and — per the one-pager's
own caveat — only 31%-coverage OI snapshots that can't resolve intraweek positioning builds.
The mechanism may exist in India in some form, but this cheap-test cannot detect it cleanly with
current data, and the signal we *can* extract is internally inconsistent enough to indicate
noise/data-limitation rather than a real, tradeable structural effect.

**Recommendation to Data Officer (Kavya Reddy):** if a denser (ideally daily) NIFTY OI-by-strike
source becomes available later, H1 is worth one more clean look — this kill is conditioned on
the current 31%-coverage snapshot cadence, and criterion #4 already flagged that a live gate
needs denser data regardless of this cheap-test's sign-direction outcome. Do not resurrect on
weak-signal grounds alone (Convention A's marginal placebo pass); resurrect only if OI cadence
improves enough to re-run this exact test with a denser, less noisy GEX series.

**No change to any live/paper sleeve.** S-01..S-04 sizing remains ungated by GEX.

## 6. Files
- Hypothesis one-pager: `Shreyas_Ionic_AMC/04_RND_LAB/ideas/20260703_dealer_gamma_gex.md`
- This cheap-test script: `Shreyas_Ionic_AMC/04_RND_LAB/BROAD_RESEARCH_2036/h1_gex_cheaptest.py`
- Full run log: `Shreyas_Ionic_AMC/04_RND_LAB/BROAD_RESEARCH_2036/h1_gex_cheaptest_log.txt`
- Inputs: `datasets/derived/nifty_oi_surface.parquet`, `datasets/index_daily/nifty50.parquet`,
  `FINAL_STRATEGY_FORWARD_CHECK/04_Short_Strangle/strangle_trades.csv`
- Prior assessment that unblocked this test: `Shreyas_Ionic_AMC/04_RND_LAB/BROAD_RESEARCH_2036/ALPHA_RESEARCH_ASSESSMENT.md`
