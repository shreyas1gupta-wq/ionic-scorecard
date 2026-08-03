import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"
LEVEL = ROOT + r"\results\factor_replication\20260704_perf_table\level_NIFTY50_official.csv"

LOT = 75
CAP0 = 1_000_000.0   # [ASSUMPTION] reference starting capital for a definable MaxDD %, matches the
                      # S1-F convention used elsewhere this session (Rs 10L reference)

full = pd.read_csv(f"{OUT}/BACKSPREAD_21Y_full_series.csv", parse_dates=["entry_date", "roll_date", "expiry"])
full = full.sort_values("roll_date").reset_index(drop=True)
full["equity"] = CAP0 + full["net_pnl_pts"].cumsum() * LOT
full["dd_pct"] = (full["equity"] - full["equity"].cummax()) / full["equity"].cummax() * 100

lvl = pd.read_csv(LEVEL, parse_dates=["date"]).set_index("date").sort_index()["level"]
lvl = lvl[(lvl.index >= full["roll_date"].min()) & (lvl.index <= full["roll_date"].max())]
lvl_idx = lvl / lvl.iloc[0] * 100
eq_idx = full["equity"] / full["equity"].iloc[0] * 100

INK, BLUE, GOLD, RED, GRID, MUTED, SURF = "#0b0b0b", "#2a78d6", "#c98a1a", "#b3261e", "#e1e0d9", "#898781", "#fcfcfb"

fig, axes = plt.subplots(2, 1, figsize=(13, 8.5), dpi=150, height_ratios=[2, 1])
fig.patch.set_facecolor(SURF)

ax = axes[0]
ax.set_facecolor(SURF)
real_start = full[full["source"] == "REAL"]["roll_date"].min()
ax.axvspan(full["roll_date"].min(), real_start, color=MUTED, alpha=0.08)
ax.text(full["roll_date"].min(), ax.get_ylim()[1] if ax.get_ylim()[1] else 100, "  MODELED (Black-Scholes, calibrated)",
        fontsize=8, color=MUTED, va="top")
ax.plot(full["roll_date"], eq_idx, color=BLUE, lw=1.8,
        label=f"Backspread strategy (indexed=100 at {full['roll_date'].min().date()})")
ax.plot(lvl_idx.index, lvl_idx.values, color=GOLD, lw=1.4, alpha=0.85, label="NIFTY 50 (indexed=100)")
ax.axvline(real_start, color=RED, lw=1, ls="--", alpha=0.7)
ax.annotate("real option data starts", (real_start, ax.get_ylim()[0]), fontsize=7.5, color=RED,
            xytext=(4, 4), textcoords="offset points")
ax.set_yscale("log")
ax.set_title(f"BACKSPREAD (sell 1x 2.5% OTM PE / buy 2x 10% OTM PE, 30D, roll T-5) vs NIFTY 50, "
             f"2005-2026 (log scale) [shaded = modeled pre-2016 period]",
             fontsize=10.5, color=INK, loc="left", fontweight="bold")
ax.grid(axis="y", color=GRID, lw=0.6, which="both")
ax.tick_params(colors=MUTED, labelsize=8)
ax.legend(fontsize=8.5, frameon=False, loc="upper left")
for s in ax.spines.values():
    s.set_visible(False)

ax = axes[1]
ax.set_facecolor(SURF)
ax.axvspan(full["roll_date"].min(), real_start, color=MUTED, alpha=0.08)
ax.fill_between(full["roll_date"], full["dd_pct"], 0, color=RED, alpha=0.30, lw=0)
ax.plot(full["roll_date"], full["dd_pct"], color=RED, lw=1.3)
worst_idx = full["dd_pct"].idxmin()
ax.annotate(f"worst: {full['dd_pct'].min():.1f}%\n({full.loc[worst_idx,'roll_date'].date()})",
            (full.loc[worst_idx, "roll_date"], full["dd_pct"].min()), fontsize=8, color=INK,
            xytext=(10, -6), textcoords="offset points")
ax.set_title(f"Backspread drawdown (%) on Rs {CAP0/1e5:.0f}L reference capital, 1 lot each rung",
             fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.6)
ax.tick_params(colors=MUTED, labelsize=8)
for s in ax.spines.values():
    s.set_visible(False)

fig.tight_layout()
out = f"{OUT}/BACKSPREAD_21Y_vs_NIFTY50.png"
fig.savefig(out, facecolor=SURF, bbox_inches="tight")
print("saved:", out)

yrs = (full["roll_date"].iloc[-1] - full["roll_date"].iloc[0]).days / 365.25
cagr = (full["equity"].iloc[-1] / full["equity"].iloc[0]) ** (1 / yrs) - 1
n50_yrs = (lvl.index[-1] - lvl.index[0]).days / 365.25
n50_cagr = (lvl.iloc[-1] / lvl.iloc[0]) ** (1 / n50_yrs) - 1
print(f"\n21y (2005-2026) BACKSPREAD: final Rs {full['equity'].iloc[-1]:,.0f} from Rs {CAP0:,.0f} | "
      f"CAGR {cagr:+.2%} | MaxDD {full['dd_pct'].min():+.2f}% (on Rs{CAP0/1e5:.0f}L ref capital, 1 lot only)")
print(f"NIFTY 50 (price index, same window): CAGR {n50_cagr:+.2%} | "
      f"MaxDD {((lvl-lvl.cummax())/lvl.cummax()*100).min():+.2f}%")
print(f"n rungs: {len(full)} (128 modeled 2005-2016 + 116 real 2016-2026)")
