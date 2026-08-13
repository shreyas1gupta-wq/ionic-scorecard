import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"

p100 = pd.read_csv(f"{OUT}/UNDERLYING_PLUS_HEDGE_DAILY_100pct.csv", parse_dates=["date"]).set_index("date")
p50 = pd.read_csv(f"{OUT}/UNDERLYING_PLUS_HEDGE_DAILY_50pct.csv", parse_dates=["date"]).set_index("date")

INK, GOLD, BLUE, GREEN, GRID, MUTED, SURF = "#0b0b0b", "#c98a1a", "#2a78d6", "#15803d", "#e1e0d9", "#898781", "#fcfcfb"


def dd(s):
    return (s - s.cummax()) / s.cummax() * 100


fig, axes = plt.subplots(2, 1, figsize=(13, 8.5), dpi=150, height_ratios=[2, 1])
fig.patch.set_facecolor(SURF)

ax = axes[0]
ax.set_facecolor(SURF)
ax.axvspan(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-04-10"), color="red", alpha=0.10)
ax.plot(p100.index, p100["underlying_value"] / 1e5, color=GOLD, lw=1.6, label="NIFTY 50 only")
ax.plot(p100.index, p100["combined"] / 1e5, color=BLUE, lw=1.8, label="+ 100% hedge (daily MTM)")
ax.plot(p50.index, p50["combined"] / 1e5, color=GREEN, lw=1.5, label="+ 50% hedge (daily MTM)")
ax.set_title("DAILY mark-to-market (fixes the earlier monthly-only staleness): NIFTY 50 alone vs. + hedge, "
             "real data 2016-2026, Rs lakh [red = actual COVID window]",
             fontsize=10.3, color=INK, loc="left", fontweight="bold")
ax.grid(axis="y", color=GRID, lw=0.6)
ax.tick_params(colors=MUTED, labelsize=8)
ax.legend(fontsize=8.5, frameon=False, loc="upper left")
for s in ax.spines.values():
    s.set_visible(False)

ax = axes[1]
ax.set_facecolor(SURF)
ax.axvspan(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-04-10"), color="red", alpha=0.10)
dd_u, dd_100, dd_50 = dd(p100["underlying_value"]), dd(p100["combined"]), dd(p50["combined"])
ax.plot(p100.index, dd_u, color=GOLD, lw=1.3, label=f"NIFTY 50 only (worst {dd_u.min():.1f}%)")
ax.plot(p100.index, dd_100, color=BLUE, lw=1.4, label=f"+ 100% hedge (worst {dd_100.min():.1f}%)")
ax.plot(p50.index, dd_50, color=GREEN, lw=1.3, label=f"+ 50% hedge (worst {dd_50.min():.1f}%)")
ax.set_title("Drawdown (%), daily mark-to-market", fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.6)
ax.tick_params(colors=MUTED, labelsize=8)
ax.legend(fontsize=8.5, frameon=False, loc="lower left")
for s in ax.spines.values():
    s.set_visible(False)

fig.tight_layout()
out = f"{OUT}/DAILY_MTM_comparison_chart.png"
fig.savefig(out, facecolor=SURF, bbox_inches="tight")
print("saved:", out)
