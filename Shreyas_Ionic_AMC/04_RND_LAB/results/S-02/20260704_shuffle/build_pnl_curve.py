"""Illustrative cumulative-return curve for S-02: earnings-conditioned (c4_short_thru)
vs calendar-matched unconditional short-vol (rv_iv, base B) - same gate/match logic as
S02_shuffle.py. NOT a capital-managed portfolio backtest (no sizing/turnover model exists
for S-02 - it was killed at the statistical pre-IC gate). Sequential compounding of the
gated per-event paired returns, ordered by event exit (expiry) date, purely to visualize
the divergence already captured in the -10.1% incremental stat."""
import os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
EARN_PATH = os.path.join(ROOT, r"intraday_options_strategy\buying\stock_earnings_vol.parquet")
RVIV_PATH = os.path.join(ROOT, r"intraday_options_strategy\buying\rv_iv_vol.parquet")
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\results\S-02\20260704_shuffle")

e = pd.read_parquet(EARN_PATH)
e["earn"] = pd.to_datetime(e["earn"]); e["exp"] = pd.to_datetime(e["exp"])
e["dte"] = (e["exp"] - e["earn"]).dt.days
e["year"] = e["earn"].dt.year
r = pd.read_parquet(RVIV_PATH)
r["exit"] = pd.to_datetime(r["exit"]); r["exp"] = pd.to_datetime(r["exp"])

largecap_syms = set(e.loc[e["earn"] < "2024-01-01", "sym"].unique())
e["largecap"] = e["sym"].isin(largecap_syms)
gate = (e["dte"] >= 7) & (e["largecap"])
e_g = e[gate].copy()

e_g["exit_ym"] = e_g["exp"].dt.to_period("M")
r["exit_ym"] = r["exit"].dt.to_period("M")
r_month = r.groupby("exit_ym")["short_ret"].mean()
e_g["base_b"] = e_g["exit_ym"].map(r_month)
matched = e_g.dropna(subset=["base_b"]).sort_values("exp").reset_index(drop=True)

matched["cum_c4"] = (1 + matched["c4_short_thru"]).cumprod()
matched["cum_baseb"] = (1 + matched["base_b"]).cumprod()

matched.to_csv(os.path.join(OUT, "pnl_curve_data.csv"), index=False)

fig, ax = plt.subplots(figsize=(11,6))
ax.plot(matched["exp"], matched["cum_c4"], label="S-02 earnings-conditioned (c4_short_thru)", color="#b2182b", linewidth=1.4)
ax.plot(matched["exp"], matched["cum_baseb"], label="Unconditional short-vol, same exit months (base B)", color="#2166ac", linewidth=1.4)
ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.8)
ax.set_ylabel("Cumulative growth of Rs.1 (sequential compounding, per-event)")
ax.set_title("S-02: earnings-conditioned vs unconditional short-vol — same events, same exit months\n"
              "(ILLUSTRATIVE: per-event stat-study compounding, NOT a sized Rs.1Cr portfolio backtest)")
ax.legend(loc="upper left")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "s02_earnings_vs_unconditional.png"), dpi=140)

final_c4 = matched["cum_c4"].iloc[-1]; final_b = matched["cum_baseb"].iloc[-1]
print(f"n events (matched) = {len(matched)}")
print(f"Final cum growth - earnings-conditioned: {final_c4:.2f}x | unconditional (base B): {final_b:.2f}x")
print(f"Mean per-event: c4 {matched['c4_short_thru'].mean()*100:+.2f}% | base_b {matched['base_b'].mean()*100:+.2f}% | incremental {(matched['c4_short_thru']-matched['base_b']).mean()*100:+.2f}%")
