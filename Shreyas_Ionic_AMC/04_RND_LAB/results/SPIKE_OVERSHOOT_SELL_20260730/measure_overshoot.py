"""THE DECISIVE MEASUREMENT: is a 0.2-0.4 delta option genuinely 3-10 POINTS RICH after a spike?

Principal's observation: *"0.2-0.4 delta options get too much inflated if a sudden large move come,
going over few points like 3-10 points over the [fair] value, and when mean reversion kicks in we get
10-30 point pullback + this extra 3-10 points."*

If the overshoot is not in the data, the whole trade dies here and cheaply. Everything downstream
(delta-neutral vs unhedged, resting-limit fill rates, tails) only matters if this number is real.

METHOD — deliberately avoids relying on an absolute IV level:
  For each spike event at t0 (from events_raw.csv, already built):
    1. Take the option's OWN implied vol at t_pre = t0 - PRE_MIN minutes (before the spike).
    2. Reprice that same option at t0 using the PRE-SPIKE IV but the POST-SPIKE spot and time.
       -> that is "fair value if only spot moved and vol had not been bid up".
    3. OVERSHOOT (points) = actual traded price at t0  -  that repriced fair value.
  So the benchmark is the option's own pre-spike vol, not a model or a smoothed surface. Any excess is
  the vol/panic inflation the Principal describes.
  Also recorded: IV_post - IV_pre (vol points), and the decay of the excess over the following 15/30/60
  minutes -> that decay IS the profit a seller would capture.

MEMORY DISCIPLINE (two prior jobs segfaulted, rc 0xC0000005): chain.load_expiry is
@lru_cache(maxsize=64) and each expiry frame is ~40MB => up to 2.5GB. Machine has ~2GB free.
So: process ONE expiry at a time, slice only the needed strike/time rows, then cache_clear() + gc.
Never hold two expiry frames.
"""
from __future__ import annotations

import gc
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

warnings.filterwarnings("ignore")
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                   r"\NIFTY 500\intraday_options_strategy\buying")
import chain  # noqa: E402

OUT = Path(__file__).parent
PRE_MIN = 30            # how far before the spike to read "pre-spike" vol
R_RATE = 0.065
STEP = 50
DELTA_LO, DELTA_HI = 0.20, 0.40


def bs(S, K, T, sig, typ):
    if T <= 0 or sig <= 0:
        return max(0.0, (S - K) if typ == "CE" else (K - S))
    d1 = (np.log(S / K) + (R_RATE + 0.5 * sig * sig) * T) / (sig * np.sqrt(T))
    d2 = d1 - sig * np.sqrt(T)
    if typ == "CE":
        return S * norm.cdf(d1) - K * np.exp(-R_RATE * T) * norm.cdf(d2)
    return K * np.exp(-R_RATE * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def bs_delta(S, K, T, sig, typ):
    if T <= 0 or sig <= 0:
        return 1.0 if (typ == "CE" and S > K) else (1.0 if (typ == "PE" and S < K) else 0.0)
    d1 = (np.log(S / K) + (R_RATE + 0.5 * sig * sig) * T) / (sig * np.sqrt(T))
    return norm.cdf(d1) if typ == "CE" else abs(norm.cdf(d1) - 1.0)


def iv(px, S, K, T, typ):
    if px <= 0.05 or T <= 0:
        return np.nan
    intr = max(0.0, (S - K) if typ == "CE" else (K - S))
    if px < intr - 0.5:
        return np.nan
    try:
        return brentq(lambda s: bs(S, K, T, s, typ) - px, 1e-4, 5.0, maxiter=60, xtol=1e-5)
    except Exception:
        return np.nan


_IDX = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
        r"\NIFTY 500\intraday_options_strategy\datasets\raw\hf_index_options_1m\index\NIFTY.parquet")
_sp = pd.read_parquet(_IDX, columns=["timestamp", "close"])
_sp["t"] = pd.to_datetime(_sp["timestamp"]).dt.tz_localize(None)
SPOT = _sp.drop_duplicates("t").set_index("t")["close"].sort_index()
del _sp
gc.collect()
print(f"[spot] {len(SPOT):,} bars for pre-spike spot lookup", flush=True)

ev = pd.read_csv(OUT / "events_raw.csv")
ev["t0"] = pd.to_datetime(ev["t0"])
ev["expiry"] = pd.to_datetime(ev["expiry"]).dt.date
print(f"[events] {len(ev):,} spike events | expiries {ev.expiry.nunique()}", flush=True)

rows = []
for i, (exp, grp) in enumerate(ev.groupby("expiry"), 1):
    try:
        df = chain.load_expiry(exp)
    except Exception as e:
        chain.load_expiry.cache_clear(); gc.collect(); continue
    df = df[df["volume"] > 0]
    for _, e in grp.iterrows():
        t0, S0, d = e["t0"], float(e["S0"]), (1 if str(e["direction"]).lower().startswith("up") else -1)
        # a spike UP (d=+1 by the detector's convention) inflates CALLS; a spike DOWN inflates PUTS
        typ = "CE" if d > 0 else "PE"
        T0 = max((pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30) - t0).total_seconds()
                 / (365.25 * 24 * 3600), 1e-6)
        t_pre = t0 - pd.Timedelta(minutes=PRE_MIN)
        # candidate strikes in the 0.2-0.4 delta band: OTM side, 1-6 steps away
        cands = [int(round(S0 / STEP) * STEP + k * STEP * (1 if typ == "CE" else -1))
                 for k in range(1, 7)]
        sub = df[(df["option_type"] == typ) & (df["strike"].isin(cands))]
        if sub.empty:
            continue
        best = None
        for K, s in sub.groupby("strike"):
            s = s.set_index("t")[["close", "volume"]].sort_index()
            pre = s[s.index <= t_pre]
            now = s[(s.index >= t0) & (s.index <= t0 + pd.Timedelta(minutes=2))]
            if pre.empty or now.empty:
                continue
            p_pre, p_now = float(pre["close"].iloc[-1]), float(now["close"].iloc[0])
            t_pre_actual = pre.index[-1]
            S_pre_proxy = S0  # spot at t0; pre-spike spot differs, handled via IV below
            Tpre = max((pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30) - t_pre_actual
                        ).total_seconds() / (365.25 * 24 * 3600), 1e-6)
            # BUGFIX 1: invert the PRE-spike price against the PRE-spike SPOT, not S0.
            # Using S0 understated iv_pre and therefore INFLATED the measured overshoot.
            _pp = SPOT.loc[:t_pre_actual]
            if _pp.empty:
                continue
            S_pre = float(_pp.iloc[-1])
            iv_pre = iv(p_pre, S_pre, K, Tpre, typ)
            iv_now = iv(p_now, S0, K, T0, typ)
            if not (np.isfinite(iv_pre) and np.isfinite(iv_now)):
                continue
            dlt = bs_delta(S0, K, T0, iv_now, typ)
            if not (DELTA_LO <= dlt <= DELTA_HI):
                continue
            fair = bs(S0, K, T0, iv_pre, typ)          # repriced at PRE-spike vol, POST-spike spot/time
            over = p_now - fair
            # decay of the excess
            # BUGFIX 2: a raw price change conflates VOL decay with DELTA P&L from continued spot
            # movement. Measure the EXCESS-over-fair at each horizon, repricing fair at the spot
            # prevailing THEN, still at iv_pre. The FALL in excess is what a delta-hedged seller of
            # the overshoot actually captures.
            fwd = {}
            for mm in (15, 30, 60):
                w = s[(s.index > t0) & (s.index <= t0 + pd.Timedelta(minutes=mm))]
                if len(w) == 0:
                    fwd[f"exc_{mm}"] = np.nan
                    continue
                t_t = w.index[-1]
                px_t = float(w["close"].iloc[-1])
                _st = SPOT.loc[:t_t]
                if _st.empty:
                    fwd[f"exc_{mm}"] = np.nan
                    continue
                S_t = float(_st.iloc[-1])
                T_t = max((pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30) - t_t
                           ).total_seconds() / (365.25 * 24 * 3600), 1e-6)
                fwd[f"exc_{mm}"] = px_t - bs(S_t, K, T_t, iv_pre, typ)
                # also store the RAW price and spot so the UNHEDGED seller P&L can be computed:
                # unhedged P&L (seller) = px_now - px_t   (captures vol crush AND directional reversion)
                fwd[f"px_{mm}"] = px_t
                fwd[f"S_{mm}"] = S_t
            cand = dict(event_id=e["event_id"], t0=t0, expiry=str(exp), dte=e["dte"],
                        dte_band=e["dte_band"], era=e["era"], split=e["split"], typ=typ,
                        strike=int(K), S0=S0, delta=round(dlt, 3),
                        iv_pre=round(100 * iv_pre, 2), iv_now=round(100 * iv_now, 2),
                        iv_jump=round(100 * (iv_now - iv_pre), 2),
                        px_now=round(p_now, 2), fair=round(fair, 2), overshoot=round(over, 2),
                        vol_now=float(now["volume"].iloc[0]), **fwd)
            if best is None or abs(dlt - 0.30) < abs(best["delta"] - 0.30):
                best = cand
        if best:
            rows.append(best)
    chain.load_expiry.cache_clear(); gc.collect()
    if i % 25 == 0:
        print(f"  [{i}] expiry {exp}  rows so far {len(rows):,}", flush=True)

r = pd.DataFrame(rows)
r.to_csv(OUT / "overshoot_measured.csv", index=False)
print(f"\n[measured] {len(r):,} events with a usable 0.2-0.4 delta option\n", flush=True)
if r.empty:
    print("NO USABLE EVENTS -> cannot confirm or refute the observation"); sys.exit(0)

print("=" * 104)
print("OVERSHOOT (points rich vs the option's OWN pre-spike vol, repriced at post-spike spot)")
print("=" * 104)
q = r["overshoot"].describe(percentiles=[.1, .25, .5, .75, .9])
print(q.round(2).to_string())
print(f"\n  share of events with overshoot > 0 : {100*(r.overshoot>0).mean():.1f}%")
print(f"  share with overshoot >= 3 pts      : {100*(r.overshoot>=3).mean():.1f}%")
print(f"  share with overshoot 3-10 pts      : {100*r.overshoot.between(3,10).mean():.1f}%")
print(f"  mean IV jump (vol pts)             : {r.iv_jump.mean():.2f}")

for by in ("dte_band", "era", "split"):
    if by in r:
        print(f"\n--- overshoot by {by} ---")
        g = r.groupby(by)["overshoot"].agg(n="size", mean="mean", median="median",
                                          p90=lambda s: s.quantile(.9))
        print(g.round(2).to_string())

print("\n--- DECAY OF THE EXCESS (delta-neutral capture; excess = px - fair@iv_pre repriced at S_t) ---")
print(f"  excess at t0 (= the overshoot)          {r.overshoot.mean():>7.2f} pts")
for mm in (15, 30, 60):
    col = f"exc_{mm}"
    if col in r:
        d = r.dropna(subset=[col])
        cap = (d["overshoot"] - d[col]).mean()
        pctc = 100 * cap / max(d.overshoot.mean(), 1e-9)
        print(f"  +{mm:>2}min: residual {d[col].mean():>7.2f} pts | CAPTURED {cap:>7.2f} pts "
              f"({pctc:>5.1f}% of overshoot)  n={len(d)}")
if "exc_30" in r and "era" in r:
    print("\n  captured at +30min BY ERA (does it still work post-Oct-2024?):")
    for era, g in r.dropna(subset=["exc_30"]).groupby("era"):
        print(f"    {era:<14} {float((g.overshoot - g.exc_30).mean()):>7.2f} pts   n={len(g)}")
if "exc_30" in r and "split" in r:
    print("\n  captured at +30min BY SPLIT (2026 is held out):")
    for sp, g in r.dropna(subset=["exc_30"]).groupby("split"):
        print(f"    {sp:<14} {float((g.overshoot - g.exc_30).mean()):>7.2f} pts   n={len(g)}")
print("\nwrote overshoot_measured.csv")
