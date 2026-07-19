# UNI-B: Universe Technical + Flow-Micro Engine

Universe file: `data/universe/symbols_750.txt` (751 symbols)

## Coverage

- Scored: 751 / 751
- Missing price file (data still landing): 0
- Load/schema errors: 0
- Short-history (<252 bars, flagged short_history=True): 38

## Sanity check: top 10 by theme_momentum

| symbol     |   theme_momentum |   theme_meanrev |   theme_flow_micro |   n_bars | short_history   |
|:-----------|-----------------:|----------------:|-------------------:|---------:|:----------------|
| HFCL       |             96   |            54.3 |               48.3 |     1238 | False           |
| CUPID      |             95.6 |            61.3 |               90.1 |     1238 | False           |
| CEMPRO     |             95.6 |            35.2 |               53.6 |     1238 | False           |
| CPPLUS     |             95.2 |            42.3 |               53.1 |      236 | True            |
| WELCORP    |             95.1 |            40.8 |               84   |     1238 | False           |
| ATHERENERG |             94.1 |            41.6 |               93.3 |      301 | False           |
| SKYGOLD    |             94   |            54   |               70.8 |      871 | False           |
| ACUTAAS    |             93.2 |            57.5 |               63.1 |     1199 | False           |
| NEOGEN     |             92.9 |            24.6 |               86.8 |     1238 | False           |
| KIRLOSENG  |             92.7 |            85.7 |               61   |     1237 | False           |

## Sanity check: bottom 10 by theme_momentum

| symbol    |   theme_momentum |   theme_meanrev |   theme_flow_micro |   n_bars | short_history   |
|:----------|-----------------:|----------------:|-------------------:|---------:|:----------------|
| KPITTECH  |              4.4 |            50.7 |               28.8 |     1238 | False           |
| VEDL      |              5.1 |            74.9 |                9.4 |     1238 | False           |
| INOXWIND  |              5.3 |            63.9 |               29.2 |     1238 | False           |
| TATAELXSI |              6   |            70.7 |               37.3 |     1238 | False           |
| PATANJALI |              7.2 |            49.6 |               38.1 |     1238 | False           |
| RVNL      |              7.3 |            60.2 |               25.1 |     1238 | False           |
| CRIZAC    |              7.6 |            70.7 |               31.7 |      255 | False           |
| AWFIS     |              7.8 |            77   |               31.6 |      531 | False           |
| JAINREC   |              7.9 |            76.3 |               12   |      195 | True            |
| RPOWER    |              8.3 |            81.8 |               33.6 |     1238 | False           |

Saved scores: `c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\results\universe_technical_scores.parquet`

NOTE: percentiles are RELATIVE ranks among currently-scored universe symbols with enough history for each factor, NOT calibrated probabilities. Re-run as data/prices/ fills to widen coverage.
