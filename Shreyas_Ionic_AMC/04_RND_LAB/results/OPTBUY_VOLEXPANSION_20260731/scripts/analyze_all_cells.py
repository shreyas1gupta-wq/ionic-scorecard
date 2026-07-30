"""Master analysis: costs, gross/net, era splits, t-stats, realized-minus-implied distribution,
for all 10 pre-registered cells. Writes cells.csv + trades_all.parquet.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"

LOT = 65
FEE_PER_SIDE = 25.0 / LOT          # 0.3846 premium pts
SLIP_PER_SIDE = 0.5
COST_PER_SIDE = FEE_PER_SIDE + SLIP_PER_SIDE   # 0.8846
N_SIDES = 4                         # straddle = 2 legs x (entry+exit) = 4 fills
TOTAL_COST = N_SIDES * COST_PER_SIDE
print(f"[cost model] lot={LOT} fee/side={FEE_PER_SIDE:.4f} slip/side={SLIP_PER_SIDE} "
      f"-> {N_SIDES} sides -> TOTAL_COST={TOTAL_COST:.3f} pts/straddle round trip")

frames = []

# ---------------- intraday (120-min hold) trades
intr = pd.read_parquet(f"{OUT}/intraday_trades_raw.parquet")
intr["entry_premium"] = intr["ce_entry"] + intr["pe_entry"]
intr["exit_value"] = intr["ce_exit"] + intr["pe_exit"]
intr["gross"] = intr["exit_value"] - intr["entry_premium"]
intr["net"] = intr["gross"] - TOTAL_COST
intr["realized_move"] = (intr["spot_exit"] - intr["spot_entry"]).abs()
intr["breakeven_pts"] = intr["entry_premium"] + TOTAL_COST
intr["realized_minus_implied"] = intr["realized_move"] - intr["breakeven_pts"]
intr["cell"] = intr["gate"]
intr["entry_day"] = pd.to_datetime(intr["t"]).dt.normalize()
intr["dte"] = (pd.to_datetime(intr["expiry"]) - intr["entry_day"]).dt.days
intr["structure"] = "STRADDLE_ATM_120MIN"
frames.append(intr[["cell", "entry_day", "gross", "net", "realized_move", "breakeven_pts",
                     "realized_minus_implied", "dte", "structure", "entry_premium"]])

# ---------------- EOD (event/postcrash) trades
eod = pd.read_parquet(f"{OUT}/eod_trades_raw.parquet")
eod["entry_premium"] = eod["ce_entry"] + eod["pe_entry"]
eod["exit_value"] = eod["ce_exit"] + eod["pe_exit"]
eod["gross"] = eod["exit_value"] - eod["entry_premium"]
eod["net"] = eod["gross"] - TOTAL_COST
eod["realized_move"] = (eod["spot_exit"] - eod["spot_entry"]).abs()
eod["breakeven_pts"] = eod["entry_premium"] + TOTAL_COST
eod["realized_minus_implied"] = eod["realized_move"] - eod["breakeven_pts"]
eod["entry_day"] = pd.to_datetime(eod["entry_day"])
eod["dte"] = (pd.to_datetime(eod["expiry"]) - eod["entry_day"]).dt.days
eod["structure"] = "STRADDLE_ATM_EOD_MULTIDAY"
frames.append(eod[["cell", "entry_day", "gross", "net", "realized_move", "breakeven_pts",
                    "realized_minus_implied", "dte", "structure", "entry_premium"]])

# ---------------- IV term cheap trades
ivt = pd.read_parquet(f"{OUT}/ivterm_trades_raw.parquet")
ivt["entry_premium"] = ivt["ce_entry"] + ivt["pe_entry"]
ivt["exit_value"] = ivt["ce_exit"] + ivt["pe_exit"]
ivt["gross"] = ivt["exit_value"] - ivt["entry_premium"]
ivt["net"] = ivt["gross"] - TOTAL_COST
ivt["realized_move"] = (ivt["spot_exit"] - ivt["spot_entry"]).abs()
ivt["breakeven_pts"] = ivt["entry_premium"] + TOTAL_COST
ivt["realized_minus_implied"] = ivt["realized_move"] - ivt["breakeven_pts"]
ivt["entry_day"] = pd.to_datetime(ivt["entry_day"])
ivt["dte"] = (pd.to_datetime(ivt["expiry"]) - ivt["entry_day"]).dt.days
ivt["structure"] = "STRADDLE_ATM_EOD_MULTIDAY"
frames.append(ivt[["cell", "entry_day", "gross", "net", "realized_move", "breakeven_pts",
                    "realized_minus_implied", "dte", "structure", "entry_premium"]])

ALL = pd.concat(frames, ignore_index=True)
ALL.to_parquet(f"{OUT}/trades_all.parquet")
print(f"\n[all trades] {len(ALL)} rows across {ALL['cell'].nunique()} cells")

BUILD_END = pd.Timestamp("2024-10-01")
HELDOUT = pd.Timestamp("2026-01-01")

def era_stats(g):
    pre = g[g.entry_day < BUILD_END]
    post = g[(g.entry_day >= BUILD_END) & (g.entry_day < HELDOUT)]
    ho = g[g.entry_day >= HELDOUT]
    def m(x):
        return round(float(x["net"].mean()), 3) if len(x) else np.nan
    return len(pre), m(pre), len(post), m(post), len(ho), m(ho)

rows = []
for cell, g in ALL.groupby("cell"):
    n = len(g)
    yrs = max((g.entry_day.max() - g.entry_day.min()).days / 365.25, 0.1)
    win = (g["net"] > 0).mean()
    mean_net = g["net"].mean()
    mean_gross = g["gross"].mean()
    med_net = g["net"].median()
    sd = g["net"].std(ddof=1) if n > 1 else np.nan
    tstat = mean_net / (sd / np.sqrt(n)) if sd and sd > 0 else np.nan
    wins = g.loc[g["net"] > 0, "net"]
    losses = g.loc[g["net"] <= 0, "net"]
    R = (wins.mean() / abs(losses.mean())) if len(wins) and len(losses) and losses.mean() != 0 else np.nan
    breakeven_hit_rate_null = 1 / (1 + R) if R and np.isfinite(R) else np.nan
    n_pre, m_pre, n_post, m_post, n_ho, m_ho = era_stats(g)
    rows.append(dict(
        cell=cell, structure=g["structure"].iloc[0], n=n, trades_per_yr=round(n / yrs, 1),
        mean_dte=round(g["dte"].mean(), 1), win_pct=round(win * 100, 1),
        mean_gross_pts=round(mean_gross, 3), mean_net_pts=round(mean_net, 3),
        median_net_pts=round(med_net, 3), sd_net=round(sd, 3) if sd == sd else np.nan,
        t_stat=round(tstat, 2) if tstat == tstat else np.nan,
        avg_RR=round(R, 2) if R == R else np.nan,
        breakeven_hitrate_1_over_1plusR=round(breakeven_hit_rate_null * 100, 1) if breakeven_hit_rate_null == breakeven_hit_rate_null else np.nan,
        realized_minus_implied_mean=round(g["realized_minus_implied"].mean(), 3),
        realized_minus_implied_median=round(g["realized_minus_implied"].median(), 3),
        n_pre_oct2024=n_pre, mean_net_pre=m_pre, n_post_oct2024=n_post, mean_net_post=m_post,
        n_heldout2026=n_ho, mean_net_heldout=m_ho,
        max_single_trade_share_of_profit=round(
            (g.loc[g["net"] > 0, "net"].max() / g.loc[g["net"] > 0, "net"].sum() * 100)
            if (g["net"] > 0).any() else np.nan, 1),
    ))

C = pd.DataFrame(rows).sort_values("t_stat", ascending=False)
C.to_csv(f"{OUT}/cells.csv", index=False)
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
print(C.to_string(index=False))

m = len(C)
from scipy.stats import norm
bar = norm.ppf(1 - 0.025 / m)
print(f"\n[Bonferroni] m={m} cells -> two-sided alpha/m = {0.05/m:.5f} -> |t| bar (asymptotic normal) ~= {bar:.2f}")
