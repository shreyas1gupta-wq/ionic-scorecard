"""Calibrate the real ATM-IV / India-VIX multiplier m(DTE) from NSE F&O EOD
bhavcopy, plus a put-call IV average. This replaces the synthetic m=1 guess
in engine_v2 and answers the project's pivotal question: is short-DTE ATM IV
rich enough (>=1.5x VIX near 0DTE) to make the short-straddle edge real?

For each bhavcopy day and each live NIFTY expiry:
  - ATM strike = nearest StrkPric to UndrlygPric
  - IV from CE and PE settlement prices (BS inversion), averaged
  - DTE = (expiry - trade date) in calendar days (EOD valuation)
  - VIX = that day's India VIX close (from our 1-min processed series)
  - m = ATM_IV(%) / VIX

Outputs:
  results/iv_calibration_points.csv   (per day/expiry rows)
  results/iv_multiplier_curve.csv     (m by DTE bucket: median/mean/n)
  prints an extrapolated m(0) estimate and the verdict vs break-even 1.5
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DIVIDEND_YIELD, PROCESSED_DIR, RAW_DIR, RESULTS_DIR, RISK_FREE_RATE  # noqa: E402
from options.bs_pricing import implied_vol  # noqa: E402

OPT_DIR = RAW_DIR / "options"
# Trading-time annualisation (252 trading days/yr) to be CONSISTENT with the
# engine's intraday trading-time clock. At EOD, time to an expiry DTE days
# away = DTE full trading days = DTE/252 yr. (Use 365.0 for the legacy
# calendar-time convention — gives a higher, non-comparable multiplier.)
DAYS_PER_YEAR = 252.0
MIN_PER_YEAR = DAYS_PER_YEAR  # name kept for minimal churn; value is trading-time


def vix_daily_close() -> pd.Series:
    v = pd.read_parquet(PROCESSED_DIR / "vix_1min.parquet")["vix"]
    return v.groupby(v.index.normalize()).last()


def nifty_daily_close() -> pd.Series:
    n = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")["close"]
    return n.groupby(n.index.normalize()).last()


def normalize(df: pd.DataFrame, spot_fallback: float) -> tuple[pd.DataFrame, float]:
    """Return (NIFTY option rows with cols symbol/opt_type/strike/settle/expiry,
    spot). Handles UDiFF (2024-07+) and legacy bhavcopy schemas."""
    if "TckrSymb" in df.columns:                       # UDiFF
        nf = df[(df["TckrSymb"] == "NIFTY") & df["OptnTp"].isin(["CE", "PE"])].copy()
        spot = (float(nf["UndrlygPric"].dropna().iloc[0])
                if len(nf) and nf["UndrlygPric"].notna().any() else spot_fallback)
        out = pd.DataFrame({"opt_type": nf["OptnTp"], "strike": nf["StrkPric"],
                            "settle": nf["SttlmPric"], "close": nf["ClsPric"],
                            "expiry": pd.to_datetime(nf["XpryDt"])})
    else:                                              # legacy
        nf = df[(df["SYMBOL"] == "NIFTY") & (df["INSTRUMENT"] == "OPTIDX")].copy()
        spot = spot_fallback
        out = pd.DataFrame({"opt_type": nf["OPTION_TYP"], "strike": nf["STRIKE_PR"],
                            "settle": nf["SETTLE_PR"], "close": nf["CLOSE"],
                            "expiry": pd.to_datetime(nf["EXPIRY_DT"], format="mixed")})
    return out, spot


def atm_iv_for_day(df_raw: pd.DataFrame, vix: float, trad_dt: pd.Timestamp,
                   spot_fallback: float) -> list[dict]:
    rows = []
    nf, spot = normalize(df_raw, spot_fallback)
    if nf.empty or not spot or np.isnan(spot):
        return rows
    for xp, grp in nf.groupby("expiry"):
        xp = pd.Timestamp(xp)
        dte = (xp.normalize() - trad_dt.normalize()).days
        if dte < 1 or dte > 60:                      # EOD: skip 0DTE (intrinsic)
            continue
        t = dte / MIN_PER_YEAR
        atm_k = grp.iloc[(grp["strike"] - spot).abs().argsort()].iloc[0]["strike"]
        leg = {}
        for typ in ("CE", "PE"):
            row = grp[(grp["strike"] == atm_k) & (grp["opt_type"] == typ)]
            if row.empty:
                continue
            px = float(row["settle"].iloc[0])
            if not px or px <= 0:
                px = float(row["close"].iloc[0])
            iv = implied_vol(px, spot, float(atm_k), t, RISK_FREE_RATE,
                             DIVIDEND_YIELD, typ == "CE")
            if not np.isnan(iv):
                leg[typ] = iv
        if leg:
            atm_iv = np.mean(list(leg.values())) * 100      # to VIX units (%)
            rows.append({"date": trad_dt, "dte": dte, "spot": spot,
                         "atm_strike": float(atm_k), "atm_iv": atm_iv,
                         "vix": vix, "m": atm_iv / vix if vix else np.nan,
                         "n_legs": len(leg)})
    return rows


def main() -> None:
    files = sorted(OPT_DIR.glob("fo_*.csv"))
    if not files:
        print("no bhavcopy files yet — run download_options_bhavcopy.py bulk first")
        return
    vix = vix_daily_close()
    spot = nifty_daily_close()
    pts = []
    for f in files:
        trad_dt = pd.Timestamp(f.stem.split("_")[1])
        v = float(vix.get(trad_dt.normalize(), np.nan))
        sp = float(spot.get(trad_dt.normalize(), np.nan))
        if np.isnan(v):
            continue
        try:
            df = pd.read_csv(f)
        except Exception:  # noqa: BLE001
            continue
        pts.extend(atm_iv_for_day(df, v, trad_dt, sp))
    if not pts:
        print("no calibration points extracted")
        return
    pdf = pd.DataFrame(pts)
    pdf = pdf[(pdf["m"] > 0.3) & (pdf["m"] < 5)]              # sanity clip
    RESULTS_DIR.mkdir(exist_ok=True)
    pdf.to_csv(RESULTS_DIR / "iv_calibration_points.csv", index=False)

    # m by DTE bucket
    bins = [0, 1, 2, 3, 4, 7, 14, 31, 61]
    pdf["dte_bucket"] = pd.cut(pdf["dte"], bins=bins, labels=bins[1:])
    curve = pdf.groupby("dte_bucket", observed=True).agg(
        m_median=("m", "median"), m_mean=("m", "mean"),
        iv_median=("atm_iv", "median"), n=("m", "size")).reset_index()
    curve.to_csv(RESULTS_DIR / "iv_multiplier_curve.csv", index=False)

    print(f"calibration points: {len(pdf)} from {pdf['date'].nunique()} days "
          f"({pdf['date'].min().date()}..{pdf['date'].max().date()})")
    print("\nm = ATM IV / India VIX, by DTE bucket:")
    print(curve.to_string(index=False))

    # log-linear extrapolation of m vs DTE to DTE->0 using DTE<=7 points
    short = pdf[pdf["dte"] <= 7]
    if len(short) > 20:
        x = np.log(short["dte"].to_numpy())
        y = short["m"].to_numpy()
        b, a = np.polyfit(x, y, 1)                            # m ~ a + b*ln(dte)
        m0 = a + b * np.log(0.5)                              # ~0.5 trading-day proxy for 09:20 entry
        m1 = a + b * np.log(1)
        print(f"\nlog-fit m(DTE) = {a:.3f} {b:+.3f}*ln(DTE)")
        print(f"  m(DTE=1) ~ {m1:.2f}   extrapolated m(0DTE,~0.25d) ~ {m0:.2f}")
        verdict = ("LIKELY VIABLE" if m0 >= 1.5 else
                   "MARGINAL" if m0 >= 1.3 else "UNLIKELY")
        print(f"\nVERDICT vs S3 break-even m=1.5: 0DTE edge is {verdict} "
              f"(extrapolated m0={m0:.2f})")
    print(f"\nsaved -> {RESULTS_DIR / 'iv_multiplier_curve.csv'}")


if __name__ == "__main__":
    main()
