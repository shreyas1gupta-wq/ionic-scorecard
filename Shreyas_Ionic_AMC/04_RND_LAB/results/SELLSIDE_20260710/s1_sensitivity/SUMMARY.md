# S1 sensitivity surface (net pts/trade | t | PF). PRIMARY = 09:20 straddle+0 SL30.

## entry 09:20
       struct             SL20              SL30              SL40              SL50
 straddle-100 +9.8|t2.6|pf1.49 +14.3|t3.4|pf1.65 +10.1|t2.2|pf1.37 +13.6|t2.9|pf1.50
  straddle-50 +8.6|t2.8|pf1.53 +12.4|t3.7|pf1.77 +10.3|t2.9|pf1.57  +9.2|t2.4|pf1.46
   straddle+0 +7.3|t2.9|pf1.52  +8.0|t2.9|pf1.56  +5.8|t2.0|pf1.38  +7.0|t2.2|pf1.48
  straddle+50 +5.6|t2.0|pf1.36  +3.9|t1.2|pf1.22  +3.3|t1.0|pf1.16  +4.3|t1.2|pf1.20
 straddle+100 +2.9|t0.8|pf1.14  +1.7|t0.4|pf1.07  +0.7|t0.2|pf1.02  +0.8|t0.2|pf1.02
 strangle_w50 +2.8|t1.4|pf1.26  +4.9|t2.2|pf1.48  +3.9|t1.6|pf1.35  +3.8|t1.5|pf1.34
strangle_w100 +0.9|t0.6|pf1.11  +1.5|t0.9|pf1.20  +1.0|t0.5|pf1.12  +1.5|t0.8|pf1.18

## entry 09:45
       struct              SL20              SL30              SL40              SL50
 straddle-100  +6.3|t1.8|pf1.31 +10.0|t2.6|pf1.46 +11.1|t2.7|pf1.48 +11.9|t2.8|pf1.49
  straddle-50  +3.6|t1.3|pf1.21  +6.9|t2.3|pf1.40  +7.9|t2.5|pf1.44  +8.4|t2.5|pf1.46
   straddle+0  +1.8|t0.7|pf1.11  +3.2|t1.2|pf1.20  +4.3|t1.7|pf1.29  +3.3|t1.1|pf1.21
  straddle+50 -0.0|t-0.0|pf1.00  +1.6|t0.5|pf1.09  +0.1|t0.0|pf1.00 -0.2|t-0.1|pf0.99
 straddle+100 -2.6|t-0.8|pf0.89 -2.0|t-0.5|pf0.92 -3.2|t-0.8|pf0.89 -4.0|t-0.9|pf0.88
 strangle_w50  +0.2|t0.1|pf1.02  +1.1|t0.6|pf1.10  +1.8|t1.0|pf1.17  +2.1|t1.0|pf1.19
strangle_w100 -0.4|t-0.3|pf0.94 -0.1|t-0.1|pf0.99  +0.4|t0.3|pf1.06  +0.0|t0.0|pf1.00

## entry 10:15
       struct              SL20              SL30              SL40              SL50
 straddle-100  +7.6|t2.3|pf1.41 +11.0|t2.9|pf1.54 +11.5|t2.9|pf1.53 +10.9|t2.6|pf1.46
  straddle-50  +7.5|t2.8|pf1.54  +8.3|t2.8|pf1.53 +10.4|t3.4|pf1.67  +9.9|t3.0|pf1.58
   straddle+0  +4.5|t2.1|pf1.35  +4.1|t1.7|pf1.29  +5.8|t2.3|pf1.46  +6.9|t2.6|pf1.57
  straddle+50  +1.3|t0.5|pf1.08  +1.7|t0.6|pf1.10  +1.5|t0.5|pf1.09  +3.3|t1.1|pf1.18
 straddle+100 -0.1|t-0.0|pf0.99 -1.1|t-0.3|pf0.96 -3.2|t-0.8|pf0.89 -1.7|t-0.4|pf0.94
 strangle_w50  +3.0|t2.1|pf1.39  +2.9|t1.7|pf1.33  +3.8|t2.0|pf1.43  +4.4|t2.2|pf1.51
strangle_w100  +0.4|t0.4|pf1.07  +1.1|t0.9|pf1.19  +1.7|t1.3|pf1.30  +2.2|t1.6|pf1.38

# Plateau check: primary=+8.02 | 3x3 neighborhood mean=+7.26 min=+3.27 max=+12.40 | all-surface: 72/84 cells positive, best=+14.32 @('09:20', 'straddle-100', np.int64(30)) (in-sample selection - do NOT adopt), median=+3.28

## ERA/YEAR ROBUSTNESS OF THE DOWN-SHIFT GRADIENT (appended)
straddle-100: era21-23 +15.12 / era24-26 +13.44; straddle-50: +10.88 / +14.07. Both positive ALL SIX years (min +3.8). Monotonic across all 3 entry times. Interpretation: short-delta tilt on 0DTE (short ITM CE + OTM PE) harvests expiry-day drift/call-side richness on top of VRP. STATUS: strongest in-sample gradient, NOT adopted; candidate S1b challenger for pre-registered forward validation alongside primary.
