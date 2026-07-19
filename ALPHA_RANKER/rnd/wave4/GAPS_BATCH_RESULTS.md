# W4G -- coverage-map GAP-UNTESTED cheap-test batch results

Aditya Verma (R&D), 2026-07-17. Four distinct-mechanism candidates from `coverage_map.json`'s GAP-UNTESTED list, each tested ONCE through the shared harness (`rnd/lib/harness.py`). Frozen 7-leg model read-only, never edited.

Fresh 7-leg baseline (recomputed this run, min_legs=5-of-7, corp-action-guarded): 1Y IC_IR=1.3450 (n_dates=145); 5Y IC_IR=1.8993 (n_dates=96).

**Addendum 2026-07-17 14:1x (Aditya Verma):** the batch above (all 4 candidates: hurst,
ts_abs_mom, reinvestment_runway, moat_margin_stability) had in fact already run to
completion (`run_w4g_gaps.log` timestamp 14:04:57, "DONE") by the time this follow-up
task was dispatched -- the "background-exited after Hurst+TS-momentum" premise was
stale. Verified against `wave4/run_w4g_gaps.log` + all 8 `cards/W4G_*` JSONs before
reporting. One gap remained: the reinvestment_runway/moat spec asked specifically for
corr-vs-QMJ (orthogonality to the quality leg), which the batch run only checked vs
the composite + `mom_resid_peer`, not vs `quality_QMJ` itself. Ran that one check
synchronously in foreground (`wave4/run_w4g_moat_qmj_check.py`, rebuild of the moat
factor + one per-date Spearman vs the `quality_QMJ` leg from `panel/capstone_legs.parquet`,
no re-run of the harness) -- see the appended line under moat_margin_stability below.
Skew (payoff convexity, both from the harness's DSR block, already computed in the
batch): reinvestment_runway skew=-1.061 (concave/left-tailed), moat_margin_stability
skew=-1.170 (concave/left-tailed) -- both negatively skewed, i.e. any residual edge
would carry crash-risk tails, not convex payoff; consistent with both being killed.

## hurst

- horizon/basis: 1Y/resid
- n_obs=116916, n_dates=212, panel_source=real_panel_long
- IC_mean=0.030625512324558898, IC_IR=0.2959484702852079, NW_t=1.7567743617089453
- decile monotonicity=0.7696969696969697
- lag_test_delta=0.167449042437963 (gate <=0.25); placebo_IC=-0.0020667805391267864 (gate <=0.02 abs)
- DSR=0.0, PBO=0.9783549783549783 (advisory only, low-t rule)
- harness verdict: **KILL (PBO 0.978 > 0.5; DSR 0.000 <= 0.0)**
- corr vs canonical_7leg composite score: {'mean_corr': 0.08588145979492276, 'n_dates': 154}
- corr vs mom_resid_peer leg: {'mean_corr': 0.13852010140448132, 'n_dates': 225}
- incremental 8-leg: baseline_ic_ir=1.3450288630259197, 8leg_ic_ir=1.363484723514511, delta=0.01845586048859138 -> **redundant (no material delta)**

## ts_abs_mom

- horizon/basis: 1Y/raw
- n_obs=127072, n_dates=223, panel_source=real_panel_long
- IC_mean=0.07632147760018786, IC_IR=0.439094061485063, NW_t=2.5146796427739524
- decile monotonicity=0.9757575757575757
- lag_test_delta=0.13688361076861374 (gate <=0.25); placebo_IC=0.002320968874228767 (gate <=0.02 abs)
- DSR=2.8700862212926567e-211, PBO=1.0 (advisory only, low-t rule)
- harness verdict: **KILL (PBO 1.000 > 0.5)**
- corr vs canonical_7leg composite score: {'mean_corr': 0.5324396410440215, 'n_dates': 158}
- corr vs mom_resid_peer leg: {'mean_corr': 0.7668760494275039, 'n_dates': 234}
- incremental 8-leg: baseline_ic_ir=1.3450288630259197, 8leg_ic_ir=1.22396216599206, delta=-0.12106669703385964 -> **hurts (dilutive)**

## reinvestment_runway

- horizon/basis: 5Y/resid
- n_obs=24142, n_dates=170, panel_source=real_panel_long
- IC_mean=-0.07305785522090151, IC_IR=-0.40745077265026214, NW_t=-0.9658962334774525
- decile monotonicity=-0.8545454545454544
- lag_test_delta=0.09013604663641174 (gate <=0.25); placebo_IC=-0.006777014189438657 (gate <=0.02 abs)
- DSR=0.0, PBO=0.922077922077922 (advisory only, low-t rule)
- harness verdict: **KILL (IC_IR -0.407 < 0.2; PBO 0.922 > 0.5; DSR 0.000 <= 0.0)**
- corr vs canonical_7leg composite score: {'mean_corr': 0.27662969570174617, 'n_dates': 130}
- corr vs mom_resid_peer leg: {'mean_corr': 0.07330684437485373, 'n_dates': 130}
- incremental 8-leg: baseline_ic_ir=1.8992826899247137, 8leg_ic_ir=1.4944916787486284, delta=-0.4047910111760853 -> **hurts (dilutive)**

## moat_margin_stability

- horizon/basis: 5Y/resid
- n_obs=40645, n_dates=150, panel_source=real_panel_long
- IC_mean=0.014588222907332587, IC_IR=0.19059575239967366, NW_t=0.5967619796323352
- decile monotonicity=-0.8787878787878788
- lag_test_delta=0.05102523576394686 (gate <=0.25); placebo_IC=0.005323801848856221 (gate <=0.02 abs)
- DSR=0.0, PBO=0.8917748917748918 (advisory only, low-t rule)
- harness verdict: **KILL (IC_IR 0.191 < 0.2; PBO 0.892 > 0.5; DSR 0.000 <= 0.0)**
- corr vs canonical_7leg composite score: {'mean_corr': 0.1923564673756761, 'n_dates': 142}
- corr vs mom_resid_peer leg: {'mean_corr': 0.04362730653253309, 'n_dates': 142}
- corr vs QMJ leg (quality_QMJ, orthogonality check): {'mean_corr': 0.3801921057126106, 'n_dates': 142}
- incremental 8-leg: baseline_ic_ir=1.8992826899247137, 8leg_ic_ir=1.705264725458808, delta=-0.1940179644659057 -> **hurts (dilutive)**


## 2026-07-17 -- W5 priority-H convex/forensic candidates (Sanjay Kulkarni task)

Base 7-leg reconstructed (min_legs=5, capstone_legs.parquet cache) for reference: IC_IR=1.3374, mono=0.9999999999999999, gates_pass=True (frozen composite itself is NOT touched -- research only).

| Factor | Signed IC_IR (1Y) | Hard gates (lag<=0.25/|placebo|<=0.02) | Corr vs composite | Nearest leg (corr) | Incr. 8-leg IR delta | Skew (1M LS) | Crash-episode mean (COVID/2022/GFC) | Shape | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| W5_01_cost_elasticity_base | 0.2839 | lag=0.023(P)/placebo=-0.0034(P) | 0.081 | quality_QMJ (0.127) | 0.3959 | -1.15 | COVID -1.9% / 2022 +0.2% / GFC no data | CONCAVE | CANDIDATE |
| W5_01_cost_elasticity_refine | 0.1827 | lag=0.005(P)/placebo=-0.0028(P) | 0.137 | value_EY (0.187) | n/a | -0.12 | COVID +0.4% / 2022 +0.8% / GFC no data | LINEAR/mixed | CANDIDATE |
| W5_02_implied_borrow_cost_base | 0.0722 | lag=0.124(P)/placebo=0.0005(P) | 0.028 | quality_cfo_pat (-0.161) | -0.0987 | +0.01 | COVID +4.4% / 2022 +0.2% / GFC no data | LINEAR/mixed | PARK (weak linear + not convex) |
| W5_04_net_fin_slack_base | 0.3196 | lag=0.012(P)/placebo=-0.0048(P) | 0.156 | quality_cfo_pat (-0.387) | -0.1104 | -1.03 | COVID +0.0% / 2022 -0.3% / GFC no data | CONCAVE | PARK (weak linear + not convex) |
| W5_04x02_interaction_refine | 0.2413 | lag=0.105(P)/placebo=0.0035(P) | n/a | n/a | n/a | n/a | n/a | n/a | ran-conditionally |

Diagnostics: {"n_symbols_before_financials_excl": 2356, "n_symbols_after_financials_excl": 2252, "n_financials_excluded": 104, "n_annual_rows": 23851, "n_annual_rows_w501_base": 8828, "n_annual_rows_w501_refine": 4639, "n_annual_rows_w502": 16843, "n_annual_rows_w504": 23695}
Worst-decile market-month cutoff: -0.0566 (25 months).
