import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
S = pd.read_parquet(f"{OUT}/intraday_signal_buckets.parquet")
FWD_MIN = 120

def one_at_a_time(gate_col):
    hits = S[S[gate_col]].sort_index()
    kept = []
    next_free = None
    for t, row in hits.iterrows():
        if next_free is not None and t < next_free:
            continue
        kept.append(t)
        next_free = t + pd.Timedelta(minutes=FWD_MIN)
    return kept

all_trades = []
for g in ["G1_ML", "G2_VOV", "G3_ATRCONS"]:
    kept = one_at_a_time(g)
    print(f"{g}: {S[g].sum()} raw -> {len(kept)} non-overlapping trades")
    for t in kept:
        all_trades.append(dict(t=t, gate=g, d=S.loc[t, "d"]))

T = pd.DataFrame(all_trades)
print(T.groupby("gate").size())
print("date range:", T.t.min(), T.t.max())
T.to_parquet(f"{OUT}/intraday_trade_candidates.parquet")
print("wrote intraday_trade_candidates.parquet", len(T), "rows")
