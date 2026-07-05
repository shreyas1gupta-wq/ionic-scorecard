# AGMAAF verification + attribution decomposition + deflated-Sharpe illustration.
# Neel Basu / attribution desk. ASCII prints only. All numbers labeled by source.
import numpy as np
import pandas as pd
from math import log, sqrt, exp, erf

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
fn = pd.read_parquet(ROOT + r"\datasets\index_daily\factor_navs_principal.parquet")
fn["date"] = pd.to_datetime(fn["date"])
ni = pd.read_parquet(ROOT + r"\datasets\index_daily\nse_official_all_indices.parquet")
ni["date"] = pd.to_datetime(ni["date"])

def series_fn(name):
    s = fn[fn["series"] == name].sort_values("date").set_index("date")["nav"].astype(float)
    return s[~s.index.duplicated()]

def series_ni(name):
    d = ni[ni["index_name"].str.lower() == name.lower()].sort_values("date")
    return d.set_index("date")["close"].astype(float)

def stats(px, label, ann=252):
    px = px.dropna()
    yrs = (px.index[-1] - px.index[0]).days / 365.25
    cagr = (px.iloc[-1] / px.iloc[0]) ** (1 / yrs) - 1
    r = px.pct_change().dropna()
    vol = r.std() * sqrt(ann)
    dd = (px / px.cummax() - 1).min()
    print("  %-32s %s->%s (%.1fy)  CAGR=%6.2f%%  vol=%6.2f%%  maxDD=%7.2f%%" % (
        label, px.index[0].date(), px.index[-1].date(), yrs, cagr*100, vol*100, dd*100))
    return dict(cagr=cagr, vol=vol, dd=dd, yrs=yrs)

def window(s, a, b):
    return s[(s.index >= a) & (s.index <= b)]

print("="*90)
print("1) NIFTY 50 -- verify deck p13 claim: CAGR 11.04% (labeled TRI), vol 20.66%, maxDD -59.50%")
print("   window Jan-2006 -> May-2026")
print("="*90)
n50 = series_fn("NIFTY 50")                       # factor_navs, PRICE index, 2005-04->2026-01
n50w = window(n50, "2006-01-01", "2026-12-31")
st_price = stats(n50w, "NIFTY50 PRICE (our data)")
# approx TRI = price CAGR + avg dividend yield (NIFTY 50 ~1.3%/yr)
divy = 0.0130
print("  NIFTY50 approx TRI CAGR (price + %.2f%% avg div) = %.2f%%" % (divy*100, (st_price["cagr"]+divy)*100))
print("  --> DECK says 'NIFTY TRI' = 11.04%%. Our PRICE = %.2f%%. Our approx-TRI = %.2f%%." % (
    st_price["cagr"]*100, (st_price["cagr"]+divy)*100))

print()
print("="*90)
print("2) NIFTY 200 -- p18 benchmark leg (35%% N200 TRI). window Jan-2020 -> Apr-2026")
print("="*90)
n200 = series_ni("Nifty 200")                     # 2016+ price
n200w = window(n200, "2020-01-01", "2026-04-30")
st200 = stats(n200w, "NIFTY200 PRICE (our data)")
print("  NIFTY200 approx TRI CAGR (+1.3%% div) = %.2f%%" % ((st200["cagr"]+0.013)*100))

# NIFTY 50 over the p18 window too (for context)
n50_2020 = window(series_ni("Nifty 50"), "2020-01-01", "2026-04-30")
stats(n50_2020, "NIFTY50 PRICE 2020-2026")

print()
print("="*90)
print("3) GOLD (GOLDBEES) -- verify 'Gold Super-Cycle Jul-24->May-26 gold +50%%' (p5) + full era")
print("="*90)
gb_etf = pd.read_parquet(ROOT + r"\datasets\etf_gold_silver\goldbees_daily.parquet")
gb_etf["date"] = pd.to_datetime(gb_etf["timestamp"]).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None).dt.normalize()
gb = gb_etf.sort_values("date").set_index("date")["close"].astype(float)
# gold super-cycle window
sc = window(gb, "2024-07-01", "2026-05-31")
print("  GOLDBEES Jul-2024 -> May-2026: %.2f -> %.2f = %+.1f%% total (deck p5 says gold +50%%)" % (
    sc.iloc[0], sc.iloc[-1], (sc.iloc[-1]/sc.iloc[0]-1)*100))
stats(window(gb, "2021-01-01", "2026-07-31"), "GOLDBEES etf (verified D-009)")
# longer gold history from factor_navs GOLDBEES (watch for split; sanity check)
gbf = series_fn("GOLDBEES")
stats(window(gbf, "2006-01-01", "2026-12-31"), "GOLDBEES factor_navs full")
stats(window(gbf, "2020-01-01", "2026-12-31"), "GOLDBEES factor_navs 2020+")

print()
print("="*90)
print("4) DEBT proxy (HDFC Liquid Fund G, factor_navs) -- lower bound for FI leg")
print("="*90)
liq = series_fn("HDFC Liquid Fund(G)")
st_liq = stats(window(liq, "2006-01-01", "2026-12-31"), "HDFC Liquid (cash proxy)")
print("  NOTE: deck FI = CRISIL AAA SHORT-TERM bond ~ liquid + 0.3-0.7pp; use 7.25%% as FI point est.")

print()
print("="*90)
print("5) ATTRIBUTION: decompose claimed 13.90%% CAGR from AVG net exposures (p11)")
print("   Equity 28.50%%  FI 45.75%%  Commodity 25.75%%")
print("="*90)
# asset return assumptions over ~2006-2026, using OUR verified numbers where possible
eq_tri = st_price["cagr"] + divy          # NIFTY50 approx TRI (our data)
eq_px  = st_price["cagr"]                 # price
gold   = stats(window(gbf,"2006-01-01","2026-12-31"), "  (gold used)") if False else None
gold_cagr = (window(gbf,"2006-01-01","2026-12-31").iloc[-1]/window(gbf,"2006-01-01","2026-12-31").iloc[0])**(1/((window(gbf,"2006-01-01","2026-12-31").index[-1]-window(gbf,"2006-01-01","2026-12-31").index[0]).days/365.25))-1
fi_cagr = st_liq["cagr"] + 0.005          # liquid + 0.5pp for short-term AAA
w_eq, w_fi, w_co = 0.285, 0.4575, 0.2575
for eqlab, eq in [("equity=PRICE", eq_px), ("equity=approxTRI", eq_tri)]:
    beta = w_eq*eq + w_fi*fi_cagr + w_co*gold_cagr
    print("  [%s] weighted beta = %.3f*%.2f + %.4f*%.2f + %.4f*%.2f = %.2f%%" % (
        eqlab, w_eq, eq*100, w_fi, fi_cagr*100, w_co, gold_cagr*100, beta*100))
    print("      claimed AGMAAF 13.90%% - beta %.2f%% = %+.2f pp residual (timing+selection)" % (
        beta*100, (0.1390-beta)*100))
print("  contribution split (equity=approxTRI case):")
beta = w_eq*eq_tri + w_fi*fi_cagr + w_co*gold_cagr
print("     equity beta contrib  = %.2f pp (%.0f%% of 13.90)" % (w_eq*eq_tri*100, w_eq*eq_tri/0.1390*100))
print("     FI beta contrib      = %.2f pp (%.0f%% of 13.90)" % (w_fi*fi_cagr*100, w_fi*fi_cagr/0.1390*100))
print("     commodity beta contrib = %.2f pp (%.0f%% of 13.90)" % (w_co*gold_cagr*100, w_co*gold_cagr/0.1390*100))
print("     total beta           = %.2f pp (%.0f%% of 13.90)" % (beta*100, beta/0.1390*100))
print("     RESIDUAL timing+selection = %.2f pp (%.0f%% of 13.90)" % ((0.1390-beta)*100, (0.1390-beta)/0.1390*100))

# sanity: reconstruct deck 'Static Multi-Asset' 60/25/15 = deck says 9.56%
static = 0.60*eq_tri + 0.25*fi_cagr + 0.15*gold_cagr
static_px = 0.60*eq_px + 0.25*fi_cagr + 0.15*gold_cagr
print("  SANITY reconstruct static 60/25/15 (deck=9.56%%): approxTRI-eq=%.2f%%  price-eq=%.2f%%" % (static*100, static_px*100))

print()
print("="*90)
print("6) DEFLATED-SHARPE illustration on claimed backtest Sharpe = 1.90")
print("="*90)
def Phi(x):  return 0.5*(1+erf(x/sqrt(2)))
def Phinv(p):
    # Beasley-Springer/Moro approx
    a=[-39.6968302866538,220.946098424521,-275.928510446969,138.357751867269,-30.6647980661472,2.50662827745924]
    b=[-54.4760987982241,161.585836858041,-155.698979859887,66.8013118877197,-13.2806815528857]
    c=[-0.00778489400243029,-0.322396458041136,-2.40075827716184,-2.54973253934373,4.37466414146497,2.93816398269878,1.00000000000000]
    d=[0.00778469570904146,0.32246712907004,2.445134137143,3.75440866190742]
    pl=0.02425; ph=1-pl
    if p<pl:
        q=sqrt(-2*log(p)); return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p<=ph:
        q=p-0.5; r=q*q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    q=sqrt(-2*log(1-p)); return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)

SR_ann = 1.90
freq = 12                       # treat reported returns as monthly for the estimator
n = 245                         # Jan-2006 -> May-2026 ~ 245 months
SR_pp = SR_ann/sqrt(freq)       # per-period sharpe
se_pp = sqrt((1 + 0.5*SR_pp**2)/n)          # Lo(2002) SE of per-period Sharpe (iid)
se_ann = se_pp*sqrt(freq)
print("  Reported annualized Sharpe = %.2f  (per-month %.3f, n=%d months)" % (SR_ann, SR_pp, n))
print("  SE of the Sharpe estimate (Lo 2002, iid) = +/-%.3f annualized  -> naive 95%% CI [%.2f, %.2f]" % (
    se_ann, SR_ann-1.96*se_ann, SR_ann+1.96*se_ann))
gamma = 0.5772156649
se0_pp = sqrt(1.0/n)            # SE under null SR=0
se0_ann = se0_pp*sqrt(freq)
print("  --- Expected BEST-of-N Sharpe from pure noise (annualized), and DSR, and MinTRL ---")
print("   %5s  %14s  %12s  %14s" % ("N", "noise-ceiling", "DSR(SR>0)", "MinTRL(mo) vs ceiling"))
for N in [1,10,50,200,1000]:
    if N==1:
        emax_ann=0.0
    else:
        z1=Phinv(1-1.0/N); z2=Phinv(1-1.0/(N*exp(1)))
        emax_ann = se0_ann*((1-gamma)*z1 + gamma*z2)
    srstar_pp = emax_ann/sqrt(freq)
    # DSR: prob true SR>ceiling
    denom = sqrt(1 - 0*SR_pp + 0.5*SR_pp**2)   # skew=0,kurt=3 assumption
    dsr = Phi((SR_pp - srstar_pp)*sqrt(n-1)/denom)
    # min track length (months) to reject SR<=ceiling at 95%
    if SR_pp>srstar_pp:
        mintrl = 1 + denom**2 * (1.645/(SR_pp-srstar_pp))**2
    else:
        mintrl = float('inf')
    print("   %5d  %12.2f    %10.4f    %12.1f" % (N, emax_ann, dsr, mintrl))
print("  READ: even best-of-1000 discrete trials leaves 1.90 'significant' (DSR~1) IF it were a")
print("        genuine realized sample -- so the problem is NOT sampling noise. It is that 1.90 is")
print("        the OPTIMIZATION OBJECTIVE computed in-sample on spliced/synthetic history, which DSR")
print("        cannot repair. MinTRL shows ~1-2 years of LIVE data would confirm a real 1.90; they show 0.")

print()
print("="*90)
print("7) INTERNAL-CONSISTENCY arithmetic (deck's own numbers)")
print("="*90)
for lakh, yrs, lab in [(12.47,19.4,"p12 AGMAAF 1L->12.47L, 2007->May26"),
                       (12.90,19.3,"enabler AGMAAF 1L->12.9L, Jan07->Apr26"),
                       (7.50,19.4,"p12 NIFTY 1L->7.5L"),
                       (7.90,19.3,"enabler NIFTY 1L->7.9L")]:
    print("  %-42s implied CAGR = %.2f%%" % (lab, (lakh)**(1/yrs)*100-100 if False else (lakh**(1/yrs)-1)*100))
print("  -> 13.90 (p13) vs 14.17 (enabler) vs 16.32 (p18 2020-26): window artifacts; SAME vol/Sharpe/maxDD")
print("     (7.44/1.90/-12.79) reported for BOTH p13 20.4y and enabler 19.3y windows = not recomputed.")
print("  -> maxDD -12.79%% identical on p13(full), p14, p18(2020-26) => worst DD is INSIDE 2020-26 (COVID),")
print("     so p14's 'survived 2008 at -12.79%%' mislabels the COVID drawdown as the GFC one.")
