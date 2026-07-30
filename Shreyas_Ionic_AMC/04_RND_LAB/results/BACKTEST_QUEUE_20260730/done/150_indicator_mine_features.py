"""150_indicator_mine_features.py -- Arjun Rao, 2026-07-30.

Feature extraction for the INDICATOR_MINE_20260730 mandate (option-chain-derived signals for
intraday directional naked option buying). Loops all 261 valid weekly-chain expiries and
builds a compact 15-min-bucket table of CE/PE volume, CE/PE OI, and OTM strike-concentration
-- the RAM-heavy part, queued per the Principal's architecture ruling.

RAM discipline (this machine crashed 3x today, once inside chain.load_expiry's own
drop_duplicates + pandas pivot_table on job 140): reads ONLY the 5 needed columns via
pyarrow (never chain.load_expiry's full 12-col frame), never pivots/unstacks a per-minute-
per-strike frame (only small per-minute or per-bucket-strike intermediates are unstacked/
grouped), retries once after gc.collect()+sleep on MemoryError, then skips-and-logs (never
silently drops). Pre-registered in ../INDICATOR_MINE_20260730/PRE_REGISTRATION.md.

Output: results/INDICATOR_MINE_20260730/chain_features_15min.parquet
        results/INDICATOR_MINE_20260730/feature_extraction_log.json
"""
from __future__ import annotations

import gc
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/INDICATOR_MINE_20260730"
OUT.mkdir(parents=True, exist_ok=True)
COLS = ["timestamp", "strike", "option_type", "volume", "open_interest"]


def load_lean(path: Path) -> pd.DataFrame:
    tbl = pq.read_table(path, columns=COLS)
    df = tbl.to_pandas()
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    return df.drop(columns=["timestamp"])


def process_one(exp, path: Path, spot_min: pd.Series) -> pd.DataFrame | None:
    df = load_lean(path)
    # dedup + collapse (cheap: agg via max, avoids drop_duplicates on the full frame)
    g = df.groupby(["t", "strike", "option_type"], as_index=False).agg(
        volume=("volume", "max"), open_interest=("open_interest", "max"))
    del df
    g["bucket"] = g["t"].dt.floor("15min")

    # --- per-minute collapse across strikes (small, ~3000 rows) ---
    per_min_vol = g.groupby(["t", "option_type"])["volume"].sum().unstack(fill_value=0)
    per_min_vol.columns = [f"{c.lower()}_vol" for c in per_min_vol.columns]
    per_min_oi = g.groupby(["t", "option_type"])["open_interest"].sum().unstack(fill_value=0)
    per_min_oi.columns = [f"{c.lower()}_oi" for c in per_min_oi.columns]
    per_min = per_min_vol.join(per_min_oi, how="outer").sort_index()
    for c in ("ce_vol", "pe_vol", "ce_oi", "pe_oi"):
        if c not in per_min.columns:
            per_min[c] = 0

    per_min["bucket"] = per_min.index.floor("15min")
    bucket = per_min.groupby("bucket").agg(
        ce_vol=("ce_vol", "sum"), pe_vol=("pe_vol", "sum"),
        ce_oi=("ce_oi", "last"), pe_oi=("pe_oi", "last"))
    bucket["spot_ref"] = bucket.index.map(spot_min)

    # --- concentration: bucket x strike x type volume (small, buckets x strikes x 2) ---
    bs = g.groupby(["bucket", "strike", "option_type"], as_index=False)["volume"].sum()
    bs["spot_ref"] = bs["bucket"].map(spot_min)
    ce_otm = bs[(bs["option_type"] == "CE") & (bs["strike"] > bs["spot_ref"])]
    pe_otm = bs[(bs["option_type"] == "PE") & (bs["strike"] < bs["spot_ref"])]
    agg_ce = ce_otm.groupby("bucket")["volume"].agg(mx="max", sm="sum")
    agg_pe = pe_otm.groupby("bucket")["volume"].agg(mx="max", sm="sum")
    bucket["conc_ce"] = (agg_ce["mx"] / agg_ce["sm"].replace(0, np.nan))
    bucket["conc_pe"] = (agg_pe["mx"] / agg_pe["sm"].replace(0, np.nan))

    bucket = bucket.reset_index().rename(columns={"index": "bucket"})
    bucket["expiry"] = str(exp)
    del g, per_min, bs, ce_otm, pe_otm
    return bucket


def main():
    t_start = time.time()
    mapping, exps = chain.build_expiry_index()
    spot_path = (ROOT / "intraday_options_strategy/datasets/raw/hf_index_options_1m"
                 "/index/NIFTY.parquet")
    spot = pd.read_parquet(spot_path, columns=["timestamp", "close"])
    spot["t"] = pd.to_datetime(spot["timestamp"]).dt.tz_localize(None)
    spot = spot.drop_duplicates("t").set_index("t").sort_index()
    spot_min = spot["close"]
    del spot
    print(f"[spot] {len(spot_min):,} minute closes loaded", flush=True)

    parts: list[pd.DataFrame] = []
    skipped: list[dict] = []
    for i, exp in enumerate(exps):
        path = mapping[exp]
        ok = False
        for attempt in (1, 2):
            try:
                b = process_one(exp, path, spot_min)
                parts.append(b)
                ok = True
                break
            except MemoryError as e:
                print(f"[MemoryError] {exp} attempt {attempt}: {e}", flush=True)
                gc.collect()
                time.sleep(2)
            except Exception as e:
                print(f"[ERROR] {exp}: {type(e).__name__}: {e}", flush=True)
                traceback.print_exc()
                break
        if not ok:
            skipped.append({"expiry": str(exp), "reason": "memory_or_error_after_retry"})
        # RAM discipline: clear per-expiry cache-equivalents every iteration regardless
        chain.load_expiry.cache_clear()
        gc.collect()
        if (i + 1) % 25 == 0:
            print(f"[progress] {i+1}/{len(exps)} expiries, {len(parts)} ok, "
                  f"{len(skipped)} skipped, {time.time()-t_start:.0f}s elapsed", flush=True)

    feat = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    feat = feat.sort_values("bucket").reset_index(drop=True)
    feat.to_parquet(OUT / "chain_features_15min.parquet", index=False)
    log = {
        "n_expiries_total": len(exps), "n_ok": len(parts), "n_skipped": len(skipped),
        "skipped": skipped, "rows_out": int(len(feat)),
        "bucket_min": str(feat["bucket"].min()) if len(feat) else None,
        "bucket_max": str(feat["bucket"].max()) if len(feat) else None,
        "elapsed_s": round(time.time() - t_start, 1),
    }
    (OUT / "feature_extraction_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"\n[DONE] {json.dumps(log, indent=2)}", flush=True)
    if log["n_skipped"] > 0:
        print(f"[WARN] {log['n_skipped']} expiries skipped -- see feature_extraction_log.json", flush=True)


if __name__ == "__main__":
    sys.exit(main())
