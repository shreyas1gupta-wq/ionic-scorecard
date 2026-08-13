"""Stage A: per-expiry, per-5min-bucket value-weighted OI-flow classification.

Reads each NIFTY weekly-options expiry file (1-min, all strikes), cleans the
open_interest column (0 -> NaN placeholder -> ffill within day), restricts to a
near-ATM band, buckets to 5-min, classifies each (strike,type,bucket) into one of
the four buildup quadrants using the OPTION'S OWN price direction + its OI direction,
values the flow in Rs crore, and writes one small parquet per expiry so the job is
fully resumable and RAM-safe (chain_slot grab-extract-release per expiry).

Output: results/FLOW_IMBALANCE_20260731/bucket_flow/{expiry}.parquet
Columns: expiry, trading_day, dte, is_monthly, bucket (Timestamp),
         call_writing_cr, call_buying_cr, call_covering_cr, call_unwind_cr,
         put_writing_cr,  put_buying_cr,  put_covering_cr,  put_unwind_cr,
         call_writing_otm_cr, put_writing_otm_cr,           (OTM-wing check)
         n_anom, spot_bucket_open, spot_bucket_high, spot_bucket_low, spot_bucket_close
         (spot_bucket_* are NIFTY 1-min OHLC aggregated to the same 5-min bucket, for the
          later confirmation stage; avoids re-joining spot data in stage B)
"""
import sys, gc, time, json
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
from chainlock import chain_slot, free_ram_gb  # noqa: E402
import chain  # noqa: E402

OUT_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/FLOW_IMBALANCE_20260731/bucket_flow"
LOG_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/FLOW_IMBALANCE_20260731/logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOT_SIZE = 65          # Principal-specified constant multiplier (see PRE_REGISTRATION.md caveat)
BAND_STRIKES = 8        # +/- 8 strikes around day-open spot
ANOM_REL_JUMP = 0.40    # |dOI|/prior_level above this -> anomaly, excluded from value sums
BUCKET = "5min"
EXPIRY_DAY_CUTOFF = dt.time(15, 20)   # exclude 0DTE buckets after this (settlement collapse)


def log(msg):
    line = f"[{dt.datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG_DIR / "01_build_bucket_flow.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def monthly_expiry_set(all_exps):
    """Last valid expiry date in each (year,month) = monthly; else weekly."""
    by_ym = {}
    for e in all_exps:
        by_ym.setdefault((e.year, e.month), []).append(e)
    return {max(v) for v in by_ym.values()}


def classify_and_value(day_df):
    """day_df: rows for ONE trading_day, ONE expiry, already band-filtered.
    Returns per-bucket aggregated flow dict-of-lists (long format rows)."""
    d = day_df.copy()
    d = d.sort_values(["strike", "option_type", "t"])
    # --- OI clean: 0 -> NaN -> ffill within (strike, option_type) for this single day ---
    d["oi_clean"] = d["open_interest"].where(d["open_interest"] != 0, np.nan)
    d["oi_clean"] = d.groupby(["strike", "option_type"])["oi_clean"].ffill()
    # --- 5-min bucket ---
    d["bucket"] = d["t"].dt.floor(BUCKET)
    # last-known price & OI per (strike,type,bucket)
    g = (d.groupby(["strike", "option_type", "bucket"], as_index=False)
           .agg(close=("close", "last"), oi=("oi_clean", "last")))
    g = g.sort_values(["strike", "option_type", "bucket"])
    grp = g.groupby(["strike", "option_type"])
    g["d_oi"] = grp["oi"].diff()
    g["prior_oi"] = grp["oi"].shift(1)
    g["d_px"] = grp["close"].diff()
    g = g.dropna(subset=["d_oi", "d_px", "prior_oi"])
    if g.empty:
        return None
    rel_jump = (g["d_oi"].abs() / g["prior_oi"].clip(lower=1))
    g["anom"] = rel_jump > ANOM_REL_JUMP
    g["value_cr"] = (g["d_oi"].abs() * g["close"] * LOT_SIZE) / 1e7
    # quadrant
    cond_lb = (g["d_oi"] > 0) & (g["d_px"] > 0)   # long buildup / buying
    cond_sb = (g["d_oi"] > 0) & (g["d_px"] < 0)   # short buildup / writing
    cond_sc = (g["d_oi"] < 0) & (g["d_px"] > 0)   # short covering
    cond_lu = (g["d_oi"] < 0) & (g["d_px"] < 0)   # long unwind
    g["quad"] = np.select([cond_lb, cond_sb, cond_sc, cond_lu],
                           ["buying", "writing", "covering", "unwind"], default="flat")
    g_ok = g[~g["anom"]]
    n_anom = int(g["anom"].sum())
    piv = (g_ok.groupby(["option_type", "quad", "bucket"])["value_cr"]
              .sum().unstack(["option_type", "quad"], fill_value=0.0))
    return piv, n_anom


def process_expiry(exp, is_monthly_set, spot_idx):
    out_path = OUT_DIR / f"{exp}.parquet"
    if out_path.exists():
        return "skip"
    with chain_slot("flow-imbalance", min_free_gb=1.0):
        if free_ram_gb() < 1.0:
            log(f"LOW RAM before load ({free_ram_gb():.2f}GB free) - exiting cleanly")
            return "low_ram"
        df = chain.load_expiry(exp)
        keep_cols = ["t", "trading_day", "open", "high", "low", "close", "volume",
                     "open_interest", "strike", "option_type"]
        df = df[keep_cols]
        rows = []
        for tday_str, day_df in df.groupby("trading_day"):
            tday = dt.date.fromisoformat(tday_str)
            dte = (exp - tday).days
            if dte < 0:
                continue
            # spot ref = day's first bar close at/after 09:15
            day_spot = spot_idx[spot_idx.index.date == tday]
            day_spot = day_spot[day_spot.index.time >= dt.time(9, 15)]
            if day_spot.empty:
                continue
            spot_ref = float(day_spot.iloc[0]["close"])
            strikes = np.sort(day_df["strike"].unique())
            if len(strikes) < 2:
                continue
            step = float(np.median(np.diff(strikes))) or 50.0
            lo, hi = spot_ref - BAND_STRIKES * step, spot_ref + BAND_STRIKES * step
            band = day_df[(day_df["strike"] >= lo) & (day_df["strike"] <= hi)].copy()
            if dte == 0:
                band = band[band["t"].dt.time <= EXPIRY_DAY_CUTOFF]
            if band.empty:
                continue
            res = classify_and_value(band)
            if res is None:
                continue
            piv, n_anom = res
            piv = piv.reset_index()
            piv.columns = ["_".join(c).strip("_") if isinstance(c, tuple) else c for c in piv.columns]
            piv["expiry"] = exp.isoformat()
            piv["trading_day"] = tday_str
            piv["dte"] = dte
            piv["is_monthly"] = exp in is_monthly_set
            piv["n_anom"] = n_anom
            # attach spot OHLC for the same 5-min buckets (for stage-B confirmation)
            sp = spot_idx[(spot_idx.index.date == tday)].copy()
            sp["bucket"] = sp.index.floor(BUCKET)
            sp_agg = sp.groupby("bucket").agg(spot_open=("open", "first"), spot_high=("high", "max"),
                                               spot_low=("low", "min"), spot_close=("close", "last"))
            piv = piv.merge(sp_agg, on="bucket", how="left")
            rows.append(piv)
        del df
        if rows:
            out = pd.concat(rows, ignore_index=True)
            for col in ["CE_buying", "CE_writing", "CE_covering", "CE_unwind",
                        "PE_buying", "PE_writing", "PE_covering", "PE_unwind"]:
                if col not in out.columns:
                    out[col] = 0.0
            out.to_parquet(out_path, index=False)
            n_written = len(out)
        else:
            pd.DataFrame().to_parquet(out_path)  # mark done, empty
            n_written = 0
    chain.load_expiry.cache_clear()
    gc.collect()
    return f"ok:{n_written}"


def main():
    import os
    t0 = time.time()
    mapping, exps = chain.build_expiry_index()
    is_monthly_set = monthly_expiry_set(exps)
    spot_idx = chain.load_index()
    limit = int(os.environ.get("FLOW_LIMIT", "0"))
    if limit:
        exps = exps[:limit]
    log(f"{len(exps)} expiries to process; spot bars {len(spot_idx):,}")
    done, skipped, low_ram_stop = 0, 0, False
    for i, exp in enumerate(exps):
        status = process_expiry(exp, is_monthly_set, spot_idx)
        if status == "skip":
            skipped += 1
            continue
        if status == "low_ram":
            log("stopping cleanly on low RAM; rerun script to resume (skip-existing)")
            low_ram_stop = True
            break
        done += 1
        if i % 10 == 0 or i == len(exps) - 1:
            log(f"[{i+1}/{len(exps)}] {exp} -> {status}  free_ram={free_ram_gb():.2f}GB "
                f"elapsed={time.time()-t0:.0f}s")
    log(f"DONE. processed={done} skipped(existing)={skipped} low_ram_stop={low_ram_stop} "
        f"total_elapsed={time.time()-t0:.0f}s")
    with open(LOG_DIR / "01_status.json", "w") as f:
        json.dump({"processed": done, "skipped": skipped, "low_ram_stop": low_ram_stop,
                   "elapsed_s": time.time() - t0}, f)


if __name__ == "__main__":
    main()
