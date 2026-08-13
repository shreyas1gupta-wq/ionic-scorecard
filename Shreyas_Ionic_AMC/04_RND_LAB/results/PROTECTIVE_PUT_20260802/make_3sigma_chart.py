import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"

skip = pd.read_csv(f"{OUT}/trades_PUT_30D_3SIGMA_SKIP.csv", parse_dates=["entry_date", "roll_date", "expiry"])
skip = skip.sort_values("roll_date").reset_index(drop=True)
skip["cum_pts"] = skip["net_pnl_pts"].cumsum()

INK, BLUE, GOLD, GRID, MUTED, SURF = "#0b0b0b", "#2a78d6", "#c98a1a", "#e1e0d9", "#898781", "#fcfcfb"

fig, ax = plt.subplots(figsize=(12.5, 4.8), dpi=150)
fig.patch.set_facecolor(SURF)
ax.plot(skip["roll_date"], skip["cum_pts"], color=BLUE, lw=1.8,
        label=f"With 3-sigma skip-a-month rule ({skip['cum_pts'].iloc[-1]:+.0f} pts)")
ax.axhline(0, color=MUTED, lw=0.8)
ax.axvspan(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-04-10"), color="red", alpha=0.10)
ax.set_title("10% OTM PE, 30D, roll T-5, skip 1 cycle after a 3-sigma gain -- cumulative pts, 1 lot "
             "[red = actual COVID window]", fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7)
ax.tick_params(colors=MUTED, labelsize=8)
ax.legend(fontsize=8.5, frameon=False, loc="upper left")
for s in ax.spines.values():
    s.set_visible(False)
fig.tight_layout()
out = f"{OUT}/PUT_3SIGMA_SKIP_cumulative.png"
fig.savefig(out, facecolor=SURF, bbox_inches="tight")
print("saved:", out)
