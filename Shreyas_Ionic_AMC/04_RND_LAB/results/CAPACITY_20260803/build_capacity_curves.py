"""Assemble capacity_curves.csv from verified ADV extracts + STT_RECOST + STRATEGY_REGISTER numbers.
All source numbers cited inline; nothing here is invented. See FINDINGS.md for full derivation.
"""
import json
from pathlib import Path
import pandas as pd

OUT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
           r"\Shreyas_Ionic_AMC\04_RND_LAB\results\CAPACITY_20260803")

ADV_FUT = 85_664          # NIFTY near-month futures ADV20, 2026 YTD median, lots (adv_futures_daily.csv)
ADV_OPT_TIGHT_MED = 13_539_249   # 2026 YTD median of min(CE,PE) vol at ATM 0DTE strike (adv_options_expiry_daily.csv)
ADV_OPT_TIGHT_WORST = 389_104    # worst single day, tighter leg, full 2025-26 history

rows = []

# ---------------- SWEEP (SWEEP_E, swing3_trail60, 1 lot = natural unit; FUTIDX NIFTY) ----------
sweep_sizes = [("1x (registered)", 1), ("HIGH_CAGR AU=11.92", 11.92), ("40-lot benchmark (LOT_SCALING cap)", 40)]
for label, lots in sweep_sizes:
    rows.append(dict(sleeve="SWEEP (SWEEP_E swing3_trail60)", vehicle="NIFTY FUTIDX near-month",
                      size_label=label, lots=lots,
                      notional_rs=round(lots * 75 * 24124),
                      adv_lots=ADV_FUT, participation_pct=round(100 * lots / ADV_FUT, 5),
                      adv_threshold_flag="OK, <<5%/10%",
                      net_edge_pts_per_trade_OLD_STT=10.941, net_edge_pts_per_trade_NEW_STT=3.741,
                      cost_note="STT delta +7.20pts/RT applied firmwide (STT_RECOST); statutory cost "
                                 "per-lot flat or improving with size (fixed Rs20 brokerage amortised), "
                                 "no participation-based impact at this ADV%",
                      tstat_new=2.52))

# ---------------- S1-F / BOOK options leg (0DTE ATM NIFTY straddle) ----------------------------
s1f_sizes = [("1x registered standalone (3-4 lots/Rs10L)", 3.5),
             ("HIGH_CAGR naive AU=7.87 x 3-4 lots (LITERAL reading of the mandate note)", 27.6),
             ("40-lot benchmark", 40),
             ("CORRECTED: BOOK's true native unit is Rs1cr not Rs10L (see FINDINGS #3) -> "
              "78.67% weight = 0.787x native -> S1F ~2.36 lots", 2.36)]
for label, lots in s1f_sizes:
    rows.append(dict(sleeve="BOOK / S1-F (0DTE NIFTY ATM short straddle)", vehicle="NIFTY OPTIDX ATM, both legs",
                      size_label=label, lots=lots,
                      notional_rs=round(lots * 75 * 27.5),  # premium notional only, ~Rs27.5 median ATM straddle premium
                      adv_lots=ADV_OPT_TIGHT_MED, participation_pct=round(100 * lots / ADV_OPT_TIGHT_MED, 7),
                      adv_threshold_flag="OK, negligible even vs worst-day ADV "
                                         f"({round(100*lots/ADV_OPT_TIGHT_WORST,6)}%)",
                      net_edge_pts_per_trade_OLD_STT=9.71, net_edge_pts_per_trade_NEW_STT=9.655,
                      cost_note="Options STT hits premium only (1.027x ratio); edge barely moves with cost regime",
                      tstat_new=None))

df = pd.DataFrame(rows)
df.to_csv(OUT / "capacity_curves.csv", index=False)
print(df.to_string(index=False))

# ---------------- liquidity zero-crossing (10% ADV hard cap, COST_STANDARDS) --------------------
zero_cross = dict(
    sweep_10pct_adv_lots=round(0.10 * ADV_FUT),
    sweep_10pct_adv_vs_high_cagr_ratio=round(0.10 * ADV_FUT / 11.92, 0),
    s1f_10pct_adv_lots_median=round(0.10 * ADV_OPT_TIGHT_MED),
    s1f_10pct_adv_lots_worstday=round(0.10 * ADV_OPT_TIGHT_WORST),
)
json.dump(zero_cross, open(OUT / "liquidity_zero_cross.json", "w"), indent=2)
print(json.dumps(zero_cross, indent=2))
