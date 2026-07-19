"""Phase-1.1 + 1.6 : technical/momentum/mean-reversion factor library + relative scoring core.
Needs ONLY OHLCV (unblocked). Computes point-in-time factors at the latest date for each
pilot stock, converts each to a cross-sectional percentile (relative scoring, no hard cutoffs),
sign-adjusts for the 1M lens, aggregates into Momentum & MeanRev themes, and emits a PROVISIONAL
(uncalibrated) 1M relative conviction. Calibration to true probability is Phase-6.
"""
import os, glob
import numpy as np, pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER"
PRICES = os.path.join(BASE, "data", "prices")
RES = os.path.join(BASE, "results"); os.makedirs(RES, exist_ok=True)

def load(tk):
    return pd.read_parquet(os.path.join(PRICES, f"{tk}.parquet")).sort_index()

bench = load("_NSEI")["Close"]

def rsi(close, n=14):
    d = close.diff(); up = d.clip(lower=0).rolling(n).mean(); dn = (-d.clip(upper=0)).rolling(n).mean()
    rs = up / dn.replace(0, np.nan); return 100 - 100/(1+rs)

def atr_pct(df, n=14):
    hl = df.High - df.Low; hc = (df.High - df.Close.shift()).abs(); lc = (df.Low - df.Close.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1); return (tr.rolling(n).mean() / df.Close) * 100

def factors_for(tk):
    df = load(tk); c = df.Close; v = df.Volume
    f = {}
    # --- Momentum ---
    f["ret_1m"]   = c.iloc[-1]/c.iloc[-22]-1
    f["ret_3m"]   = c.iloc[-1]/c.iloc[-64]-1
    f["ret_6m_sk"]= c.iloc[-22]/c.iloc[-127]-1          # 6m skipping most-recent 1m
    f["ret_12_1"] = c.iloc[-22]/c.iloc[-253]-1          # 12-1 momentum
    # relative strength vs NIFTY (3m)
    b = bench.reindex(c.index).ffill()
    f["rs_3m"] = (c.iloc[-1]/c.iloc[-64]) / (b.iloc[-1]/b.iloc[-64]) - 1
    # trend / MA structure
    ma20, ma50, ma200 = c.rolling(20).mean(), c.rolling(50).mean(), c.rolling(200).mean()
    f["dist_50dma"]  = c.iloc[-1]/ma50.iloc[-1]-1
    f["dist_200dma"] = c.iloc[-1]/ma200.iloc[-1]-1
    f["ma_align"]    = float(ma20.iloc[-1] > ma50.iloc[-1] > ma200.iloc[-1])   # stacked bullish
    f["prox_52wh"]   = c.iloc[-1]/c.iloc[-252:].max()                          # 1=at high
    # --- Mean-reversion / exhaustion ---
    f["rsi14"]  = rsi(c).iloc[-1]
    sd20 = c.rolling(20).std(); f["boll_pctb"] = (c.iloc[-1]-ma20.iloc[-1])/(2*sd20.iloc[-1]) # 0=mid,>1 upper
    f["rev_1w"] = -(c.iloc[-1]/c.iloc[-6]-1)                                   # short-term reversal (sign-flipped)
    # --- Volatility / volume ---
    f["atr_pct"]   = atr_pct(df).iloc[-1]
    f["vol_ratio"] = v.iloc[-5:].mean()/v.iloc[-63:].mean()                    # recent vs 3m volume
    return f

tickers = sorted([os.path.basename(p)[:-8] for p in glob.glob(os.path.join(PRICES,"*.parquet")) if "_NSEI" not in p])
raw = pd.DataFrame({tk: factors_for(tk) for tk in tickers}).T

# --- Relative scoring: cross-sectional percentile per factor (robust, no hard cutoffs) ---
pct = raw.rank(pct=True)*100
# sign map for the 1M lens: +1 bullish-higher, -1 bullish-lower
sign = {"ret_1m":+1,"ret_3m":+1,"ret_6m_sk":+1,"ret_12_1":+1,"rs_3m":+1,"dist_50dma":+1,"dist_200dma":+1,
        "ma_align":+1,"prox_52wh":+1,"rsi14":0,"boll_pctb":0,"rev_1w":+1,"atr_pct":-1,"vol_ratio":+1}
# RSI & Bollinger are non-monotonic (extreme = mean-revert risk): score = -(distance from neutral)
adj = pct.copy()
adj["rsi14"]     = 100 - (raw["rsi14"]-50).abs()/50*100        # near 50 good, extremes penalised
adj["boll_pctb"] = 100 - raw["boll_pctb"].abs().clip(0,2)/2*100
for k,s in sign.items():
    if s==-1: adj[k] = 100-pct[k]
# themes
MOM = ["ret_1m","ret_3m","ret_6m_sk","ret_12_1","rs_3m","dist_50dma","dist_200dma","ma_align","prox_52wh"]
MR  = ["rsi14","boll_pctb","rev_1w"]
theme_mom = adj[MOM].mean(axis=1)
theme_mr  = adj[MR].mean(axis=1)
# 1M prior weights (Momentum 0.30, MeanRev 0.10, Flow/vol 0.25 proxy via vol_ratio+atr) -> renormalised for available themes
theme_flow = adj[["vol_ratio","atr_pct"]].mean(axis=1)
w = {"mom":0.45,"flow":0.35,"mr":0.20}   # renormalised (fundamentals/catalyst themes pending screener)
comp = w["mom"]*theme_mom + w["flow"]*theme_flow + w["mr"]*theme_mr     # 0..100
# provisional relative conviction in [-100,+100]: centre on cross-sectional median
prov = ((comp - 50)/50*100).round(0)

out = pd.DataFrame({
    "theme_momentum": theme_mom.round(0), "theme_flow": theme_flow.round(0), "theme_meanrev": theme_mr.round(0),
    "PROVISIONAL_1M_score": prov,
}).sort_values("PROVISIONAL_1M_score", ascending=False)
raw_r = raw.round(3)
raw_r.to_csv(os.path.join(RES,"pilot_1m_factors_raw.csv"))
out.to_csv(os.path.join(RES,"pilot_1m_scores.csv"))

pd.set_option("display.width",200)
print("=== RAW 1M FACTORS (point-in-time, latest date) ===")
print(raw_r.to_string())
print("\n=== PROVISIONAL 1M RELATIVE SCORE (uncalibrated; cross-sectional among pilot) ===")
print(out.to_string())
print("\nNOTE: scores are RELATIVE ranks among the 10 pilot names, NOT calibrated probabilities.")
print("Fundamentals/valuation/quality/catalyst themes are pending screener login. Calibration = Phase 6.")
