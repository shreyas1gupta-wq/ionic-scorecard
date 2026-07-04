"""D-M4 FINAL LEG: factor-index replication on the PIT UNION *PRICE* panel (v1).
Owner: Arjun Rao (E-004, Head of Quant). Landmine guards mandatory (D-028).

WHAT THIS IS
------------
Round-3 of the D-M4 replication. Re-runs the EXACT same scoring/index/stats engine as
`results/factor_replication/20260704_momentm30_exact/replicate_factor_indices.py`
(imported unchanged -- already D-028 audited) but swaps the PRICE SOURCE:

    close  <- FROZEN COPY of Manoj's PIT union PRICE panel v1 (HF + Delisted + Raw500),
              survivorship-complete, PRICE basis (as-traded, split/bonus-adjusted, NOT
              dividend-adjusted -> basis-consistent with the official NSE *price* indices).
    volume <- HF daily parquet where available (union panel carries no volume). The
              liquidity-mcap variant needs a turnover proxy; symbols not in HF get 0 volume
              (they fall out of the mcap tilt but remain in the EW variant).

BASIS NOTE (why this panel, not the Master re-run):
  Manoj's ground-truth check (BUILD_REPORT.md sec.2) proved MASTER xlsx is dividend-adjusted
  RETURN basis, while HF/Delisted/Raw500 are as-traded PRICE basis matching the exchange
  bhavcopy exactly. The official factor NAVs we benchmark against are PRICE indices. So this
  PRICE panel is basis-consistent; the task-3 Master-EW re-run mixed RETURN-basis prices into
  a PRICE-index comparison and is caveated accordingly in the report.

MEMBERSHIP: N200/N500 PIT xlsx snapshots are MARCH + SEPTEMBER (months {3,9}), not Jun/Dec
  (Manoj discovery). The imported members_asof() already forward-fills most-recent-on-or-before,
  so the real Mar/Sep snapshot calendar is honoured automatically -- no future look.

FROZEN INPUTS (all under this run dir, md5-verified against source at snapshot time):
  close_panel_price.parquet  (md5 cc5f70d1f94129d52bd55fc8b77d0094)
  symbol_aliases.csv, quarantined_segments_price.csv (empty -> no price-segment quarantines)

Run: PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python replicate_union_rerun.py
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
import guards as G  # noqa: E402  (landmine guards mandatory in every entry point)

# reuse the D-M4 build engine UNCHANGED (momentum_scores, lowvol_scores, build_index,
# tracking_stats, per_year_stats, rebal_dates, members_asof, apply_aliases,
# load_n200_members, load_n100_members)
ENGINE_DIR = os.path.join(ROOT, r"results\factor_replication\20260704_momentm30_exact")
sys.path.insert(0, ENGINE_DIR)
import replicate_factor_indices as R  # noqa: E402

OUTDIR = os.path.join(ROOT, r"results\factor_replication\20260704_union_rerun")
UNION_PRICE = os.path.join(OUTDIR, "close_panel_price.parquet")   # FROZEN COPY, work from this
HF_PANEL = os.path.join(ROOT, r"swing_momentum\data\hf_stock_minute\day\train-00000.parquet")
NAV_PATH = os.path.join(ROOT, r"datasets\index_daily\factor_navs_principal.parquet")

DATA_MAX_DATE = pd.Timestamp("2026-01-22")  # union panel end (HF stale-tail carries through)
PANEL_VERSION = "pit_union_panel_v1 (PRICE basis; frozen copy md5 cc5f70d1f94129d52bd55fc8b77d0094)"


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------------------
# DATA LOADER -- the ONLY substantive change vs the audited engine.
#   close  from the frozen UNION PRICE panel (long -> wide)
#   volume from HF daily parquet (union panel has no volume), IST-date-fixed to align
# ---------------------------------------------------------------------------
def load_union_price_and_hf_volume():
    """Return (close_wide, vol_wide): trading-date index, symbol columns.
    close from union PRICE panel; volume from HF where available (else NaN -> 0 in mcap path).
    Both restricted to <= DATA_MAX_DATE (L7 stale-tail guard)."""
    log("[panel] reading FROZEN union PRICE panel ...")
    up = pd.read_parquet(UNION_PRICE, columns=["date", "symbol", "close"])
    up["date"] = pd.to_datetime(up["date"])
    up = up[up["date"] <= DATA_MAX_DATE]
    up["symbol"] = up["symbol"].astype(str).str.strip().str.upper()
    # panel guarantees 0 dup (symbol,date) and no <=0 closes; enforce defensively anyway
    up = up.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"], keep="last")
    up = up[up["close"] > 0]
    log(f"[panel] union rows={len(up):,} symbols={up['symbol'].nunique():,} "
        f"{up['date'].min().date()}->{up['date'].max().date()}")
    close = up.pivot(index="date", columns="symbol", values="close").sort_index()

    log("[panel] reading HF daily parquet for volume ...")
    hf = pd.read_parquet(HF_PANEL, columns=["symbol", "timestamp", "volume"])
    hf = G.fix_ist_dates(hf, ts_col="timestamp", out_col="date")  # L1 IST-date fix
    hf["date"] = pd.to_datetime(hf["date"])
    hf = hf[hf["date"] <= DATA_MAX_DATE]
    hf["symbol"] = hf["symbol"].astype(str).str.strip().str.upper()
    hf = hf.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"], keep="last")
    vol = hf.pivot(index="date", columns="symbol", values="volume").sort_index()

    # align volume onto the union close grid (reindex to close's date/col axes; missing -> NaN).
    # NaN volume is fine: build_index mcap path does close*median(vol); NaN->the symbol gets 0
    # liquidity weight, i.e. it drops out of the mcap tilt but stays in EW. LOUD via a stat below.
    vol = vol.reindex(index=close.index, columns=close.columns)
    hf_cov = vol.notna().any(axis=0).mean()
    log(f"[panel] volume coverage: {hf_cov:.1%} of union symbols have HF volume "
        f"({int(vol.notna().any(axis=0).sum())}/{close.shape[1]})")
    return close, vol


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    log("=" * 74)
    log("D-M4 FINAL LEG -- factor replication on UNION PRICE panel (Momentum30 + LowVol30 v2)")
    log("=" * 74)

    close, vol = load_union_price_and_hf_volume()
    tdays = close.index

    navs = pd.read_parquet(NAV_PATH)
    navs["date"] = pd.to_datetime(navs["date"])
    mom_off = navs[navs["series"] == "NIFTY 200 Momentum 30"].set_index("date")["nav"].sort_index()
    lv_off = navs[navs["series"] == "NIFTY 100 Low Vol 30"].set_index("date")["nav"].sort_index()
    log(f"[nav] momentum {mom_off.index.min().date()}->{mom_off.index.max().date()} ({len(mom_off)})")
    log(f"[nav] lowvol   {lv_off.index.min().date()}->{lv_off.index.max().date()} ({len(lv_off)})")

    n200 = R.apply_aliases(R.load_n200_members())
    n100 = R.apply_aliases(R.load_n100_members())
    log(f"[members] N200 snapshots={len(n200)} ({min(n200).date()}->{max(n200).date()})")
    log(f"[members] N100 months={len(n100)} ({min(n100).date()}->{max(n100).date()})")
    log(f"[members] Mar/Sep snapshot calendar honoured via members_asof (most-recent<=date)")

    results = {}

    # ---- MOMENTUM: 4 variants (A_incl/B_excl x ew/mcap), semiannual Jun/Dec effective ----
    mom_rebals = R.rebal_dates(tdays, months=(6, 12), start_year=2004, end_year=2026)
    log(f"[mom] semiannual rebalance count={len(mom_rebals)}")

    mom_variants = [
        ("mom_Aincl_ew", False, "ew"),
        ("mom_Bexcl_ew", True, "ew"),
        ("mom_Aincl_mcap", False, "mcap"),
        ("mom_Bexcl_mcap", True, "mcap"),
    ]
    for tag, excl, wmode in mom_variants:
        log(f"\n[build] {tag} ...")
        sc = (lambda c, d, u, _e=excl: R.momentum_scores(c, d, u, exclude_recent_month=_e))
        try:
            level, hold = R.build_index(close, vol, n200, mom_rebals, sc, wmode,
                                        top_n=30, cap=0.05, tag=tag)
        except RuntimeError as e:
            log(f"  SKIP {tag}: {e}")
            continue
        st = R.tracking_stats(level, mom_off)
        if st is None:
            log(f"  SKIP {tag}: insufficient overlap")
            continue
        py = R.per_year_stats(st["rr"], st["ro"])
        results[tag] = {"st": st, "py": py}
        out = pd.DataFrame({"date": st["rep"].index, "replica": st["rep"].values,
                            "official": st["off"].values})
        out.to_csv(os.path.join(OUTDIR, f"daily_{tag}.csv"), index=False)
        py.to_csv(os.path.join(OUTDIR, f"peryear_{tag}.csv"), index=False)
        log(f"  {tag}: corr={st['corr']:.4f} TE={st['te']:.4%} "
            f"[{st['start']}->{st['end']}, n={st['n']}]")

    # ---- LOW VOL 30 v2: inverse-vol, quarterly, real N100 membership ----
    lv_rebals = R.rebal_dates(tdays, months=(3, 6, 9, 12), start_year=2008, end_year=2026)
    log(f"\n[lowvol] quarterly rebalance count={len(lv_rebals)}")
    sc_lv = (lambda c, d, u: R.lowvol_scores(c, d, u))
    try:
        lv_level, lv_hold = R.build_index(close, vol, n100, lv_rebals, sc_lv, "invvol",
                                          top_n=30, cap=0.05, tag="lowvol_invvol_q")
        st = R.tracking_stats(lv_level, lv_off)
        if st is not None:
            py = R.per_year_stats(st["rr"], st["ro"])
            results["lowvol_invvol_q"] = {"st": st, "py": py}
            out = pd.DataFrame({"date": st["rep"].index, "replica": st["rep"].values,
                                "official": st["off"].values})
            out.to_csv(os.path.join(OUTDIR, "daily_lowvol_invvol_q.csv"), index=False)
            py.to_csv(os.path.join(OUTDIR, "peryear_lowvol_invvol_q.csv"), index=False)
            log(f"  lowvol_invvol_q: corr={st['corr']:.4f} TE={st['te']:.4%} "
                f"[{st['start']}->{st['end']}, n={st['n']}]")
    except RuntimeError as e:
        log(f"  SKIP lowvol: {e}")

    # ---- era-sliced stats (same era boundaries as round-1 for apples-to-apples) ----
    eras = [("2005-01-01", "2015-12-31", "2005-15"),
            ("2016-01-01", "2019-12-31", "2016-19"),
            ("2020-01-01", "2022-12-31", "2020-22"),
            ("2023-01-01", "2026-12-31", "2023-26")]
    era_rows = []
    for tag, r in results.items():
        rr, ro = r["st"]["rr"], r["st"]["ro"]
        for lo, hi, lab in eras:
            m = (rr.index >= lo) & (rr.index <= hi)
            a = rr[m].dropna()
            b = ro.reindex(a.index)
            if len(a) < 30:
                continue
            era_rows.append({"variant": tag, "era": lab, "n": len(a),
                             "corr": round(a.corr(b), 4),
                             "te_ann": round((a - b).std(ddof=0) * np.sqrt(252), 4)})
    edf = pd.DataFrame(era_rows)
    edf.to_csv(os.path.join(OUTDIR, "era_stats.csv"), index=False)
    log("\nERA-SLICED corr/TE (union price panel):")
    log(edf.to_string(index=False))

    # ---- headline summary ----
    summary = []
    for tag, r in results.items():
        st = r["st"]
        summary.append({"variant": tag, "corr": round(st["corr"], 4),
                        "te_ann": round(st["te"], 4), "start": st["start"],
                        "end": st["end"], "n_days": st["n"]})
    sdf = pd.DataFrame(summary).sort_values("te_ann")
    sdf.to_csv(os.path.join(OUTDIR, "headline_summary.csv"), index=False)
    log("\n" + "=" * 74)
    log("HEADLINE SUMMARY (sorted by TE):")
    log(sdf.to_string(index=False))
    log("=" * 74)

    cfg = {"built": datetime.now().isoformat(timespec="seconds"),
           "run": "D-M4 final leg -- union PRICE panel re-run",
           "close_source": UNION_PRICE,
           "close_source_version": PANEL_VERSION,
           "volume_source": HF_PANEL + " (HF where available; union panel has no volume)",
           "panel_max_date": str(DATA_MAX_DATE.date()),
           "nav": NAV_PATH,
           "n200_xlsx": R.N200_XLSX, "n100_xlsx": R.N100_XLSX,
           "membership_snapshot_calendar": "Mar/Sep (months {3,9}) -- Manoj correction, honoured via members_asof",
           "engine": ENGINE_DIR + r"\replicate_factor_indices.py (imported UNCHANGED, D-028 audited)",
           "momentum_rebalance": "semiannual (Jun/Dec last trading day)",
           "lowvol_rebalance": "quarterly (Mar/Jun/Sep/Dec last trading day)",
           "momentum_score": "z(6M vol-adj ret)+z(12M vol-adj ret) avg, cap +-3, tilt=1+z",
           "lowvol_score": "inverse trailing-252d daily-ret vol, inverse-vol weights",
           "variants": [s["variant"] for s in summary],
           "frictionless": True,
           "deviations": ["D1 full-mcap(liquidity) proxy not free-float (HF volume where avail)",
                          "D2 5% cap on mcap variant only",
                          "D3 effective date = last trading day of review month; Mar/Sep snaps ff'd",
                          "D4 panel ends 2026-01-22 vs NAV 2026-02-27 -- common window",
                          "D5 no IWF/divisor maintenance",
                          "D6 EARLY-ERA COVERAGE -- PARTIALLY RECOVERED by union panel (see REPORT)"],
           "basis_note": "PRICE basis, excludes Master (RETURN basis) -> basis-consistent with official price indices"}
    with open(os.path.join(OUTDIR, "config.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    log(f"[done] outputs in {OUTDIR}")


if __name__ == "__main__":
    main()
