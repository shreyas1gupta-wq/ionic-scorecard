"""D-M4 forensics TASK 1+2: corporate-action ADJUSTMENT audit + coverage cross-check.
Owner: Arjun Rao (E-004). Principal's #1 suspicion: are 2005-2018 prices UNADJUSTED?

An UNADJUSTED series drops by ~1/split on the ex-date (a fake 'crash'); an ADJUSTED
series shows only the normal daily move (~1). Momentum winners split/bonus often, so an
unadjusted panel systematically fakes crashes on exactly the names momentum picks -> would
explain replica CAGR 9.85% vs official 17.8% better than pure coverage.

Method per event: ratio = close(ex_date) / close(prev_trading_day). Compare to 1/split.
  - ratio ~ 1/split  -> UNADJUSTED (raw exchange price, split not applied)
  - ratio ~ 1        -> ADJUSTED (back-adjusted for the split)

Sources tested: (a) HF panel (train-00000, the one D-M4 used), (b) Master Dataset xlsx.

Run: PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python ca_adjustment_audit.py
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
LIB = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib")
sys.path.insert(0, LIB)
import guards as G  # noqa: E402

OUT = os.path.join(ROOT, r"results\factor_replication\20260704_data_forensics")
HF_PANEL = os.path.join(ROOT, r"swing_momentum\data\hf_stock_minute\day\train-00000.parquet")
MASTER = os.path.join(ROOT, "Nifty500_Master_Dataset_2005_2025.xlsx")
DELISTED = os.path.join(ROOT, "Nifty500_Delisted_2005_2025.xlsx")
CA_DIR = os.path.join(ROOT, r"raw\corporate_actions")
N200_XLSX = os.path.join(ROOT, "NIFTY200_TICKER_2005_2025.xlsx")


def log(*a):
    print(*a, flush=True)


# ---- test events: liquid splits/bonuses spread 2006-2018 (found in recon) ----
TEST_EVENTS = [
    ("TCS", "2006-07-28", 2.0, "split 1:2"),
    ("LT", "2006-09-28", 2.0, "split 1:2"),
    ("LT", "2008-10-01", 2.0, "split 1:2"),
    ("TCS", "2009-06-16", 2.0, "split 1:2"),
    ("RELIANCE", "2009-11-26", 2.0, "split 1:2"),
    ("WIPRO", "2010-06-15", 1.6667, "bonus 2:3"),
    ("SUNPHARMA", "2010-11-25", 5.0, "split 1:5"),
    ("LT", "2013-07-11", 1.5, "bonus 1:2"),
    ("SUNPHARMA", "2013-07-29", 2.0, "split 1:2"),
    ("SBIN", "2014-11-20", 10.0, "split 1:10"),
    ("WIPRO", "2017-06-13", 2.0, "bonus 1:1"),
    ("LT", "2017-07-13", 1.5, "bonus 1:2"),
    ("RELIANCE", "2017-09-07", 2.0, "bonus 1:1"),
    ("TCS", "2018-05-31", 2.0, "bonus 1:1"),
]


# ---- source loaders: symbol -> daily close Series (date-indexed) ----
def hf_close(symbols: set) -> dict:
    log("[hf] reading panel close for test symbols ...")
    df = pd.read_parquet(HF_PANEL, columns=["symbol", "timestamp", "close"])
    df = G.fix_ist_dates(df, ts_col="timestamp", out_col="date")  # L1
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
    df = df[df["symbol"].isin(symbols)]
    out = {}
    for s, g in df.groupby("symbol"):
        out[s] = g.sort_values("date").drop_duplicates("date", keep="last").set_index("date")["close"]
    return out


def wide_xlsx_close(path: str, symbols: set) -> dict:
    """Load specific ticker columns from a wide close-only xlsx (Date + ticker cols)."""
    log(f"[xlsx] reading {os.path.basename(path)} columns for test symbols ...")
    raw = pd.read_excel(path)
    raw = raw.rename(columns={raw.columns[0]: "date"})
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.set_index("date")
    raw.columns = [str(c).strip().upper() for c in raw.columns]
    out = {}
    for s in symbols:
        if s in raw.columns:
            col = raw[s]
            if isinstance(col, pd.DataFrame):  # duplicate columns (e.g. 8KMILES) -> first
                col = col.iloc[:, 0]
            out[s] = col.dropna()
    return out


def exdate_ratio(series: pd.Series, ex_date: pd.Timestamp):
    """close(ex_date or next avail) / close(prev trading day). None if data absent."""
    if series is None or len(series) == 0:
        return None
    s = series.sort_index()
    on_after = s.loc[s.index >= ex_date]
    before = s.loc[s.index < ex_date]
    if len(on_after) == 0 or len(before) == 0:
        return None
    return float(on_after.iloc[0] / before.iloc[-1])


def verdict(ratio, split):
    if ratio is None:
        return "NO DATA"
    inv = 1.0 / split
    # unadjusted: ratio near 1/split (within 25%); adjusted: near 1 (0.80-1.25 normal day)
    if abs(ratio - inv) / inv < 0.25:
        return "UNADJUSTED"
    if 0.80 <= ratio <= 1.25:
        return "ADJUSTED"
    return f"AMBIGUOUS ({ratio:.3f})"


def task1_adjustment():
    syms = {e[0] for e in TEST_EVENTS}
    hf = hf_close(syms)
    mst = wide_xlsx_close(MASTER, syms)
    rows = []
    for sym, ds, split, desc in TEST_EVENTS:
        ex = pd.Timestamp(ds)
        r_hf = exdate_ratio(hf.get(sym), ex)
        r_ms = exdate_ratio(mst.get(sym), ex)
        rows.append({"sym": sym, "ex_date": ds, "action": desc, "split_mult": split,
                     "expected_if_unadj": round(1.0 / split, 4),
                     "hf_ratio": None if r_hf is None else round(r_hf, 4),
                     "hf_verdict": verdict(r_hf, split),
                     "master_ratio": None if r_ms is None else round(r_ms, 4),
                     "master_verdict": verdict(r_ms, split)})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "task1_adjustment_audit.csv"), index=False)
    log("\n" + "=" * 90)
    log("TASK 1 -- CORPORATE-ACTION ADJUSTMENT AUDIT")
    log("=" * 90)
    log(df.to_string(index=False))
    # tally
    for src in ["hf_verdict", "master_verdict"]:
        vc = df[src].value_counts().to_dict()
        log(f"  {src} tally: {vc}")
    return df


def load_n200_members():
    d = pd.read_excel(N200_XLSX).rename(columns={"Month-Year": "lab", "Ticker": "sym"})
    d["sym"] = d["sym"].astype(str).str.strip().str.upper()
    mm = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7,
          "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
    out = {}
    for lab, g in d.groupby("lab"):
        snap = pd.Timestamp(year=int(str(lab)[3:]), month=mm[str(lab)[:3]], day=1)
        out[snap] = set(g["sym"])
    return out


def members_asof(members, date):
    keys = [k for k in members if k <= date]
    return members[max(keys)] if keys else set()


def task2_coverage():
    log("\n" + "=" * 90)
    log("TASK 2 -- COVERAGE CROSS-CHECK (HF panel vs Master Dataset vs Delisted)")
    log("=" * 90)
    # full symbol sets from each wide source (columns), + HF panel symbols
    log("[cov] reading master header ...")
    mhead = pd.read_excel(MASTER, nrows=1)
    master_syms = {str(c).strip().upper() for c in mhead.columns[1:]}
    log("[cov] reading delisted header ...")
    dhead = pd.read_excel(DELISTED, nrows=1)
    delisted_syms = {str(c).strip().upper() for c in dhead.columns[1:]}
    log("[cov] reading HF panel symbol list ...")
    hf_syms = set(pd.read_parquet(HF_PANEL, columns=["symbol"])["symbol"]
                  .astype(str).str.strip().str.upper().unique())
    log(f"  master cols={len(master_syms)} delisted cols={len(delisted_syms)} hf syms={len(hf_syms)}")

    # For full-history coverage we need per-rebalance date sets in each source.
    # Load master + delisted close (all cols) once -> combined availability index.
    log("[cov] loading full master + delisted closes (for full-252d test) ...")
    m = pd.read_excel(MASTER).rename(columns={0: "date"})
    m.columns = ["date"] + [str(c).strip().upper() for c in m.columns[1:]]
    m["date"] = pd.to_datetime(m["date"]); m = m.set_index("date")
    m = m.loc[:, ~m.columns.duplicated()]
    dl = pd.read_excel(DELISTED)
    dl.columns = ["date"] + [str(c).strip().upper() for c in dl.columns[1:]]
    dl["date"] = pd.to_datetime(dl["date"]); dl = dl.set_index("date")
    dl = dl.loc[:, ~dl.columns.duplicated()]
    # master + delisted union (delisted fills names master lacks)
    combined = m.join(dl[[c for c in dl.columns if c not in m.columns]], how="outer").sort_index()
    log(f"  combined master+delisted: {combined.shape[0]} days x {combined.shape[1]} cols")

    # HF close (all) for full-history test -- reuse pattern
    log("[cov] loading HF panel close (all) ...")
    hf = pd.read_parquet(HF_PANEL, columns=["symbol", "timestamp", "close"])
    hf = G.fix_ist_dates(hf, ts_col="timestamp", out_col="date")
    hf["date"] = pd.to_datetime(hf["date"]); hf["symbol"] = hf["symbol"].astype(str).str.upper()
    hf_wide = hf.pivot_table(index="date", columns="symbol", values="close", aggfunc="last").sort_index()

    n200 = load_n200_members()

    def full_hist_frac(wide, rb, uni, need=253):
        hist = wide.loc[:rb]
        if len(hist) < need:
            return 0.0, 0
        cnt = 0
        for u in uni:
            if u in hist.columns:
                s = hist[u].dropna()
                if len(s) >= need and (s.tail(need) > 0).all():
                    cnt += 1
        return cnt / len(uni), cnt

    rows = []
    probes = ["2006-06-30", "2008-06-30", "2010-06-30", "2012-06-30",
              "2014-06-30", "2016-06-30", "2018-06-30"]
    hf_days = hf_wide.index
    for p in probes:
        rb = hf_days[hf_days <= pd.Timestamp(p)].max()
        uni = members_asof(n200, rb)
        f_hf, c_hf = full_hist_frac(hf_wide, rb, uni)
        f_ms, c_ms = full_hist_frac(combined, rb, uni)
        # how many missing-in-HF names does combined (esp delisted) supply?
        miss_hf = {u for u in uni if u not in hf_wide.columns or
                   (u in hf_wide.columns and len(hf_wide.loc[:rb, u].dropna()) < 253)}
        recovered = {u for u in miss_hf if u in combined.columns and
                     len(combined.loc[:rb, u].dropna()) >= 253}
        rows.append({"rebal": str(rb.date()), "uni": len(uni),
                     "hf_fullhist_frac": round(f_hf, 3), "hf_n": c_hf,
                     "master_fullhist_frac": round(f_ms, 3), "master_n": c_ms,
                     "missing_in_hf": len(miss_hf),
                     "recovered_by_master": len(recovered)})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "task2_coverage.csv"), index=False)
    log(df.to_string(index=False))
    # save combined for task3 reuse
    combined.to_parquet(os.path.join(OUT, "_combined_master_delisted_close.parquet"))
    log(f"[cov] combined close cached -> _combined_master_delisted_close.parquet")
    # how many delisted names are ever N200 members?
    all_n200 = set().union(*n200.values())
    dl_in_n200 = all_n200 & delisted_syms
    log(f"  delisted names that were EVER N200 members: {len(dl_in_n200)}")
    return df


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    t1 = task1_adjustment()
    t2 = task2_coverage()
    log("\n[done] task1+task2 outputs written to results/factor_replication/20260704_data_forensics/")
