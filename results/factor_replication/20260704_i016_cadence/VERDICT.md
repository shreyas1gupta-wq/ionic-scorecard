# I-016 CADENCE TEST — VERDICT
**Devika Menon (E-016), 2026-07-04. Equities & Momentum book.**
Idea file: `Shreyas_Ionic_AMC/04_RND_LAB/ideas/20260704_n500_lowvol50_sleeve.md` (pre-registered kills).
Run dir: `results/factor_replication/20260704_i016_cadence/`. Engine + panels reused UNCHANGED from
Arjun's D-029 factor family (`20260704_factor_family`); NEW stale-mask layer applied.

## HEADLINE VERDICT (per variant)
| Variant | VERDICT |
|---|---|
| **N500 LowVol 50 — QUARTERLY** | **KILL** (misses pre-registered (b) p75-frictionless leg only) — resurrect on p75-bar re-spec |
| **N500 MQ 50 — SEMIANNUAL** | **KILL** (misses (a), (b), (c) — semiannual cadence starves the momentum edge) |

Both go to KILLED_IDEAS per the pre-registered rule ("ANY miss -> KILLED"). I am NOT overriding my own
pre-registration after seeing the data — that is goalpost-moving, the exact sin the firm guards. BUT the
LowVol quarterly kill is a *knife-edge, bar-artifact* kill (see §p75 caveat), whereas the MQ semiannual
kill is a *clean, structural* kill. They are not the same kind of dead. Resurrection conditions differ.

---

## THE NUMBERS (full period 2005-04 -> 2026-01, RETURN panel, stale-mask applied)
| Variant | Frictionless | 1x cost | 2x cost | maxDD (2x) | Ann. turnover |
|---|---|---|---|---|---|
| LowVol50 monthly (restated, masked) | 16.81% | 15.32% | 13.84% | -45.2% | 172.6% |
| **LowVol50 QUARTERLY** | **17.46%** | **16.54%** | **15.62%** | **-44.2%** | **109.6%** |
| MQ50 monthly (restated, masked) | 18.94% | 15.42% | 12.00% | -69.3% | 419.5% |
| **MQ50 SEMIANNUAL** | **12.34%** | **11.22%** | **10.10%** | **-74.6%** | **139.3%** |

**Turnover comparison (the whole point of the cadence test):**
- LowVol50: monthly **172.6% -> quarterly 109.6%** (-37% turnover). Quarterly is BETTER on every axis:
  higher fric/1x/2x CAGR AND lower turnover AND slightly shallower drawdown. Cadence change is a pure win.
- MQ50: monthly **419.5% -> semiannual 139.3%** (-67% turnover) — but semiannual **destroys the return**
  (fric 18.94% -> 12.34%). Momentum decays fast; holding 6 months lets winners round-trip. Turnover fell
  but so did the edge, and faster. Cadence change is a net loss.

## STALE-MASK RESTATEMENT (mandatory apples-to-apples layer)
The 212-symbol frozen-price mask (D-029) maps to 190 syms / 0.314% of cells on my price grid (the rest are
frozen dates/symbols outside the panel). Restating the family's MONTHLY numbers WITH the mask:
- LowVol50 monthly: **15.32% / 13.84%** (masked) vs family **15.3% / 13.8%** (unmasked) — IMMATERIAL.
- MQ50 monthly: **15.42% / 12.00%** (masked) vs family **15.4% / 12.0%** (unmasked) — IMMATERIAL.
**No material change. The family's headline numbers were NOT contaminated by frozen prices.** The mask
matters most for LowVol (a frozen run has ~0 measured vol -> inverse-vol would over-weight fake-stable
names); I vetoed any name frozen today or frozen >=40% of the trailing 252d window from the pool, and
zeroed frozen-cell returns in P&L. It moved the headline <0.05pp — worth doing for correctness, not a
result-changer here.

---

## PER-CRITERION PASS/FAIL (pre-registered kills)
Bars: N500 TR hurdle = random-N500-50 NET mean **12.74%** (the D-029 firm floor); p75 discussed below.

| Criterion | LowVol50 QUARTERLY | MQ50 SEMIANNUAL |
|---|---|---|
| **(a)** 2x-cost clears N500 TR hurdle (12.74%) by >=+0.5pp/yr | **PASS** +2.88pp (15.62% vs 12.74%) | **FAIL** -2.64pp (10.10% vs 12.74%) |
| **(b1)** beat random-N500-50 MEAN (12.74%) at 1x | **PASS** 16.54% > 12.74% (+3.8pp) | **FAIL** 11.22% < 12.74% |
| **(b2)** beat random-N500-50 p75 at FRICTIONLESS | **FAIL** 17.46% < 19.92% net-p75 / <23.2% fric-p75-est | **FAIL** 12.34% << both |
| **(b)** overall (b1 AND b2) | **FAIL** (b1 pass, b2 fail) | **FAIL** |
| **(c)** no post-2020 sign flip vs hurdle | **PASS** full +2.88pp, post-2020 +3.51pp (same sign, positive) | **FAIL** full -2.64pp (already below hurdle) |
| **(d)** maxDD <= -50% floor | **PASS** -44.2% | **FAIL** -74.6% |

## THE p75 CAVEAT — read before actioning the LowVol kill
Criterion (b2) as pre-registered says "beat the p75 at frictionless." Two honest problems with that bar,
flagged LOUDLY (not used to reverse the verdict — flagged for the resurrection condition):

1. **No frictionless p75 exists on disk.** Ishaan's benchmark shipped only 8 NAV parquets; the percentile
   paths (`nav_p05..p95`) are NET (cost-loaded) per README §NAV construction, and the intermediate
   gross/qreturns matrices were cleaned from the workdir. On-disk net-p75 CAGR = **19.92%**. I estimated
   frictionless-p75 = net-p75 + N500-50 mean cost drag (3.31pp) = **~23.2%** — an APPROXIMATION.
2. **The p75 path is path-of-percentiles, not percentile-of-paths** (README §NAV construction, explicit).
   It chains the 75th-best QUARTER every quarter — a fictional always-upper-quartile path no single random
   basket ever walked. As a *skill hurdle* this overstates the bar: a single deterministic strategy is ONE
   path and structurally cannot sit at the 75th percentile every quarter. The README itself names the
   **MEAN as the floor** and **p95 as the genuine-skill bar**; p75 is a self-imposed intermediate that,
   as constructed, is inflated.

LowVol50 quarterly frictionless (17.46%) clears the net **mean** (13.06%) and net **median** (11.80%) paths
comfortably; it clears the firm-mandated D-029 floor (12.74% mean, at 1x with +3.8pp room). It misses only
the chained-p75 construct. **On the firm's actual mandated bar it is a clear pass and a real diversifier.**

I am honoring the pre-registration (miss -> kill) rather than reversing it post-hoc. The correct fix is
NOT for me to wave it through; it is to have Ishaan produce a proper frictionless per-path p75 (percentile
of terminal-path CAGRs, not chained-quarter percentiles) and re-judge — registered as the resurrection
condition below.

## DIVERSIFIER NOTE (my book's mandate)
This sleeve is long-only equity low-vol — the firm's ONLY non-short-vol exposure sits in my book. LowVol50
quarterly at 15.62% net-2x, vol ~12-13%, maxDD -44% is a legitimate diversifier candidate on correlation
grounds, independent of whether it clears an inflated p75 dart-throw bar. Per IC-1 read-across I argue this
with numbers, not rhetoric: the case is the +3.8pp-over-mean selection margin at 1x AND the orthogonality
to the four short-vol sleeves — NOT the headline CAGR. That case survives this kill and is the substance of
the resurrection.

## D-028 SELF-AUDIT — PASS
- **T3 same-bar:** first NAV ~1.0, first move on day AFTER first rebalance (weights applied T+1). CLEAN.
- **T5 PIT membership:** 42 N500 snapshots, `members_asof` (most-recent on/before rb), never a static list.
- Selection = exactly 50 names/rebalance. Costs = COST_STANDARDS approved + execution_realism vol-mult,
  identical stack to the family; 2x stress computed.
- Stale-mask applied as selection veto + P&L-cell zero. **Residual limitation (stated):** a name held
  through a run that unfreezes mid-hold could still book the unfreeze jump on the first non-frozen day
  (second-order, <0.05pp effect given monthly-restatement immateriality).
- **MQ50 quality coverage median 0.23** — MQ selection is majority momentum-fallback (only 23% of picked
  names carry quality data on this panel). Same panel as the family, so apples-to-apples, but the "quality"
  in MQ50 is thin — a caveat for any future MQ resurrection, not a factor in today's semiannual kill (the
  kill is on return decay + drawdown, not coverage).

## OUTPUTS
- NAV CSVs (frictionless / 1x / 2x): `nav_{A,B,C,D}_*.csv`
- `verdict_table.csv` (machine-readable per-criterion), `turnover_comparison.csv`, `config.json`
- `coverage_*.csv` (per-rebalance n_sel + quality coverage), `run.log`, `run_i016_cadence.py`
