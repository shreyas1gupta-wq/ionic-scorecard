"""
135_spike_overshoot_measure.py -- Vikram Shah, 2026-07-30.

STEP 2 of the Principal's SPIKE_OVERSHOOT_SELL mandate (his own trading observation):
MEASURE whether 0.20-0.40 delta NIFTY weekly options overshoot fair value by ~3-10 pts
after a sudden move, BEFORE any P&L simulation. This is the cheap, highest-value number
in the whole mandate -- if it doesn't exist in the data, the trade idea is dead.

Spec: SPIKE_OVERSHOOT_SELL_20260730/PRE_REGISTRATION.md (written BEFORE this ran).
Self-contained, argument-free. Loops the whole option chain (261 expiries) -> queued per
BACKTEST_QUEUE_20260730 architecture, not run directly. Cache-clears every expiry
(chain.load_expiry is @lru_cache(maxsize=64), ~40MB/expiry -- a prior job segfaulted
(rc 0xC0000005) from letting this cache grow on a ~2GB-free machine).

Writes to SPIKE_OVERSHOOT_SELL_20260730/: events_raw.csv (event list for 140 to reuse),
overshoot_measurements.csv (event x strike rows -- the core dataset), MEASUREMENT_SUMMARY.md.
"""
from __future__ import annotations

import datetime as dt
import gc
import sys
import time
import traceback
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402  (read-only legacy, reused not edited)

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SPIKE_OVERSHOOT_SELL_20260730"
OUT.mkdir(parents=True, exist_ok=True)
LOG: list[str] = []


def log(msg):
    print(msg, flush=True)
    LOG.append(str(msg))


t_start = time.time()
R = 0.065  # [ASSUMPTION] flat risk-free proxy, stated loudly, not fitted/varied.
LOT = 75
STEP = 50  # NIFTY strike step
COOLDOWN_MIN = 30
TRAILING_DAYS = 20
CRISIS_DATES = {"2021-11-26", "2022-02-24", "2024-06-04"}


# ============================================================== vectorized Black-Scholes
# py_vollib_vectorized is broken on this stack (options-python-libs skill) -- hand-vectorize.
def bs_price_vec(is_call, S, K, T, r, sigma):
    S = np.asarray(S, float); K = np.asarray(K, float)
    T = np.maximum(np.asarray(T, float), 1e-6)
    sigma = np.maximum(np.asarray(sigma, float), 1e-4)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    put = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return np.where(is_call, call, put)


def bs_delta_vec(is_call, S, K, T, r, sigma):
    S = np.asarray(S, float); K = np.asarray(K, float)
    T = np.maximum(np.asarray(T, float), 1e-6)
    sigma = np.maximum(np.asarray(sigma, float), 1e-4)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return np.where(is_call, norm.cdf(d1), norm.cdf(d1) - 1)


def bs_iv_vec(price, is_call, S, K, T, r, n_iter=60):
    price = np.asarray(price, float); S = np.asarray(S, float); K = np.asarray(K, float)
    T = np.maximum(np.asarray(T, float), 1e-6)
    sigma = np.full_like(price, 0.20, dtype=float)
    for _ in range(n_iter):
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        vega = S * norm.pdf(d1) * np.sqrt(T)
        model = bs_price_vec(is_call, S, K, T, r, sigma)
        vega_safe = np.where(vega < 1e-8, 1e-8, vega)
        step = np.clip((model - price) / vega_safe, -0.5, 0.5)
        sigma = np.clip(sigma - step, 0.01, 3.0)
    return sigma


# ============================================================== phase 1: spot + triggers
log("[phase1] loading spot index + building triggers")
idx = chain.load_index()
idx = idx[idx.index.time >= dt.time(9, 15)].copy()   # landmine #2: drop pre-open auction
idx["day"] = idx.index.date

def per_day_returns(g):
    c = g["close"]
    g = g.copy()
    g["ret1"] = np.log(c / c.shift(1))
    g["ret5"] = np.log(c / c.shift(5))
    g["ret15"] = np.log(c / c.shift(15))
    g["rv30"] = g["ret1"].rolling(30, min_periods=10).std()
    return g

idx = idx.groupby("day", group_keys=False).apply(per_day_returns)
idx["day"] = idx.index.date  # defensive: some pandas groupby.apply paths drop the grouping col

daily_vol15 = idx.groupby("day")["ret15"].std()
daily_vol5 = idx.groupby("day")["ret5"].std()
days_sorted = sorted(daily_vol15.index)
trailing_sigma15 = daily_vol15.reindex(days_sorted).rolling(TRAILING_DAYS, min_periods=TRAILING_DAYS).mean().shift(1)
trailing_sigma5 = daily_vol5.reindex(days_sorted).rolling(TRAILING_DAYS, min_periods=TRAILING_DAYS).mean().shift(1)
idx["sigma15"] = idx["day"].map(trailing_sigma15)
idx["sigma5"] = idx["day"].map(trailing_sigma5)
idx["z15"] = idx["ret15"] / idx["sigma15"]
idx["z5"] = idx["ret5"] / idx["sigma5"]

# Trigger B: intraday-vol (rv30) top-decile vs trailing 20-day pooled distribution (causal)
daily_rv30 = {d: idx.loc[idx["day"] == d, "rv30"].dropna().to_numpy() for d in days_sorted}
thresh90: dict = {}
window: deque = deque(maxlen=TRAILING_DAYS)
for d in days_sorted:
    if len(window) >= TRAILING_DAYS:
        pooled = np.concatenate(list(window)) if window else np.array([])
        thresh90[d] = np.nanpercentile(pooled, 90) if pooled.size else np.nan
    else:
        thresh90[d] = np.nan
    window.append(daily_rv30[d])
idx["rv30_thresh90"] = idx["day"].map(thresh90)
idx["triggerB"] = idx["rv30"] >= idx["rv30_thresh90"]

for thr in (1.5, 2.0, 2.5):
    idx[f"triggerA_{thr}"] = idx["z15"].abs() >= thr

idx["triggerA_primary"] = idx["triggerA_2.0"]
idx["any_trigger"] = idx["triggerA_primary"] | idx["triggerB"]
n_candidates = int(idx["any_trigger"].sum())
log(f"[phase1] candidate trigger bars (pre-cooldown): {n_candidates} "
    f"(A2.0={int(idx['triggerA_primary'].sum())}, B={int(idx['triggerB'].sum())})")

# cooldown per day
events = []
for d, sub in idx[idx["any_trigger"]].groupby("day"):
    last_t = None
    for t in sub.index:
        if last_t is None or (t - last_t) >= pd.Timedelta(minutes=COOLDOWN_MIN):
            row = idx.loc[t]
            events.append({
                "t0": t, "day": d, "S0": row["close"],
                "z15": row["z15"], "z5": row["z5"], "rv30": row["rv30"],
                "trigA": bool(row["triggerA_primary"]), "trigB": bool(row["triggerB"]),
                "trigA_1.5": bool(row["triggerA_1.5"]), "trigA_2.5": bool(row["triggerA_2.5"]),
                "direction": "up" if row["ret15"] > 0 else "down",
            })
            last_t = t

ev_df = pd.DataFrame(events)
log(f"[phase1] events after {COOLDOWN_MIN}-min cooldown: {len(ev_df)}")

# map each event to its nearest expiry (0-7 DTE)
mapping, exps = chain.build_expiry_index()
def nearest_exp(day):
    e = chain.nearest_expiry(day, min_dte=0, max_dte=7)
    return e

ev_df["expiry"] = ev_df["day"].apply(nearest_exp)
ev_df = ev_df.dropna(subset=["expiry"]).reset_index(drop=True)
ev_df["dte"] = ev_df.apply(lambda r: (r["expiry"] - r["day"]).days, axis=1)
ev_df["dte_band"] = np.where(ev_df["dte"] <= 1, "0-1DTE", "2-7DTE")
ev_df["era"] = np.where(pd.to_datetime(ev_df["day"]) < pd.Timestamp("2024-10-01"), "pre_Oct2024", "post_Oct2024")
ev_df["split"] = np.where(pd.to_datetime(ev_df["day"]) < pd.Timestamp("2026-01-01"), "build", "held_out_2026")
ev_df["event_id"] = np.arange(len(ev_df))
ev_df.to_csv(OUT / "events_raw.csv", index=False)
log(f"[phase1] events_raw.csv written: {len(ev_df)} events, "
    f"{ev_df['expiry'].nunique()} distinct target expiries")

spot_close_lookup = idx["close"].to_dict()  # O(1) lookups for decay-horizon spot (was O(n) scan)

# ============================================================== phase 2: per-expiry overshoot measurement
log("[phase2] measuring overshoot per event, batched by expiry (memory-safe)")
rows_out = []
by_exp = ev_df.groupby("expiry")
n_exp_done = 0
for exp, sub in by_exp:
    try:
        df = chain.load_expiry(exp)
        wide_close = df.pivot_table(index="t", columns=["option_type", "strike"], values="close")
        wide_vol = df.pivot_table(index="t", columns=["option_type", "strike"], values="volume")
        wide_close_m = wide_close.where(wide_vol > 0)
        expiry_dt = pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30)
        idx_times = wide_close_m.index

        for _, ev in sub.iterrows():
            t0 = ev["t0"]
            if t0 not in idx_times:
                continue
            S0 = ev["S0"]
            pre_win = wide_close_m.loc[(idx_times >= t0 - pd.Timedelta(minutes=10)) &
                                        (idx_times < t0)]
            if len(pre_win) < 3:
                continue
            pre_mean = pre_win.mean(skipna=True).dropna()
            if pre_mean.empty:
                continue
            obs_row = wide_close_m.loc[t0].dropna()
            common = pre_mean.index.intersection(obs_row.index)
            if len(common) == 0:
                continue
            strikes = common.get_level_values("strike").to_numpy(dtype=float)
            types = common.get_level_values("option_type").to_numpy()
            is_call = (types == "CE")
            T0 = (expiry_dt - t0) / pd.Timedelta(days=365)
            if T0 <= 0:
                continue
            Tarr = np.full(len(strikes), T0)
            Sarr = np.full(len(strikes), S0)
            pre_px = pre_mean.loc[common].to_numpy(dtype=float)
            obs_px = obs_row.loc[common].to_numpy(dtype=float)
            # guard degenerate/zero prices before IV solve
            valid = (pre_px > 0.05) & (obs_px > 0.05)
            if valid.sum() == 0:
                continue
            iv_pre = bs_iv_vec(pre_px[valid], is_call[valid], Sarr[valid], strikes[valid], Tarr[valid], R)
            iv_obs = bs_iv_vec(obs_px[valid], is_call[valid], Sarr[valid], strikes[valid], Tarr[valid], R)
            delta_obs = bs_delta_vec(is_call[valid], Sarr[valid], strikes[valid], Tarr[valid], R, iv_obs)
            band = (np.abs(delta_obs) >= 0.20) & (np.abs(delta_obs) <= 0.40)
            if band.sum() == 0:
                continue
            fair_val = bs_price_vec(is_call[valid][band], Sarr[valid][band], strikes[valid][band],
                                     Tarr[valid][band], R, iv_pre[band])
            excess = obs_px[valid][band] - fair_val

            # decay snapshots
            decay = {}
            for horizon in (5, 15, 30, 60):
                th = t0 + pd.Timedelta(minutes=horizon)
                if th in idx_times:
                    row_h = wide_close_m.loc[th].reindex(common[valid][band])
                    Th = (expiry_dt - th) / pd.Timedelta(days=365)
                    if Th > 0:
                        Sh = spot_close_lookup.get(th, np.nan)
                        if not np.isnan(Sh):
                            fv_h = bs_price_vec(is_call[valid][band], np.full(band.sum(), Sh),
                                                 strikes[valid][band], np.full(band.sum(), Th),
                                                 R, iv_pre[band])
                            excess_h = row_h.to_numpy(dtype=float) - fv_h
                            decay[f"excess_t{horizon}"] = excess_h
                        else:
                            decay[f"excess_t{horizon}"] = np.full(band.sum(), np.nan)
                    else:
                        decay[f"excess_t{horizon}"] = np.full(band.sum(), np.nan)
                else:
                    decay[f"excess_t{horizon}"] = np.full(band.sum(), np.nan)

            same_side = np.where(ev["direction"] == "up", is_call[valid][band], ~is_call[valid][band])

            for i in range(band.sum()):
                r = {
                    "event_id": ev["event_id"], "t0": t0, "day": ev["day"], "expiry": exp,
                    "dte": ev["dte"], "dte_band": ev["dte_band"], "era": ev["era"],
                    "split": ev["split"], "trigA": ev["trigA"], "trigB": ev["trigB"],
                    "z15": ev["z15"], "rv30": ev["rv30"], "direction": ev["direction"],
                    "option_type": types[valid][band][i], "strike": strikes[valid][band][i],
                    "S0": S0, "iv_pre": iv_pre[band][i], "iv_obs": iv_obs[band][i],
                    "delta_obs": delta_obs[band][i], "excess_pts": excess[i],
                    "same_side_as_move": bool(same_side[i]),
                    "fair_value_t0": fair_val[i], "obs_price_t0": obs_px[valid][band][i],
                }
                for horizon in (5, 15, 30, 60):
                    r[f"excess_t{horizon}"] = decay[f"excess_t{horizon}"][i]
                rows_out.append(r)
        n_exp_done += 1
    except Exception as e:
        log(f"[phase2] expiry {exp} FAILED: {e}")
        log(traceback.format_exc(limit=3))
    finally:
        chain.load_expiry.cache_clear()
        gc.collect()
    if n_exp_done % 25 == 0:
        log(f"[phase2] ...{n_exp_done}/{len(by_exp)} expiries done, {len(rows_out)} rows so far, "
            f"{time.time()-t_start:.0f}s elapsed")

meas = pd.DataFrame(rows_out)
meas.to_csv(OUT / "overshoot_measurements.csv", index=False)
log(f"[phase2] DONE. overshoot_measurements.csv: {len(meas)} (event,strike) rows from "
    f"{n_exp_done} expiries, {time.time()-t_start:.0f}s total")

# ============================================================== phase 3: summary
def pct_stats(s):
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0, "mean": np.nan, "median": np.nan, "p90": np.nan}
    return {"n": len(s), "mean": s.mean(), "median": s.median(), "p90": s.quantile(0.90)}

lines = ["# MEASUREMENT SUMMARY -- Spike Overshoot (Step 2, cheap-first)", ""]
lines.append(f"Total qualifying (event,strike) observations: {len(meas)}")
lines.append(f"Distinct spike events with >=1 band member: {meas['event_id'].nunique() if len(meas) else 0}")
lines.append("")
lines.append("## Overshoot excess (points) at t0, by delta bucket x DTE band")
if len(meas):
    meas["delta_bucket"] = np.where(meas["delta_obs"].abs() < 0.30, "0.20-0.30", "0.30-0.40")
    for dte_b in ["0-1DTE", "2-7DTE"]:
        for db in ["0.20-0.30", "0.30-0.40"]:
            sub = meas[(meas["dte_band"] == dte_b) & (meas["delta_bucket"] == db)]["excess_pts"]
            st = pct_stats(sub)
            lines.append(f"- {dte_b} / delta {db}: n={st['n']} mean={st['mean']:.2f} "
                         f"median={st['median']:.2f} p90={st['p90']:.2f}" if st["n"] else
                         f"- {dte_b} / delta {db}: n=0")
    lines.append("")
    lines.append("## By move-size bucket (|z15|)")
    for lo, hi, name in [(1.5, 2.0, "1.5-2.0σ"), (2.0, 2.5, "2.0-2.5σ"), (2.5, 99, "2.5σ+")]:
        sub = meas[(meas["z15"].abs() >= lo) & (meas["z15"].abs() < hi)]["excess_pts"]
        st = pct_stats(sub)
        lines.append(f"- {name}: n={st['n']} mean={st['mean']:.2f} median={st['median']:.2f} "
                     f"p90={st['p90']:.2f}" if st["n"] else f"- {name}: n=0")
    lines.append("")
    lines.append("## Same-side-as-move vs opposite side")
    for flag, name in [(True, "same side (mechanism expected here)"), (False, "opposite side (diagnostic)")]:
        sub = meas[meas["same_side_as_move"] == flag]["excess_pts"]
        st = pct_stats(sub)
        lines.append(f"- {name}: n={st['n']} mean={st['mean']:.2f} median={st['median']:.2f}" if st["n"] else
                     f"- {name}: n=0")
    lines.append("")
    lines.append("## Trigger definition comparison (which detects overshoot better)")
    for flag, name in [("trigA", "Sigma-move (A)"), ("trigB", "Intraday-vol-percentile (B)")]:
        sub = meas[meas[flag] == True]["excess_pts"]
        st = pct_stats(sub)
        lines.append(f"- {name}: n={st['n']} mean={st['mean']:.2f} median={st['median']:.2f}" if st["n"] else
                     f"- {name}: n=0")
    lines.append("")
    lines.append("## Pre/post Oct-2024 (headline)")
    for era in ["pre_Oct2024", "post_Oct2024"]:
        sub = meas[meas["era"] == era]["excess_pts"]
        st = pct_stats(sub)
        lines.append(f"- {era}: n={st['n']} mean={st['mean']:.2f} median={st['median']:.2f}" if st["n"] else
                     f"- {era}: n=0")
    lines.append("")
    lines.append("## Decay of excess after t0 (mean excess remaining at each horizon, same band)")
    for horizon in (5, 15, 30, 60):
        col = f"excess_t{horizon}"
        st = pct_stats(meas[col])
        lines.append(f"- t0+{horizon}min: n={st['n']} mean={st['mean']:.2f}" if st["n"] else
                     f"- t0+{horizon}min: n=0")
    lines.append("")
    lines.append("## IV vs observed (sanity: did IV itself pop)")
    lines.append(f"mean iv_pre={meas['iv_pre'].mean():.4f}  mean iv_obs={meas['iv_obs'].mean():.4f}  "
                 f"mean(iv_obs-iv_pre)={ (meas['iv_obs']-meas['iv_pre']).mean():.4f}")
else:
    lines.append("NO QUALIFYING OBSERVATIONS -- see log for failures.")

lines.append("")
lines.append("## Run log tail")
lines.extend(LOG[-40:])
(OUT / "MEASUREMENT_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
log("[phase3] MEASUREMENT_SUMMARY.md written. 135 complete.")
