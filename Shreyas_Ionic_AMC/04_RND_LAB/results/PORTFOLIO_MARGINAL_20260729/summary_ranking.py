import pandas as pd

OUT = r"Shreyas_Ionic_AMC/04_RND_LAB/results/PORTFOLIO_MARGINAL_20260729"
w = pd.read_csv(f"{OUT}/marginal_weight_sweep.csv")
stats = pd.read_csv(f"{OUT}/candidate_standalone_stats.csv")

rows = []
book0 = w[w.weight == 0.0].iloc[0]
for cand, g in w.groupby("candidate"):
    g = g.sort_values("weight")
    best_sh_row = g.loc[g["sharpe"].idxmax()]
    best_wm_row = g.loc[g["worst_month_pct"].idxmax()]  # least negative = best
    at10 = g[g.weight == 0.10].iloc[0]
    still_rising_sharpe = g.iloc[-1]["sharpe"] >= g.iloc[-2]["sharpe"]
    rows.append(dict(
        candidate=cand,
        best_weight_for_sharpe=best_sh_row.weight, sharpe_at_best=round(best_sh_row.sharpe, 3),
        calmar_at_bestw=round(best_sh_row.calmar, 3), maxDD_at_bestw=round(best_sh_row.maxDD_pct, 2),
        best_weight_for_worstmonth=best_wm_row.weight, worst_month_at_bestw=round(best_wm_row.worst_month_pct, 2),
        still_rising_at_w50=still_rising_sharpe,
        sharpe_w10=round(at10.sharpe, 3), delta_sharpe_w10=round(at10.sharpe - book0.sharpe, 3),
        calmar_w10=round(at10.calmar, 3), delta_calmar_w10=round(at10.calmar - book0.calmar, 3),
        worst_month_w10=round(at10.worst_month_pct, 2), delta_worst_month_w10=round(at10.worst_month_pct - book0.worst_month_pct, 2),
    ))
rank = pd.DataFrame(rows).merge(
    stats[["candidate", "family", "n", "t_stat", "corr_book_quarterly", "corr_book_monthly"]], on="candidate")
rank = rank.sort_values("delta_sharpe_w10", ascending=False)
rank.to_csv(f"{OUT}/summary_ranking.csv", index=False)
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
print(rank.to_string(index=False))
