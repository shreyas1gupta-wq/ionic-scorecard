"""Angel One SmartAPI: (A) fetch historical intraday option candles for
currently-tradable NFO contracts, and (B) record live ATM option quotes during
the paper month. Both need YOUR Angel creds (set as env vars) — no creds are
stored in code.

Why: confirms the real 09:20 ATM straddle premium / IV multiplier m(0DTE) — the
project's #1 open input (currently extrapolated to ~0.96 from EOD bhavcopy).

Setup (one-time):
  pip install smartapi-python pyotp logzero websocket-client
  setx ANGEL_API_KEY  "...";  setx ANGEL_CLIENT "...";
  setx ANGEL_PIN "...";       setx ANGEL_TOTP_SECRET "..."   (base32 from Angel)

Usage:
  python data/angel_fetch_options.py hist  NIFTY16JUN2625000CE 2026-06-12 2026-06-16
  python data/angel_fetch_options.py record NIFTY 2026-06-16   # live ATM straddle logger

Limits: getCandleData serves history only for contracts in the live master
(current + next few expiries); EXPIRED-series intraday is not available — for a
full historical 0DTE dataset, run `record` on expiry mornings going forward.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402

MASTER = RAW_DIR / "options" / "angel_nfo_nifty.csv"
OUTDIR = RAW_DIR / "options" / "angel_intraday"


def _login():
    import pyotp
    from SmartApi import SmartConnect  # smartapi-python
    api_key = os.environ["ANGEL_API_KEY"]
    obj = SmartConnect(api_key=api_key)
    totp = pyotp.TOTP(os.environ["ANGEL_TOTP_SECRET"]).now()
    obj.generateSession(os.environ["ANGEL_CLIENT"], os.environ["ANGEL_PIN"], totp)
    return obj


def _token_for(symbol: str) -> str:
    m = pd.read_csv(MASTER)
    row = m[m["symbol"] == symbol]
    if row.empty:
        raise SystemExit(f"{symbol} not in master {MASTER} (run angel_scripmaster.py; "
                         "contract may be expired/not yet listed)")
    return str(row.iloc[0]["token"])


def hist(symbol: str, frm: str, to: str) -> None:
    obj = _login()
    token = _token_for(symbol)
    p = {"exchange": "NFO", "symboltoken": token, "interval": "ONE_MINUTE",
         "fromdate": f"{frm} 09:15", "todate": f"{to} 15:30"}
    data = obj.getCandleData(p)["data"]
    df = pd.DataFrame(data, columns=["dt", "open", "high", "low", "close", "volume"])
    OUTDIR.mkdir(parents=True, exist_ok=True)
    f = OUTDIR / f"{symbol}.csv"
    df.to_csv(f, index=False)
    print(f"{symbol}: {len(df)} candles -> {f}")


def record(name: str, expiry_str: str, poll_sec: int = 30) -> None:
    """Poll the ATM CE+PE LTP through an expiry session; append to a CSV.
    Run from ~09:16; pick ATM from the index LTP each poll (rolls with spot)."""
    obj = _login()
    m = pd.read_csv(MASTER)
    m = m[(m["name"] == name) & (m["expiry"].astype(str).str.upper()
          == expiry_str.replace("-", "").upper().lstrip("0"))]
    # caller should pass expiry in master's format, e.g. 16JUN2026
    if m.empty:
        m = pd.read_csv(MASTER)
        m = m[(m["name"] == name)]
        m = m[m["expiry_dt"] == pd.Timestamp(expiry_str)]
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = OUTDIR / f"record_{name}_{expiry_str}.csv"
    idx_token = "26000" if name == "NIFTY" else ("26009" if name == "BANKNIFTY" else "26037")
    rows = []
    while pd.Timestamp.now().time() < pd.Timestamp("15:20").time():
        try:
            ltp = obj.ltpData("NSE", f"{name} 50" if name == "NIFTY" else name, idx_token)
            spot = float(ltp["data"]["ltp"])
            atm = round(spot / 50) * 50
            for typ in ("CE", "PE"):
                r = m[(m["strike"] == atm) & (m["symbol"].str.endswith(typ))]
                if r.empty:
                    continue
                tok = str(r.iloc[0]["token"]); sym = r.iloc[0]["symbol"]
                q = obj.ltpData("NFO", sym, tok)
                rows.append({"ts": pd.Timestamp.now(), "spot": spot, "atm": atm,
                             "type": typ, "ltp": float(q["data"]["ltp"])})
            pd.DataFrame(rows).to_csv(out, index=False)
        except Exception as exc:  # noqa: BLE001
            print(f"poll err: {str(exc)[:120]}")
        time.sleep(poll_sec)
    print(f"recorded {len(rows)} quotes -> {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
    elif sys.argv[1] == "hist":
        hist(sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1] == "record":
        record(sys.argv[2], sys.argv[3])
