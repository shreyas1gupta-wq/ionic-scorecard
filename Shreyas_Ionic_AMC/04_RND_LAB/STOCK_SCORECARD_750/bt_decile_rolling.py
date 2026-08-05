# -*- coding: utf-8 -*-
"""bt_decile_rolling.py - rolling-formation decile study (Principal asks, 2026-08-05).

Three changes on bt_decile_pit.py, all requested after seeing the first result:

  1. TRIMMED MEAN, 5% each side, alongside the plain mean and median. The first run showed why he
     asked: 3Y decile 3 had a +94.8% mean against a +49.0% median, so a handful of names were
     carrying that bucket. A 5%-trimmed mean is the typical outcome without letting one multibagger
     define a decile.

  2. ROLLING 1-YEAR FORMATIONS, as many as the data allows, replacing the single Mar-2025 formation.
     This is the fix for the caveat I raised on the first run: one formation is one observation, and
     a +17pp D10-D1 spread from a single draw is not evidence. Pooling ~30 monthly formations gives a
     distribution, and the per-formation hit rate ("in how many formations did D10 beat D1") is the
     number that survives a red-team.

  3. BOTH RANKING BASES: the post-gate `final` score and the pre-gate `composite_3y`. This isolates
     whether the balance-sheet gates, penalty and boost layer ADDS ranking power or destroys it. If
     the composite ranks better than the final, the gate layer is costing us and we should know.

NO-LOOKAHEAD, unchanged from bt_decile_pit: scoring is bt_pit_quant.score_asof(), the firm's
red-teamed PIT scorer. Universe as-of the formation month, fundamentals gated on available_date,
prices and ownership <= formation, regime tilt neutralised, entry lagged one session.

OVERLAPPING WINDOWS - stated because it inflates apparent significance. Monthly formations with a
1-year holding period overlap 11/12ths with their neighbours, so the ~30 formations are nowhere near
30 independent observations. The per-formation hit rate is reported for exactly this reason: it is
robust to overlap in a way that a pooled t-statistic is not. No t-stat is quoted here.

Banks results per formation as it goes, so a long run that dies mid-way loses nothing.
Outputs -> results/DECILE_ROLLING_20260805/
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

OUT = os.path.join(HERE, "results", "DECILE_ROLLING_20260805")
os.makedirs(OUT, exist_ok=True)
OBS = os.path.join(OUT, "observations.csv")

NAVY = "#1B27A3"; NT2 = "#8C95DE"; GOLD = "#F2A93C"
INK = "#16233B"; SLATE = "#6B7280"; HAIR = "#E5E7EB"; SELL = "#E0402F"

NDEC = 10
HOLD_MONTHS = 12
BASES = ["final", "composite_3y"]          # post-gate, and pre-gate
MIN_HIST_SESSIONS = 260                    # score_asof's own requirement


def trimmed_mean(x, p=0.05):
    """Mean after dropping p from EACH tail. Returns nan if trimming leaves nothing."""
    a = np.sort(np.asarray(pd.Series(x).dropna(), dtype=float))
    if len(a) == 0:
        return np.nan
    k = int(len(a) * p)
    core = a[k:len(a) - k] if len(a) > 2 * k else a
    return float(core.mean()) if len(core) else np.nan


def fwd(pxm, sym, e0, e1):
    if sym not in pxm.columns:
        return np.nan
    a, b = pxm[sym].asof(e0), pxm[sym].asof(e1)
    if pd.isna(a) or pd.isna(b) or a <= 0:
        return np.nan
    return b / a - 1


def formations(pxm):
    """Every month-end that has enough history behind it AND a full holding period ahead."""
    first_ok = pxm.index[MIN_HIST_SESSIONS - 1]
    last_ok = pxm.index.max() - pd.DateOffset(months=HOLD_MONTHS)
    me = pd.date_range(first_ok, last_ok, freq="ME")
    return [d for d in me if d >= first_ok and d <= last_ok]


def run():
    print("loading PIT panels and prices ...")
    fund, mem, sh, sect, pxm, vol, idx = B.load()
    print(f"  prices: {pxm.shape[1]} symbols, {pxm.index.min().date()} to {pxm.index.max().date()}")

    fdates = formations(pxm)
    print(f"  formations: {len(fdates)}  ({fdates[0].date()} .. {fdates[-1].date()}), "
          f"{HOLD_MONTHS}m holding")

    done = set()
    if os.path.exists(OBS):                                   # resume
        prev = pd.read_csv(OBS)
        done = set(prev["formation"].unique())
        print(f"  resuming: {len(done)} formations already banked")

    for t in fdates:
        key = str(t.date())
        if key in done:
            continue
        sc = B.score_asof(t, fund, mem, sh, sect, pxm, vol)
        if sc is None or sc.empty:
            print(f"  {key}: scorer returned nothing, skipped")
            continue
        e0 = B.next_session(pxm, t)
        end = t + pd.DateOffset(months=HOLD_MONTHS)
        e1 = pxm.index[pxm.index <= end].max()
        if e0 is None or pd.isna(e1) or e1 <= e0:
            continue
        sc = sc.copy()
        sc["fwd"] = [fwd(pxm, s, e0, e1) for s in sc["sym"]]
        sc = sc.dropna(subset=["fwd"])
        if len(sc) < 100:
            print(f"  {key}: only {len(sc)} scored+priced names, skipped")
            continue
        sc["formation"] = key
        sc["entry"] = str(e0.date()); sc["exit"] = str(e1.date())
        for basis in BASES:
            sc[f"dec_{basis}"] = pd.qcut(sc[basis].rank(method="first"), NDEC,
                                         labels=range(1, NDEC + 1)).astype(int)
        keep = ["formation", "entry", "exit", "sym", "final", "composite_3y", "fwd",
                "dec_final", "dec_composite_3y"]
        sc[keep].to_csv(OBS, mode="a", header=not os.path.exists(OBS), index=False)
        print(f"  {key}: n={len(sc)}  banked")

    # ---------------- aggregate -----------------------------------------------------
    obs = pd.read_csv(OBS)
    print(f"\npooled observations: {len(obs)} across {obs['formation'].nunique()} formations")

    summary, tables = {}, {}
    for basis in BASES:
        col = f"dec_{basis}"
        g = obs.groupby(col, observed=True)["fwd"]
        tab = pd.DataFrame({
            "n": g.size(),
            "mean": (g.mean() * 100).round(2),
            "trim5": (g.apply(lambda x: trimmed_mean(x, 0.05)) * 100).round(2),
            "median": (g.median() * 100).round(2),
            "hit_pos": (g.apply(lambda x: (x > 0).mean()) * 100).round(1),
        })
        # per-formation D10 - D1, on the trimmed mean: the overlap-robust consistency stat
        per = []
        for f, sub in obs.groupby("formation"):
            a = sub[sub[col] == 1]["fwd"]; b = sub[sub[col] == NDEC]["fwd"]
            if len(a) and len(b):
                per.append(dict(formation=f,
                                d1=trimmed_mean(a) * 100, d10=trimmed_mean(b) * 100,
                                spread=(trimmed_mean(b) - trimmed_mean(a)) * 100))
        per = pd.DataFrame(per)
        ic = obs[[basis, "fwd"]].corr(method="spearman").iloc[0, 1]
        summary[basis] = dict(
            pooled_n=int(len(obs)), formations=int(obs["formation"].nunique()),
            d1_trim5=float(tab.loc[1, "trim5"]), d10_trim5=float(tab.loc[NDEC, "trim5"]),
            spread_trim5_pp=round(float(tab.loc[NDEC, "trim5"] - tab.loc[1, "trim5"]), 2),
            spread_mean_pp=round(float(tab.loc[NDEC, "mean"] - tab.loc[1, "mean"]), 2),
            spearman_ic=round(float(ic), 4),
            monotonic_trim5=bool((tab["trim5"].diff().dropna() > 0).all()),
            formations_d10_beat_d1=int((per["spread"] > 0).sum()) if len(per) else 0,
            formations_total=int(len(per)),
            hit_rate_pct=round(float((per["spread"] > 0).mean() * 100), 1) if len(per) else None,
            median_formation_spread_pp=round(float(per["spread"].median()), 2) if len(per) else None,
            worst_formation_spread_pp=round(float(per["spread"].min()), 2) if len(per) else None,
        )
        tables[basis] = tab
        per.to_csv(os.path.join(OUT, f"per_formation_{basis}.csv"), index=False)

        print(f"\n=== ranking basis: {basis}")
        print(tab.to_string())
        s = summary[basis]
        print(f"  D10-D1 (trim5) = {s['spread_trim5_pp']:+.2f}pp   "
              f"(plain mean {s['spread_mean_pp']:+.2f}pp)   IC = {s['spearman_ic']:+.4f}")
        print(f"  monotonic on trim5: {s['monotonic_trim5']}")
        print(f"  D10 beat D1 in {s['formations_d10_beat_d1']}/{s['formations_total']} formations "
              f"({s['hit_rate_pct']}%)   median spread {s['median_formation_spread_pp']:+.1f}pp   "
              f"worst {s['worst_formation_spread_pp']:+.1f}pp")

    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # ---------------- chart ---------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 4.5), dpi=200, squeeze=False)
    for ax, basis in zip(axes[0], BASES):
        tab, s = tables[basis], summary[basis]
        x = tab.index.astype(int)
        ax.bar(x - 0.20, tab["trim5"], 0.40, color=NAVY, edgecolor="white", lw=0.8,
               zorder=3, label="_")
        ax.bar(x + 0.20, tab["median"], 0.40, color=NT2, edgecolor="white", lw=0.8, zorder=3)
        for xi, v in zip(x, tab["trim5"]):
            ax.text(xi - 0.20, v + 0.5, f"{v:.0f}", ha="center", fontsize=7.2, color=INK)
        ax.axhline(trimmed_mean(obs["fwd"]) * 100, color=GOLD, lw=1.4, ls=(0, (4, 2)), zorder=4)
        ttl = "post-gate score (final)" if basis == "final" else "pre-gate composite"
        ax.set_title(ttl, fontsize=11.5, color=INK, fontweight="bold", loc="left", pad=9)
        ax.text(0.01, 0.955,
                f"{s['formations']} rolling formations, {HOLD_MONTHS}m hold, pooled n={s['pooled_n']}",
                transform=ax.transAxes, fontsize=8, color=SLATE)
        ax.text(0.01, 0.895,
                f"D10-D1 {s['spread_trim5_pp']:+.1f}pp   IC {s['spearman_ic']:+.3f}   "
                f"D10>D1 in {s['hit_rate_pct']:.0f}% of formations",
                transform=ax.transAxes, fontsize=8, color=SLATE)
        ax.set_xticks(range(1, 11))
        ax.set_xlabel("score decile  (1 = lowest, 10 = highest)", fontsize=8.6, color=SLATE)
        ax.set_ylabel("forward return, %", fontsize=8.8, color=SLATE)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(HAIR)
        ax.grid(axis="y", color=HAIR, lw=0.7, zorder=0); ax.set_axisbelow(True)
        ax.tick_params(length=0, labelsize=8.2, colors=SLATE)
    axes[0][0].text(0.01, 0.83, "dark = 5% trimmed mean     light = median",
                    transform=axes[0][0].transAxes, fontsize=7.8, color=SLATE)

    fig.text(0.005, 0.02,
             "Point-in-time rescore at every month-end with a full holding period ahead; entry "
             "lagged one session. Overlapping windows mean these formations are NOT independent, so "
             "the per-formation hit rate is reported and no t-statistic is quoted. Quant score only; "
             "the analyst layer cannot be reconstructed historically.",
             fontsize=7.4, color=SLATE)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.885, bottom=0.185, wspace=0.18)
    p = os.path.join(OUT, "decile_rolling.png")
    fig.savefig(p, facecolor="white")
    print("\nwrote", p)


if __name__ == "__main__":
    run()
