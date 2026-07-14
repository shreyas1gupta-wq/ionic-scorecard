"""
PRICE-LEVEL FILTER TEST — does absolute stock price predict momentum
continuation? Tested on 3 INDEPENDENT datasets so the answer isn't an
artifact of one signal definition:

  A) Chartlink VCP breakout scanner (1,505 signals, PIT-clean, fwd30_ret)
  B) Gap-up trigger, ALL stock-days meeting gap>=5% (momentum_trigger_daily,
     using T4/T5 masks) — much larger N, unfiltered by liquidity/turnover
  C) Gap strategy REAL TRADED P&L (gap_ledger_SWING_30d_5pct.csv) — actual
     entry price recorded per trade, actual net P&L after costs/SL/exits.
     This is the least bias-prone check: real money, real friction.

Bins chosen to bracket the exact levels asked about:
  <10, 10-25, 25-50, 50-100, 100-250, 250-500, 500-1000, 1000-1500,
  1500-2000, 2000-2500, 2500-5000, >5000
No cherry-picking: full table reported, every bin, every dataset.
"""
import os, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

SCAN_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
OPT_DIR = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NIFTY_OPTIONS_ML_20260714"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NIFTY_OPTIONS_ML_20260710_pricebands"
os.makedirs(OUT, exist_ok=True)

BINS = [0, 1, 5, 10, 25, 50, 100, 250, 500, 1000, 1500, 2000, 2500, 5000, 1e9]
LABELS = ["<1", "1-5", "5-10", "10-25", "25-50", "50-100", "100-250", "250-500", "500-1000",
          "1000-1500", "1500-2000", "2000-2500", "2500-5000", ">5000"]

def band_report(df, price_col, ret_col, label, weight_col=None):
    d = df.dropna(subset=[price_col, ret_col]).copy()
    d["band"] = pd.cut(d[price_col], bins=BINS, labels=LABELS)
    print(f"\n{'='*100}\n{label}  (n={len(d)})\n{'='*100}")
    print(f"{'Band':<12} {'n':>6} {'mean%':>8} {'median%':>8} {'win%':>6} {'t-stat vs rest':>15} {'p-value':>9}")
    overall_mean = d[ret_col].mean()
    rows = []
    for b in LABELS:
        sub = d[d["band"] == b]
        rest = d[d["band"] != b]
        if len(sub) < 5:
            print(f"{b:<12} {len(sub):>6}  (too few)")
            continue
        t, p = stats.ttest_ind(sub[ret_col], rest[ret_col], equal_var=False)
        print(f"{b:<12} {len(sub):>6} {sub[ret_col].mean():>8.3f} {sub[ret_col].median():>8.3f} "
              f"{(sub[ret_col]>0).mean()*100:>5.1f}% {t:>15.2f} {p:>9.4f}")
        rows.append({"band": b, "n": len(sub), "mean": sub[ret_col].mean(),
                     "median": sub[ret_col].median(), "win": (sub[ret_col]>0).mean()*100,
                     "t": t, "p": p})
    # overall correlation (log price vs return) - continuous check, no binning bias
    lp = np.log(d[price_col])
    corr, corr_p = stats.pearsonr(lp, d[ret_col])
    print(f"\nContinuous check: corr(log(price), {ret_col}) = {corr:.4f}  (p={corr_p:.4f})  [overall mean {overall_mean:.3f}%]")
    return pd.DataFrame(rows)

# ============ A) Chartlink VCP scanner — REAL traded P&L (champion SL10%/30d, 679 trades) ============
scan = pd.read_csv(os.path.join(SCAN_DIR, "loser_forensics.csv"))
rA = band_report(scan, "price_level", "ret_pct",
                 "A) Chartlink VCP champion (SL10%/30d) REAL traded P&L by ENTRY price band")
rA.to_csv(os.path.join(OUT, "priceband_A_chartlink.csv"), index=False)

# ============ B) Gap-trigger universe (momentum_trigger_daily, unfiltered) ============
mt = pd.read_parquet(os.path.join(OPT_DIR, "momentum_trigger_daily.parquet"))
gap_today = mt[mt["today_gap_pct"] >= 5].copy()
gap_today["entry_price"] = gap_today["open"] if "open" in gap_today.columns else gap_today["close"]
rB1 = band_report(gap_today, "entry_price", "fwd_10d_pct",
                  "B1) ALL gap-up>=5% stock-days (unfiltered universe, 1039 stocks): fwd 10-day return by price band")
rB1.to_csv(os.path.join(OUT, "priceband_B1_gaptrigger_fwd10d.csv"), index=False)

gap_today["entry_price_bucket_check"] = gap_today["open"]
rB2 = band_report(gap_today, "entry_price", "fwd_5d_pct",
                  "B2) Same gap>=5% universe: fwd 5-day return by price band")
rB2.to_csv(os.path.join(OUT, "priceband_B2_gaptrigger_fwd5d.csv"), index=False)

# ============ C) REAL traded P&L from the gap strategy (best config) ============
led_path = os.path.join(OPT_DIR, "gap_ledger_SWING_30d_5pct.csv")
if os.path.exists(led_path):
    led = pd.read_csv(led_path, parse_dates=["entry_date"])
    panel = pd.read_parquet(os.path.join(SCAN_DIR, "chartlink_prices_full5yr_v2.parquet"),
                            columns=["symbol", "date", "open"])
    panel["date"] = pd.to_datetime(panel["date"])
    led = led.merge(panel, left_on=["symbol", "entry_date"], right_on=["symbol", "date"], how="left")
    led = led.rename(columns={"open": "entry_price"})
    print(f"\nMatched entry price for {led['entry_price'].notna().sum()}/{len(led)} trades")
    rC = band_report(led, "entry_price", "ret_pct",
                     "C) REAL TRADED P&L (Swing-SL/30d/5% gap strategy, net of all costs) by entry price band")
    rC.to_csv(os.path.join(OUT, "priceband_C_realtraded.csv"), index=False)
else:
    print(f"\n[C skipped: {led_path} not found]")

print("\n\nSaved: priceband_A_chartlink.csv, priceband_B1_gaptrigger_fwd10d.csv, priceband_B2_gaptrigger_fwd5d.csv, priceband_C_realtraded.csv")
