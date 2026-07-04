"""D-M4 follow-up: NIFTY500 Momentum 50 replica + the Principal's SIX-SERIES performance table.
Owner: Arjun Rao (E-004). Landmine guards mandatory (D-028).

PART 1 -- build NIFTY500 Momentum 50 replica on the FROZEN union PRICE panel copy:
  universe = N500 PIT members as-of (NIFTY500_TICKER_2005_2025_Final.xlsx, Mar/Sep snapshots),
  6M+12M vol-adjusted z-score composite (B_excl + A_incl, EW + liquidity-mcap), TOP 50, 5% cap,
  semiannual rebalance, frictionless, chain-linked. Same engine as round-1 (imported UNCHANGED).
  Benchmark: 'NIFTY 500 Momentum 50' (factor_navs_principal, 2005->2026-01) stitched with
  'Nifty500 Momentum 50' (nse_official_all_indices archive, ->2026-07-03). Splice verified 1:1.

  NAMING NOTE: the N500 factor index is officially "NIFTY 500 Momentum 50" (top 50 names), NOT a
  "Momentum 30" -- the Principal's shorthand "nifty 500 momentum 30" = this Momentum 50 index.

PART 2 -- performance table for SIX series {N200M30 replica, N200M30 official, N500M50 replica,
  N500M50 official, NIFTY 50 official, NIFTY 500 official}: trailing 1/3/5/10Y + full-period
  CAGR and annualized vol, full-period max drawdown, excess CAGR vs NIFTY 50. Computed as of the
  latest common date AND as of panel-end 2026-01-22 (both stated). ALL PRICE-INDEX basis, NO
  costs -- dividends excluded everywhere (~1-1.5pp/yr understatement of total return, uniform).

Run: PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python build_perf_table.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
LIB = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib")
sys.path.insert(0, LIB)
import guards as G  # noqa: E402

ENGINE_DIR = os.path.join(ROOT, r"results\factor_replication\20260704_momentm30_exact")
sys.path.insert(0, ENGINE_DIR)
import replicate_factor_indices as R  # noqa: E402  (engine imported UNCHANGED)

OUTDIR = os.path.join(ROOT, r"results\factor_replication\20260704_perf_table")
# FROZEN union PRICE panel copy already snapshotted in the union_rerun dir (md5 cc5f70d1...)
UNION_PRICE = os.path.join(ROOT, r"results\factor_replication\20260704_union_rerun\close_panel_price.parquet")
HF_PANEL = os.path.join(ROOT, r"swing_momentum\data\hf_stock_minute\day\train-00000.parquet")
NAV_PATH = os.path.join(ROOT, r"datasets\index_daily\factor_navs_principal.parquet")
ARCH_PATH = os.path.join(ROOT, r"datasets\index_daily\nse_official_all_indices.parquet")
N500_XLSX = os.path.join(ROOT, "NIFTY500_TICKER_2005_2025_Final.xlsx")

DATA_MAX_DATE = pd.Timestamp("2026-01-22")   # union panel end (replica cannot go past this)
PANEL_END = pd.Timestamp("2026-01-22")
TD = 252


def log(*a):
    print(*a, flush=True)


# --- N500 membership: identical schema/logic to N200 loader, different file (T5 as-of) ---
def load_n500_members() -> dict:
    """dict {snap_date(Timestamp) -> set(symbols)}, Mar/Sep PIT snapshots. Same as N200 loader."""
    d = pd.read_excel(N500_XLSX)
    d = d.rename(columns={"Month-Year": "lab", "Ticker": "sym"})
    d["sym"] = d["sym"].astype(str).str.strip().str.upper()
    out = {}
    for lab, g in d.groupby("lab"):
        mon, yr = str(lab)[:3], str(lab)[3:]
        snap = pd.Timestamp(year=int(yr), month=R._MONTH_MAP[mon], day=1)
        out[snap] = set(g["sym"])
    return out


def load_union_price_and_hf_volume():
    """close from FROZEN union PRICE panel; volume from HF where available."""
    up = pd.read_parquet(UNION_PRICE, columns=["date", "symbol", "close"])
    up["date"] = pd.to_datetime(up["date"])
    up = up[up["date"] <= DATA_MAX_DATE]
    up["symbol"] = up["symbol"].astype(str).str.strip().str.upper()
    up = up.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"], keep="last")
    up = up[up["close"] > 0]
    log(f"[panel] union rows={len(up):,} symbols={up['symbol'].nunique():,} "
        f"{up['date'].min().date()}->{up['date'].max().date()}")
    close = up.pivot(index="date", columns="symbol", values="close").sort_index()

    hf = pd.read_parquet(HF_PANEL, columns=["symbol", "timestamp", "volume"])
    hf = G.fix_ist_dates(hf, ts_col="timestamp", out_col="date")  # L1
    hf["date"] = pd.to_datetime(hf["date"])
    hf = hf[hf["date"] <= DATA_MAX_DATE]
    hf["symbol"] = hf["symbol"].astype(str).str.strip().str.upper()
    hf = hf.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"], keep="last")
    vol = hf.pivot(index="date", columns="symbol", values="volume").sort_index()
    vol = vol.reindex(index=close.index, columns=close.columns)
    return close, vol


def stitched_official(principal_name, archive_name, nav, arch):
    """PRICE-index level series: principal NAV (early) stitched with archive close (tail).
    Splice verified 1:1 (level-ratio median 1.0000, std 0.0), so we concat with archive tail
    appended after the principal's last date -- no rescale."""
    p = nav[nav["series"] == principal_name].set_index("date")["nav"].sort_index()
    p.index = pd.to_datetime(p.index)
    a = arch[arch["index_name"] == archive_name].set_index("date")["close"].sort_index()
    a.index = pd.to_datetime(a.index)
    tail = a[a.index > p.index.max()]
    out = pd.concat([p, tail]).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    return out


# --- performance metrics ---
def cagr(level: pd.Series, start=None, end=None):
    s = level.copy()
    if start is not None:
        s = s[s.index >= start]
    if end is not None:
        s = s[s.index <= end]
    s = s.dropna()
    if len(s) < 20:
        return np.nan
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    if yrs <= 0:
        return np.nan
    return (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1


def ann_vol(level: pd.Series, start=None, end=None):
    s = level.copy()
    if start is not None:
        s = s[s.index >= start]
    if end is not None:
        s = s[s.index <= end]
    r = s.pct_change().dropna()
    if len(r) < 20:
        return np.nan
    return r.std(ddof=0) * np.sqrt(TD)


def max_dd(level: pd.Series, start=None, end=None):
    s = level.copy()
    if start is not None:
        s = s[s.index >= start]
    if end is not None:
        s = s[s.index <= end]
    s = s.dropna()
    if len(s) < 20:
        return np.nan
    peak = s.cummax()
    return (s / peak - 1).min()


def build_momentum(close, vol, members, top_n, excl, wmode, tag):
    rebals = R.rebal_dates(close.index, months=(6, 12), start_year=2004, end_year=2026)
    sc = (lambda c, d, u: R.momentum_scores(c, d, u, exclude_recent_month=excl))
    level, _ = R.build_index(close, vol, members, rebals, sc, wmode, top_n=top_n, cap=0.05, tag=tag)
    return level


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    log("=" * 78)
    log("D-M4 follow-up -- N500 Momentum 50 replica + SIX-SERIES performance table")
    log("=" * 78)

    close, vol = load_union_price_and_hf_volume()
    nav = pd.read_parquet(NAV_PATH); nav["date"] = pd.to_datetime(nav["date"])
    arch = pd.read_parquet(ARCH_PATH); arch["date"] = pd.to_datetime(arch["date"])

    # official stitched PRICE-index levels
    off_n200m = stitched_official("NIFTY 200 Momentum 30", "Nifty200 Momentum 30", nav, arch)
    off_n500m = stitched_official("NIFTY 500 Momentum 50", "Nifty500 Momentum 50", nav, arch)
    off_n50 = stitched_official("NIFTY 50", "Nifty 50", nav, arch)
    off_n500 = stitched_official("NIFTY 500", "Nifty 500", nav, arch)
    for nm, s in [("N200M30", off_n200m), ("N500M50", off_n500m), ("NIFTY50", off_n50), ("NIFTY500", off_n500)]:
        log(f"[official] {nm}: {s.index.min().date()}->{s.index.max().date()} n={len(s)}")

    n200 = R.apply_aliases(R.load_n200_members())
    n500 = R.apply_aliases(load_n500_members())
    log(f"[members] N200 snaps={len(n200)}  N500 snaps={len(n500)} (Mar/Sep, as-of)")

    # ---------- PART 1: replicas ----------
    log("\n[build] N200 Momentum 30 replica (mom_Bexcl_mcap) ...")
    rep_n200m = build_momentum(close, vol, n200, 30, True, "mcap", "n200m30_Bexcl_mcap")
    log("[build] N500 Momentum 50 replica (mom_Bexcl_mcap) ...")
    rep_n500m = build_momentum(close, vol, n500, 50, True, "mcap", "n500m50_Bexcl_mcap")
    # cheap extra: EW variants for robustness
    rep_n500m_ew = build_momentum(close, vol, n500, 50, True, "ew", "n500m50_Bexcl_ew")

    # replication quality (corr/TE) per era vs stitched official (replica capped at panel end)
    def rep_quality(rep_level, off_level, name):
        st = R.tracking_stats(rep_level, off_level[off_level.index <= PANEL_END])
        if st is None:
            log(f"  {name}: insufficient overlap"); return None
        rows = []
        eras = [("2005-01-01", "2015-12-31", "2005-15"), ("2016-01-01", "2019-12-31", "2016-19"),
                ("2020-01-01", "2022-12-31", "2020-22"), ("2023-01-01", "2026-12-31", "2023-26"),
                ("2005-01-01", "2026-12-31", "FULL")]
        rr, ro = st["rr"], st["ro"]
        for lo, hi, lab in eras:
            m = (rr.index >= lo) & (rr.index <= hi)
            a = rr[m].dropna(); b = ro.reindex(a.index)
            if len(a) < 30:
                continue
            rows.append({"series": name, "era": lab, "n": len(a),
                         "corr": round(a.corr(b), 4),
                         "te_ann": round((a - b).std(ddof=0) * np.sqrt(TD), 4)})
        df = pd.DataFrame(rows)
        log(f"  {name} full corr={st['corr']:.4f} TE={st['te']:.4%} [{st['start']}->{st['end']}]")
        return df

    q_rows = []
    for lvl, offs, nm in [(rep_n200m, off_n200m, "N200 Momentum 30 (Bexcl_mcap)"),
                          (rep_n500m, off_n500m, "N500 Momentum 50 (Bexcl_mcap)"),
                          (rep_n500m_ew, off_n500m, "N500 Momentum 50 (Bexcl_ew)")]:
        q = rep_quality(lvl, offs, nm)
        if q is not None:
            q_rows.append(q)
    qual = pd.concat(q_rows, ignore_index=True)
    qual.to_csv(os.path.join(OUTDIR, "replication_quality_era.csv"), index=False)
    log("\n=== REPLICATION QUALITY (corr/TE) per era ===")
    log(qual.to_string(index=False))

    # ---------- PART 2: performance table ----------
    series = {
        "N200M30_replica": rep_n200m,
        "N200M30_official": off_n200m,
        "N500M50_replica": rep_n500m,
        "N500M50_official": off_n500m,
        "NIFTY50_official": off_n50,
        "NIFTY500_official": off_n500,
    }
    # save the daily levels for audit
    for k, s in series.items():
        s.to_frame("level").to_csv(os.path.join(OUTDIR, f"level_{k}.csv"))

    # two "as-of" anchors
    latest_common = min(s.index.max() for s in series.values())
    anchors = {"latest_common": latest_common, "panel_end_2026-01-22": PANEL_END}
    log(f"\n[perf] latest common date across all six = {latest_common.date()}")
    log(f"[perf] panel-end anchor = {PANEL_END.date()}")

    windows = {"1Y": 1, "3Y": 3, "5Y": 5, "10Y": 10}
    # full-period common start (replicas start ~2005-07)
    full_start = max(s.index.min() for s in series.values())
    log(f"[perf] full-period common start = {full_start.date()}")

    rows = []
    for anchor_name, asof in anchors.items():
        n50_cagrs = {}
        # precompute NIFTY50 cagr per window at this anchor for excess calc
        for wl, wy in windows.items():
            start = asof - pd.DateOffset(years=wy)
            n50_cagrs[wl] = cagr(off_n50, start=start, end=asof)
        n50_full = cagr(off_n50, start=full_start, end=asof)
        for sname, s in series.items():
            sc = s[s.index <= asof]
            row = {"anchor": anchor_name, "asof": asof.date().isoformat(), "series": sname,
                   "last_date": sc.dropna().index.max().date().isoformat() if sc.dropna().size else None}
            for wl, wy in windows.items():
                start = asof - pd.DateOffset(years=wy)
                c = cagr(s, start=start, end=asof)
                v = ann_vol(s, start=start, end=asof)
                row[f"cagr_{wl}"] = None if pd.isna(c) else round(c, 4)
                row[f"vol_{wl}"] = None if pd.isna(v) else round(v, 4)
                nc = n50_cagrs[wl]
                row[f"excess_vs_n50_{wl}"] = None if (pd.isna(c) or pd.isna(nc)) else round(c - nc, 4)
            cf = cagr(s, start=full_start, end=asof)
            vf = ann_vol(s, start=full_start, end=asof)
            row["cagr_full"] = None if pd.isna(cf) else round(cf, 4)
            row["vol_full"] = None if pd.isna(vf) else round(vf, 4)
            row["excess_vs_n50_full"] = None if (pd.isna(cf) or pd.isna(n50_full)) else round(cf - n50_full, 4)
            row["maxdd_full"] = round(max_dd(s, start=full_start, end=asof), 4)
            rows.append(row)
    perf = pd.DataFrame(rows)
    perf.to_csv(os.path.join(OUTDIR, "perf_table.csv"), index=False)
    log("\n=== PERFORMANCE TABLE (both anchors) ===")
    log(perf.to_string(index=False))

    cfg = {"built": datetime.now().isoformat(timespec="seconds"),
           "close_source": UNION_PRICE + " (FROZEN union PRICE panel copy, md5 cc5f70d1...)",
           "volume_source": HF_PANEL + " (HF where available)",
           "engine": ENGINE_DIR + r"\replicate_factor_indices.py (imported UNCHANGED, D-028 audited)",
           "n500_xlsx": N500_XLSX, "n200_xlsx": R.N200_XLSX,
           "n500_snapshot_months": "Mar/Sep {3,9}", "n500_snaps": len(n500),
           "benchmarks_stitched": "principal NAV (2005->2026-01/02) + nse_official archive (->2026-07-03); splice verified level-ratio median 1.0000 std 0.0 dailyret corr 1.0",
           "official_series_map": {"N200M30": "NIFTY 200 Momentum 30 | Nifty200 Momentum 30",
                                   "N500M50": "NIFTY 500 Momentum 50 | Nifty500 Momentum 50 (Momentum 50, not 30)",
                                   "NIFTY50": "NIFTY 50 | Nifty 50", "NIFTY500": "NIFTY 500 | Nifty 500"},
           "replica_variant": "mom_Bexcl_mcap (best from union rerun); N500 EW also built for robustness",
           "top_n": {"N200M30": 30, "N500M50": 50}, "cap": 0.05, "frictionless": True,
           "basis": "PRICE-index basis everywhere; dividends EXCLUDED -> absolute CAGRs understate total return ~1-1.5pp/yr uniformly",
           "anchors": {"latest_common": latest_common.date().isoformat(),
                       "panel_end": PANEL_END.date().isoformat()},
           "full_start": full_start.date().isoformat(),
           "deviations": "D1 liquidity-proxy mcap not free-float; D3 Mar/Sep snaps ff'd; D5 no IWF/divisor; replica capped at panel end 2026-01-22"}
    with open(os.path.join(OUTDIR, "config.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    log(f"\n[done] outputs in {OUTDIR}")


if __name__ == "__main__":
    main()
