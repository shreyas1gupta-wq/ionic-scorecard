# W5 Validation -- Dr. Sameer Bhat (E-027), 2026-07-17

## 0. Base-7 sanity check (MANDATORY precondition)

Official registered IC_IR (CANONICAL_7LEG_1Y.json): **1.345029** (ic_mean=0.188998, n_obs=86838, n_ic_dates=145).

Rebuilt base-7 using the OFFICIAL legs (mom_resid_plain, freshly built): ic_ir=1.345029, ic_mean=0.188998, n_obs=86838, n_ic_dates=145. **Sanity check: PASS**.

For contrast, the base-7 actually used by rnd/wave4/run_w5_convex.py ('base7_reconstructed' in hypotheses_w5.json, ic_ir=1.337357) substituted the leg 'mom_resid_peer' (capstone_legs.parquet cache) for the official 'mom_resid_plain' -- a leg that doesn't even exist in that cache. This is a SILENT construction bug: every incremental-8-leg number in the W5 batch used the WRONG base-7.

## 1. W5-01 cost-elasticity: incremental IR after sanity-checked rebuild

Originally reported (buggy base): delta_ic_ir = +0.3959 ('+0.396 incremental IR as 8th leg').

Recomputed against the CORRECTED, sanity-checked base-7 (restricted to W5-01's 142 candidate dates): base7_ic_ir=1.7316, with8_ic_ir=1.6630, **delta_ic_ir = -0.0686**.

Drop-one-year (21 years tested, 12 distinct delta values -- confirms the drop-one loop is actually varying, not a no-op): worst year {'key': 'year_2024', 'delta_ic_ir': -0.0834321327151415}. n_years with delta<=0: 21. **survives_drop_one = False**.

Era split (halves): {'first_half': {'base7_ic_ir': 2.7891485328110592, 'with8_ic_ir': 2.7946605924052723, 'delta_ic_ir': 0.005512059594213081, 'n_ic_dates': 71}, 'second_half': {'base7_ic_ir': 1.2288071557416502, 'with8_ic_ir': 1.1614402200081175, 'delta_ic_ir': -0.0673669357335327, 'n_ic_dates': 58}}. **survives_era_split = False**.

## 2. W5-02 implied-borrow-cost: convex-hedge validation (hedge-axis, not IC)

Per-episode monthly LS values: {
  "GFC_2008-09": {},
  "COVID_2020-02_03": {
    "2020-01-31": 0.07586816009556399,
    "2020-02-28": 0.09920502752678534,
    "2020-03-31": -0.04431174238152463
  },
  "SELLOFF_2022": {
    "2021-12-31": -0.003436610400397646,
    "2022-01-31": -0.011132693199798899,
    "2022-02-28": 0.01930274747259801,
    "2022-03-31": 0.0012716042652572224,
    "2022-04-29": 0.02904231256029538,
    "2022-05-31": -0.0034326618382694504,
    "2022-06-30": -0.014960949274982108
  }
}

Drop-one-crash-episode: {
  "only_COVID_2020": {
    "n": 3,
    "mean": 0.04358714841360823,
    "min": -0.04431174238152463,
    "all_positive": false
  },
  "only_SELLOFF_2022": {
    "n": 7,
    "mean": 0.00237910708352893,
    "min": -0.014960949274982108,
    "all_positive": false
  },
  "GFC_2008-09": {
    "n": 0,
    "note": "NO DATA -- panel/factor has 0 dates in this window (checked directly), cannot assess 2008 crisis at all"
  }
}

both_episodes_positive_mean = True; one_episode_carries_all_magnitude = True.

Unconditional era-split IC (own factor, not incremental): first_half=0.0497, second_half=-0.0444.

For completeness, the corrected incremental-IR test for W5-02 (this hypothesis is a HEDGE candidate, not an IC play, so this is secondary): delta_ic_ir_full=-0.0881, survives_drop_one=False, survives_era_split=False.

