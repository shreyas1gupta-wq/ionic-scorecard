"""LIVE FF signal check (Tara Singh) -- redo of Task 2 using the REAL Angel SmartAPI
connection (same creds/pattern as C:\\Users\\Shreyas.1Gupta\\AppData\\Local\\angel_capture\\
daily_capture.py), not the stale cached files.

Two things:
  (A) TODAY snapshot: pull live spot + near-month(M1)/back-month(M2) ATM CE quotes (LTP+OI+vol)
      for the 53/54-name FF universe, compute iv1/iv2/FF exactly as ff_v3_causal.py does, report
      whether FF>=0.25 fires TODAY for any name.
  (B) STRUCTURAL TEST: for a few names, pull ONE_DAY candles for the BACK-month ATM CE over the
      full 80-day window (same window daily_capture.py requests) and see how far back non-zero
      volume actually starts -- tests whether the 30-session lookback the signal needs is a
      live-access problem or a genuine market-inactivity (structural) problem.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import truststore
truststore.inject_into_ssl()
import pyotp
from SmartApi import SmartConnect

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy"))
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
from options.bs_pricing import implied_vol  # noqa: E402
from forward_factor_strategy import forward_vol  # noqa: E402

CAP_DIR = Path(r"C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture")
CREDS = json.loads((CAP_DIR / "creds.json").read_text())
SCRIP_CACHE = CAP_DIR / "scrip_master.json"

R_, Q_ = 0.065, 0.0
FF_MIN = 0.25
OUT = ROOT / "results/S-03/20260705_resurrection"


def login():
    obj = SmartConnect(api_key=CREDS["api_key"])
    totp = pyotp.TOTP(CREDS["totp_secret"]).now()
    s = obj.generateSession(CREDS["client_id"], CREDS["pin"], totp)
    if not s.get("status"):
        raise SystemExit(f"login failed: {s}")
    print("[login] OK", flush=True)
    return obj


def load_scrip():
    # reuse cached scrip master (daily_capture.py refreshes it each run) -- avoid re-downloading
    scrip = json.loads(SCRIP_CACHE.read_bytes())
    print(f"[scrip] loaded cached master, {len(scrip):,} instruments, mtime="
          f"{pd.Timestamp(SCRIP_CACHE.stat().st_mtime, unit='s')}", flush=True)
    return scrip


def main():
    obj = login()
    scrip = load_scrip()

    causal = pd.read_csv(OUT / "causal_per_trade.csv")
    universe = sorted(causal["sym"].unique())
    print(f"[universe] {len(universe)} FF large-cap names", flush=True)

    eq = {x["name"]: x for x in scrip if x.get("exch_seg") == "NSE"
          and str(x.get("symbol", "")).endswith("-EQ") and x.get("name") in universe}
    opt = [x for x in scrip if x.get("exch_seg") == "NFO" and x.get("instrumenttype") == "OPTSTK"
           and x.get("name") in universe and x.get("symbol", "").endswith("CE")]
    print(f"[scrip] eq tokens found for {len(eq)}/{len(universe)}; CE contracts in universe: {len(opt)}", flush=True)

    import datetime as dt

    def ed(s):
        try:
            return dt.datetime.strptime(s, "%d%b%Y").date()
        except Exception:
            return None

    now = dt.datetime.now()
    exps_all = sorted({e for e in (ed(x["expiry"]) for x in opt) if e and e >= now.date()})
    front_exp, back_exp = exps_all[0], exps_all[1]
    front_str = front_exp.strftime("%d%b%Y").upper()
    back_str = back_exp.strftime("%d%b%Y").upper()
    print(f"[expiries] front(M1)={front_exp} back(M2)={back_exp}", flush=True)

    # ---- bulk spot ----
    missing_eq = [s for s in universe if s not in eq]
    if missing_eq:
        print(f"[warn] no equity token for: {missing_eq}", flush=True)
    names = list(eq.keys())
    toks = [eq[n]["token"] for n in names]
    spot = {}
    for i in range(0, len(toks), 45):
        r = obj.getMarketData("LTP", {"NSE": toks[i:i + 45]})
        for f in r.get("data", {}).get("fetched", []):
            spot[str(f["symbolToken"])] = f.get("ltp")
        time.sleep(1.2)
    spotmap = {n: spot.get(str(eq[n]["token"])) for n in names}
    print(f"[spot] got {sum(v is not None for v in spotmap.values())}/{len(names)}", flush=True)

    # ---- pick ATM strike per name per expiry ----
    def nearest_strike(nm, exp_str, s):
        rows = [x for x in opt if x["name"] == nm and x["expiry"] == exp_str]
        if not rows or s is None:
            return None
        best = min(rows, key=lambda x: abs(float(x["strike"]) / 100 - s))
        return best

    front_pick, back_pick = {}, {}
    for nm in names:
        s = spotmap.get(nm)
        if s is None:
            continue
        f = nearest_strike(nm, front_str, s)
        b = nearest_strike(nm, back_str, s)
        if f is not None:
            front_pick[nm] = f
        if b is not None:
            back_pick[nm] = b
    print(f"[strikes] front picked {len(front_pick)}, back picked {len(back_pick)}", flush=True)

    # ---- bulk FULL quotes (LTP+OI+volume) for front & back ATM CE tokens ----
    all_tok = list({v["token"] for v in front_pick.values()} | {v["token"] for v in back_pick.values()})
    full = {}
    for i in range(0, len(all_tok), 45):
        r = obj.getMarketData("FULL", {"NFO": all_tok[i:i + 45]})
        for f in r.get("data", {}).get("fetched", []):
            full[str(f["symbolToken"])] = f
        time.sleep(1.2)
    print(f"[quotes] FULL mode returned {len(full)}/{len(all_tok)} tokens", flush=True)
    # inspect field names once
    if full:
        sample = next(iter(full.values()))
        print(f"[quotes] sample fields: {sorted(sample.keys())}", flush=True)

    T1 = max((front_exp - now.date()).days / 365.0, 1e-4)
    T2 = max((back_exp - now.date()).days / 365.0, 1e-4)
    recs = []
    for nm in names:
        s = spotmap.get(nm)
        f = front_pick.get(nm)
        b = back_pick.get(nm)
        if s is None or f is None or b is None:
            continue
        qf = full.get(str(f["token"]))
        qb = full.get(str(b["token"]))
        if qf is None or qb is None:
            continue
        px1 = qf.get("ltp")
        px2 = qb.get("ltp")
        if not px1 or not px2:
            continue
        iv1 = implied_vol(float(px1), s, float(f["strike"]) / 100, T1, R_, Q_, True)
        iv2 = implied_vol(float(px2), s, float(b["strike"]) / 100, T2, R_, Q_, True)
        fv = forward_vol(iv1, T1, iv2, T2) if (iv1 and iv2 and np.isfinite(iv1) and np.isfinite(iv2)) else None
        ff = (iv1 - fv) / fv if (fv and fv > 0) else None
        recs.append(dict(sym=nm, spot=s, front_strike=float(f["strike"]) / 100, front_ltp=px1,
                          front_oi=qf.get("opnInterest"), front_vol=qf.get("tradeVolume"),
                          back_strike=float(b["strike"]) / 100, back_ltp=px2,
                          back_oi=qb.get("opnInterest"), back_vol=qb.get("tradeVolume"),
                          iv1=iv1, iv2=iv2, fv=fv, ff=ff))

    df = pd.DataFrame(recs).sort_values("ff", ascending=False, na_position="last")
    df.to_csv(OUT / "live_ff_snapshot_20260707.csv", index=False)
    print(f"\n[checkpoint] wrote {OUT / 'live_ff_snapshot_20260707.csv'} rows={len(df)}", flush=True)
    print(df.to_string(index=False), flush=True)
    fires = df[df["ff"] >= FF_MIN]
    print(f"\n[VERDICT-A] names with FF>={FF_MIN} TODAY: {len(fires)}", flush=True)
    if len(fires):
        print(fires.to_string(index=False), flush=True)

    # ---- (B) structural test: back-month ATM CE historical depth, 3 sample names ----
    print("\n===== (B) STRUCTURAL TEST: back-month (M2) historical candle depth =====", flush=True)
    test_names = [n for n in ["ABB", "RELIANCE", "TCS"] if n in back_pick] or list(back_pick.keys())[:3]
    day_from = (now - dt.timedelta(days=80)).strftime("%Y-%m-%d 09:15")
    to_s = now.strftime("%Y-%m-%d %H:%M")
    for nm in test_names:
        b = back_pick[nm]
        try:
            r = obj.getCandleData({"exchange": "NFO", "symboltoken": str(b["token"]),
                                    "interval": "ONE_DAY", "fromdate": day_from, "todate": to_s})
            data = r.get("data") or []
        except Exception as exc:  # noqa: BLE001
            print(f"  {nm} M2 ATM ({b['symbol']}): ERROR {str(exc)[:150]}", flush=True)
            time.sleep(1.2)
            continue
        if not data:
            print(f"  {nm} M2 ATM ({b['symbol']}): 0 candles returned for {day_from}->{to_s}", flush=True)
        else:
            cdf = pd.DataFrame(data, columns=["dt", "o", "h", "l", "c", "v"])
            cdf["dt"] = pd.to_datetime(cdf["dt"])
            nonzero = cdf[cdf["v"] > 0]
            print(f"  {nm} M2 ATM ({b['symbol']}): {len(cdf)} candles, range "
                  f"{cdf['dt'].min().date()}..{cdf['dt'].max().date()}; "
                  f"{len(nonzero)} with volume>0, earliest nonzero-vol day = "
                  f"{nonzero['dt'].min().date() if len(nonzero) else 'NONE'}", flush=True)
        time.sleep(1.2)

    print("\n[done]", flush=True)


if __name__ == "__main__":
    main()
