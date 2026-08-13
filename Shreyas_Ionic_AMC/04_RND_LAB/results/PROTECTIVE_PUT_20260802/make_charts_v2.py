import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DIR = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"
LOT = 75

INK, BLUE, RED, GREEN, GRID, MUTED, SURF = "#0b0b0b", "#2a78d6", "#b3261e", "#15803d", "#e1e0d9", "#898781", "#fcfcfb"


def style(ax, title):
    ax.set_facecolor(SURF)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.tick_params(colors=MUTED, labelsize=8)
    for s in ax.spines.values():
        s.set_visible(False)


# --- 1. CREDIT_1x1 cumulative points, 1 lot ---
cr = pd.read_csv(f"{OUT_DIR}/trades_CREDIT_1x1.csv", parse_dates=["entry_date", "roll_date", "expiry"])
cr = cr.sort_values("roll_date").reset_index(drop=True)
cr["cum_pts"] = cr["net_pnl_pts"].cumsum()

fig, ax = plt.subplots(figsize=(12.5, 4.6), dpi=150)
fig.patch.set_facecolor(SURF)
ax.plot(cr["roll_date"], cr["cum_pts"], color=GREEN, lw=1.8)
ax.axhline(0, color=MUTED, lw=0.8)
ax.axvspan(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-04-10"), color="red", alpha=0.10)
ax.annotate(f"{cr['cum_pts'].iloc[-1]:+.0f} pts\n(Rs {cr['cum_pts'].iloc[-1]*LOT:+,.0f} at 1 lot)",
            (cr["roll_date"].iloc[-1], cr["cum_pts"].iloc[-1]), xytext=(6, 0),
            textcoords="offset points", fontsize=9, color=INK, va="center")
style(ax, "Bull put CREDIT spread (sell 2.5% OTM PE / buy 7.5% OTM PE, 30D, roll T-5) "
          "— cumulative pts, 1 lot [red = actual COVID window]")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/CREDIT_1x1_cumulative_1lot.png", facecolor=SURF, bbox_inches="tight")
print("saved: CREDIT_1x1_cumulative_1lot.png")

# --- 2. PROT_PUT cumulative %, 1 lot each time (return on premium paid, additive not compounded) ---
pp = pd.read_csv(f"{OUT_DIR}/trades_PROT_PUT.csv", parse_dates=["entry_date", "roll_date", "expiry"])
pp = pp.sort_values("roll_date").reset_index(drop=True)
pp["pct_return"] = pp["net_pnl_pts"] / pp["entry_px"] * 100     # return on premium paid, this rung
pp["cum_pct"] = pp["pct_return"].cumsum()                        # additive: "1 lot each time", no reinvestment

fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), dpi=150, width_ratios=[1.6, 1])
fig.patch.set_facecolor(SURF)
ax = axes[0]
ax.plot(pp["roll_date"], pp["cum_pct"], color=BLUE, lw=1.8)
ax.axhline(0, color=MUTED, lw=0.8)
ax.axvspan(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-04-10"), color="red", alpha=0.10)
ax.annotate(f"{pp['cum_pct'].iloc[-1]:+.0f}%", (pp["roll_date"].iloc[-1], pp["cum_pct"].iloc[-1]),
            xytext=(6, 0), textcoords="offset points", fontsize=9, color=INK, va="center")
style(ax, "Plain long 5% OTM PE, 1 lot each rung — cumulative % return ON PREMIUM PAID "
          "(additive, not compounded) [red = actual COVID window]")

ax = axes[1]
ax.hist(pp["pct_return"], bins=25, color=BLUE, alpha=0.75)
ax.axvline(0, color=MUTED, lw=0.8)
style(ax, f"Per-rung % return distribution (n={len(pp)}, median {pp['pct_return'].median():+.0f}%)")

fig.tight_layout()
fig.savefig(f"{OUT_DIR}/PROT_PUT_cumulative_pct_1lot.png", facecolor=SURF, bbox_inches="tight")
print("saved: PROT_PUT_cumulative_pct_1lot.png")
print(f"PROT_PUT: n={len(pp)} final cum%={pp['cum_pct'].iloc[-1]:+.1f}% | "
      f"worst single rung %={pp['pct_return'].min():+.1f}% | best={pp['pct_return'].max():+.1f}% | "
      f"mean per-rung %={pp['pct_return'].mean():+.1f}% median={pp['pct_return'].median():+.1f}%")
