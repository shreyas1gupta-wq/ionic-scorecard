import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DIR = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"
LOT = 75

INK, BLUE, RED, GREEN, GOLD, GRID, MUTED, SURF = "#0b0b0b", "#2a78d6", "#b3261e", "#15803d", "#c98a1a", "#e1e0d9", "#898781", "#fcfcfb"

series = [
    ("trades_PROT_PUT.csv", "Plain long 5% OTM put", MUTED),
    ("trades_CREDIT_1x1.csv", "Credit spread (sell2.5/buy7.5, capped)", RED),
    ("trades_BACKSPREAD_1x2_10pct.csv", "Backspread (sell1x2.5/buy2x10)", GREEN),
    ("trades_LADDER_75_125.csv", "Ladder (sell1x2.5/buy7.5+12.5)", GOLD),
]

fig, ax = plt.subplots(figsize=(13, 5.2), dpi=150)
fig.patch.set_facecolor(SURF)
ax.set_facecolor(SURF)
ax.axvspan(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-04-10"), color="red", alpha=0.10, label="_nolegend_")

for fname, label, color in series:
    df = pd.read_csv(f"{OUT_DIR}/{fname}", parse_dates=["roll_date"]).sort_values("roll_date")
    df["cum_pts"] = df["net_pnl_pts"].cumsum()
    ax.plot(df["roll_date"], df["cum_pts"], color=color, lw=1.8, label=f"{label} ({df['cum_pts'].iloc[-1]:+.0f} pts)")

ax.axhline(0, color=MUTED, lw=0.8)
ax.set_title("Four put-hedge structures, cumulative points, 1 lot each (no sizing/compounding) "
             "[red = actual COVID window]", fontsize=10.5, color=INK, loc="left", fontweight="bold")
ax.grid(axis="y", color=GRID, lw=0.7)
ax.tick_params(colors=MUTED, labelsize=8)
ax.legend(fontsize=8.5, frameon=False, loc="upper left")
for s in ax.spines.values():
    s.set_visible(False)
fig.tight_layout()
out = f"{OUT_DIR}/COMPARISON_4_structures.png"
fig.savefig(out, facecolor=SURF, bbox_inches="tight")
print("saved:", out)
