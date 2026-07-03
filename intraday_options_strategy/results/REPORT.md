# STRATEGY REPORT — consensus params StrategyParams(sl_pct=0.2, target_pct=0.55, ema_fast=3, ema_slow=34, orb_minutes=10, max_trades_per_day=10)

```
Round-trip cost example: premium Rs.150, 1 lot(s) x 75
  brokerage      : Rs.   40.00
  STT (sell)     : Rs.    7.02
  NSE txn        : Rs.   11.92
  GST            : Rs.    9.35
  SEBI           : Rs.    0.02
  slippage (2x0.15%): Rs.   33.75
  TOTAL          : Rs.  102.06 (0.907% of premium value)
```


```
═══ IS ═══
Net P&L          : Rs.      -279,409  (-2.8%)
CAGR net / gross : -0.36% / -0.17%
Max DD           : 3.63% (Rs.365,985), 1886 days
VaR 95/99 (daily): Rs.1,563 / Rs.18,821
Ann vol          : 0.76%
Sharpe/Sortino/Calmar: -9.00 / -4.53 / -0.10
Trades           : 1118 (4.4/day avg, med 4, max 10)
Win rate         : 39.7%   PF: 0.85   R:R: 1.29
Avg win/loss     : Rs.3,519 / Rs.2,733   hold 156 min
Best/worst day   : Rs.66,632 / Rs.-48,684   days +ve: 5%
Costs            : Rs.147,097 (explicit Rs.89,046 + slip Rs.58,051; avg Rs.132/trade)
Avg |delta|      : 0.50   avg theta/day: Rs.-8.8 (per unit)
```


### IS attribution by signal

| signal   |   trades |   win_rate |   net_pnl |    avg_pnl |   avg_hold_min |
|:---------|---------:|-----------:|----------:|-----------:|---------------:|
| A2       |      137 |   0.437956 |  121099   |   883.931  |        191.46  |
| A3       |       28 |   0.357143 |   28251.7 |  1008.99   |        166.321 |
| B2       |      256 |   0.398438 |  -18021.8 |   -70.3975 |        150.09  |
| A1       |      446 |   0.408072 | -143390   |  -321.503  |        158.746 |
| B1       |      251 |   0.358566 | -267348   | -1065.13   |        136.1   |


```
═══ OOS ═══
Net P&L          : Rs.       321,380  (+3.2%)
CAGR net / gross : +0.95% / +1.38%
Max DD           : 2.04% (Rs.214,865), 694 days
VaR 95/99 (daily): Rs.14,186 / Rs.25,859
Ann vol          : 1.49%
Sharpe/Sortino/Calmar: -3.72 / -4.21 / 0.47
Trades           : 686 (2.8/day avg, med 2, max 10)
Win rate         : 40.7%   PF: 1.14   R:R: 1.66
Avg win/loss     : Rs.9,426 / Rs.5,672   hold 139 min
Best/worst day   : Rs.56,483 / Rs.-36,732   days +ve: 14%
Costs            : Rs.144,911 (explicit Rs.75,776 + slip Rs.69,135; avg Rs.211/trade)
Avg |delta|      : 0.50   avg theta/day: Rs.-14.8 (per unit)
```


### OOS attribution by signal

| signal   |   trades |   win_rate |   net_pnl |    avg_pnl |   avg_hold_min |
|:---------|---------:|-----------:|----------:|-----------:|---------------:|
| A1       |      350 |   0.408571 | 302901    |   865.431  |        138.757 |
| B1       |      118 |   0.457627 |  50588.8  |   428.719  |        123.373 |
| A2       |       71 |   0.394366 |  16329.3  |   229.99   |        161.676 |
| B2       |      131 |   0.381679 |   9737.47 |    74.3318 |        140.824 |
| A3       |       16 |   0.25     | -58176.3  | -3636.02   |        137.062 |


### rob_slippage

|                |   n_trades |   net_pnl |   win_rate |   profit_factor |   sharpe |   max_dd_pct |
|:---------------|-----------:|----------:|-----------:|----------------:|---------:|-------------:|
| slippage 0.15% |        686 |    321380 |     0.4067 |          1.1392 |  -3.7249 |       0.0204 |
| slippage 0.25% |        780 |    371842 |     0.4051 |          1.1269 |  -3.1378 |       0.0195 |
| slippage 0.50% |        674 |    198155 |     0.3872 |          1.0954 |  -4.1911 |       0.0248 |
| slippage 1.00% |        527 |   -246756 |     0.3472 |          0.7874 |  -7.8712 |       0.0399 |


### rob_costs

|          |   n_trades |   net_pnl |   win_rate |   profit_factor |   sharpe |   max_dd_pct |
|:---------|-----------:|----------:|-----------:|----------------:|---------:|-------------:|
| costs x1 |        686 |    321380 |     0.4067 |          1.1392 |  -3.7249 |       0.0204 |
| costs x2 |        769 |    390630 |     0.4057 |          1.1263 |  -2.9259 |       0.0215 |
| costs x3 |        666 |    174193 |     0.3814 |          1.0833 |  -4.2256 |       0.0272 |


### rob_params

|               |   n_trades |   net_pnl |   win_rate |   profit_factor |   sharpe |   max_dd_pct |   pnl_vs_base |
|:--------------|-----------:|----------:|-----------:|----------------:|---------:|-------------:|--------------:|
| base          |        686 |    321380 |     0.4067 |          1.1392 |  -3.7249 |       0.0204 |        0      |
| sl90% tg90%   |        724 |    120110 |     0.3743 |          1.0539 |  -4.6391 |       0.0276 |       -0.6263 |
| sl90% tg110%  |        702 |    356655 |     0.3718 |          1.1619 |  -3.6101 |       0.0185 |        0.1098 |
| sl110% tg90%  |        966 |    613461 |     0.411  |          1.1476 |  -2.2691 |       0.0196 |        0.9088 |
| sl110% tg110% |        643 |    222305 |     0.4044 |          1.1084 |  -4.0246 |       0.0218 |       -0.3083 |


### rob_vix_regime

|           |   n_trades |   net_pnl |   win_rate |   profit_factor |   sharpe |   max_dd_pct |
|:----------|-----------:|----------:|-----------:|----------------:|---------:|-------------:|
| VIX>18.0  |         52 |   22339.3 |     0.4231 |          1.2876 | -12.6888 |       0.0008 |
| VIX<=18.0 |        634 |  299041   |     0.4054 |          1.1341 |  -3.5454 |       0.0206 |


### rob_mc_removal

```
{
  "full_net_pnl": 321379.97162797995,
  "mc_median": 289430.85576838144,
  "mc_p5": 130027.85005810353,
  "mc_p95": 416970.52529623307
}
```
