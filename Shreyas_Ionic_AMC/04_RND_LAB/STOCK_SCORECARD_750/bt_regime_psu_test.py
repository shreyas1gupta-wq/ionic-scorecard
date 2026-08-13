# -*- coding: utf-8 -*-
"""bt_regime_psu_test.py - is the decile edge real, or is it one bull market plus a PSU rally?
(Principal challenge, 2026-08-05.)

HIS CHALLENGE, WHICH IS THE RIGHT ONE TO MAKE
  "2020-2025 was a bull market in which ROE ROCE FCF does not matter much as those stocks would have
   risen much but in full cycle with bear in control they will fall. Similarly there was a PSU effect
   too along with this."

Both halves are testable and both threaten the results reported so far. Three tests:

  T1  UP versus DOWN forward windows. Each formation's 12-month forward period is classified by the
      Nifty 500's own return over that same period. If the decile spread only exists when the market
      rose, the "edge" is beta dressed as skill.

  T2  QUALITY specifically, in up versus down. His precise claim is that ROE and ROCE stop
      discriminating in a rally. Measured as the Quality pillar's standalone rank correlation with
      forward return, computed separately by regime.

  T3  PSU EFFECT. A hand-built list of government-owned names (below) is used to measure PSU
      concentration by decile and to re-run the spread with PSUs REMOVED. If the edge dies without
      them it was a PSU rally.

WHAT THIS CANNOT TEST, STATED PLAINLY
  The price panel begins 2021-07-16. The COVID crash, the 2018-19 small-cap bear and every earlier
  drawdown are OUTSIDE the data. The deepest forward drawdown available is roughly -6% over twelve
  months. So this tests a FLAT-TO-SOFT market, not a bear market, and it cannot answer whether
  low-quality names collapse in a real cycle. He is right that they would; nothing here confirms or
  refutes it, and no result below should be read as if it did.

  Sample split is 29 up formations against 7 down, and the down windows overlap heavily with one
  another, so the down-regime numbers are ONE episode viewed seven times, not seven episodes.

PSU LIST: hand-built from domain knowledge of government-owned NSE listings. It is deliberately
inclusive of the well-known names and is certainly not exhaustive; a name missing from it is counted
as non-PSU, which biases T3 TOWARD finding that the edge survives PSU removal. The bias direction is
stated because it works against the conclusion being drawn.
"""
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
NIFTY = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OBS = os.path.join(HERE, "results", "DECILE_ROLLING_20260805", "observations.csv")
DIAG = os.path.join(HERE, "results", "DECILE_DIAG_20260805", "diag_detail.csv")
IDX = os.path.join(NIFTY, "datasets", "index_daily", "nse_official_all_indices.parquet")
OUT = os.path.join(HERE, "results", "REGIME_PSU_20260805")
os.makedirs(OUT, exist_ok=True)

NDEC = 10

PSU = {
    # energy / oil & gas
    "ONGC", "OIL", "IOC", "BPCL", "HINDPETRO", "GAIL", "PETRONET", "MGL", "IGL",
    # power / utilities
    "NTPC", "POWERGRID", "NHPC", "SJVN", "THERMAX", "NLCINDIA", "PFC", "RECLTD", "IREDA",
    # metals / mining
    "COALINDIA", "NMDC", "SAIL", "NALCO", "MOIL", "HINDCOPPER", "KIOCL", "GMDCLTD",
    # defence / shipbuilding / engineering
    "BEL", "HAL", "BHEL", "BEML", "MAZDOCK", "COCHINSHIP", "GRSE", "BDL", "MIDHANI",
    "ENGINERSIN", "ITI",
    # transport / infra / construction
    "IRFC", "RVNL", "IRCTC", "IRCON", "RITES", "NBCC", "HUDCO", "CONCOR", "SCI", "RAILTEL",
    # banks
    "SBIN", "CANBK", "PNB", "BANKBARODA", "UNIONBANK", "INDIANB", "CENTRALBK", "IOB",
    "UCOBANK", "MAHABANK", "PSB", "J&KBANK",
    # financials / insurance
    "LICI", "GICRE", "NIACL", "IFCI", "SBICARD", "SBILIFE",
    # other
    "BALMLAWRIE", "STCINDIA", "MMTC", "HINDZINC", "FACT", "RCF", "NFL", "GSFC",
}


def trim(x, p=0.05):
    a = np.sort(np.asarray(pd.Series(x).dropna(), dtype=float))
    k = int(len(a) * p)
    core = a[k:len(a) - k] if len(a) > 2 * k else a
    return float(core.mean()) if len(core) else np.nan


def bench_map(formations):
    i = pd.read_parquet(IDX, columns=["index_name", "date", "close"])
    i = i[i["index_name"] == "Nifty 500"].copy()
    i["date"] = pd.to_datetime(i["date"])
    s = i.set_index("date").sort_index()["close"]
    out = {}
    for f in formations:
        t = pd.Timestamp(f)
        a, b = s.asof(t), s.asof(t + pd.DateOffset(months=12))
        out[f] = (b / a - 1) if pd.notna(a) and pd.notna(b) else np.nan
    return out


def spread_table(d, col="dec_final"):
    g = d.groupby(col, observed=True)["fwd"]
    return g.apply(lambda x: trim(x) * 100).round(1)


def main():
    d = pd.read_csv(OBS)
    bm = bench_map(sorted(d["formation"].unique()))
    d["bench_fwd"] = d["formation"].map(bm)
    d["regime"] = np.where(d["bench_fwd"] > 0, "up", "down")

    nf = d.groupby("regime")["formation"].nunique()
    print(f"formations: up={nf.get('up',0)}  down={nf.get('down',0)}   "
          f"observations: {len(d)}")
    print("down-window formations:",
          ", ".join(sorted(d[d['regime']=='down']['formation'].unique())))

    # ---- T1: decile spread by regime -------------------------------------------------
    print("\n=== T1  DECILE SPREAD, UP versus DOWN forward windows ===")
    rows = {}
    for r in ("up", "down"):
        sub = d[d["regime"] == r]
        t = spread_table(sub)
        rows[r] = t
        per = []
        for f, s2 in sub.groupby("formation"):
            a = s2[s2["dec_final"] == 1]["fwd"]; b = s2[s2["dec_final"] == NDEC]["fwd"]
            if len(a) and len(b):
                per.append((trim(b) - trim(a)) * 100)
        hit = np.mean([p > 0 for p in per]) * 100 if per else np.nan
        print(f"\n  {r.upper()}  ({sub['formation'].nunique()} formations, n={len(sub)})")
        print("   " + t.to_string().replace("\n", "\n   "))
        print(f"    D10-D1 = {t.loc[NDEC]-t.loc[1]:+.1f}pp   "
              f"D10>D1 in {hit:.0f}% of formations   median spread {np.median(per):+.1f}pp")
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "spread_by_regime.csv"))

    # ---- T3: PSU concentration and PSU-excluded spread -------------------------------
    d["is_psu"] = d["sym"].astype(str).str.upper().isin(PSU)
    print(f"\n=== T3  PSU EFFECT   (PSU rows: {d['is_psu'].sum()} of {len(d)} = "
          f"{d['is_psu'].mean()*100:.1f}%) ===")
    psu_by_dec = (d.groupby("dec_final")["is_psu"].mean() * 100).round(1)
    psu_ret = d.groupby("is_psu")["fwd"].apply(lambda x: trim(x) * 100).round(1)
    print("  PSU share of each decile (%):")
    print("   " + psu_by_dec.to_string().replace("\n", "\n   "))
    print(f"  PSU forward return {psu_ret.get(True)}%  vs non-PSU {psu_ret.get(False)}%")
    ex = d[~d["is_psu"]]
    t_all, t_ex = spread_table(d), spread_table(ex)
    print(f"\n  D10-D1 with PSUs    : {t_all.loc[NDEC]-t_all.loc[1]:+.1f}pp")
    print(f"  D10-D1 without PSUs : {t_ex.loc[NDEC]-t_ex.loc[1]:+.1f}pp  "
          f"(n={len(ex)})")
    pd.DataFrame({"with_psu": t_all, "ex_psu": t_ex,
                  "psu_share_pct": psu_by_dec}).to_csv(os.path.join(OUT, "psu_test.csv"))

    # ---- T2: does QUALITY discriminate only in a rally? ------------------------------
    if os.path.exists(DIAG):
        dg = pd.read_csv(DIAG)
        dg["bench_fwd"] = dg["formation"].map(bench_map(sorted(dg["formation"].unique())))
        dg["regime"] = np.where(dg["bench_fwd"] > 0, "up", "down")
        print("\n=== T2  PILLAR rank-correlation with forward return, BY REGIME ===")
        print("    (his claim: ROE/ROCE stop discriminating in a bull market)")
        out = {}
        for r in ("up", "down"):
            sub = dg[dg["regime"] == r]
            if len(sub) < 100:
                continue
            out[f"{r} (n={len(sub)}, {sub['formation'].nunique()}f)"] = {
                p: round(float(sub[[p, "fwd"]].corr(method="spearman").iloc[0, 1]), 4)
                for p in ("quality", "growth", "value", "stage", "final", "composite_3y")}
        print(pd.DataFrame(out).to_string())
        pd.DataFrame(out).to_csv(os.path.join(OUT, "pillar_ic_by_regime.csv"))
        print("\n  formation-level forward market returns used for the split:")
        for f in sorted(dg["formation"].unique()):
            print(f"    {f}: {dg[dg['formation']==f]['bench_fwd'].iloc[0]*100:+.1f}%")

    print("\nwrote", OUT)


if __name__ == "__main__":
    main()
