# -*- coding: utf-8 -*-
"""FINAL STATE: how forward growth is used now vs v1, and the score distribution v1 vs v3.
Principal, 2026-08-07.

Two v1s exist and conflating them is the easy mistake:
  v1-UNIVERSE  full750_scored.csv -- pure quant, NO forward adjustment at all.
  v1-CLIENT    compute_client_scores.py v6.2 -- the full forward adjustment, applied per client book.
The comparison below states which is which at every point.

Writes pr_template/out/v1_vs_v3_distribution.png and prints the usage table.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PRT = os.path.abspath(os.path.join(HERE, "..", "pr_template"))


def _root(p):
    while True:
        p, tail = os.path.split(p)
        if not tail:
            raise RuntimeError("root not found")
        if tail == "NIFTY 500":
            return os.path.join(p, tail)


ROOT = _root(HERE)
RES = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
OUT = os.path.join(PRT, "out", "v1_vs_v3_distribution.png")

INK, SLATE, HAIR, WHITE = "#16233B", "#6B7280", "#E5E7EB", "#FFFFFF"
NAVY, GREEN, AMBER, RED = "#1B27A3", "#1E9E6A", "#F2A93C", "#E0402F"

d = pd.read_csv(os.path.join(RES, "full750_scored_v3.csv"))
v1 = pd.to_numeric(d["final_score_3y"], errors="coerce")
v3 = pd.to_numeric(d["ionic_score_v3"], errors="coerce")
base = pd.to_numeric(d["base_score_v3"], errors="coerce")
adj = pd.to_numeric(d["forward_adjustment"], errors="coerce")
gpts = pd.to_numeric(d["fwd_growth_points"], errors="coerce")
cpts = pd.to_numeric(d["conviction_points"], errors="coerce")
ginp = pd.to_numeric(d["fwd_growth_input_pct"], errors="coerce")

# ---- 1. how forward growth is used -----------------------------------------------------------------
# With the growth leg disabled it contributes ZERO points -- but the frozen low-growth CAP still reads
# the same figure, and that cap can suppress an analyst rescue. So the forward number has not stopped
# mattering; it has stopped scoring. Worth stating explicitly, because "leg off" reads like "unused".
rescue_wanted = cpts > 0
rescue_killed = rescue_wanted & (adj <= 0)
print("HOW THE FORWARD GROWTH FIGURE IS USED")
print(f"  growth-leg points, all names        : min {gpts.min():.0f}  max {gpts.max():.0f}  "
      f"non-zero {int((gpts != 0).sum())}   <- leg DISABLED")
print(f"  conviction points                   : -6 on {int((cpts < 0).sum())}, "
      f"+6 on {int((cpts > 0).sum())}, 0 on {int((cpts == 0).sum())}")
print(f"  net adjustment range                : {adj.min():.0f} to {adj.max():.0f}")
print(f"  analyst rescues SUPPRESSED by the low-growth cap (<10% expected): "
      f"{int(rescue_killed.sum())} of {int(rescue_wanted.sum())}")
print(f"  forward growth input, 60:40         : median {ginp.median():.1f}%  "
      f"p10 {ginp.quantile(.1):.1f}%  p90 {ginp.quantile(.9):.1f}%")

print("\nSCORE DISTRIBUTION")
hdr = f"  {'band':>10s} {'v1 count':>9s} {'v1 %':>6s} {'v3 count':>9s} {'v3 %':>6s} {'change':>7s}"
print(hdr)
bands = [(0, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 101)]
rows = []
for lo, hi in bands:
    a = int(((v1 >= lo) & (v1 < hi)).sum())
    b = int(((v3 >= lo) & (v3 < hi)).sum())
    rows.append((f"{lo}-{hi if hi <= 100 else 100}", a, b))
    print(f"  {rows[-1][0]:>10s} {a:9d} {a/len(d)*100:5.1f}% {b:9d} {b/len(d)*100:5.1f}% "
          f"{b-a:+7d}")
print(f"  {'mean':>10s} {v1.mean():9.1f} {'':6s} {v3.mean():9.1f}")
print(f"  {'sd':>10s} {v1.std():9.1f} {'':6s} {v3.std():9.1f}")
print(f"  {'below 40':>10s} {int((v1<40).sum()):9d} {(v1<40).mean()*100:5.1f}% "
      f"{int((v3<40).sum()):9d} {(v3<40).mean()*100:5.1f}%")

# ---- 2. chart --------------------------------------------------------------------------------------
fig = plt.figure(figsize=(14.0, 6.4), dpi=190)
fig.text(0.045, 0.955, "Score distribution — v1 versus v3 final", fontsize=15,
         color=INK, fontweight="bold")
fig.text(0.045, 0.918,
         "v1 = the 750-universe quant score (no forward adjustment). v3 = base blend + conviction leg, "
         "capped [5,95]. The growth leg is off.", fontsize=8.6, color=SLATE)

ax = fig.add_axes([0.045, 0.13, 0.44, 0.72])
bins = np.arange(5, 101, 5)
ax.hist(v1.dropna(), bins=bins, alpha=0.55, color=SLATE, label=f"v1  (sd {v1.std():.1f})")
ax.hist(v3.dropna(), bins=bins, alpha=0.65, color=NAVY, label=f"v3  (sd {v3.std():.1f})")
for x, c in ((40, RED), (50, AMBER)):
    ax.axvline(x, color=c, lw=1.4, ls="--")
ax.text(40, ax.get_ylim()[1] * 0.97, " Sell bar 40", fontsize=7.5, color=RED, va="top")
ax.text(50, ax.get_ylim()[1] * 0.88, " Trim ceiling 50", fontsize=7.5, color=AMBER, va="top")
ax.set_xlabel("score", fontsize=8.5, color=SLATE); ax.set_ylabel("names", fontsize=8.5, color=SLATE)
ax.legend(frameon=False, fontsize=8.5)
ax.tick_params(labelsize=8, colors=SLATE)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

ax2 = fig.add_axes([0.555, 0.13, 0.41, 0.72])
labels = [r[0] for r in rows]
x = np.arange(len(rows)); w = 0.4
ax2.bar(x - w/2, [r[1] for r in rows], w, color=SLATE, alpha=0.7, label="v1")
ax2.bar(x + w/2, [r[2] for r in rows], w, color=NAVY, alpha=0.85, label="v3")
ax2.set_xticks(x); ax2.set_xticklabels(labels, fontsize=7.5, color=SLATE, rotation=0)
ax2.set_ylabel("names", fontsize=8.5, color=SLATE)
ax2.legend(frameon=False, fontsize=8.5)
ax2.tick_params(labelsize=8, colors=SLATE)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)
for i, (_, a, b) in enumerate(rows):
    if b - a:
        ax2.text(i, max(a, b) + 4, f"{b-a:+d}", ha="center", fontsize=7,
                 color=(GREEN if b > a else RED))

fig.text(0.045, 0.035,
         "v3 widens the tails only slightly (sd %.1f vs %.1f). The conviction leg is the whole of the "
         "forward adjustment now: -6 on an analyst Sell, +6 where the analyst rescues a quant Sell."
         % (v3.std(), v1.std()), fontsize=8.2, color=SLATE)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, facecolor=WHITE)
print("\nwrote", OUT)
