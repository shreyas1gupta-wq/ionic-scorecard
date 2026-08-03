import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"

panel = pd.read_csv(f"{OUT}/UNDERLYING_PLUS_HEDGE_REAL_ONLY.csv", parse_dates=["date"]).set_index("date")

INK, GOLD, BLUE, RED, GRID, MUTED, SURF = "#0b0b0b", "#c98a1a", "#2a78d6", "#b3261e", "#e1e0d9", "#898781", "#fcfcfb"


def dd(s):
    return (s - s.cummax()) / s.cummax() * 100


dd_u = dd(panel["underlying_value"])
dd_c = dd(panel["combined"])

fig, axes = plt.subplots(2, 1, figsize=(13, 8.5), dpi=150, height_ratios=[2, 1])
fig.patch.set_facecolor(SURF)

ax = axes[0]
ax.set_facecolor(SURF)
ax.axvspan(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-04-10"), color="red", alpha=0.10)
ax.plot(panel.index, panel["underlying_value"] / 1e5, color=GOLD, lw=1.6,
        label=f"NIFTY 50 only (Rs {panel['underlying_value'].iloc[-1]/1e5:.1f}L, CAGR +11.9%)")
ax.plot(panel.index, panel["combined"] / 1e5, color=BLUE, lw=1.8,
        label=f"NIFTY 50 + 100% backspread hedge (Rs {panel['combined'].iloc[-1]/1e5:.1f}L, CAGR +13.8%)")
ax.set_title("REAL OPTION DATA ONLY (2016-2026): NIFTY 50 alone vs. + backspread hedge, "
             "Rs lakh [red = actual COVID window]", fontsize=10.5, color=INK, loc="left", fontweight="bold")
ax.grid(axis="y", color=GRID, lw=0.6)
ax.tick_params(colors=MUTED, labelsize=8)
ax.legend(fontsize=8.5, frameon=False, loc="upper left")
for s in ax.spines.values():
    s.set_visible(False)

ax = axes[1]
ax.set_facecolor(SURF)
ax.axvspan(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-04-10"), color="red", alpha=0.10)
ax.plot(panel.index, dd_u, color=GOLD, lw=1.3, label=f"NIFTY 50 only (worst {dd_u.min():.1f}%, {dd_u.idxmin().date()})")
ax.plot(panel.index, dd_c, color=BLUE, lw=1.4, label=f"+ hedge (worst {dd_c.min():.1f}%, {dd_c.idxmin().date()})")
ax.fill_between(panel.index, dd_u, dd_c, where=(dd_c > dd_u), color="#15803d", alpha=0.15, interpolate=True)
ax.fill_between(panel.index, dd_u, dd_c, where=(dd_c < dd_u), color=RED, alpha=0.15, interpolate=True)
ax.set_title("Drawdown (%) — green = hedge helped, red = hedge hurt, at that point in time",
             fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.6)
ax.tick_params(colors=MUTED, labelsize=8)
ax.legend(fontsize=8.5, frameon=False, loc="lower left")
for s in ax.spines.values():
    s.set_visible(False)

fig.tight_layout()
out = f"{OUT}/UNDERLYING_PLUS_HEDGE_REAL_ONLY_chart.png"
fig.savefig(out, facecolor=SURF, bbox_inches="tight")
print("saved:", out)
