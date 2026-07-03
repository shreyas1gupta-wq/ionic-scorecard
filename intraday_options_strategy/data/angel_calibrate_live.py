"""Measure the REAL intraday ATM-IV/VIX multiplier from live Angel option
candles for the current NIFTY weekly — validates the extrapolated m(DTE).

Creds via env vars only (never written to disk). Spot + India VIX come from
openchart (IDX, no auth); the option candles come from Angel getCandleData.
For each session and the 09:20 bar we compute the ATM straddle premium, back
out implied vol (TRADING-TIME, consistent with the engine), and m = IV/VIX.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import truststore
truststore.inject_into_ssl()

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DIVIDEND_YIELD, RAW_DIR, RESULTS_DIR, RISK_FREE_RATE  # noqa: E402
from options.bs_pricing import implied_vol  # noqa: E402

MASTER = RAW_DIR / "options" / "angel_nfo_nifty.csv"
TRADING_MIN_YEAR = 252 * 375


def login():
    import pyotp
    from SmartApi import SmartConnect
    obj = SmartConnect(api_key=os.environ["ANGEL_API_KEY"])
    totp = pyotp.TOTP(os.environ["ANGEL_TOTP_SECRET"]).now()
    s = obj.generateSession(os.environ["ANGEL_CLIENT"], os.environ["ANGEL_PIN"], totp)
    if not s.get("status"):
        raise SystemExit(f"login failed: {s}")
    print("login OK")
    return obj


def oc_index(nse, name: str, days: int = 12) -> pd.DataFrame:
    end = pd.Timestamp.now(); start = end - pd.Timedelta(days=days)
    df = nse.historical(name, "IDX", start.to_pydatetime(), end.to_pydatetime(), "1m")
    if df is None or not len(df):
        return pd.DataFrame()
    df = df.rename(columns=str.lower)
    if "timestamp" in df.columns:
        df = df.set_index(pd.to_datetime(df["timestamp"]))
    df.index = pd.DatetimeIndex(df.index).tz_localize(None)
    return df


def candles(obj, token: str, frm: str, to: str, exchange: str = "NFO") -> pd.DataFrame:
    p = {"exchange": exchange, "symboltoken": str(token), "interval": "ONE_MINUTE",
         "fromdate": f"{frm} 09:15", "todate": f"{to} 15:30"}
    d = obj.getCandleData(p).get("data", [])
    df = pd.DataFrame(d, columns=["dt", "o", "h", "l", "c", "v"])
    if len(df):
        df["dt"] = pd.to_datetime(df["dt"]).dt.tz_localize(None)
        df = df.set_index("dt")
    return df


# Angel NSE index tokens
IDX_TOKENS = {"NIFTY 50": "99926000", "INDIA VIX": "99926017"}


def angel_index(obj, name: str, frm: str, to: str) -> pd.DataFrame:
    for tok in ([IDX_TOKENS.get(name)] + (["99926037"] if name == "INDIA VIX" else [])):
        if not tok:
            continue
        try:
            df = candles(obj, tok, frm, to, exchange="NSE")
            if len(df):
                return df
        except Exception as exc:  # noqa: BLE001
            print(f"  index {name} tok {tok} err: {str(exc)[:80]}")
    return pd.DataFrame()


def main() -> None:
    obj = login()
    frm = (pd.Timestamp.now() - pd.Timedelta(days=12)).strftime("%Y-%m-%d")
    to = pd.Timestamp.now().strftime("%Y-%m-%d")

    nifty = angel_index(obj, "NIFTY 50", frm, to)
    vix = angel_index(obj, "INDIA VIX", frm, to)
    spot_now = float(nifty["c"].iloc[-1]) if len(nifty) else 24000.0
    print(f"spot~{spot_now:.0f}; nifty bars={len(nifty)} vix bars={len(vix)}")

    m = pd.read_csv(MASTER, parse_dates=["expiry_dt"])
    m = m[m["name"] == "NIFTY"]
    expiry = m["expiry_dt"].min()                       # nearest weekly
    atm = round(spot_now / 50) * 50
    leg = {}
    for typ in ("CE", "PE"):
        r = m[(m["expiry_dt"] == expiry) & (np.isclose(m["strike"], atm))
              & (m["symbol"].str.endswith(typ))]
        if not r.empty:
            leg[typ] = str(r.iloc[0]["token"])
    print(f"nearest expiry {expiry.date()}, ATM {atm}, tokens={leg}")
    if len(leg) < 2:
        raise SystemExit("ATM CE/PE not found in master for nearest expiry")

    ce = candles(obj, leg["CE"], frm, to)
    pe = candles(obj, leg["PE"], frm, to)
    print(f"CE candles={len(ce)} PE candles={len(pe)}")
    if not len(ce) or not len(pe):
        raise SystemExit("no option candles returned (market closed / lookback limit)")

    rows = []
    days = sorted(set(ce.index.normalize()) & set(pe.index.normalize()))
    for d in days:
        t0 = d + pd.Timedelta("09:20:00")
        if t0 not in ce.index or t0 not in pe.index:
            continue
        straddle = float(ce.loc[t0, "c"]) + float(pe.loc[t0, "c"])
        # real spot from parity if index feed missing: S ~ K + (CE-PE)
        sp = float(nifty["c"].get(t0, np.nan)) if len(nifty) else np.nan
        if np.isnan(sp):
            sp = atm + (float(ce.loc[t0, "c"]) - float(pe.loc[t0, "c"]))
        vx = float(vix["c"].get(t0, np.nan)) if len(vix) else np.nan
        dte_min = max((expiry + pd.Timedelta("15:30:00") - t0).total_seconds() / 60, 1)
        # trading-time years remaining (intraday → ~full trading mins)
        full_days = (expiry.normalize() - d).days
        rem_today = max((d + pd.Timedelta("15:30:00") - t0).total_seconds() / 60, 0)
        tmin = rem_today + 375 * full_days
        t_yr = max(tmin, 1) / TRADING_MIN_YEAR
        iv_ce = implied_vol(float(ce.loc[t0, "c"]), sp, atm, t_yr, RISK_FREE_RATE, DIVIDEND_YIELD, True)
        iv_pe = implied_vol(float(pe.loc[t0, "c"]), sp, atm, t_yr, RISK_FREE_RATE, DIVIDEND_YIELD, False)
        iv = np.nanmean([iv_ce, iv_pe]) * 100
        rows.append({"date": d.date(), "dte_days": full_days, "spot": round(sp, 1),
                     "atm": atm, "straddle": round(straddle, 1), "iv": round(iv, 2),
                     "vix": round(vx, 2) if not np.isnan(vx) else np.nan,
                     "m": round(iv / vx, 3) if vx and not np.isnan(vx) else np.nan})
    out = pd.DataFrame(rows)
    RESULTS_DIR.mkdir(exist_ok=True)
    out.to_csv(RESULTS_DIR / "live_iv_calibration.csv", index=False)
    print("\n=== REAL 09:20 ATM straddle, implied vol, and m vs VIX ===")
    print(out.to_string(index=False))
    if len(out) and out["m"].notna().any():
        print(f"\nmean m (real intraday) = {out['m'].mean():.2f} "
              f"vs engine default_iv_mult(DTE=1)=0.90, (3)=0.80")
    print(f"saved -> {RESULTS_DIR / 'live_iv_calibration.csv'}")


if __name__ == "__main__":
    main()
