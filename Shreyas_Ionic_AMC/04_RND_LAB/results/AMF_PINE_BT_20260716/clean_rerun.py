"""Rebuild portfolio NAV + trade stats EXCLUDING trades that touch a corrupted DELISTED-
source print (single-day price ratio >4x or <0.25x, unspliced -- confirmed artifact via
MAGMA case: coin-flip between two price scales day to day, e.g. 17.60 <-> 990.00).
Treat contaminated trades as NOT TAKEN AT ALL (conservative). Recompute CAGR/Sharpe/
maxDD/per-year table + t-stat for the cleaned trade set, for all 12 cells, and diff vs raw.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
PANEL_PATH = ROOT / "datasets" / "derived" / "pit_union_panel_v1" / "close_panel_price.parquet"
BENCH_PATH = ROOT / "datasets" / "index_daily" / "nse_official_all_indices.parquet"
COST_RT = 0.0067

p = pd.read_parquet(PANEL_PATH)
p = p.sort_values(['symbol', 'date'])
p['prev_close'] = p.groupby('symbol')['close'].shift(1)
p['ratio'] = p['close'] / p['prev_close']
p['bad'] = (~p['spliced']) & ((p['ratio'] > 4) | (p['ratio'] < 0.25))
bad_set = set(zip(p.loc[p['bad'], 'symbol'], p.loc[p['bad'], 'date']))
print(f"[data] {len(bad_set)} corrupted (symbol,date) prints flagged (unspliced |ratio|>4x or <0.25x)")

close_lookup = {sym: g.set_index('date')['close'] for sym, g in p.groupby('symbol', sort=False)}

bench = pd.read_parquet(BENCH_PATH)
bench = bench[bench['index_name'] == 'Nifty 500'].copy()
bench['date'] = pd.to_datetime(bench['date'])
bench = bench.sort_values('date').drop_duplicates('date').set_index('date')['close']

cells = ["Efficiency_MACD_V1", "Efficiency_MACD_V2", "Efficiency_MACD_V3",
         "Efficiency_PPO_V1", "Efficiency_PPO_V2", "Efficiency_PPO_V3",
         "Momentum_MACD_V1", "Momentum_MACD_V2", "Momentum_MACD_V3",
         "Momentum_PPO_V1", "Momentum_PPO_V2", "Momentum_PPO_V3"]

rows = []
for cell in cells:
    led = pd.read_csv(HERE / f"ledger_{cell}.csv")
    led['entry_date'] = pd.to_datetime(led['entry_date'])
    led['exit_date'] = pd.to_datetime(led['exit_date'])
    led['contaminated'] = [
        (sym, ed) in bad_set or (sym, xd) in bad_set
        for sym, ed, xd in zip(led['symbol'], led['entry_date'], led['exit_date'])
    ]
    closed = led[~led['is_open']].copy()
    clean = closed[~closed['contaminated']].copy()
    clean['net_ret'] = clean['gross_ret'] - COST_RT
    n = len(clean)
    win_pct = (clean['net_ret'] > 0).mean() * 100 if n else np.nan
    mean_net = clean['net_ret'].mean() * 100 if n else np.nan
    std = clean['net_ret'].std(ddof=1) if n > 1 else 0.0
    tstat = (clean['net_ret'].mean() / (std / np.sqrt(n))) if (n > 1 and std > 0) else np.nan

    # rebuild daily contributions for clean trades only
    daily = {}
    for _, row in clean.iterrows():
        sym = row['symbol']
        cl = close_lookup.get(sym)
        if cl is None:
            continue
        try:
            window = cl.loc[row['entry_date']:row['exit_date']]
        except Exception:
            continue
        window = window[(window.index > row['entry_date'])]
        if len(window) == 0:
            continue
        rets = window.pct_change()
        rets.iloc[0] = (window.iloc[0] / cl.loc[:row['entry_date']].iloc[-1]) - 1.0 if len(cl.loc[:row['entry_date']]) else np.nan
        for i, (dd, gr) in enumerate(rets.items()):
            if not np.isfinite(gr):
                continue
            net = gr - (COST_RT if dd == row['exit_date'] else 0.0)
            daily.setdefault(dd, []).append(net)

    if len(daily) > 5:
        dates_sorted = sorted(daily.keys())
        port = pd.Series([np.mean(daily[d]) for d in dates_sorted], index=pd.to_datetime(dates_sorted))
        eq = (1 + port).cumprod()
        yrs = (port.index[-1] - port.index[0]).days / 365.25
        cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else np.nan
        sharpe = port.mean() / (port.std() + 1e-12) * np.sqrt(252)
        maxdd = (eq / eq.cummax() - 1).min()
        yearly = port.groupby(port.index.year).apply(lambda r: (1 + r).prod() - 1)
        bw = bench.loc[(bench.index >= port.index[0]) & (bench.index <= port.index[-1])]
        byrs = (bw.index[-1] - bw.index[0]).days / 365.25
        bench_cagr = (bw.iloc[-1] / bw.iloc[0]) ** (1 / byrs) - 1 if byrs > 0 else np.nan
    else:
        cagr = sharpe = maxdd = bench_cagr = np.nan
        yearly = pd.Series(dtype=float)

    rows.append(dict(cell=cell, n_clean_trades=n, n_dropped=len(closed) - n,
                      win_pct=round(win_pct, 2), mean_net_pct=round(mean_net, 4),
                      t_stat=round(tstat, 3) if np.isfinite(tstat) else np.nan,
                      cagr_clean_pct=round(cagr * 100, 2) if np.isfinite(cagr) else np.nan,
                      sharpe_clean=round(sharpe, 3) if np.isfinite(sharpe) else np.nan,
                      maxdd_clean_pct=round(maxdd * 100, 2) if np.isfinite(maxdd) else np.nan,
                      bench_cagr_pct=round(bench_cagr * 100, 2) if np.isfinite(bench_cagr) else np.nan,
                      vs_bench_clean=round(cagr * 100 - bench_cagr * 100, 2) if (np.isfinite(cagr) and np.isfinite(bench_cagr)) else np.nan))
    print(f"[{cell}] clean n={n} (dropped {len(closed)-n}) cagr={rows[-1]['cagr_clean_pct']} "
          f"sharpe={rows[-1]['sharpe_clean']} maxdd={rows[-1]['maxdd_clean_pct']} vs_bench={rows[-1]['vs_bench_clean']}")
    if cell in ("Efficiency_MACD_V1", "Momentum_MACD_V3"):
        print("  per-year (clean):", (yearly * 100).round(1).to_dict())

out = pd.DataFrame(rows)
out.to_csv(HERE / "results_CLEANED.csv", index=False)
print("\nWROTE results_CLEANED.csv")
print(out.to_string())
