"""RECENCY SCREEN — which candidates still work in 2025-2026? (2026-07-30)

Principal: "post 2025 much of alpha has decayed, pay special attention to strategies that keep
working on 2025-2026." This independently corroborates the era-split finding that the liquidity-sweep
flagship went flat from Oct-2024 (PF 0.99, win-rate exactly 50.0%, n=600, 1.62 yrs).

METHOD NOTE ON HOW RECENT PERFORMANCE IS USED (this matters statistically):
recent windows have small n, so selecting the BEST recent performer is itself an overfitting act -
you would simply crown whichever sleeve got lucky lately. So recency is applied ASYMMETRICALLY:
  * as a NEGATIVE screen -> a sleeve that is DEAD recently is disqualified regardless of its history
    (a dead edge is dead whatever the backtest says);
  * NOT as a POSITIVE selector -> a sleeve that looks best recently is NOT crowned on that basis;
    it merely survives to be judged on its full record.
Kill on recent death; do not anoint on recent success. Reported both ways so the asymmetry is visible.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
R = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
         r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results")
OUT = Path(__file__).parent
LOT, CARRY_M = 75, 0.005

WINDOWS = [
    ("full",            None,                    None),
    ("pre_Oct2024",     None,                    pd.Timestamp("2024-09-30")),
    ("Oct2024_to_2026", pd.Timestamp("2024-10-01"), None),
    ("cal_2025",        pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")),
    ("cal_2026",        pd.Timestamp("2026-01-01"), None),
]

S: dict[str, pd.DataFrame] = {}

# SWEEP E / D (carry-adjusted, 1 lot) -------------------------------------------------------
for tag, fn, stop in (("SWEEP_E", "trades_E_swing3_trail60_1lot.csv", 60),
                      ("SWEEP_D", "trades_D_overnight1_trail40_1lot.csv", 40)):
    t = pd.read_csv(R / "SWEEP_11YR_20260729" / fn)
    t["date"] = pd.to_datetime(t["date"])
    carry = t["entry"] * (CARRY_M / 30.0) * np.maximum(t["hold_min"] / 375.0, 0.5)
    t["pts"] = t["gross_pts"] - np.sign(t["dir"]) * carry
    t["net"] = t["pts"] * LOT - t["cost"]
    S[tag] = t[["date", "pts", "net"]]

# CALENDAR 1x1 3d_before (NET) --------------------------------------------------------------
rc = pd.read_csv(R / "RATIO_CALENDAR_20260730" / "grid_a_trades_raw.csv")
c = rc[(rc.strike_struct == "ATM_ATM") & (rc.ratio == "1x1") & (rc.exit_variant == "3d_before")]
c = c.drop_duplicates(subset=["day0", "near_expiry"]).copy()
c["date"] = pd.to_datetime(c["exit_day"])
c["pts"] = c["net_pts"]
c["net"] = c["net_pts"] * LOT
S["CALENDAR_1x1"] = c[["date", "pts", "net"]]

# SWING prior-week fixed_10 -----------------------------------------------------------------
sw = pd.read_csv(R / "SWING_DELTA1_20260729" / "all_trades.csv")
m = [x for x in sw["cell"].unique() if "priorweek" in x and "fixed_10" in x]
if m:
    q = sw[sw["cell"] == m[0]].copy()
    q["date"] = pd.to_datetime(q["exit_date"])
    q["pts"] = q["gross_pts"]
    S["SWING_pw10"] = q[["date", "pts", "net"]]

# existing book sleeves (daily) -------------------------------------------------------------
bk = pd.read_csv(R / "STACKED_BOOK_20260711" / "book_daily_pnl.csv", index_col=0)
bk.index = pd.to_datetime(bk.index)
for col in ("s1f", "b1b", "midsmall", "breakout", "total"):
    if col in bk.columns:
        x = bk[[col]].reset_index()
        x.columns = ["date", "net"]
        x = x[x["net"] != 0]
        x["pts"] = np.nan
        S[f"book_{col}"] = x[["date", "pts", "net"]]


def stat(df: pd.DataFrame, lo, hi) -> dict:
    d = df
    if lo is not None:
        d = d[d.date >= lo]
    if hi is not None:
        d = d[d.date <= hi]
    if len(d) < 5:
        return {"n": len(d)}
    w, l = d[d.net > 0]["net"], d[d.net <= 0]["net"]
    x = d["net"].to_numpy(float)
    mu, n = x.mean(), len(x)
    dv = x - mu
    v = (dv @ dv) / n
    for L in range(1, 6):
        v += 2 * (1 - L / 6) * ((dv[L:] @ dv[:-L]) / n)
    tt = mu / np.sqrt(v / n) if v > 0 else np.nan
    mo = d.set_index("date")["net"].resample("ME").sum()
    return {"n": int(n), "net_rs": round(float(d.net.sum())),
            "mean_pts": round(float(d["pts"].mean()), 2) if d["pts"].notna().any() else None,
            "win": round(float((d.net > 0).mean()), 3),
            "PF": round(float(w.sum() / abs(l.sum())), 2) if l.sum() else None,
            "t": round(float(tt), 2),
            "mo_pos": f"{int((mo > 0).sum())}/{len(mo)}" if len(mo) else "-"}


rows = []
for name, df in S.items():
    r = {"strategy": name}
    for wn, lo, hi in WINDOWS:
        s = stat(df, lo, hi)
        r[f"{wn}_n"] = s.get("n")
        r[f"{wn}_PF"] = s.get("PF")
        r[f"{wn}_t"] = s.get("t")
        r[f"{wn}_net"] = s.get("net_rs")
    rows.append(r)
res = pd.DataFrame(rows)
res.to_csv(OUT / "recency_screen.csv", index=False)

print("=" * 130)
print("RECENCY SCREEN — PF / t / n by window   (PF<1.0 = losing;  PF~1.0 = coin flip)")
print("=" * 130)
hdr = f"{'strategy':<16}" + "".join(f"{w:>23}" for w, _, _ in WINDOWS)
print(hdr)
print("-" * len(hdr))
for _, r in res.iterrows():
    cells = ""
    for wn, _, _ in WINDOWS:
        n, pf, t = r[f"{wn}_n"], r[f"{wn}_PF"], r[f"{wn}_t"]
        cells += f"{'' if pd.isna(n) else f'PF{pf} t{t} n{int(n)}':>23}"
    print(f"{r['strategy']:<16}{cells}")

print()
print("=" * 130)
print("VERDICT — negative screen applied to the RECENT window (Oct-2024 onward)")
print("=" * 130)
for _, r in res.iterrows():
    pf, n, t = r["Oct2024_to_2026_PF"], r["Oct2024_to_2026_n"], r["Oct2024_to_2026_t"]
    if pd.isna(n) or n < 15:
        v = f"INSUFFICIENT n={0 if pd.isna(n) else int(n)} - cannot judge"
    elif pf is None or pf < 0.95:
        v = "DEAD recently -> DISQUALIFY"
    elif pf < 1.10:
        v = "COIN FLIP recently -> do not size"
    elif t is not None and t > 1.5:
        v = "STILL WORKING (survives; not crowned on this basis alone)"
    else:
        v = "positive but weak/underpowered recently"
    print(f"  {r['strategy']:<16} PF={pf} t={t} n={0 if pd.isna(n) else int(n):<5} -> {v}")
print("\nwrote recency_screen.csv")
