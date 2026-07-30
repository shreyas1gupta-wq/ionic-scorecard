import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
gdays = pd.read_csv(f"{OUT}/iv_gate_days.csv", parse_dates=["gate_day"]).gate_day.tolist()

IDX = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
       r"\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet")
px = pd.read_parquet(IDX, columns=["close"]).sort_index()
px["d"] = px.index.normalize()
trading_days = px["d"].drop_duplicates().sort_values().reset_index(drop=True)

def next_trading_day(d, n=1):
    pos = trading_days.searchsorted(pd.Timestamp(d))
    j = pos + n
    return trading_days.iloc[j] if 0 <= j < len(trading_days) else None

# collapse consecutive gate days into episodes; entry = first day of episode close, hold 5 trading days
episodes = []
cur_start = None
prev = None
for d in gdays:
    if cur_start is None:
        cur_start = d
    elif (d - prev).days > 5:
        episodes.append(cur_start)
        cur_start = d
    prev = d
if cur_start is not None:
    episodes.append(cur_start)

print(f"{len(episodes)} distinct episodes from {len(gdays)} gate days")
rows = []
HOLD = 5
for ep in episodes:
    entry_day = ep  # enter AT the gate day's own close (gate value known at that day's close -- no lookahead)
    exit_day = next_trading_day(entry_day, HOLD)
    if exit_day is None:
        continue
    rows.append(dict(cell="IV_TERM_CHEAP", entry_day=entry_day, exit_day=exit_day, event_day=entry_day, note="vix_pctile<=q20 & term_slope<=0"))
E = pd.DataFrame(rows)
print(E)
E.to_csv(f"{OUT}/iv_term_trade_candidates.csv", index=False)
