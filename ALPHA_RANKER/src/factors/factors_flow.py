"""Delivery/flow + microstructure factor library (1M lens) — complement to factors_technical.py.

DATA REALITY CHECK (verified by running, see reports/AG3_flow.md for full detail):
  datasets/nse_bhavcopy_daily/delivery_2022_2026.parquet covers ONLY 2022-10-03 -> 2024-06-21
  (SHAKTIPUMP ends 2024-06-06) despite its filename. It has ZERO date overlap with the pilot
  OHLCV in ALPHA_RANKER/data/prices/*.parquet (2024-07-16 -> 2026-07-16, i.e. "today").
  => Delivery-dependent factors (deliv % level/spike/qty-trend/accumulation-vs-distribution) can
     ONLY be computed AS OF the last available delivery date per symbol (2024-06/2024-06-06 for
     SHAKTIPUMP) — they are a HISTORICAL snapshot, not current. Presenting them as "today's"
     delivery read would be fabrication.
  => Non-delivery microstructure factors (volume expansion, OBV slope, Amihud illiquidity,
     turnover-adjusted momentum) need only OHLCV, so those ARE computed as of the latest price
     date (today) directly from data/prices/.
  For the delivery-window historical panel, Close comes from datasets/nse_bhavcopy_daily/
  close_all.parquet (series=='EQ' only) since data/prices/ pilot OHLCV does not go back to
  2022-2024; Volume/turnover for that window comes from delivery's ttl_qty (total traded qty).
  NO LOOKAHEAD: every rolling stat uses only data up to and including its own as-of date.
"""
import os
import numpy as np
import pandas as pd
import pyarrow.dataset as ds

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
PROJ = os.path.join(BASE, "ALPHA_RANKER")
PRICES = os.path.join(PROJ, "data", "prices")
RES = os.path.join(PROJ, "results"); os.makedirs(RES, exist_ok=True)
REP = os.path.join(PROJ, "reports"); os.makedirs(REP, exist_ok=True)

DELIV_PATH = os.path.join(BASE, "datasets", "nse_bhavcopy_daily", "delivery_2022_2026.parquet")
CLOSEALL_PATH = os.path.join(BASE, "datasets", "nse_bhavcopy_daily", "close_all.parquet")

PILOT = ["HDFCBANK", "ASIANPAINT", "NESTLEIND", "TATASTEEL", "HINDALCO",
         "MARUTI", "TCS", "INFY", "GRAVITA", "SHAKTIPUMP"]

# ---------- Step 1: pull ONLY the pilot rows from the two large parquets (pyarrow filter, never load whole file) ----------
_deliv_tbl = ds.dataset(DELIV_PATH, format="parquet").to_table(filter=ds.field("symbol").isin(PILOT))
deliv_all = _deliv_tbl.to_pandas().sort_values(["symbol", "date"])

_close_tbl = ds.dataset(CLOSEALL_PATH, format="parquet").to_table(
    filter=ds.field("symbol").isin(PILOT) & (ds.field("series") == "EQ"))
close_all = _close_tbl.to_pandas().sort_values(["symbol", "date"])

DELIV_COVERAGE = deliv_all.groupby("symbol")["date"].agg(["min", "max", "count"])


def load_price(tk):
    return pd.read_parquet(os.path.join(PRICES, f"{tk}.parquet")).sort_index()


def slope_norm(y):
    """OLS slope of y vs 0..n-1, normalised by mean(|y|) so it's a dimensionless %/period trend."""
    y = np.asarray(y, dtype=float)
    n = len(y)
    x = np.arange(n)
    b = np.polyfit(x, y, 1)[0]
    denom = np.mean(np.abs(y)) if np.mean(np.abs(y)) != 0 else np.nan
    return b / denom


def delivery_factors(tk):
    """Delivery-dependent factors, computed at the LAST available delivery date for this symbol.
    Close comes from close_all.parquet (EQ series), Volume proxy = ttl_qty from delivery data."""
    d = deliv_all[deliv_all.symbol == tk].copy()
    c = close_all[close_all.symbol == tk][["date", "close"]]
    panel = d.merge(c, on="date", how="inner").sort_values("date").reset_index(drop=True)
    if len(panel) < 25:
        return None, None
    panel["ret"] = panel["close"].pct_change()
    asof = panel["date"].iloc[-1]

    dp = panel["deliv_per"]
    dq = panel["deliv_qty"]
    r20 = dp.rolling(20)
    r60 = dp.rolling(60)
    z20 = (dp.iloc[-1] - r20.mean().iloc[-1]) / r20.std().iloc[-1] if len(panel) >= 20 else np.nan
    z60 = (dp.iloc[-1] - r60.mean().iloc[-1]) / r60.std().iloc[-1] if len(panel) >= 60 else np.nan
    qty_trend = slope_norm(dq.tail(20)) if len(panel) >= 20 else np.nan

    win = panel.tail(40)
    up_mask, dn_mask = win["ret"] > 0, win["ret"] < 0
    accum = (win.loc[up_mask, "deliv_per"].mean() - win.loc[dn_mask, "deliv_per"].mean()
             if up_mask.sum() >= 3 and dn_mask.sum() >= 3 else np.nan)

    f = {
        "deliv_pct_latest": dp.iloc[-1],
        "deliv_z20": z20,
        "deliv_z60": z60,
        "deliv_qty_trend": qty_trend,
        "deliv_accum_up_minus_down": accum,
    }
    return f, asof


def micro_factors(tk):
    """Non-delivery microstructure factors from CURRENT OHLCV (data/prices), as of latest price date."""
    df = load_price(tk)
    c, v = df["Close"], df["Volume"]
    ret = c.pct_change()
    turnover = c * v  # rupee turnover proxy (no shares-outstanding data -> can't do true % free-float turnover)
    asof = df.index[-1]

    vol_expansion = v.tail(5).mean() / v.tail(60).mean()

    obv = (np.sign(c.diff().fillna(0)) * v).cumsum()
    obv_slope = slope_norm(obv.tail(20))

    amihud = (ret.abs() / turnover).tail(20).mean() * 1e6  # scaled for readability; higher = more illiquid

    ret_21 = c.iloc[-1] / c.iloc[-22] - 1
    t_ratio = turnover.rolling(20).mean().iloc[-1] / turnover.rolling(120).mean().iloc[-1]
    turnover_adj_mom = ret_21 / t_ratio

    f = {
        "vol_expansion_5_60": vol_expansion,
        "obv_slope20": obv_slope,
        "amihud_illiq": amihud,
        "turnover_adj_mom": turnover_adj_mom,
    }
    return f, asof


rows_deliv, asof_deliv = {}, {}
rows_micro, asof_micro = {}, {}
for tk in PILOT:
    fd, ad = delivery_factors(tk)
    fm, am = micro_factors(tk)
    rows_deliv[tk] = fd if fd is not None else {}
    asof_deliv[tk] = ad
    rows_micro[tk] = fm
    asof_micro[tk] = am

raw_deliv = pd.DataFrame(rows_deliv).T
raw_micro = pd.DataFrame(rows_micro).T
raw = pd.concat([raw_deliv, raw_micro], axis=1)
raw["asof_date_delivery"] = pd.Series(asof_deliv)
raw["asof_date_price"] = pd.Series(asof_micro)

# ---------- Cross-sectional percentile scoring (0-100, no hard cutoffs) ----------
DELIV_COLS = ["deliv_pct_latest", "deliv_z20", "deliv_z60", "deliv_qty_trend", "deliv_accum_up_minus_down"]
MICRO_COLS = ["vol_expansion_5_60", "obv_slope20", "amihud_illiq", "turnover_adj_mom"]
SIGN = {c: +1 for c in DELIV_COLS + MICRO_COLS}
SIGN["amihud_illiq"] = -1  # higher illiquidity = worse

num = raw[DELIV_COLS + MICRO_COLS].apply(pd.to_numeric, errors="coerce")
pct = num.rank(pct=True) * 100
adj = pct.copy()
for k, s in SIGN.items():
    if s == -1:
        adj[k] = 100 - pct[k]

theme_flow_delivery_hist = adj[DELIV_COLS].mean(axis=1).round(1)   # snapshot at last delivery date (~2024-06)
theme_flow_micro_current = adj[MICRO_COLS].mean(axis=1).round(1)   # current, as of latest price date (today)
theme_flow_allcols_ref = adj[DELIV_COLS + MICRO_COLS].mean(axis=1).round(1)  # reference only, mixes dates

out = raw.copy()
out["theme_flow_delivery_hist_asof2024"] = theme_flow_delivery_hist
out["theme_flow_micro_current"] = theme_flow_micro_current
out["theme_flow_ALLTIME_REFERENCE_mixed_dates"] = theme_flow_allcols_ref
out = out.sort_values("theme_flow_micro_current", ascending=False)

out_path = os.path.join(RES, "pilot_flow_factors.csv")
out.to_csv(out_path)

print("=== Delivery coverage per pilot symbol ===")
print(DELIV_COVERAGE)
print("\n=== Flow/microstructure raw + theme scores ===")
pd.set_option("display.width", 220)
print(out.to_string())
print(f"\nSaved: {out_path}")
