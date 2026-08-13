import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DIR = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PUTCAL_LADDER_20260802"
LOT = 75

df = pd.read_csv(f"{OUT_DIR}/trades_B_T7_90v30.csv", parse_dates=["entry_date", "roll_date", "far_exp", "near_exp"])
df = df.sort_values("roll_date").reset_index(drop=True)
df["cum_pts"] = df["net_pnl_pts"].cumsum()
df["cum_rs_1lot"] = df["cum_pts"] * LOT

dd_pts = df["cum_pts"] - df["cum_pts"].cummax()

INK, BLUE, RED, GRID, MUTED, SURF = "#0b0b0b", "#2a78d6", "#b3261e", "#e1e0d9", "#898781", "#fcfcfb"

fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), dpi=150, width_ratios=[1.6, 1])
fig.patch.set_facecolor(SURF)

ax = axes[0]
ax.set_facecolor(SURF)
ax.plot(df["roll_date"], df["cum_pts"], color=BLUE, lw=1.8)
ax.axhline(0, color=MUTED, lw=0.8)
ax.annotate(f"{df['cum_pts'].iloc[-1]:+.0f} pts\n(Rs {df['cum_rs_1lot'].iloc[-1]:+,.0f} at 1 lot)",
            (df["roll_date"].iloc[-1], df["cum_pts"].iloc[-1]), xytext=(6, 0),
            textcoords="offset points", fontsize=9, color=INK, va="center")
ax.set_title("B_T7_90v30 put calendar (buy 90D PE / sell 30D PE, roll T-7) — cumulative pts, 1 lot, raw (no sizing/compounding)",
             fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7)
ax.tick_params(colors=MUTED, labelsize=8)
for s in ax.spines.values():
    s.set_visible(False)

ax = axes[1]
ax.set_facecolor(SURF)
ax.fill_between(df["roll_date"], dd_pts, 0, color=RED, alpha=0.30, lw=0)
ax.plot(df["roll_date"], dd_pts, color=RED, lw=1.2)
ax.set_title(f"Drawdown (pts) — worst {dd_pts.min():.0f} pts (Rs {dd_pts.min()*LOT:,.0f} at 1 lot)",
             fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7)
ax.tick_params(colors=MUTED, labelsize=8)
for s in ax.spines.values():
    s.set_visible(False)

fig.tight_layout()
out = f"{OUT_DIR}/B_T7_90v30_cumulative_1lot.png"
fig.savefig(out, facecolor=SURF, bbox_inches="tight")
print("saved:", out)
print(f"n={len(df)} | final cum pts={df['cum_pts'].iloc[-1]:+.1f} | worst dd pts={dd_pts.min():.1f} | "
      f"best single rung={df['net_pnl_pts'].max():+.1f} | worst single rung={df['net_pnl_pts'].min():+.1f}")
