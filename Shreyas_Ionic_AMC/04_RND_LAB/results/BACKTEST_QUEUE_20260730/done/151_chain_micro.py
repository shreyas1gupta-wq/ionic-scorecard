r"""Stage-1 chain-microstructure signal measurement (Ishaan Gupta, ML expert, 2026-07-30).
Pre-registration: ../../CHAIN_MICRO_20260730/PRE_REGISTRATION.md  (written BEFORE this ran).
Mandate: find an intraday DIRECTIONAL signal from the OPTION CHAIN ITSELF (not a price transform)
for naked long option buying. This script is STAGE 1 ONLY: does each candidate predict the signed
forward NIFTY move, beating a block-permuted placebo? No P&L here.

Self-contained / argument-free from the queue runner's perspective. Internally it is BOTH the
orchestrator (no argv) and, when called with --worker, a short-lived child process that handles one
batch of expiries and then exits -- this is the fix for the memory-fragmentation segfaults that hit
3 jobs earlier today inside chain.load_expiry's drop_duplicates(). See PRE_REGISTRATION.md.

Writes all outputs to: Shreyas_Ionic_AMC/04_RND_LAB/results/CHAIN_MICRO_20260730/
"""
from __future__ import annotations

import gc
import json
import subprocess
import sys
import warnings
from bisect import bisect_left
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.optimize import brentq
from scipy.stats import norm

warnings.filterwarnings("ignore")

PY = r"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe"
BASE_OPT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                 r"\NIFTY 500\intraday_options_strategy\datasets\raw\hf_index_options_1m")
NIFTY_OPT_DIR = BASE_OPT / "options" / "NIFTY"
NIFTY_INDEX = BASE_OPT / "index" / "NIFTY.parquet"
OUT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
           r"\Shreyas_Ionic_AMC\04_RND_LAB\results\CHAIN_MICRO_20260730")
OUT.mkdir(parents=True, exist_ok=True)
TMP = OUT / "_batches"
TMP.mkdir(exist_ok=True)

CORRUPT = {"2023-06-29"}
MIN_FILE_BYTES = 500_000
STEP = 50
R_RATE = 0.065
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}       # scheduled-event days, session standard
BATCH_SIZE = 15
HORIZONS = (15, 30, 60)

# ---------------------------------------------------------------- BS helpers (same formula as
# ---------------------------------------------------------------- measure_overshoot.py; copied, not
# ---------------------------------------------------------------- imported -- that script is a
# ---------------------------------------------------------------- top-level pipeline w/ no __main__
# ---------------------------------------------------------------- guard and would re-run itself.

def bs(S, K, T, sig, typ):
    if T <= 0 or sig <= 0:
        return max(0.0, (S - K) if typ == "CE" else (K - S))
    d1 = (np.log(S / K) + (R_RATE + 0.5 * sig * sig) * T) / (sig * np.sqrt(T))
    d2 = d1 - sig * np.sqrt(T)
    if typ == "CE":
        return S * norm.cdf(d1) - K * np.exp(-R_RATE * T) * norm.cdf(d2)
    return K * np.exp(-R_RATE * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def iv(px, S, K, T, typ):
    if px is None or not np.isfinite(px) or px <= 0.05 or T <= 0:
        return np.nan
    intr = max(0.0, (S - K) if typ == "CE" else (K - S))
    if px < intr - 0.5:
        return np.nan
    try:
        return brentq(lambda s: bs(S, K, T, s, typ) - px, 1e-4, 5.0, maxiter=60, xtol=1e-5)
    except Exception:
        return np.nan


# ---------------------------------------------------------------- shared expiry index (filenames
# ---------------------------------------------------------------- only, no data read -- cheap)

def build_expiry_index():
    import datetime as dt
    mapping, skipped = {}, []
    for p in NIFTY_OPT_DIR.glob("*.parquet"):
        name = p.stem
        if name in CORRUPT:
            skipped.append((name, "corrupt")); continue
        if p.stat().st_size < MIN_FILE_BYTES:
            skipped.append((name, "stub")); continue
        try:
            mapping[dt.datetime.strptime(name, "%Y-%m-%d").date()] = p
        except ValueError:
            skipped.append((name, "bad name"))
    exps = sorted(mapping)
    return mapping, exps, skipped


# ================================================================== WORKER MODE
def worker_main(spec_path: str, out_prefix: str):
    spec = json.loads(Path(spec_path).read_text())
    mapping, exps, _ = build_expiry_index()
    exp_by_str = {str(e): mapping[e] for e in exps}

    sp = pq.read_table(NIFTY_INDEX, columns=["timestamp", "close"]).to_pandas()
    sp["t"] = pd.to_datetime(sp["timestamp"]).dt.tz_localize(None)
    sp = sp.drop_duplicates("t").set_index("t").sort_index()
    sp = sp[sp.index.time >= pd.Timestamp("09:15").time()]
    spot = sp["close"]
    del sp
    gc.collect()

    min_rows, iv_rows, oi_rows = [], [], []
    cols = ["timestamp", "trading_day", "strike", "option_type", "close", "high", "low",
            "volume", "open_interest"]

    for exp_str, days in spec:
        path = exp_by_str.get(exp_str)
        if path is None:
            continue
        exp_close = pd.Timestamp(exp_str) + pd.Timedelta(hours=15, minutes=30)
        try:
            df = pq.read_table(path, columns=cols).to_pandas()
        except Exception as e:
            print(f"[worker] READ FAIL {exp_str}: {e}", flush=True)
            continue
        df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
        df = df[df["trading_day"].isin(days)]
        if df.empty:
            del df; gc.collect(); continue
        df = df.drop(columns=["timestamp"])
        key = ["t", "strike", "option_type", "trading_day"]
        g = (df.groupby(key, sort=False, as_index=False)
               .agg(close=("close", "mean"), high=("high", "mean"), low=("low", "mean"),
                    volume=("volume", "mean"), oi=("open_interest", "mean")))
        del df
        g["spot"] = g["t"].map(spot)
        g = g.dropna(subset=["spot"])
        if g.empty:
            del g; gc.collect(); continue
        g["side"] = np.where(g["strike"] > g["spot"], "above", "below")
        g["moneyness"] = g["strike"] - g["spot"]
        g["day"] = g["trading_day"]

        # ---- signals 1 & 2: per-minute volume pivots (vectorized over the whole slice) ----
        vol_type = g.pivot_table(index="t", columns="option_type", values="volume",
                                  aggfunc="sum", fill_value=0.0)
        vol_side = g.pivot_table(index="t", columns="side", values="volume",
                                  aggfunc="sum", fill_value=0.0)
        for c in ("CE", "PE"):
            if c not in vol_type.columns:
                vol_type[c] = 0.0
        for c in ("above", "below"):
            if c not in vol_side.columns:
                vol_side[c] = 0.0

        # ---- signal 4: volume-weighted aggressor proxy near ATM (<=3 steps) ----
        near = g[(g["moneyness"].abs() <= 3 * STEP) & (g["volume"] > 0) & (g["high"] > g["low"])].copy()
        aggr_wide = pd.DataFrame(index=vol_type.index, columns=["CE", "PE"], dtype=float)
        if not near.empty:
            near["aggr"] = (near["close"] - near["low"]) / (near["high"] - near["low"])
            near["wv"] = near["aggr"] * near["volume"]
            agg = near.groupby(["t", "option_type"]).agg(wv=("wv", "sum"), v=("volume", "sum"))
            agg_ratio = (agg["wv"] / agg["v"]).unstack("option_type")
            aggr_wide = agg_ratio.reindex(index=vol_type.index, columns=["CE", "PE"])

        mf = pd.DataFrame(index=vol_type.index)
        mf["CE_vol"] = vol_type["CE"]; mf["PE_vol"] = vol_type["PE"]
        mf["vol_above"] = vol_side["above"]; mf["vol_below"] = vol_side["below"]
        mf["CE_aggr"] = aggr_wide["CE"]; mf["PE_aggr"] = aggr_wide["PE"]
        mf["day"] = g.drop_duplicates("t").set_index("t")["day"].reindex(mf.index)
        mf["expiry"] = exp_str
        min_rows.append(mf.reset_index())

        # ---- signal 5 (IV wing-skew jump) & signal 6 (OI eod) : per-day loop (cheap, <=14 days) ----
        day_list = sorted(g["day"].unique())
        prev_ce_oi = prev_pe_oi = None
        prev_day_for_oi = None
        for day in day_list:
            dgrp = g[g["day"] == day].sort_values("t")
            if dgrp.empty:
                continue
            # -- signal 6: EOD OI by type --
            last_t = dgrp["t"].max()
            eod = dgrp[dgrp["t"] == last_t]
            ce_oi = float(eod.loc[eod.option_type == "CE", "oi"].sum())
            pe_oi = float(eod.loc[eod.option_type == "PE", "oi"].sum())
            if prev_day_for_oi is not None:
                oi_rows.append(dict(day=day, prev_day=prev_day_for_oi, expiry=exp_str,
                                     ce_oi=ce_oi, pe_oi=pe_oi,
                                     ce_oi_chg=ce_oi - prev_ce_oi, pe_oi_chg=pe_oi - prev_pe_oi))
            prev_ce_oi, prev_pe_oi, prev_day_for_oi = ce_oi, pe_oi, day

            # -- signal 5: 15-min IV snapshot grid --
            t0d, t1d = dgrp["t"].min(), dgrp["t"].max()
            snaps = pd.date_range(t0d.ceil("15min"), t1d, freq="15min")
            if len(snaps) < 2:
                continue
            series_by_key = {kk: sub.set_index("t")["close"].sort_index()
                              for kk, sub in dgrp.groupby(["strike", "option_type"], sort=False)}

            def px_at(K, typ, snap):
                s = series_by_key.get((K, typ))
                if s is None or s.empty:
                    return np.nan
                pos = s.index.searchsorted(snap, side="right") - 1
                if pos < 0:
                    return np.nan
                return float(s.iloc[pos])

            prev_wing = np.nan
            for snap in snaps:
                s_upto = spot.loc[:snap]
                if s_upto.empty:
                    continue
                S = float(s_upto.iloc[-1])
                base = round(S / STEP) * STEP
                Kc3, Kp3 = base + 3 * STEP, base - 3 * STEP
                T = max((exp_close - snap).total_seconds() / (365.25 * 24 * 3600), 1e-6)
                pxc3, pxp3 = px_at(Kc3, "CE", snap), px_at(Kp3, "PE", snap)
                ivc3, ivp3 = iv(pxc3, S, Kc3, T, "CE"), iv(pxp3, S, Kp3, T, "PE")
                wing = (ivc3 - ivp3) if (np.isfinite(ivc3) and np.isfinite(ivp3)) else np.nan
                if np.isfinite(wing) and np.isfinite(prev_wing):
                    iv_rows.append(dict(t=snap, day=day, expiry=exp_str,
                                         iv_wing_jump=wing - prev_wing))
                if np.isfinite(wing):
                    prev_wing = wing
        del g, vol_type, vol_side, near, aggr_wide, mf
        gc.collect()

    pd.concat(min_rows, ignore_index=True).to_parquet(f"{out_prefix}_min.parquet") if min_rows else None
    pd.DataFrame(iv_rows).to_parquet(f"{out_prefix}_iv.parquet") if iv_rows else None
    pd.DataFrame(oi_rows).to_parquet(f"{out_prefix}_oi.parquet") if oi_rows else None
    print(f"[worker] done: {len(min_rows)} expiry-slices, {len(iv_rows)} iv rows, "
          f"{len(oi_rows)} oi rows", flush=True)


# ================================================================== ORCHESTRATOR
def rolling_z(df: pd.DataFrame, col: str, day_col: str = "day") -> pd.Series:
    """Causal rolling 20-trading-day z-score, shifted 1 day (today never sees its own stats)."""
    daily = df.groupby(day_col)[col].agg(["mean", "std", "count"]).sort_index()
    m = daily["mean"].rolling(20, min_periods=5).mean().shift(1)
    s = daily["mean"].rolling(20, min_periods=5).std().shift(1)
    z_map_m = m.to_dict(); z_map_s = s.to_dict()
    dm = df[day_col].map(z_map_m); ds = df[day_col].map(z_map_s)
    z = (df[col] - dm) / ds.replace(0, np.nan)
    return z


def fwd_returns(spot: pd.Series, times: pd.Series) -> pd.DataFrame:
    out = {}
    idx = spot.index
    pos = np.searchsorted(idx.values, times.values)
    pos = np.clip(pos - 0, 0, len(idx) - 1)
    # exact/most-recent-<=  lookup for t0 itself
    pos0 = np.searchsorted(idx.values, times.values, side="right") - 1
    pos0 = np.clip(pos0, 0, len(idx) - 1)
    base_day = idx[pos0].normalize()
    for h in HORIZONS:
        target = times + pd.Timedelta(minutes=h)
        posh = np.searchsorted(idx.values, target.values, side="right") - 1
        posh = np.clip(posh, 0, len(idx) - 1)
        same_day = idx[posh].normalize() == base_day
        valid = same_day & (idx[posh].values >= target.values - np.timedelta64(2, "m"))
        r = idx[posh].to_series(index=range(len(posh))).values  # placeholder unused
        vals = spot.values[posh] - spot.values[pos0]
        vals = np.where(valid, vals, np.nan)
        out[f"fwd_{h}"] = vals
    return pd.DataFrame(out, index=times.index)


def block_permute_test(day_arr, val_arr, ret_arr, n_perm=500, seed=0):
    """Day-block permutation placebo. Pivots to (day x minute-of-day-rank) grids so a day-shuffle
    preserves each row's within-day position (kills spurious time-of-day seasonality) but breaks the
    true day-to-day link between signal and forward return."""
    tmp = pd.DataFrame({"day": day_arr, "val": val_arr, "ret": ret_arr}).dropna()
    if tmp["day"].nunique() < 30 or len(tmp) < 200:
        return np.nan, np.nan, len(tmp), tmp["day"].nunique()
    tmp["rank"] = tmp.groupby("day").cumcount()
    piv_val = tmp.pivot(index="day", columns="rank", values="val")
    piv_ret = tmp.pivot(index="day", columns="rank", values="ret")
    common_cols = piv_val.columns.intersection(piv_ret.columns)
    piv_val, piv_ret = piv_val[common_cols], piv_ret[common_cols]

    def effect(v_mat, r_mat):
        v = v_mat.values.ravel(); r = r_mat.values.ravel()
        m = np.isfinite(v) & np.isfinite(r)
        v, r = v[m], r[m]
        if len(v) < 100:
            return np.nan
        thr_hi, thr_lo = np.nanpercentile(v, 90), np.nanpercentile(v, 10)
        hi = r[v >= thr_hi]; lo = r[v <= thr_lo]
        if len(hi) < 5 or len(lo) < 5:
            return np.nan
        return float(np.nanmean(hi) - np.nanmean(lo)), len(m[m])

    obs = effect(piv_val, piv_ret)
    if obs is None or (isinstance(obs, tuple) and not np.isfinite(obs[0])):
        return np.nan, np.nan, len(tmp), tmp["day"].nunique()
    obs_eff, n_used = obs
    rng = np.random.default_rng(seed)
    days = piv_ret.index.values.copy()
    null = np.empty(n_perm)
    ret_vals = piv_ret.values
    for i in range(n_perm):
        perm = rng.permutation(len(days))
        r_shuf = pd.DataFrame(ret_vals[perm], index=piv_val.index, columns=piv_ret.columns)
        e = effect(piv_val, r_shuf)
        null[i] = e[0] if (e is not None and isinstance(e, tuple) and np.isfinite(e[0])) else np.nan
    null = null[np.isfinite(null)]
    if len(null) < 50:
        return obs_eff, np.nan, n_used, tmp["day"].nunique()
    p = float((np.abs(null) >= abs(obs_eff)).mean())
    return obs_eff, p, n_used, tmp["day"].nunique()


def orchestrator_main():
    mapping, exps, skipped = build_expiry_index()
    print(f"[orch] {len(exps)} valid expiries {exps[0]}..{exps[-1]} (skipped {len(skipped)})", flush=True)

    sp = pq.read_table(NIFTY_INDEX, columns=["timestamp", "close"]).to_pandas()
    sp["t"] = pd.to_datetime(sp["timestamp"]).dt.tz_localize(None)
    sp = sp.drop_duplicates("t").set_index("t").sort_index()
    sp = sp[sp.index.time >= pd.Timestamp("09:15").time()]
    spot_full = sp["close"]
    all_days = sorted(set(sp.index.normalize()))
    del sp
    print(f"[orch] {len(all_days)} trading days from spot index", flush=True)

    exp_to_days: dict[str, list[str]] = {}
    for d in all_days:
        d_date = d.date()
        i = bisect_left(exps, d_date)
        if i >= len(exps):
            continue
        e = exps[i]
        dte = (e - d_date).days
        if 0 <= dte <= 7:
            exp_to_days.setdefault(str(e), []).append(str(d_date))
    exp_keys = sorted(exp_to_days)
    print(f"[orch] {len(exp_keys)} expiries have >=1 assigned front-week day "
          f"({sum(len(v) for v in exp_to_days.values())} day-assignments total)", flush=True)

    batches = [exp_keys[i:i + BATCH_SIZE] for i in range(0, len(exp_keys), BATCH_SIZE)]
    min_parts, iv_parts, oi_parts = [], [], []
    for bi, batch in enumerate(batches):
        spec = [[e, exp_to_days[e]] for e in batch]
        spec_path = TMP / f"batch_{bi:03d}.json"
        spec_path.write_text(json.dumps(spec))
        out_prefix = str(TMP / f"out_{bi:03d}")
        r = subprocess.run([PY, __file__, "--worker", str(spec_path), out_prefix],
                            capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            print(f"[orch] batch {bi} FAILED rc={r.returncode}\nSTDOUT:{r.stdout[-2000:]}\n"
                  f"STDERR:{r.stderr[-2000:]}", flush=True)
        else:
            print(f"[orch] batch {bi}/{len(batches)} OK: {r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ''}",
                  flush=True)
        for tag, parts in (("min", min_parts), ("iv", iv_parts), ("oi", oi_parts)):
            p = Path(f"{out_prefix}_{tag}.parquet")
            if p.exists():
                parts.append(pd.read_parquet(p))

    min_df = pd.concat(min_parts, ignore_index=True) if min_parts else pd.DataFrame()
    iv_df = pd.concat(iv_parts, ignore_index=True) if iv_parts else pd.DataFrame()
    oi_df = pd.concat(oi_parts, ignore_index=True) if oi_parts else pd.DataFrame()
    print(f"[orch] collected: min={len(min_df):,} iv={len(iv_df):,} oi={len(oi_df):,}", flush=True)
    min_df.to_parquet(OUT / "raw_minute_features.parquet")
    iv_df.to_parquet(OUT / "raw_iv_features.parquet")
    oi_df.to_parquet(OUT / "raw_oi_features.parquet")

    # ---------------- attach split / era / scheduled-event flags, forward returns ----------------
    def tag(df, tcol="t"):
        df = df.copy()
        df["day_s"] = df["day"].astype(str)
        df["split"] = np.where(df["day_s"] >= "2026-01-01", "held_out_2026", "build")
        df["era"] = np.where(df["day_s"] >= "2024-10-01", "post_Oct2024", "pre_Oct2024")
        df = df[~df["day_s"].isin(SCH)]
        return df

    min_df = tag(min_df)
    iv_df = tag(iv_df)

    for df, tcol in ((min_df, "t"), (iv_df, "t")):
        if df.empty:
            continue
        fr = fwd_returns(spot_full, df[tcol])
        for h in HORIZONS:
            df[f"fwd_{h}"] = fr[f"fwd_{h}"].values

    # signal raw values
    if not min_df.empty:
        min_df["sig_ce_pe_imb"] = min_df["CE_vol"] - min_df["PE_vol"]
        tot = (min_df["CE_vol"] + min_df["PE_vol"]).replace(0, np.nan)
        min_df["sig_pcr_level"] = min_df["PE_vol"] / min_df["CE_vol"].replace(0, np.nan)
        min_df["sig_strike_mig"] = min_df["vol_above"] / (min_df["vol_above"] + min_df["vol_below"]).replace(0, np.nan)
        min_df["sig_aggressor"] = min_df["CE_aggr"] - min_df["PE_aggr"]
        min_df = min_df.sort_values("t")
        min_df["sig_pcr_roc"] = min_df.groupby("day_s")["sig_pcr_level"].transform(lambda s: s.diff(15))

    build_min = min_df[min_df["split"] == "build"] if not min_df.empty else min_df
    build_iv = iv_df[iv_df["split"] == "build"] if not iv_df.empty else iv_df

    results = []
    cell_defs = [
        ("CM-01/02/03", "ce_pe_vol_imbalance", build_min, "sig_ce_pe_imb"),
        ("CM-04/05/06", "strike_migration", build_min, "sig_strike_mig"),
        ("CM-07/08/09", "pcr_level", build_min, "sig_pcr_level"),
        ("CM-10/11/12", "pcr_roc", build_min, "sig_pcr_roc"),
        ("CM-13/14/15", "aggressor_proxy", build_min, "sig_aggressor"),
    ]
    for cid, name, df, col in cell_defs:
        if df is None or df.empty or col not in df:
            for h in HORIZONS:
                results.append(dict(id=f"{cid}@{h}", signal=name, horizon=h, n=0, n_days=0,
                                     effect_pts=np.nan, placebo_p=np.nan, verdict="NO DATA"))
            continue
        z = rolling_z(df, col)
        for h in HORIZONS:
            obs, p, n, nd = block_permute_test(df["day_s"].values, z.values, df[f"fwd_{h}"].values)
            verdict = ("NO DATA" if not np.isfinite(obs) else
                       "DEAD (fails placebo)" if (np.isfinite(p) and p >= 0.05) else
                       "PLACEBO-INDETERMINATE (n too small for 500 draws)" if not np.isfinite(p) else
                       "FORWARD-TEST CANDIDATE (Stage-2 eligible, |effect|>=10pt)" if abs(obs) >= 10 else
                       "UNDERPOWERED-UNRESOLVED (beats placebo, <10pt)" if abs(obs) >= 2 else
                       "DEAD (beats placebo but ~0pt, no economic content)")
            results.append(dict(id=f"{cid}@{h}", signal=name, horizon=h, n=n, n_days=nd,
                                 effect_pts=round(obs, 3) if np.isfinite(obs) else np.nan,
                                 placebo_p=round(p, 4) if np.isfinite(p) else np.nan, verdict=verdict))

    if build_iv is not None and not build_iv.empty:
        z = rolling_z(build_iv, "iv_wing_jump")
        for h in HORIZONS:
            obs, p, n, nd = block_permute_test(build_iv["day_s"].values, z.values, build_iv[f"fwd_{h}"].values)
            verdict = ("NO DATA" if not np.isfinite(obs) else
                       "DEAD (fails placebo)" if (np.isfinite(p) and p >= 0.05) else
                       "PLACEBO-INDETERMINATE (n too small for 500 draws)" if not np.isfinite(p) else
                       "FORWARD-TEST CANDIDATE (Stage-2 eligible, |effect|>=10pt)" if abs(obs) >= 10 else
                       "UNDERPOWERED-UNRESOLVED (beats placebo, <10pt)" if abs(obs) >= 2 else
                       "DEAD (beats placebo but ~0pt, no economic content)")
            results.append(dict(id=f"CM-16/17/18@{h}", signal="iv_wing_skew_jump", horizon=h,
                                 n=n, n_days=nd, effect_pts=round(obs, 3) if np.isfinite(obs) else np.nan,
                                 placebo_p=round(p, 4) if np.isfinite(p) else np.nan, verdict=verdict))
    else:
        for h in HORIZONS:
            results.append(dict(id=f"CM-16/17/18@{h}", signal="iv_wing_skew_jump", horizon=h, n=0,
                                 n_days=0, effect_pts=np.nan, placebo_p=np.nan, verdict="NO DATA"))

    # ---- signal 6: OI build/unwind, daily, vs next-day close-to-close return ----
    if not oi_df.empty:
        oi_df = oi_df.copy()
        oi_df["day_s"] = oi_df["day"].astype(str)
        oi_df = oi_df[~oi_df["day_s"].isin(SCH)]
        oi_df["sig_oi"] = oi_df["ce_oi_chg"] - oi_df["pe_oi_chg"]
        daily_close = spot_full.resample("1D").last().dropna()
        daily_close.index = daily_close.index.normalize()
        c2c = daily_close.diff().rename("c2c")
        # next-day return relative to `day` (the day the OI change was OBSERVED at EOD;
        # forward = the FOLLOWING trading day's close-to-close move)
        oi_df["day_ts"] = pd.to_datetime(oi_df["day_s"])
        uniq_days = sorted(daily_close.index)
        day_pos = {d: i for i, d in enumerate(uniq_days)}
        def next_day_ret(d):
            i = day_pos.get(d)
            if i is None or i + 1 >= len(uniq_days):
                return np.nan
            return float(c2c.iloc[i + 1]) if (i + 1) < len(c2c) else np.nan
        oi_df["fwd_1d"] = oi_df["day_ts"].map(next_day_ret)

        for tagname, sub in (("clean_2021_2024", oi_df[oi_df["day_s"] < "2025-01-01"]),
                              ("thinned_2025_2026", oi_df[oi_df["day_s"] >= "2025-01-01"])):
            sub = sub.dropna(subset=["sig_oi", "fwd_1d"])
            if len(sub) < 60:
                results.append(dict(id=f"CM-19/20:{tagname}", signal="oi_buildup_unwind", horizon="1d",
                                     n=len(sub), n_days=sub["day_s"].nunique(), effect_pts=np.nan,
                                     placebo_p=np.nan, verdict=f"NO DATA (n={len(sub)})"))
                continue
            thr_hi, thr_lo = sub["sig_oi"].quantile(0.9), sub["sig_oi"].quantile(0.1)
            hi = sub.loc[sub["sig_oi"] >= thr_hi, "fwd_1d"]
            lo = sub.loc[sub["sig_oi"] <= thr_lo, "fwd_1d"]
            obs_eff = float(hi.mean() - lo.mean())
            rng = np.random.default_rng(1)
            vals = sub["fwd_1d"].values.copy()
            null = np.empty(500)
            sigvals = sub["sig_oi"].values
            for i in range(500):
                shuf = rng.permutation(vals)
                hh = shuf[sigvals >= thr_hi]; ll = shuf[sigvals <= thr_lo]
                null[i] = hh.mean() - ll.mean() if (len(hh) > 3 and len(ll) > 3) else np.nan
            null = null[np.isfinite(null)]
            p = float((np.abs(null) >= abs(obs_eff)).mean()) if len(null) > 50 else np.nan
            verdict = ("DEAD (fails placebo)" if (np.isfinite(p) and p >= 0.05) else
                       "PLACEBO-INDETERMINATE" if not np.isfinite(p) else
                       "FORWARD-TEST CANDIDATE (Stage-2 eligible, |effect|>=10pt)" if abs(obs_eff) >= 10 else
                       "UNDERPOWERED-UNRESOLVED (beats placebo, <10pt)" if abs(obs_eff) >= 2 else
                       "DEAD (beats placebo but ~0pt)")
            results.append(dict(id=f"CM-19/20:{tagname}", signal="oi_buildup_unwind", horizon="1d",
                                 n=len(sub), n_days=sub["day_s"].nunique(),
                                 effect_pts=round(obs_eff, 3), placebo_p=round(p, 4) if np.isfinite(p) else np.nan,
                                 verdict=verdict))
    else:
        results.append(dict(id="CM-19/20", signal="oi_buildup_unwind", horizon="1d", n=0, n_days=0,
                             effect_pts=np.nan, placebo_p=np.nan, verdict="NO DATA"))

    res_df = pd.DataFrame(results)
    res_df.to_csv(OUT / "stage1_results.csv", index=False)
    print("\n" + "=" * 110, flush=True)
    print(res_df.to_string(index=False), flush=True)
    print("=" * 110, flush=True)

    # ---- held-out 2026 read for any survivor (report only, never select) ----
    survivors = res_df[res_df["verdict"].str.startswith("FORWARD-TEST CANDIDATE", na=False)]
    if not survivors.empty and not min_df.empty:
        print(f"\n[orch] {len(survivors)} Stage-1 survivor(s) -- checking held-out 2026:", flush=True)
        ho_min = min_df[min_df["split"] == "held_out_2026"]
        for _, row in survivors.iterrows():
            sig_map = {"ce_pe_vol_imbalance": "sig_ce_pe_imb", "strike_migration": "sig_strike_mig",
                       "pcr_level": "sig_pcr_level", "pcr_roc": "sig_pcr_roc",
                       "aggressor_proxy": "sig_aggressor"}
            col = sig_map.get(row["signal"])
            if col is None or ho_min.empty:
                continue
            h = row["horizon"]
            z = rolling_z(ho_min, col)
            thr_hi, thr_lo = z.quantile(0.9), z.quantile(0.1)
            hi = ho_min.loc[z >= thr_hi, f"fwd_{h}"]; lo = ho_min.loc[z <= thr_lo, f"fwd_{h}"]
            print(f"  {row['id']} ({row['signal']}, h={h}): build_effect={row['effect_pts']:.2f} "
                  f"| 2026_effect={(hi.mean()-lo.mean()):.2f} n2026={len(hi)+len(lo)}", flush=True)

    print(f"\nwrote {OUT/'stage1_results.csv'}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        worker_main(sys.argv[2], sys.argv[3])
    else:
        orchestrator_main()
