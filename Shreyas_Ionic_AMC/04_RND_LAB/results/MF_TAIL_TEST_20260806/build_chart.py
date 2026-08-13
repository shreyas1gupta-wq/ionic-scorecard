# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import numpy as np  # noqa: E402

RESULTS = (r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
           r"\.claude\worktrees\sweet-austin-283067\Shreyas_Ionic_AMC\04_RND_LAB\results\MF_TAIL_TEST_20260806")

partA = pd.read_csv(RESULTS + r"\partA_safety_factor_by_index.csv")
fm = pd.read_csv(RESULTS + r"\partBD_fund_level_metrics.csv")

fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))

# ---- Panel 1: safety-factor multiple by index x crisis, monthly-basis ----
ax = axes[0]
crisis_order = ["y2022_selloff", "y2018_19_ilfs", "covid_2020"]
crisis_labels = {"y2022_selloff": "2022\n(Oct21-Jun22)", "y2018_19_ilfs": "2018-19\n(smallcap+IL&FS)",
                 "covid_2020": "COVID\n(Jan-Jun 2020)"}
index_order = ["Nifty 50", "Nifty 500", "Nifty Midcap 150", "Nifty Smallcap 250"]
colors = {"Nifty 50": "#1f4e79", "Nifty 500": "#2e75b6", "Nifty Midcap 150": "#bf8f00",
          "Nifty Smallcap 250": "#c00000"}

x = np.arange(len(crisis_order))
width = 0.2
for i, iname in enumerate(index_order):
    sub = partA[partA["index"] == iname].set_index("crisis")
    vals = [sub.loc[c, "multiple_monthly_basis"] for c in crisis_order]
    ax.bar(x + (i - 1.5) * width, vals, width, label=iname, color=colors[iname])

ax.axhline(2.5, color="black", linestyle="--", linewidth=1.5, label="2.5x (proposed)")
ax.set_xticks(x)
ax.set_xticklabels([crisis_labels[c] for c in crisis_order])
ax.set_ylabel("Crisis MDD / Calm ES90  (monthly-return basis)")
ax.set_title("Safety-factor multiple: 2.5x vs measured\n(calm window 2023-08..2026-07)")
ax.legend(fontsize=7.5, loc="upper left")
ax.grid(axis="y", alpha=0.3)

# ---- Panel 2: ES90 vs MDD across funds ----
ax = axes[1]
ax.scatter(fm["mdd"] * 100, fm["es90"] * 100, s=10, alpha=0.35, color="#2e75b6")
lims = [fm["mdd"].min() * 100 * 1.05, 2]
ax.plot(lims, lims, color="grey", linestyle=":", linewidth=1, label="y=x reference")
ax.set_xlabel("Max Drawdown, %  (available window, <=18mo)")
ax.set_ylabel("ES90, %  (mean of worst decile of monthly returns)")
rho = fm["es90"].corr(fm["mdd"], method="spearman")
ax.set_title(f"ES90 vs MDD across {len(fm)} funds\nSpearman rho = {rho:.2f} "
             f"(worst-quintile overlap = 44%)")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

plt.tight_layout()
out_path = RESULTS + r"\tail_risk_test_chart.png"
plt.savefig(out_path, dpi=150)
print("saved:", out_path)
