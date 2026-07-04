"""D-M4 forensics TASK 3: early-era momentum EW re-run on the MASTER+DELISTED close panel.
Owner: Arjun Rao (E-004).

Task-1 verdict: BOTH HF panel and Master Dataset are split/bonus-ADJUSTED (14/14 and 13/14;
the 1 Master 'AMBIGUOUS' is a single LT-2006 bad print, HF is clean there). So NO CA-factor
re-adjustment is needed -- we use Master closes as-is. (LOUD: if any source had been unadjusted
we would have divided by cumulative split factors from raw/corporate_actions first.)

This re-runs ONLY the equal-weight momentum variant (close-only is sufficient for EW; the
mcap-proxy needed volume which the Master lacks) using the SAME scoring engine as the D-M4
build, but sourcing prices from combined master+delisted instead of the HF panel. It compares
per-year TE/corr 2006-2018 old (HF) vs new (Master) and reports the new full-period number.

Reuses the cached _combined_master_delisted_close.parquet from ca_adjustment_audit.py task2.
Run: PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python task3_master_rerun.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
LIB = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib")
sys.path.insert(0, LIB)
import guards as G  # noqa: E402
# reuse the D-M4 build engine (momentum_scores, build_index, tracking_stats, per_year_stats,
# rebal_dates, members_asof, apply_aliases, load_n200_members)
sys.path.insert(0, os.path.join(ROOT, r"results\factor_replication\20260704_momentm30_exact"))
import replicate_factor_indices as R  # noqa: E402

OUT = os.path.join(ROOT, r"results\factor_replication\20260704_data_forensics")
COMBINED = os.path.join(OUT, "_combined_master_delisted_close.parquet")
NAV_PATH = os.path.join(ROOT, r"datasets\index_daily\factor_navs_principal.parquet")
DATA_MAX_DATE = pd.Timestamp("2026-01-22")  # match HF window for apples-to-apples


def log(*a):
    print(*a, flush=True)


def load_master_close() -> pd.DataFrame:
    """Wide close (date index, symbol cols) from cached master+delisted, cleaned + windowed."""
    df = pd.read_parquet(COMBINED)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df[df.index <= DATA_MAX_DATE]
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    # drop all-NaN and non-positive-only columns
    df = df.replace(0.0, np.nan)
    return df


def main():
    os.makedirs(OUT, exist_ok=True)
    log("=" * 80)
    log("TASK 3 -- MOMENTUM EW re-run on MASTER+DELISTED close panel")
    log("(sources verified ADJUSTED in task1 -> no CA re-adjustment applied)")
    log("=" * 80)

    close = load_master_close()
    # build a dummy volume frame (zeros) since EW path never uses volume
    vol = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    log(f"[master] close {close.shape[0]} days x {close.shape[1]} cols "
        f"{close.index.min().date()}->{close.index.max().date()}")

    n200 = R.apply_aliases(R.load_n200_members())
    navs = pd.read_parquet(NAV_PATH)
    navs["date"] = pd.to_datetime(navs["date"])
    mom_off = navs[navs["series"] == "NIFTY 200 Momentum 30"].set_index("date")["nav"].sort_index()

    tdays = close.index
    rebals = R.rebal_dates(tdays, months=(6, 12), start_year=2004, end_year=2026)
    log(f"[master] semiannual rebalance count={len(rebals)}")

    # score fn: EW, A-variant (incl recent month), same engine
    sc = (lambda c, d, u: R.momentum_scores(c, d, u, exclude_recent_month=False))
    level, hold = R.build_index(close, vol, n200, rebals, sc, "ew",
                                top_n=30, cap=0.05, tag="mom_master_ew")
    st = R.tracking_stats(level, mom_off)
    py = R.per_year_stats(st["rr"], st["ro"])
    log(f"\n[master EW] FULL: corr={st['corr']:.4f} TE={st['te']:.4%} "
        f"[{st['start']}->{st['end']}, n={st['n']}]")

    # write daily + per-year
    out = pd.DataFrame({"date": st["rep"].index, "replica": st["rep"].values,
                        "official": st["off"].values})
    out.to_csv(os.path.join(OUT, "task3_daily_master_ew.csv"), index=False)
    py.to_csv(os.path.join(OUT, "task3_peryear_master_ew.csv"), index=False)

    # load the OLD HF EW per-year for side-by-side 2006-2018
    old_py = pd.read_csv(os.path.join(
        ROOT, r"results\factor_replication\20260704_momentm30_exact\peryear_mom_Aincl_ew.csv"))
    old_py = old_py.set_index("year")
    new_py = py.set_index("year")
    rows = []
    for yr in range(2006, 2019):
        o = old_py.loc[yr] if yr in old_py.index else None
        n = new_py.loc[yr] if yr in new_py.index else None
        rows.append({"year": yr,
                     "hf_corr": None if o is None else o["corr"],
                     "hf_te": None if o is None else o["te_ann"],
                     "master_corr": None if n is None else n["corr"],
                     "master_te": None if n is None else n["te_ann"],
                     "hf_rep_ret": None if o is None else o["rep_ret"],
                     "master_rep_ret": None if n is None else n["rep_ret"],
                     "official_ret": None if n is None else n["off_ret"]})
    comp = pd.DataFrame(rows)
    comp.to_csv(os.path.join(OUT, "task3_hf_vs_master_2006_2018.csv"), index=False)
    log("\nOLD (HF EW) vs NEW (Master EW) 2006-2018:")
    log(comp.to_string(index=False))

    # full-period compare
    old_daily = pd.read_csv(os.path.join(
        ROOT, r"results\factor_replication\20260704_momentm30_exact\daily_mom_Aincl_ew.csv"),
        parse_dates=["date"]).set_index("date")
    orr = old_daily["replica"].pct_change(); oro = old_daily["official"].pct_change()
    a = orr.dropna(); b = oro.reindex(a.index)
    old_te = (a - b).std(ddof=0) * np.sqrt(252)
    old_corr = a.corr(b)
    log(f"\nFULL-PERIOD EW momentum:")
    log(f"  HF panel   : corr={old_corr:.4f} TE={old_te:.4%}")
    log(f"  Master     : corr={st['corr']:.4f} TE={st['te']:.4%}")

    cfg = {"task": "3 master EW momentum re-run", "adjustment": "sources ADJUSTED, no re-adj",
           "hf_full": {"corr": round(old_corr, 4), "te": round(old_te, 4)},
           "master_full": {"corr": round(st["corr"], 4), "te": round(st["te"], 4)},
           "window": [st["start"], st["end"]]}
    with open(os.path.join(OUT, "task3_config.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    log("\n[done] task3 outputs written.")


if __name__ == "__main__":
    main()
