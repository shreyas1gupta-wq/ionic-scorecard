import pandas as pd
R = r"Shreyas_Ionic_AMC/04_RND_LAB/results"
for sig, fname in [("breakout20","stageA_breakout20_b2_ATM_trail35.csv"),
                    ("ema_cross","stageA_ema_cross_b2_ATM_trail35.csv"),
                    ("sweep_priorweek_reclaim","stageA_sweep_priorweek_reclaim_b2_ATM_trail35.csv")]:
    df = pd.read_csv(f"{R}/TREND_CATCHER_MULTIDAY_20260729/trades/{fname}")
    net = df["net_pnl"]
    gross_profit = net[net>0].sum(); gross_loss = -net[net<0].sum()
    pf = gross_profit/gross_loss if gross_loss>0 else float("inf")
    total_net = net.sum()
    top1_share = net.max()/total_net if total_net>0 else float("nan")
    top4_share = net.sort_values(ascending=False).head(4).sum()/total_net if total_net>0 else float("nan")
    print(f"{sig}: n={len(df)} net_total={total_net:,.0f} PF={pf:.2f} win_rate={(net>0).mean():.2%} top1_share={top1_share:.1%} top4_share={top4_share:.1%}")
