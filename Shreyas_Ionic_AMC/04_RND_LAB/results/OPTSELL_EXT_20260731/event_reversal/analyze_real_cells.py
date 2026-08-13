import pandas as pd
import numpy as np

ARMB = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTSELL_EXT_20260731\event_reversal"
COST = 3.538  # Arm B's round-trip cost constant (Rs25/lot/side + slippage, straddle 2-leg), reused verbatim

eod = pd.read_parquet(f"{ARMB}/eod_trades_raw.parquet")
iv = pd.read_parquet(f"{ARMB}/ivterm_trades_raw.parquet")
allt = pd.concat([eod, iv], ignore_index=True)
allt["gross_pts"] = (allt["ce_exit"] + allt["pe_exit"]) - (allt["ce_entry"] + allt["pe_entry"])  # buyer's raw payoff
allt["reversed_net_pts"] = -allt["gross_pts"] - COST  # seller's net, same cost applied to the mirror side
allt["spot_move_pct"] = (allt["spot_exit"] - allt["spot_entry"]) / allt["spot_entry"] * 100
allt["entry_day"] = pd.to_datetime(allt["entry_day"])
allt["post_oct2024"] = allt["entry_day"] >= "2024-10-01"
allt["heldout2026"] = allt["entry_day"] >= "2026-01-01"

for cell in ["EVENT_BUDGET", "EVENT_FED", "IV_TERM_CHEAP"]:
    sub = allt[allt.cell == cell].sort_values("entry_day").reset_index(drop=True)
    print(f"\n{'='*90}\n{cell}  n={len(sub)}")
    print(sub[["entry_day", "exit_day", "spot_entry", "spot_exit", "spot_move_pct",
                "gross_pts", "reversed_net_pts", "note"]].to_string(index=False))
    mean_rev = sub["reversed_net_pts"].mean()
    win = (sub["reversed_net_pts"] > 0).mean() * 100
    # concentration: share of TOTAL POSITIVE profit contributed by the single best trade
    pos = sub[sub["reversed_net_pts"] > 0]["reversed_net_pts"]
    total_signed = sub["reversed_net_pts"].sum()
    conc = (sub["reversed_net_pts"].max() / total_signed * 100) if total_signed != 0 else np.nan
    t = mean_rev / (sub["reversed_net_pts"].std(ddof=1) / np.sqrt(len(sub))) if len(sub) > 1 else np.nan
    print(f"-- mean_reversed_net={mean_rev:.2f}  win%={win:.1f}  t={t:.2f}  "
          f"best-trade-share-of-net-sum={conc:.1f}%  n_pre_oct24={(~sub.post_oct2024).sum()} "
          f"n_post_oct24={(sub.post_oct2024 & ~sub.heldout2026).sum()} n_heldout2026={sub.heldout2026.sum()}")
    print(f"-- era means: pre-Oct24={sub[~sub.post_oct2024]['reversed_net_pts'].mean():.2f}  "
          f"post-Oct24(excl 2026)={sub[sub.post_oct2024 & ~sub.heldout2026]['reversed_net_pts'].mean():.2f}  "
          f"heldout2026={sub[sub.heldout2026]['reversed_net_pts'].mean() if sub.heldout2026.sum() else float('nan'):.2f}")

allt.to_csv(f"{OUT}/real_cells_reversed.csv", index=False)
print(f"\nsaved {OUT}/real_cells_reversed.csv")
