# Curated combo strategies — Set A (combos 1-5) — 2026-07-07
Agent's own REPORT.md write was blocked by subagent policy; content below is verbatim from the agent's final report. Process note from the agent: an earlier background run was a mistake (hit the leaf-agent stall pattern); all 5 combos were re-run fully synchronously in the foreground and every number below is from that completed run.

## Results (2021-05 to 2026-06, 261 weekly expiries)

Causal indicators throughout; 1-bar execution lag on the option; real 1-minute option marks used through the entire hold (so theta reflects the actual observed premium path, not just entry/exit marks); no-fill on zero-volume bars = DROP; costs per approved COST_STANDARDS. Edge is denominator-free (points and %-of-spot, never %-of-premium). Single position at a time. "VWAP" uses an anchored typical-price proxy since the index has zero volume data. "ATM+/-1" means one strike out-of-the-money. Weekly expiry = Thursday.

| # | Spec | N | win% | PF | pts/tr net | %spot GROSS | %spot NET | Sharpe | maxDD %spot | net %spot @2x |
|---|------|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 1 | 5m / 0DTE / ATM / VWAP trend / ORB entry / EOD exit | 257 | 33.5 | 0.84 | -4.89 | -0.0142 | -0.0190 | -0.38 | -9.49 | -0.0237 |
| 2 | 15m / weekly / ATM+/-1 / EMA20 trend / 20-bar breakout / ATR-stop / VIX-band filter / vol-scale sizing | 199 | 25.1 | 1.20 | +7.35 | +0.0334 | **+0.0267** | +0.30 | -7.09 | **+0.0201** |
| 3 | 10m / 1DTE / ATM / Supertrend / pullback entry / trailing-ATR exit / RV-calm filter / Kelly sizing | 115 | 34.8 | 0.87 | -0.79 | -0.0001 | -0.0057 | -0.34 | -1.64 | -0.0114 |
| 4 | 5m / weekly / ATM / ADX / Bollinger-squeeze breakout / 30pct-target-50pct-stop / gap filter | 253 | 58.5 | 1.03 | +0.71 | +0.0103 | +0.0035 | +0.06 | -6.20 | -0.0034 |
| 5 | 15m / 0DTE / ATM+/-1 / VWAP / 20-bar breakout / EOD exit / VIX-band filter / vol-scale sizing | 224 | 24.6 | 0.90 | -1.82 | -0.0041 | -0.0081 | -0.23 | -4.57 | -0.0121 |

## Per-combo verdicts

**Combo 2 is the only net-positive result and the only one surviving the 2x cost stress** (+0.020%/trade net). But its entire edge is concentrated in one regime: excluding 2024 data, the combo is -0.56% of spot (N=146) versus +5.32% all-in — meaning essentially the entire positive result comes from a single year.

- **Combo 1: FAKE** — negative even at the gross level, a straightforward theta donation.
- **Combo 2: FRAGILE** — single-regime, tail-dependent, as described above.
- **Combo 3: FAKE** — gross edge is approximately 0.000%, a cost-eroded coin flip with no underlying signal.
- **Combo 4: FRAGILE, trending toward FAIL** — roughly breakeven gross, negative at 2x cost. Its apparently attractive 58.5% win rate is a mechanical artifact of the 30%-target/50%-stop cap structure: capping the profit target kills exactly the fat right tail that an options-buying strategy needs to overcome its frequent small losses.
- **Combo 5: FAKE** — negative at both gross and net levels.

Every combo tripped only the generic "P&L rides on top-5 trades" degenerate flag; none showed Sharpe>4, an artificially smooth equity curve, or any leak flag — these are honest, unglamorous results, not suspiciously good ones. No combo breached the Sharpe < -2 standing-rule threshold, so reversed versions were not required (the results are near-zero-edge, not wrong-signed).

## Standing reminder from the agent
This was a hand-picked 5-combo sample from a menu spanning more than 10,000 possible cells — not an exhaustive or random search. Nothing here constitutes a finding. Even combo 2 is only a hypothesis worth a dedicated, pre-registered follow-up (walk-forward validation on a 3-year/1-year split, DSR above 0.95 computed on an honest trial count, PBO below 25%, and an untouched 2024 holdout given that's where all its apparent edge currently lives). Quoting "the best of 5 curated cells" as if it were a discovered edge would itself be exactly the kind of p-hacking this whole exercise exists to guard against.

## Files
`Shreyas_Ionic_AMC/04_RND_LAB/results/CURATED_COMBOS_20260707/SET_A/` contains per-trade `C1_trades.csv` through `C5_trades.csv` (entry/exit timestamps, strike, premiums, cost points, net points) and `stats_C1.json` through `stats_C5.json`.
