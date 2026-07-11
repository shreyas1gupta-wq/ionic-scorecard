# HEDGING ANALYSIS PROGRESS
started 2026-07-08 16:11

[16:11:50] loading data
[16:11:51] regime_info: {"us_cape_q25": 11.75, "us_cape_q75": 21.07, "us_cape_now": 41.77, "us_regime_now": "RICH", "india_pb_q25": 3.37, "india_pb_q75": 4.04, "india_pb_now": 3.19, "india_regime_now": "CHEAP", "india_pe_q25": 21.79, "india_pe_q75": 26.4, "india_pe_now": 21.06, "india_pe_regime_now": "CHEAP"}
[16:11:51] === US: 1866 months 1871-02->2026-07; skew=0.9 val=cape
[16:11:51] US regime stats:
market regime  n_months  mean_ann_ret  median_ann_ret  ann_vol  fwd12m_mean  fwd12m_median  fwd12m_p10  fwd12m_worst  pct_neg_month
    US  CHEAP       466      0.006970        0.031810 0.166453     0.089357       0.107753   -0.132143     -0.389465       0.454936
    US   FAIR       931      0.037734        0.052805 0.131121     0.030094       0.044997   -0.176428     -1.067382       0.433942
    US   RICH       468      0.108401        0.162389 0.126894     0.038884       0.075361   -0.206372     -0.563352       0.324786
    US    ALL      1865      0.047780        0.083334 0.140141     0.047184       0.070511   -0.174111     -1.067382       0.411796
[16:11:53]   done H_put_ATM
[16:11:56]   done H_put_95
[16:11:58]   done H_put_90
[16:12:00]   done H_putspread_95_85
[16:12:02]   done H_putspread_90_80
[16:12:04]   done H_collar_95_105
[16:12:06]   done H_collar_90_110
[16:12:09]   done H_collar_95_110
[16:12:11]   done H_putratio_1x2_95_85
[16:12:13]   done H_backspread_1x2_100_90
[16:12:16]   done H_pspread_collar_95_85_105
[16:12:18]   done P_longput_97
[16:12:20]   done P_longput_95
[16:12:22]   done P_longput_90
[16:12:25]   done P_bearspread_97_90
[16:12:31]   done P_bearspread_95_85
[16:12:38]   done P_backspread_1x2_97_90
[16:12:45]   done P_backspread_1x3_97_90
[16:12:52]   done P_ratio_2x1_95_85
[16:12:59]   done P_ratio_3x1_92_82
[16:13:05]   done P_ratio_3x2_95_85
[16:13:11]   done P_ratio_3x3_95_85
[16:13:17]   done P_riskrev_95_105
[16:13:23]   done P_shortcall_102
[16:13:23] US: hist rows=384 mc rows=384 saved.
[16:13:23] === INDIA: 127 months 2016-01->2026-07; skew=0.5 val=pb
[16:13:23] INDIA regime stats:
market regime  n_months  mean_ann_ret  median_ann_ret  ann_vol  fwd12m_mean  fwd12m_median  fwd12m_p10  fwd12m_worst  pct_neg_month
 INDIA  CHEAP        34     -0.058479       -0.045779 0.239637     0.241525       0.198632    0.117911      0.032510       0.529412
 INDIA   FAIR        60      0.158363        0.173162 0.129449     0.057205       0.074262   -0.055480     -0.301563       0.416667
 INDIA   RICH        32      0.204885        0.197694 0.121443     0.106213       0.082805   -0.005054     -0.032585       0.312500
 INDIA    ALL       126      0.111665        0.138673 0.166302     0.115720       0.104836   -0.020730     -0.301563       0.420635
[16:13:27]   done H_put_ATM
[16:13:31]   done H_put_95
[16:13:35]   done H_put_90
[16:13:39]   done H_putspread_95_85
[16:13:43]   done H_putspread_90_80
[16:13:47]   done H_collar_95_105
[16:13:51]   done H_collar_90_110
[16:13:55]   done H_collar_95_110
[16:13:59]   done H_putratio_1x2_95_85
[16:14:03]   done H_backspread_1x2_100_90
[16:14:07]   done H_pspread_collar_95_85_105
[16:14:11]   done P_longput_97
[16:14:15]   done P_longput_95
[16:14:19]   done P_longput_90
[16:14:23]   done P_bearspread_97_90
[16:14:26]   done P_bearspread_95_85
[16:14:30]   done P_backspread_1x2_97_90
[16:14:34]   done P_backspread_1x3_97_90
[16:14:37]   done P_ratio_2x1_95_85
[16:14:41]   done P_ratio_3x1_92_82
[16:14:45]   done P_ratio_3x2_95_85
[16:14:49]   done P_ratio_3x3_95_85
[16:14:53]   done P_riskrev_95_105
[16:14:56]   done P_shortcall_102
[16:14:56] INDIA: hist rows=384 mc rows=384 saved.
[16:14:56] ALL GRIDS DONE
[16:30:48] V2: winsorize + complete-market-median-PE + small-cap
[16:30:48] BROAD median-PE q25=20.6 q75=28.7 now=25.6 regime_now=FAIR n=53
[16:32:23] SMALLCAP PE q25=28.0 q75=61.5 now=36.2 regime_now=FAIR n=119
[16:34:09] V2 info: {"broad_medpe_q25": 20.599616993099914, "broad_medpe_q75": 28.700712067680282, "broad_medpe_now": 25.634680543025425, "broad_regime_now": "FAIR", "smallcap_pe_q25": 27.979999999999997, "smallcap_pe_q75": 61.519999999999996, "smallcap_pe_now": 36.23, "smallcap_regime_now": "FAIR", "median_pe_latest": 25.634680543025425, "median_pe_date": "2026-01-01"}
[16:34:09] V2 DONE
[16:34:49] V2: winsorize + complete-market-median-PE + small-cap
[16:34:50] BROAD median-PE q25=18.0 q75=25.0 now=25.6 regime_now=RICH n=116
[16:36:26] SMALLCAP PE q25=28.0 q75=61.5 now=36.2 regime_now=FAIR n=119
[16:38:06] V2 info: {"broad_medpe_q25": 17.981948099004107, "broad_medpe_q75": 25.003340008880627, "broad_medpe_now": 25.634680543025425, "broad_regime_now": "RICH", "smallcap_pe_q25": 27.979999999999997, "smallcap_pe_q75": 61.519999999999996, "smallcap_pe_now": 36.23, "smallcap_regime_now": "FAIR", "median_pe_latest": 25.634680543025425, "median_pe_date": "2026-01-01"}
[16:38:06] V2 DONE
[19:34:36] V3: momentum sub-regimes + net-hedge-positive constraint (owner Kabir E-028)
[19:34:36] ALLOWED structures (20): ['H_put_ATM', 'H_put_95', 'H_put_90', 'H_putspread_95_85', 'H_putspread_90_80', 'H_collar_95_105', 'H_collar_90_110', 'H_collar_95_110', 'H_backspread_1x2_100_90', 'H_pspread_collar_95_85_105', 'P_longput_97', 'P_longput_95', 'P_longput_90', 'P_bearspread_97_90', 'P_bearspread_95_85', 'P_backspread_1x2_97_90', 'P_backspread_1x3_97_90', 'P_ratio_3x1_92_82', 'P_ratio_3x2_95_85', 'P_ratio_3x3_95_85']
[19:34:36] BANNED by net-hedge-positive rule (4): ['H_putratio_1x2_95_85', 'P_ratio_2x1_95_85', 'P_riskrev_95_105', 'P_shortcall_102']
[19:36:49] [US] current sub-regime = RICH_EXT; hedge recs:
  subregime                 best_hedge     tenor  n  ann_ret  maxdd  unhedged_maxdd  cvar5  cvar_improve    cost  sortino
 CHEAP_FALL            H_collar_95_105 quarterly 76    0.043 -0.153          -0.437 -0.047         0.140  0.0113      1.5
CHEAP_RECOV H_pspread_collar_95_85_105    annual 19    0.102  0.000          -0.078  0.009         0.087 -0.0245      NaN
       FAIR            H_collar_95_105    annual 78    0.032 -0.102          -0.556 -0.040         0.233  0.0194      2.9
  RICH_CALM            H_collar_95_105    annual 17    0.028 -0.067          -0.484 -0.034         0.351  0.0064      3.5
   RICH_EXT            H_collar_95_105    annual 23    0.032 -0.071          -0.377 -0.050         0.158  0.0082      2.0
[19:36:59] [INDIA_LARGE] current sub-regime = CHEAP_FALL; hedge recs:
  subregime                 best_hedge   tenor  n  ann_ret  maxdd  unhedged_maxdd  cvar5  cvar_improve   cost  sortino
 CHEAP_FALL H_pspread_collar_95_85_105 monthly 15    0.328 -0.020          -0.027 -0.020         0.007 0.0001     11.8
CHEAP_RECOV                  H_put_ATM monthly 19    0.149 -0.057          -0.287 -0.022         0.209 0.0174      8.1
       FAIR                  H_put_ATM monthly 60    0.041 -0.098          -0.214 -0.022         0.057 0.0159      2.1
  RICH_CALM                  H_put_ATM monthly 16    0.014 -0.077          -0.109 -0.024         0.024 0.0169      0.9
[19:37:08] [INDIA_BROAD] current sub-regime = RICH_CALM; hedge recs:
  subregime                 best_hedge      tenor  n  ann_ret  maxdd  unhedged_maxdd  cvar5  cvar_improve    cost  sortino
 CHEAP_FALL H_pspread_collar_95_85_105    monthly 13    0.374 -0.014          -0.023 -0.014         0.009 -0.0001     35.3
CHEAP_RECOV                  H_put_ATM  quarterly  6    0.140 -0.021          -0.288 -0.024         0.265  0.0280     22.1
       FAIR H_pspread_collar_95_85_105 semiannual  9    0.101 -0.023          -0.102 -0.023         0.079 -0.0164      NaN
  RICH_CALM                  H_put_ATM    monthly 13    0.062 -0.025          -0.078 -0.016         0.062  0.0143      3.6
   RICH_EXT                  H_put_ATM    monthly 15    0.089 -0.042          -0.075 -0.015         0.048  0.0153      5.8
[19:37:15] [INDIA_SMALLCAP] current sub-regime = FAIR; hedge recs:
  subregime      best_hedge     tenor  n  ann_ret  maxdd  unhedged_maxdd  cvar5  cvar_improve   cost  sortino
 CHEAP_FALL       H_put_ATM   monthly 12    0.398 -0.050          -0.057 -0.022         0.014 0.0265     17.6
CHEAP_RECOV       H_put_ATM   monthly 18    0.207 -0.154          -0.180 -0.034         0.065 0.0235      8.9
       FAIR       H_put_ATM quarterly 20    0.143 -0.091          -0.404 -0.040         0.298 0.0445      8.5
  RICH_CALM H_collar_95_105   monthly 13   -0.121 -0.215          -0.539 -0.052         0.284 0.0024     -2.1
   RICH_EXT       H_put_ATM   monthly 17    0.176 -0.065          -0.132 -0.024         0.049 0.0205      7.2
[19:37:15] current sub-regimes: {"US": "RICH_EXT", "INDIA_LARGE": "CHEAP_FALL", "INDIA_BROAD": "RICH_CALM", "INDIA_SMALLCAP": "FAIR"}
[19:37:15] V3 DONE
