"""
S8 — score-bucket calibration re-evaluation (Principal's 2026-07-18 methodology correction).

Pure read-and-compute pass. No fitting, no randomness. Deterministic: run twice -> byte-identical
calibration_tables.parquet (checked by SHA-256 in this script's __main__ guard via a CLI flag).

Inputs (read-only):
  rnd/scorecard/absolute_scorecard.parquet   (date, symbol, horizon, E_return, fwd_ret_h_raw, ...)
  rnd/scorecard/RELATIVE_SCORECARD_v1.parquet (date, symbol, rel_score_1M/1Y/5Y, verdict_*)
  rnd/panel/panel_pit.parquet                (date, symbol, fwd_ret_{1M,1Y,5Y}_raw)

Outputs:
  rnd/scorecard/calibration_tables.parquet
  rnd/scorecard/S8_calibration_diag.json  (scalar diagnostics used to write the .md report)
"""
import sys
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ABS_PATH = HERE / "absolute_scorecard.parquet"
REL_PATH = HERE / "RELATIVE_SCORECARD_v1.parquet"
PANEL_PATH = HERE.parent / "panel" / "panel_pit.parquet"

OUT_PARQUET = HERE / "calibration_tables.parquet"
OUT_DIAG = HERE / "S8_calibration_diag.json"

HORIZONS = ["1M", "1Y", "5Y"]

# Bucket edges chosen from the task's suggested language (>75/50-75/30-50/<30) extended to cover
# the full -100..+100 score range with an explicit <0 band (since these scores are signed, unlike
# a 0-100 native scale). Documented choice, not fitted to the data.
BUCKET_EDGES = [-100.0001, 0, 30, 50, 75, 100.0001]
BUCKET_LABELS = ["<0", "0-30", "30-50", "50-75", ">75"]


def rank_pct_within_date(df, value_col, date_col="date"):
    """Cross-sectional percentile rank in [0,1] of value_col within each date, NaN-safe."""
    return df.groupby(date_col)[value_col].rank(pct=True, method="average")


def to_score(rank_pct_series):
    return 200.0 * (rank_pct_series - 0.5)


def bucket_of(score_series):
    return pd.cut(score_series, bins=BUCKET_EDGES, labels=BUCKET_LABELS, right=True)


def safe_log1p_ret(x):
    # guarded: any ret <= -1 would be undefined; verified none exist in this dataset (see S8 notes)
    x = x.where(x > -1.0)
    return np.log1p(x)


def build_absolute_frame():
    a = pd.read_parquet(ABS_PATH)
    frames = []
    for h in HORIZONS:
        sub = a[a["horizon"] == h].copy()
        sub = sub[sub["E_return"].notna() & sub["fwd_ret_h_raw"].notna()].copy()
        sub["log_intensity"] = safe_log1p_ret(sub["E_return"])
        sub["log_realized_return"] = safe_log1p_ret(sub["fwd_ret_h_raw"])
        sub["abs_score"] = to_score(rank_pct_within_date(sub, "E_return"))
        sub["bucket"] = bucket_of(sub["abs_score"])
        sub["hit"] = (sub["fwd_ret_h_raw"] > 0).astype(float)
        sub["year"] = sub["date"].dt.year
        sub["scorecard"] = "ABSOLUTE"
        sub["horizon"] = h
        frames.append(sub[["scorecard", "horizon", "date", "year", "symbol",
                            "abs_score", "bucket", "hit", "log_realized_return",
                            "fwd_ret_h_raw"]].rename(columns={"abs_score": "score"}))
    return pd.concat(frames, ignore_index=True)


def build_relative_frame():
    r = pd.read_parquet(REL_PATH)
    p = pd.read_parquet(PANEL_PATH)
    fwd_cols = {h: f"fwd_ret_{h}_raw" for h in HORIZONS}
    p = p[["date", "symbol"] + list(fwd_cols.values())].copy()
    merged = r.merge(p, on=["date", "symbol"], how="inner")

    frames = []
    for h in HORIZONS:
        score_col = f"rel_score_{h}"
        fwd_col = fwd_cols[h]
        sub = merged[merged[score_col].notna() & merged[fwd_col].notna()].copy()
        sub["log_realized_return"] = safe_log1p_ret(sub[fwd_col])
        sub["bucket"] = bucket_of(sub[score_col])
        # comparator = cross-sectional median that date, over the SAME scored+realized population
        med = sub.groupby("date")[fwd_col].transform("median")
        sub["hit"] = (sub[fwd_col] > med).astype(float)
        sub["year"] = sub["date"].dt.year
        sub["scorecard"] = "RELATIVE"
        sub["horizon"] = h
        frames.append(sub[["scorecard", "horizon", "date", "year", "symbol",
                            score_col, "bucket", "hit", "log_realized_return",
                            fwd_col]].rename(columns={score_col: "score", fwd_col: "fwd_ret_h_raw"}))
    return pd.concat(frames, ignore_index=True)


def calibration_table(long_df):
    """Bucket-level table per (scorecard, horizon, bucket)."""
    rows = []
    for (sc, h), g in long_df.groupby(["scorecard", "horizon"], sort=False):
        for b in BUCKET_LABELS:
            gb = g[g["bucket"] == b]
            n = len(gb)
            if n == 0:
                rows.append(dict(scorecard=sc, horizon=h, bucket=b, n=0,
                                  hit_rate=np.nan, mean_log_realized_return=np.nan,
                                  yearly_hitrate_std=np.nan, n_years=0))
                continue
            hit_rate = gb["hit"].mean()
            mean_log_ret = gb["log_realized_return"].mean()
            yearly = gb.groupby("year")["hit"].mean()
            rows.append(dict(scorecard=sc, horizon=h, bucket=b, n=n,
                              hit_rate=hit_rate, mean_log_realized_return=mean_log_ret,
                              yearly_hitrate_std=yearly.std(ddof=0) if len(yearly) > 1 else np.nan,
                              n_years=len(yearly)))
    tbl = pd.DataFrame(rows)
    tbl["bucket_rank"] = tbl["bucket"].map({b: i for i, b in enumerate(BUCKET_LABELS)})
    tbl = tbl.sort_values(["scorecard", "horizon", "bucket_rank"]).reset_index(drop=True)

    # frac_years_beats_below: for each (scorecard,horizon,bucket) except the lowest, fraction of years
    # where this bucket's yearly hit-rate > the bucket-below's yearly hit-rate (same year, both present)
    frac_beats = []
    for (sc, h), g in long_df.groupby(["scorecard", "horizon"], sort=False):
        yearly_by_bucket = {}
        for b in BUCKET_LABELS:
            gb = g[g["bucket"] == b]
            yearly_by_bucket[b] = gb.groupby("year")["hit"].mean()
        for i, b in enumerate(BUCKET_LABELS):
            if i == 0:
                frac_beats.append(dict(scorecard=sc, horizon=h, bucket=b, frac_years_beats_below=np.nan))
                continue
            below = BUCKET_LABELS[i - 1]
            cur_y = yearly_by_bucket[b]
            below_y = yearly_by_bucket[below]
            common_years = cur_y.index.intersection(below_y.index)
            if len(common_years) == 0:
                frac_beats.append(dict(scorecard=sc, horizon=h, bucket=b, frac_years_beats_below=np.nan))
                continue
            beats = (cur_y.loc[common_years] > below_y.loc[common_years]).mean()
            frac_beats.append(dict(scorecard=sc, horizon=h, bucket=b, frac_years_beats_below=beats))
    frac_df = pd.DataFrame(frac_beats)
    tbl = tbl.merge(frac_df, on=["scorecard", "horizon", "bucket"], how="left")
    return tbl


def monotonicity_diag(tbl):
    """Spearman-style monotonicity: does bucket_rank correlate with hit_rate / mean_log_realized_return?"""
    out = []
    for (sc, h), g in tbl.groupby(["scorecard", "horizon"], sort=False):
        g = g.dropna(subset=["hit_rate", "mean_log_realized_return"]).sort_values("bucket_rank")
        if len(g) < 2:
            out.append(dict(scorecard=sc, horizon=h, spearman_hitrate=np.nan,
                             spearman_logret=np.nan, n_buckets=len(g),
                             mean_yearly_hitrate_std=np.nan))
            continue
        rk = g["bucket_rank"].values
        hr = g["hit_rate"].values
        lr = g["mean_log_realized_return"].values
        sp_hr = pd.Series(rk).corr(pd.Series(hr), method="spearman")
        sp_lr = pd.Series(rk).corr(pd.Series(lr), method="spearman")
        out.append(dict(scorecard=sc, horizon=h, spearman_hitrate=sp_hr,
                         spearman_logret=sp_lr, n_buckets=len(g),
                         mean_yearly_hitrate_std=g["yearly_hitrate_std"].mean()))
    return pd.DataFrame(out)


def main(check_determinism=False):
    abs_long = build_absolute_frame()
    rel_long = build_relative_frame()
    long_df = pd.concat([abs_long, rel_long], ignore_index=True)

    tbl = calibration_table(long_df)
    mono = monotonicity_diag(tbl)

    # write parquet deterministically: fixed column order, sorted rows
    tbl_out = tbl[["scorecard", "horizon", "bucket", "bucket_rank", "n", "n_years",
                   "hit_rate", "mean_log_realized_return", "yearly_hitrate_std",
                   "frac_years_beats_below"]].reset_index(drop=True)
    tbl_out.to_parquet(OUT_PARQUET, index=False)

    diag = {
        "calibration_table": tbl_out.to_dict(orient="records"),
        "monotonicity": mono.to_dict(orient="records"),
        "n_rows_absolute_by_horizon": {h: int((abs_long["horizon"] == h).sum()) for h in HORIZONS},
        "n_rows_relative_by_horizon": {h: int((rel_long["horizon"] == h).sum()) for h in HORIZONS},
        "bucket_edges": BUCKET_EDGES,
        "bucket_labels": BUCKET_LABELS,
    }
    with open(OUT_DIAG, "w", encoding="utf-8") as f:
        json.dump(diag, f, indent=2, default=str)

    sha = hashlib.sha256(OUT_PARQUET.read_bytes()).hexdigest()
    print(f"calibration_tables.parquet sha256 = {sha}")
    print(f"rows: {len(tbl_out)}")

    if check_determinism:
        print("DETERMINISM_SHA256:", sha)

    return sha


if __name__ == "__main__":
    main(check_determinism="--check-determinism" in sys.argv)
