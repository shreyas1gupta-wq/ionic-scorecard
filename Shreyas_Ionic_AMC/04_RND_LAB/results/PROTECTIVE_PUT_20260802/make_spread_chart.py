import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DIR = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"
LOT = 75

df = pd.read_csv(f"{OUT_DIR}/trades_SPREAD_1x1.csv", parse_dates=["entry_date", "roll_date", "expiry"])
df = df.sort_values("roll_date").reset_index(drop=True)
df["cum_pts"] = df["net_pnl_pts"].cumsum()
dd_pts = df["cum_pts"] - df["cum_pts"].cummax()

INK, RED, GRID, MUTED, SURF = "#0b0b0b", "#b3261e", "#e1e0d9", "#898781", "#fcfcfb"

fig, ax = plt.subplots(figsize=(12.5, 4.6), dpi=150)
fig.patch.set_facecolor(SURF)
ax.plot(df["roll_date"], df["cum_pts"], color=RED, lw=1.8)
ax.axhline(0, color=MUTED, lw=0.8)
ax.axvspan(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-04-10"), color="red", alpha=0.08)
ax.annotate(f"{df['cum_pts'].iloc[-1]:+.0f} pts\n(Rs {df['cum_pts'].iloc[-1]*LOT:+,.0f} at 1 lot)",
            (df["roll_date"].iloc[-1], df["cum_pts"].iloc[-1]), xytext=(6, 0),
            textcoords="offset points", fontsize=9, color=INK, va="center")
ax.set_title("1:1 defined-risk put spread (buy 3% OTM PE / sell 8% OTM PE, 30D, roll T-5) "
             "— cumulative pts, 1 lot [red = actual COVID window]",
             fontsize=10, color=INK, loc="left")
ax.grid(axis="y", color=GRID, lw=0.7)
ax.tick_params(colors=MUTED, labelsize=8)
for s in ax.spines.values():
    s.set_visible(False)
fig.tight_layout()
out = f"{OUT_DIR}/SPREAD_1x1_cumulative_1lot.png"
fig.savefig(out, facecolor=SURF, bbox_inches="tight")
print("saved:", out)
