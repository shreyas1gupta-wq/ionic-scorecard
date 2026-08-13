import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
C = pd.read_csv(f"{OUT}/cells.csv")

placebo_p = {"G2_VOV": 0.4635}  # Welch t-test vs matched random-time-of-day ungated baseline, n=624
C["placebo_p"] = C["cell"].map(placebo_p)
C["placebo_note"] = C["cell"].map({
    "G2_VOV": "random entry, same hhmm distribution, n=624, ungated: mean net -6.47 vs gated -5.43 (NOT sig diff)",
})
C["placebo_note"] = C["placebo_note"].fillna("not run (no positive/robust candidate to promote here; see FINDINGS)")

entry_gate_desc = {
    "G1_ML": "p_H3_vol3_HIGH>=q90(build-era) [REGIME_ML_20260730 head]",
    "G2_VOV": "rv_back15/trailing20d-same-time spike_ratio>=q90(build-era)",
    "G3_ATRCONS": "atr_consumed(day range/ATR20)>=1.00 (fixed)",
    "EVENT_BUDGET": "T-2d before Union Budget, exit T close",
    "EVENT_RBI": "T-2d before RBI MPC decision, exit T close",
    "EVENT_FED": "T-2d before FOMC decision, exit T+1 close (IST lag)",
    "EVENT_ELECTION": "T-2d before election result day, exit T close",
    "EVENT_EARNCLUSTER": "T-2d before >=3-of-top10-NIFTY-wt earnings cluster start, exit start+3d",
    "POSTCRASH": ">=2xATR20 close-to-close shock day, entry T+1, hold 2d",
    "IV_TERM_CHEAP": "India VIX pctile(expanding,10yr)<=q20(build-era) & monthly term_slope<=0, hold 5d",
}
C["entry_gate"] = C["cell"].map(entry_gate_desc)
C["dte_note"] = np.where(C["structure"] == "STRADDLE_ATM_120MIN", "0-6 DTE weekly (2hr intraday hold)",
                          "weekly, DTE picked >= hold+1 (see script)")

cols = ["cell","entry_gate","structure","dte_note","mean_dte","n","trades_per_yr","win_pct",
        "mean_gross_pts","mean_net_pts","median_net_pts","sd_net","t_stat","avg_RR",
        "breakeven_hitrate_1_over_1plusR","realized_minus_implied_mean","realized_minus_implied_median",
        "n_pre_oct2024","mean_net_pre","n_post_oct2024","mean_net_post","n_heldout2026","mean_net_heldout",
        "max_single_trade_share_of_profit","placebo_p","placebo_note"]
C = C[cols].sort_values("t_stat", ascending=False)
C.to_csv(f"{OUT}/cells.csv", index=False)
print(C.to_string(index=False))
