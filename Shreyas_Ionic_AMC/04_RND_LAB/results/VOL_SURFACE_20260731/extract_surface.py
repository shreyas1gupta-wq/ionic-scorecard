"""Extract a daily EOD (15:15-15:30 last-print) options-surface panel from the 1-min NIFTY option
chain: ATM IV, 25-delta call/put IV (skew), plus a same-contract next-day price mark for a simple
1-day-hold structure P&L check. RAM-safe per fleet chainlock protocol (grab-extract-release,
cache_clear+gc after every expiry). Checkpoints every 15 expiries so a kill loses <15 files of work.

Output: surface_panel_raw.parquet  (rows = one per (day, expiry) with dte>=1)
Each row also carries next-day same-strike marks (ce_atm_px_entry/exit, px25c_entry/exit, ...)
used later for a close-to-close (no intraday path -> pathsafe not required) 1-day-hold check.
"""
from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
sys.path.insert(0, BASE + r"\intraday_options_strategy\buying")
sys.path.insert(0, BASE + r"\Shreyas_Ionic_AMC\04_RND_LAB\lib")
sys.path.insert(0, str(Path(__file__).parent))

import chain                                   # noqa: E402
from chainlock import chain_slot, free_ram_gb  # noqa: E402
from vol_lib import iv_of, delta_of            # noqa: E402

OUT = Path(__file__).parent
CKPT = OUT / "surface_panel_raw.parquet"
PROGRESS = OUT / "extract_progress.json"
LOG = OUT / "extract_log.txt"

STRIKE_BAND = 800
WIN_LO = pd.Timestamp("15:15").time()
WIN_HI = pd.Timestamp("15:30").time()


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def eod_snapshot(df, day):
    sub = df[(df["trading_day"] == day) & (df["t"].dt.time >= WIN_LO) & (df["t"].dt.time < WIN_HI)]
    if sub.empty:
        return None
    sub = sub.sort_values("t").groupby(["strike", "option_type"], as_index=False).last()
    return sub[["t", "strike", "option_type", "close"]]


def iv_delta_frame(snap, typ, spot, T):
    s = snap[snap["option_type"] == typ].copy()
    if s.empty:
        return s
    s["iv"] = [iv_of(px, spot, float(k), T, typ) for px, k in zip(s["close"], s["strike"])]
    s = s[s["iv"].notna() & (s["iv"] > 0.02) & (s["iv"] < 3.0)]
    if s.empty:
        return s
    s["delta"] = [delta_of(spot, float(k), T, iv, typ) for k, iv in zip(s["strike"], s["iv"])]
    return s.sort_values("strike").reset_index(drop=True)


def interp_delta(frame, target):
    if frame is None or len(frame) < 2:
        return None
    d = frame["delta"].to_numpy()
    for i in range(len(d) - 1):
        hi, lo = d[i], d[i + 1]
        if (hi >= target >= lo) or (hi <= target <= lo):
            w = 0.0 if hi == lo else (hi - target) / (hi - lo)
            strike = frame["strike"].iloc[i] + w * (frame["strike"].iloc[i + 1] - frame["strike"].iloc[i])
            iv = frame["iv"].iloc[i] + w * (frame["iv"].iloc[i + 1] - frame["iv"].iloc[i])
            px = frame["close"].iloc[i] + w * (frame["close"].iloc[i + 1] - frame["close"].iloc[i])
            return float(strike), float(iv), float(px)
    return None


def build_index_daily():
    spot = pd.read_parquet(BASE + r"\intraday_options_strategy\datasets\processed\nifty_1min.parquet")
    mask = spot.index.time >= WIN_LO
    eod = spot[mask].copy()
    eod["day"] = eod.index.normalize()
    last_eod = eod.groupby("day")["close"].last()
    return {d.date().isoformat(): float(v) for d, v in last_eod.items()}


def process_expiry(exp, index_daily):
    with chain_slot("vol-surface", min_free_gb=1.0):
        df = chain.load_expiry(exp)
        days = sorted(df["trading_day"].unique())
        recs = []
        strike_choice = {}
        for day in days:
            d_date = pd.Timestamp(day).date()
            dte = (exp - d_date).days
            if dte < 0:
                continue
            snap = eod_snapshot(df, day)
            if snap is None:
                continue
            spot = index_daily.get(day)
            if spot is None or not np.isfinite(spot):
                continue
            t_sig = snap["t"].max()
            expiry_ts = pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30)
            T = (expiry_ts - t_sig).total_seconds() / (365 * 86400)
            if dte < 1 or T <= 0.4 / 365:
                continue
            lo, hi = spot - STRIKE_BAND, spot + STRIKE_BAND
            snap_band = snap[(snap["strike"] >= lo) & (snap["strike"] <= hi)]
            ce = iv_delta_frame(snap_band, "CE", spot, T)
            pe = iv_delta_frame(snap_band, "PE", spot, T)
            atm_k = round(spot / 50) * 50
            ce_atm = ce[ce["strike"] == atm_k] if len(ce) else ce
            pe_atm = pe[pe["strike"] == atm_k] if len(pe) else pe
            iv_atm_ce = float(ce_atm["iv"].iloc[0]) if len(ce_atm) else np.nan
            iv_atm_pe = float(pe_atm["iv"].iloc[0]) if len(pe_atm) else np.nan
            atm_iv = np.nanmean([iv_atm_ce, iv_atm_pe]) if not (np.isnan(iv_atm_ce) and np.isnan(iv_atm_pe)) else np.nan
            r25c = interp_delta(ce, 0.25)
            r25p = interp_delta(pe, -0.25)
            # REAL (listed, 50-pt spaced) strike nearest the interpolated 25-delta point, so the
            # structure P&L test trades an actual tradeable strike, not a fictional interpolated one.
            k25c_real = round(r25c[0] / 50) * 50 if r25c else np.nan
            k25p_real = round(r25p[0] / 50) * 50 if r25p else np.nan
            ce25_real = ce[ce["strike"] == k25c_real] if (r25c and len(ce)) else None
            pe25_real = pe[pe["strike"] == k25p_real] if (r25p and len(pe)) else None
            px25c_real = float(ce25_real["close"].iloc[0]) if (ce25_real is not None and len(ce25_real)) else np.nan
            px25p_real = float(pe25_real["close"].iloc[0]) if (pe25_real is not None and len(pe25_real)) else np.nan
            rec = dict(
                day=day, expiry=exp.isoformat(), dte=dte, T=T, spot=spot,
                atm_strike=float(atm_k), atm_iv=atm_iv, iv_atm_ce=iv_atm_ce, iv_atm_pe=iv_atm_pe,
                k25c=(r25c[0] if r25c else np.nan), iv25c=(r25c[1] if r25c else np.nan), px25c=(r25c[2] if r25c else np.nan),
                k25p=(r25p[0] if r25p else np.nan), iv25p=(r25p[1] if r25p else np.nan), px25p=(r25p[2] if r25p else np.nan),
                ce_atm_px_entry=(float(ce_atm["close"].iloc[0]) if len(ce_atm) else np.nan),
                pe_atm_px_entry=(float(pe_atm["close"].iloc[0]) if len(pe_atm) else np.nan),
                k25c_real=k25c_real, k25p_real=k25p_real,
                px25c_real_entry=px25c_real, px25p_real_entry=px25p_real,
            )
            recs.append(rec)
            strike_choice[day] = dict(
                atm_k=atm_k,
                k25c_real=k25c_real, k25p_real=k25p_real,
            )
        # next-day same-strike marks (close-to-close, no intraday path -> pathsafe N/A)
        for i, day in enumerate(days[:-1]):
            if day not in strike_choice:
                continue
            nxt = days[i + 1]
            ch = strike_choice[day]
            snap_n = eod_snapshot(df, nxt)
            if snap_n is None:
                continue

            def px_at(strike, typ, _sn=snap_n):
                if strike is None or (isinstance(strike, float) and np.isnan(strike)):
                    return np.nan
                row = _sn[(_sn["strike"] == strike) & (_sn["option_type"] == typ)]
                return float(row["close"].iloc[0]) if len(row) else np.nan

            for rec in recs:
                if rec["day"] == day:
                    rec["next_day"] = nxt
                    rec["ce_atm_px_exit"] = px_at(ch["atm_k"], "CE")
                    rec["pe_atm_px_exit"] = px_at(ch["atm_k"], "PE")
                    rec["px25c_real_exit"] = px_at(ch["k25c_real"], "CE")
                    rec["px25p_real_exit"] = px_at(ch["k25p_real"], "PE")
        del df
    chain.load_expiry.cache_clear()
    gc.collect()
    return recs


def main():
    _, exps = chain.build_expiry_index()
    index_daily = build_index_daily()
    log(f"n expiries={len(exps)}  n index_daily={len(index_daily)}  free_ram={free_ram_gb():.2f}GB")

    done = set()
    all_recs = []
    if PROGRESS.exists():
        prog = json.loads(PROGRESS.read_text())
        done = set(prog.get("done", []))
        if CKPT.exists():
            all_recs = pd.read_parquet(CKPT).to_dict("records")
        log(f"resuming: {len(done)} expiries already done, {len(all_recs)} rows loaded")

    todo = [e for e in exps if e.isoformat() not in done]
    for i, exp in enumerate(todo):
        try:
            recs = process_expiry(exp, index_daily)
            all_recs.extend(recs)
            done.add(exp.isoformat())
        except Exception as ex:
            log(f"FAILED {exp}: {ex}")
            done.add(exp.isoformat())  # don't retry a poison file forever
        if (i + 1) % 15 == 0 or i == len(todo) - 1:
            pd.DataFrame(all_recs).to_parquet(CKPT)
            PROGRESS.write_text(json.dumps({"done": sorted(done)}))
            log(f"checkpoint: {i+1}/{len(todo)} done this run, {len(all_recs)} total rows, "
                f"free_ram={free_ram_gb():.2f}GB")

    pd.DataFrame(all_recs).to_parquet(CKPT)
    PROGRESS.write_text(json.dumps({"done": sorted(done)}))
    log(f"DONE. {len(all_recs)} total rows across {len(done)} expiries.")


if __name__ == "__main__":
    main()
