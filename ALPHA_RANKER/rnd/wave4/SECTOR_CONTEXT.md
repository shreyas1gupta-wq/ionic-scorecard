# W4SEC -- Sector Context as a Conviction Modulator (not standalone alpha)

Devika Menon (FM Equities), 2026-07-17. Tests whether sector-level trailing
context (momentum, relative valuation vs own history, earnings-growth,
breadth) improves the ALPHA_RANKER 7-leg stock score's conviction/weighting.
Standalone sector rotation is ALREADY KILLED (W2S-11, IDG-I-15) -- this is
NOT re-litigating that; it is the context-modulator question only.

## Data
- [DATA] stock_valuation_pit: (148297, 11), sectors=22, dates=249
- [DATA] cube_close_long: (5131, 976)
- [DATA] panel_long: (148297, 31)
- [DATA] canonical_7leg_pit_scores: (64741, 4)
- [DATA] trailing mom computed: 231312 obs, 237 dates (needs 252d history, so early dates dropped)
- [DATA] sector-month panel: 4960 rows, 20 sectors, 249 dates
- [DATA] sector_context available: 4720 sector-months (of 4960 raw; burn-in + coverage drop the rest)
- [DATA] stock-level merged panel (score+sector+returns): 53155 rows, 199 dates

## Full run log
```
[DATA] stock_valuation_pit: (148297, 11), sectors=22, dates=249
[DATA] cube_close_long: (5131, 976)
[DATA] panel_long: (148297, 31)
[DATA] canonical_7leg_pit_scores: (64741, 4)
[DATA] trailing mom computed: 231312 obs, 237 dates (needs 252d history, so early dates dropped)
[DATA] sector-month panel: 4960 rows, 20 sectors, 249 dates
[DATA] sector_context available: 4720 sector-months (of 4960 raw; burn-in + coverage drop the rest)
[DATA] stock-level merged panel (score+sector+returns): 53155 rows, 199 dates

=== TEST 1: interaction (7-leg IC by sector regime bucket) ===
tailwind sector-months : IC mean=0.1365  n_dates=127
headwind sector-months : IC mean=0.1572  n_dates=130
all (unconditional)    : IC mean=0.1732  n_dates=122
delta (tailwind-headwind) = -0.0207
drop-one-sector jackknife on delta: min=-0.0336 max=-0.0077 all-same-sign=True
  era=first_half: IC tailwind=0.1356 (n=88), IC headwind=0.1462 (n=89), delta=-0.0106
  era=second_half: IC tailwind=0.1385 (n=39), IC headwind=0.1810 (n=41), delta=-0.0426

=== TEST 2: incremental IC/decile/Sharpe of score + w*sector_context ===
w=0.00: IC_mean=0.1735 IC_ir=1.6974 mono=1.000 ann_LS_net=2.3699 PBO=0.931 verdict=KILL (PBO 0.931 > 0.5)
w=0.15: IC_mean=0.1715 IC_ir=1.6087 mono=1.000 ann_LS_net=2.2721 PBO=0.944 verdict=KILL (PBO 0.944 > 0.5)
w=0.30: IC_mean=0.1663 IC_ir=1.5208 mono=0.988 ann_LS_net=2.2691 PBO=0.952 verdict=KILL (PBO 0.952 > 0.5)
w=0.50: IC_mean=0.1581 IC_ir=1.4200 mono=0.964 ann_LS_net=2.0947 PBO=0.965 verdict=KILL (PBO 0.965 > 0.5)
w=1.00: IC_mean=0.1361 IC_ir=1.2305 mono=0.952 ann_LS_net=1.8152 PBO=0.948 verdict=KILL (PBO 0.948 > 0.5)

best incremental w=0.15: IC delta vs w=0 baseline = -0.0020 (DOES NOT IMPROVE)
drop-one-sector jackknife on incremental IC delta @ best_w:
  n_sectors_tested=20, delta range=[-0.0038, -0.0003], all-positive=False, n_negative=20
  worst 3 sectors when dropped (i.e. delta most reduced by their absence): [('Chemicals', -0.0037588056267187087), ('Capital Goods', -0.003545127988665686), ('Consumer Durables', -0.0031845775991024006)]
era-split on incremental IC delta @ best_w:
  first_half: IC base=0.1766 IC blend=0.1711 delta=-0.0056
  second_half: IC base=0.1677 IC blend=0.1722 delta=+0.0045

=== TEST 3: intra-sector vs sector-timing decomposition ===
global (cross-sector) 7-leg score IC   = 0.1735  (w=0 baseline, test 2)
sector-NEUTRAL (intra-sector only) IC  = 0.1378  (delta vs global = -0.0357)
sector-ONLY (pure sector-rotation) IC  = 0.1055  n_dates=141
sector-only ann_LS_net=2.1006 PBO=0.952 verdict=KILL (PBO 0.952 > 0.5)
intra-sector share of global IC = 0.794 (sector positioning contributes materially)
```