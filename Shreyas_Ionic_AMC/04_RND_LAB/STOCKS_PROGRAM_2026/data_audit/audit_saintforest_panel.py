"""
D-009-style fitness audit (existing dataset, not new source) — Saintforest stock 1-min panel
for STOCKS_PROGRAM_2026 stream T-C (post-breakout intraday ORB).

Dataset: HF `Saintforest/indian-stock-market-minute-data`
Path:    swing_momentum/data/hf_stock_minute/minute/train-0000{0..7}.parquet  (8 shards)
Catalog: Shreyas_Ionic_AMC/05_DATA_OFFICE/DATA_CATALOG.md section 2 "Stock 1-min (HF)"

Memory discipline: machine has ~2GB free / 16GB total at run time. NEVER materialize
the full 813M-row panel. Use:
  - batched column-projected iteration (timestamp[, symbol]) for coverage stats
  - pyarrow.dataset filter pushdown (row-group pruning, data is sorted by symbol) for
    the 5-name deep dive — this subset is tiny (~2-3M rows)

Writes a single JSON with all findings; DATA_FITNESS.md is authored from that JSON.
"""
import json
import os
import sys
import time
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.dataset as ds
import pyarrow.compute as pc

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
PANEL_DIR = os.path.join(ROOT, "swing_momentum", "data", "hf_stock_minute", "minute")
SHARDS = sorted(
    os.path.join(PANEL_DIR, f) for f in os.listdir(PANEL_DIR) if f.endswith(".parquet")
)
OUT_JSON = os.path.join(os.path.dirname(__file__), "audit_results.json")

LIQUID_NAMES = ["RELIANCE", "HDFCBANK", "TCS", "SBIN", "TATAMOTORS"]

results = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "shards": []}

# ---------------------------------------------------------------------------
# 1. Schema + per-shard file stats (metadata only, ~free)
# ---------------------------------------------------------------------------
print("=== 1. SCHEMA + PER-SHARD METADATA ===", flush=True)
schema_arrow = None
total_rows_meta = 0
for shard in SHARDS:
    pf = pq.ParquetFile(shard)
    md = pf.metadata
    if schema_arrow is None:
        schema_arrow = pf.schema_arrow
    total_rows_meta += md.num_rows
    results["shards"].append(
        {
            "file": os.path.basename(shard),
            "size_mb": round(os.path.getsize(shard) / 1e6, 1),
            "num_rows": md.num_rows,
            "num_row_groups": md.num_row_groups,
        }
    )
    print(f"  {os.path.basename(shard)}: {md.num_rows:,} rows, "
          f"{md.num_row_groups} row groups, {os.path.getsize(shard)/1e6:.1f} MB", flush=True)

schema_fields = [{"name": f.name, "type": str(f.type)} for f in schema_arrow]
results["schema"] = schema_fields
results["total_rows_from_metadata"] = total_rows_meta
print("Schema:", schema_fields, flush=True)
print("Total rows (from parquet metadata, no data read):", f"{total_rows_meta:,}", flush=True)

# ---------------------------------------------------------------------------
# 2. Full coverage scan: batched, columns=[timestamp, symbol] only
#    -> global min/max timestamp, distinct symbol count, rows-per-year,
#       distinct-symbols-per-year (periods-per-year discipline per lesson 2026-07)
# ---------------------------------------------------------------------------
print("\n=== 2. COVERAGE SCAN (batched, timestamp+symbol only) ===", flush=True)
global_min_ts = None
global_max_ts = None
global_symbols = set()
year_rows = {}
year_symbols = {}
BATCH = 5_000_000
t0 = time.time()
rows_seen = 0

for shard in SHARDS:
    pf = pq.ParquetFile(shard)
    for batch in pf.iter_batches(columns=["timestamp", "symbol"], batch_size=BATCH):
        ts = batch.column("timestamp")
        sym = batch.column("symbol")
        # min/max via pyarrow compute (no python loop)
        bmin = pc.min(ts).as_py()
        bmax = pc.max(ts).as_py()
        if bmin is not None:
            global_min_ts = bmin if global_min_ts is None else min(global_min_ts, bmin)
        if bmax is not None:
            global_max_ts = bmax if global_max_ts is None else max(global_max_ts, bmax)

        # symbol set for this batch (small: <=2600 uniques)
        batch_syms = set(sym.unique().to_pylist())
        global_symbols |= batch_syms

        # year bucketing: convert timestamp batch -> numpy datetime64, get year array
        ts_np = ts.to_numpy(zero_copy_only=False)
        years = ts_np.astype("datetime64[Y]").astype(int) + 1970
        uniq_years, counts = np.unique(years, return_counts=True)
        sym_np = np.asarray(sym.to_pylist())
        for y, c in zip(uniq_years.tolist(), counts.tolist()):
            year_rows[y] = year_rows.get(y, 0) + c
            mask = years == y
            year_symbols.setdefault(y, set()).update(sym_np[mask].tolist())

        rows_seen += batch.num_rows
        if rows_seen % 50_000_000 < BATCH:
            print(f"  ... {rows_seen:,} rows scanned, {time.time()-t0:.0f}s elapsed", flush=True)

print(f"Coverage scan done: {rows_seen:,} rows in {time.time()-t0:.0f}s", flush=True)

results["global_min_timestamp"] = str(global_min_ts)
results["global_max_timestamp"] = str(global_max_ts)
results["distinct_symbols_total"] = len(global_symbols)
results["rows_per_year"] = {int(y): int(c) for y, c in sorted(year_rows.items())}
results["distinct_symbols_per_year"] = {int(y): len(s) for y, s in sorted(year_symbols.items())}

print("Min ts:", global_min_ts, "Max ts:", global_max_ts, flush=True)
print("Distinct symbols total:", len(global_symbols), flush=True)
print("Rows per year:", results["rows_per_year"], flush=True)
print("Distinct symbols per year:", results["distinct_symbols_per_year"], flush=True)

# ---------------------------------------------------------------------------
# 3. Targeted deep-dive on 5 liquid names via dataset filter pushdown
# ---------------------------------------------------------------------------
print("\n=== 3. LIQUID-NAME DEEP DIVE ===", flush=True)
dataset = ds.dataset(SHARDS, format="parquet")
filt = ds.field("symbol").isin(LIQUID_NAMES)
tbl = dataset.to_table(
    columns=["symbol", "timestamp", "open", "high", "low", "close", "volume", "oi"],
    filter=filt,
)
print(f"Deep-dive subset rows: {tbl.num_rows:,}", flush=True)

df = tbl.to_pandas()
# README says UTC; landmine #1 warns HF daily bars are tz-stamped. Handle both cases robustly.
ts_dtype_str = str(df["timestamp"].dtype)
results["timestamp_dtype_observed"] = ts_dtype_str
if getattr(df["timestamp"].dt, "tz", None) is not None:
    df["ts_ist"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
else:
    # naive -> assume UTC per dataset README, shift to IST
    df["ts_ist"] = df["timestamp"] + pd.Timedelta(hours=5, minutes=30)
df["date_ist"] = df["ts_ist"].dt.date
df["time_ist"] = df["ts_ist"].dt.time

liquid_results = {}
preopen_examples = []
circuit_examples = []

for name in LIQUID_NAMES:
    sub = df[df["symbol"] == name]
    if sub.empty:
        liquid_results[name] = {"error": "NO ROWS FOUND"}
        continue

    per_day = sub.groupby("date_ist").size()
    first_bar_times = sub.groupby("date_ist")["time_ist"].min()
    n_days_before_0915 = (first_bar_times < pd.to_datetime("09:15:00").time()).sum()
    example_preopen_days = first_bar_times[
        first_bar_times < pd.to_datetime("09:15:00").time()
    ].head(3)
    for d, t in example_preopen_days.items():
        preopen_examples.append({"symbol": name, "date": str(d), "first_bar_time": str(t)})

    # circuit-lock day detection: whole-day O==H==L==C (flat day)
    day_ohlc = sub.groupby("date_ist").agg(
        o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"),
        n=("open", "size"),
    )
    flat_days = day_ohlc[(day_ohlc["h"] == day_ohlc["l"]) & (day_ohlc["n"] > 50)]
    for d, row in flat_days.head(3).iterrows():
        circuit_examples.append(
            {"symbol": name, "date": str(d), "o": row["o"], "h": row["h"],
             "l": row["l"], "c": row["c"], "n_bars": int(row["n"])}
        )

    liquid_results[name] = {
        "n_rows": int(len(sub)),
        "date_span": [str(sub["date_ist"].min()), str(sub["date_ist"].max())],
        "n_trading_days": int(per_day.shape[0]),
        "minutes_per_day": {
            "mean": round(float(per_day.mean()), 1),
            "median": float(per_day.median()),
            "min": int(per_day.min()),
            "max": int(per_day.max()),
            "p05": float(per_day.quantile(0.05)),
            "pct_days_lt_300min": round(float((per_day < 300).mean() * 100), 2),
            "pct_days_eq_375_or_more": round(float((per_day >= 375).mean() * 100), 2),
        },
        "n_days_first_bar_before_0915": int(n_days_before_0915),
        "pct_days_first_bar_before_0915": round(
            float(n_days_before_0915 / len(first_bar_times) * 100), 2
        ),
        "n_flat_days_ohlc_locked": int(flat_days.shape[0]),
    }
    print(f"  {name}: {liquid_results[name]}", flush=True)

results["liquid_name_deep_dive"] = liquid_results
results["preopen_examples"] = preopen_examples
results["circuit_lock_examples"] = circuit_examples

# ---------------------------------------------------------------------------
# Write results
# ---------------------------------------------------------------------------
with open(OUT_JSON, "w") as f:
    json.dump(results, f, indent=2, default=str)

print(f"\nWrote {OUT_JSON}", flush=True)
print("=== DONE ===", flush=True)
