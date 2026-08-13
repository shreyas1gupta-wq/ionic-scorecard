# -*- coding: utf-8 -*-
"""bt_decile_pit.py - DECILE forward returns on a point-in-time rescore (Principal ask 2026-08-05).

"Recompute score 1y back for all stocks and show decile-wise returns. No lookahead bias."
Plus, on his follow-up: March-to-March, and a 3-year window if the data allows.

WHY THIS REUSES bt_pit_quant RATHER THAN RESCORING FRESH
--------------------------------------------------------
`bt_pit_quant.score_asof()` is already the firm's red-teamed no-lookahead scorer (v2 after Nikhil's
review, ADVERSARIAL_REVIEWS.md 2026-07-20). Its discipline: universe = N500 members as-of the
formation month from the 42-snapshot survivorship file; fundamentals = latest annual whose
available_date <= formation, per symbol; price pillars from prices <= formation; ownership from
shareholding available <= formation; regime tilt neutralised because the historical regime call
cannot be reconstructed. Writing a second scorer would mean re-earning that discipline, and the
usual way lookahead enters a study is a well-meant rewrite.

This file adds only: decile bucketing, the forward-return leg, and the honesty accounting below.

ENTRY AND EXIT
  Entry is the session AFTER the formation date (+1 lag, so a score computed on close t cannot be
  traded at close t). Exit is the last session at or before the window end. Both legs use the same
  Adj Close panel, so corporate actions are handled identically on both sides.

FUNDAMENTAL STALENESS - THE ONE THING TO READ BEFORE QUOTING A NUMBER
  The annual PIT panels (ratios/balance-sheet/P&L) carry available_date only to 2023-11-30. That is
  NOT lookahead - it is the opposite, staleness - but it bites the two windows very differently:

    formation 2023-03-31 -> newest available fundamentals are FY2022, filed ~Nov-2022, ~4 months
                            stale. FAITHFUL: close to what the live engine would have seen.
    formation 2025-03-31 -> still FY2022/FY2023, i.e. 16 months or more stale. VALID point-in-time,
                            but the fundamental pillars are older than the live engine would use, so
                            the 1-year read is a test of a DEGRADED version of the score.

  The script measures and prints the actual median staleness per window rather than asserting it.
  Treat the 3-year window as the primary result and the 1-year window as indicative.

Outputs -> results/DECILE_PIT_<stamp>/: deciles.csv, summary.json, decile_chart.png
"""
import json
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bt_pit_quant as B                                              # noqa: E402

OUT = os.path.join(HERE, "results", "DECILE_PIT_20260805")
os.makedirs(OUT, exist_ok=True)

NAVY = "#1B27A3"; NT2 = "#8C95DE"; NT3 = "#C9CEF0"; GOLD = "#F2A93C"
INK = "#16233B"; SLATE = "#6B7280"; HAIR = "#E5E7EB"; SELL = "#E0402F"

# (label, formation, window end). March-to-March per the Principal.
WINDOWS = [
    ("3-year  Mar-2023 to Mar-2026", "2023-03-31", "2026-03-31"),
    ("1-year  Mar-2025 to Mar-2026", "2025-03-31", "2026-03-31"),
]
NDEC = 10


def fwd_return(pxm, sym, e0, e1):
    if e0 is None or e1 is None or sym not in pxm.columns:
        return np.nan
    a = pxm[sym].asof(e0)
    b = pxm[sym].asof(e1)
    if pd.isna(a) or pd.isna(b) or a <= 0:
        return np.nan
    return b / a - 1


def staleness(fund, syms, t):
    """Median months between the newest available fundamental and the formation date."""
    ages = []
    for s in syms:
        g = fund.get(s)
        if g is None:
            continue
        av = g[g["avail"] <= t]["avail"]
        if len(av):
            ages.append((pd.Timestamp(t) - av.max()).days / 30.44)
    return float(np.median(ages)) if ages else np.nan


def run():
    print("loading PIT panels and prices (752 price files, takes a few minutes) ...")
    fund, mem, sh, sect, pxm, vol, idx = B.load()
    print(f"  price panel: {pxm.shape[1]} symbols, {pxm.index.min().date()} to {pxm.index.max().date()}")

    results, rows_all = {}, []
    for label, t_str, end_str in WINDOWS:
        t, end = pd.Timestamp(t_str), pd.Timestamp(end_str)
        if pxm.index.max() < end:
            print(f"SKIP {label}: price panel ends {pxm.index.max().date()}, before {end.date()}")
            continue

        sc = B.score_asof(t, fund, mem, sh, sect, pxm, vol)
        if sc is None or sc.empty:
            print(f"SKIP {label}: scorer returned nothing at {t.date()}")
            continue

        e0 = B.next_session(pxm, t)                       # +1 session entry lag
        e1 = pxm.index[pxm.index <= end].max()
        sc = sc.copy()
        sc["fwd"] = [fwd_return(pxm, s, e0, e1) for s in sc["sym"]]
        sc = sc.dropna(subset=["fwd"])
        yrs = (e1 - e0).days / 365.25

        # deciles: 1 = LOWEST score, 10 = HIGHEST. qcut on the score, ties broken by rank.
        sc["decile"] = pd.qcut(sc["final"].rank(method="first"), NDEC, labels=range(1, NDEC + 1))

        g = sc.groupby("decile", observed=True)
        tab = pd.DataFrame({
            "n": g["fwd"].size(),
            "score_lo": g["final"].min().round(1),
            "score_hi": g["final"].max().round(1),
            "score_med": g["final"].median().round(1),
            "ret_mean": (g["fwd"].mean() * 100).round(2),
            "ret_med": (g["fwd"].median() * 100).round(2),
            "cagr": (((1 + g["fwd"].mean()) ** (1 / yrs) - 1) * 100).round(2),
            "hit_pos": (g["fwd"].apply(lambda x: (x > 0).mean()) * 100).round(1),
        })

        ew = sc["fwd"].mean()
        i = idx["close"]
        i0, i1 = i.asof(e0), i.asof(e1)
        bench = (i1 / i0 - 1) if pd.notna(i0) and pd.notna(i1) else np.nan
        tab["vs_EW_pp"] = (tab["ret_mean"] - ew * 100).round(2)

        d1, d10 = tab.loc[1, "ret_mean"], tab.loc[NDEC, "ret_mean"]
        # rank correlation between decile and forward return: the honest single number for
        # "does a higher score actually mean a higher return"
        ic = sc[["final", "fwd"]].corr(method="spearman").iloc[0, 1]

        stale_m = staleness(fund, sc["sym"], t)
        results[label] = dict(
            formation=str(t.date()), entry=str(e0.date()), exit=str(e1.date()),
            years=round(yrs, 2), n=int(len(sc)),
            equal_weight_universe_pct=round(ew * 100, 2),
            nifty500_pct=round(bench * 100, 2) if pd.notna(bench) else None,
            decile1_pct=float(d1), decile10_pct=float(d10),
            spread_d10_minus_d1_pp=round(float(d10 - d1), 2),
            spearman_ic=round(float(ic), 4),
            monotonic_deciles=bool((tab["ret_mean"].diff().dropna() > 0).all()),
            median_fundamental_staleness_months=round(stale_m, 1),
        )
        tab.insert(0, "window", label)
        rows_all.append(tab.reset_index())

        print(f"\n=== {label}")
        print(f"  formation {t.date()}  entry {e0.date()}  exit {e1.date()}  "
              f"({yrs:.2f}y)  n={len(sc)}")
        print(f"  fundamentals median staleness at formation: {stale_m:.1f} months")
        print(tab.to_string())
        print(f"  equal-weight universe {ew*100:+.2f}%   Nifty 500 "
              f"{bench*100:+.2f}%" if pd.notna(bench) else "  Nifty 500 n/a")
        print(f"  D10 - D1 = {d10-d1:+.2f}pp   Spearman IC = {ic:+.4f}   "
              f"monotonic = {results[label]['monotonic_deciles']}")

    if not rows_all:
        print("no window produced a result")
        return

    allt = pd.concat(rows_all, ignore_index=True)
    allt.to_csv(os.path.join(OUT, "deciles.csv"), index=False)
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(results, f, indent=2)

    # ---- chart -------------------------------------------------------------------------
    n = len(rows_all)
    fig, axes = plt.subplots(1, n, figsize=(6.6 * n, 4.4), dpi=200, squeeze=False)
    for ax, tab in zip(axes[0], rows_all):
        lab = tab["window"].iloc[0]
        r = results[lab]
        x = tab["decile"].astype(int)
        cols = [SELL if v < 0 else NAVY for v in tab["ret_mean"]]
        ax.bar(x, tab["ret_mean"], color=cols, edgecolor="white", lw=0.8, zorder=3)
        ax.axhline(r["equal_weight_universe_pct"], color=GOLD, lw=1.4, ls=(0, (4, 2)), zorder=4)
        ax.text(10.4, r["equal_weight_universe_pct"], " equal-weight\n universe",
                fontsize=7.4, color="#B8801F", va="center", fontweight="bold")
        for xi, v in zip(x, tab["ret_mean"]):
            ax.text(xi, v + (1.5 if v >= 0 else -3.5), f"{v:.0f}", ha="center",
                    fontsize=7.6, color=INK)
        ax.set_xticks(range(1, 11))
        ax.set_xlabel("score decile   (1 = lowest score,  10 = highest)",
                      fontsize=8.6, color=SLATE)
        ax.set_ylabel("mean forward return, %", fontsize=8.8, color=SLATE)
        ax.set_title(lab, fontsize=11.5, color=INK, fontweight="bold", loc="left", pad=9)
        ax.text(0.01, 0.955, f"n={r['n']}   D10-D1 = {r['spread_d10_minus_d1_pp']:+.1f}pp   "
                             f"IC = {r['spearman_ic']:+.3f}",
                transform=ax.transAxes, fontsize=8.2, color=SLATE)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(HAIR)
        ax.grid(axis="y", color=HAIR, lw=0.7, zorder=0); ax.set_axisbelow(True)
        ax.tick_params(length=0, labelsize=8.2, colors=SLATE)
        ax.set_xlim(0.3, 11.6)

    fig.text(0.005, 0.02,
             "Point-in-time rescore: universe, fundamentals, prices and ownership all as-of the "
             "formation date; entry lagged one session. Fundamental staleness differs by window "
             "(printed per panel) because the annual PIT panels stop at Nov-2023 - stale, not "
             "lookahead. Quant score only; the analyst layer cannot be reconstructed historically.",
             fontsize=7.4, color=SLATE)
    fig.subplots_adjust(left=0.055, right=0.975, top=0.88, bottom=0.19, wspace=0.20)
    p = os.path.join(OUT, "decile_chart.png")
    fig.savefig(p, facecolor="white")
    print("\nwrote", p)
    print("wrote", os.path.join(OUT, "deciles.csv"))


if __name__ == "__main__":
    run()
