import os, numpy as np, pandas as pd
OUT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/ORB_MOMENTUM50_20260707/MOM3M"
for name in ["combo1", "combo3"]:
    df = pd.read_csv(os.path.join(OUT, f"trades_{name}.csv"))
    g = df["gross_ret"]
    t = g.mean() / (g.std() / np.sqrt(len(g)))
    print(f"\n==== {name}: GROSS (pre-cost) ====")
    print(f"  N={len(df)} mean_gross={g.mean()*100:+.3f}bps? no, %={g.mean()*100:+.4f}% ({g.mean()*1e4:+.2f}bps) t-stat={t:+.2f}")
    dg = df.groupby("date")["gross_ret"].mean()
    print(f"  GROSS daily-book Sharpe (ann) = {dg.mean()/dg.std()*np.sqrt(252):+.2f}  win%={(g>0).mean()*100:.1f}")
    # long-only gross
    for sd in ["L", "S"]:
        s = df[df.side == sd]["gross_ret"]
        ts = s.mean()/(s.std()/np.sqrt(len(s)))
        print(f"  {sd}: N={len(s)} gross_mean={s.mean()*1e4:+.2f}bps t={ts:+.2f} win%={(s>0).mean()*100:.1f}")
# scale sanity + sample trades
df = pd.read_csv(os.path.join(OUT, "trades_combo3.csv"))
df["atr_pct"] = df["atr_entry"] / df["entry"] * 100
df["orwidth"] = np.nan
print("\nATR as %% of entry price: p10 %.3f p50 %.3f p90 %.3f" % (df.atr_pct.quantile(.1), df.atr_pct.median(), df.atr_pct.quantile(.9)))
print("signal_bar dist:", df.signal_bar.value_counts().sort_index().head(8).to_dict())
print("\nSAMPLE 10 trades (combo3):")
print(df.sample(10, random_state=1)[["date","symbol","side","signal_bar","entry_bar","exit_bar","exit_reason","entry","exit","atr_entry","gross_ret","net_ret"]].to_string())
# long-only book (net) quick view combo3
lo = df[df.side=="L"]
dln = lo.groupby("date")["net_ret"].mean()
print("\ncombo3 LONG-ONLY net: avg %.4f%% Sharpe %.2f win%% %.1f" % (lo.net_ret.mean()*100, dln.mean()/dln.std()*np.sqrt(252), (lo.net_ret>0).mean()*100))
