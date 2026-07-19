"""
Gold as static crisis-hedge diversifier vs the firm's actual 0DTE short-vol book P&L.
Kabir Anand (Hedging & Tail Risk), 2026-07-18.

Short-vol book: intraday_options_strategy/results/v2_portfolio_daily.csv
  (0DTE/near-DTE NIFTY short straddle, audited per intraday_options_strategy/results/AUDIT.md;
   NOTE: IV multiplier calibrated only 2021-05->2026; 2015-2020 segment (incl. COVID) runs on
   extrapolated m(DTE) -- audit's own words: "do not quote a single blended Sharpe", segment eras.)
Gold: datasets/etf_gold_silver/goldbees_daily_ext.parquet (2013-2026, GOLDBEES daily OHLCV)

No lookahead: this is a diagnostic/historical characterization (realized daily P&L vs realized
gold return), same class as /stress-replay -- not a trading signal, no PIT concern.
"""
import pandas as pd
import numpy as np

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\GOLD_SHORTVOL_DIVERSIFIER_20260718"

# ---------- Load short-vol book ----------
sv = pd.read_csv(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\results\v2_portfolio_daily.csv")
sv['Date'] = pd.to_datetime(sv['Date'])
sv = sv.sort_values('Date').reset_index(drop=True)
sv['prior_capital'] = sv['Running_Capital'] - sv['Daily_PnL']
sv['sv_ret'] = sv['Daily_PnL'] / sv['prior_capital']

# ---------- Load gold ----------
g = pd.read_parquet(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets\etf_gold_silver\goldbees_daily_ext.parquet")
g = g.rename(columns={'timestamp': 'Date'})
g['Date'] = pd.to_datetime(g['Date']).dt.tz_localize(None) if g['Date'].dt.tz is not None else pd.to_datetime(g['Date'])
g = g.sort_values('Date').reset_index(drop=True)
g['gold_ret'] = g['close'].pct_change()

# ---------- Merge ----------
m = pd.merge(sv[['Date', 'Daily_PnL', 'sv_ret', 'Cumulative_PnL', 'Running_Capital']],
             g[['Date', 'gold_ret']], on='Date', how='inner').dropna(subset=['sv_ret', 'gold_ret'])
m = m.sort_values('Date').reset_index(drop=True)

print(f"Short-vol book date range: {sv['Date'].min().date()} -> {sv['Date'].max().date()}  n={len(sv)}")
print(f"Gold date range: {g['Date'].min().date()} -> {g['Date'].max().date()}  n={len(g)}")
print(f"Merged (both present) n={len(m)}, range {m['Date'].min().date()} -> {m['Date'].max().date()}")
print(f"Dropped from sv (no gold match): {len(sv) - len(m)}")

# ---------- (a) Correlation ----------
full_corr = m['sv_ret'].corr(m['gold_ret'])
print(f"\nFull-sample corr(sv_ret, gold_ret): {full_corr:.4f}")

sv_down = m[m['sv_ret'] < 0]
corr_svdown = sv_down['sv_ret'].corr(sv_down['gold_ret'])
print(f"Corr on short-vol LOSS days only (n={len(sv_down)}): {corr_svdown:.4f}")

# worst-day buckets
for pct in [0.05, 0.02, 0.01]:
    thresh = m['sv_ret'].quantile(pct)
    worst = m[m['sv_ret'] <= thresh]
    print(f"Worst {pct*100:.0f}% of short-vol days (n={len(worst)}, sv_ret<= {thresh:.4%}): "
          f"mean sv_ret={worst['sv_ret'].mean():.4%}, mean gold_ret={worst['gold_ret'].mean():.4%}, "
          f"gold win-rate on these days={ (worst['gold_ret']>0).mean():.1%}")

# ---------- Drawdown episodes on the short-vol book ----------
m['equity'] = (1 + m['sv_ret']).cumprod()
m['peak'] = m['equity'].cummax()
m['dd'] = m['equity'] / m['peak'] - 1

# find distinct drawdown episodes (trough-to-trough), report top 5 by depth
dd = m[['Date', 'dd', 'equity', 'peak']].copy()
in_dd = dd['dd'] < -0.001
episodes = []
start = None
for i, row in dd.iterrows():
    if row['dd'] < -0.001 and start is None:
        start = i
    if row['dd'] >= -0.001 and start is not None:
        seg = dd.loc[start:i]
        trough_idx = seg['dd'].idxmin()
        episodes.append((dd.loc[start, 'Date'], dd.loc[trough_idx, 'Date'], dd.loc[i, 'Date'], seg['dd'].min()))
        start = None
if start is not None:
    seg = dd.loc[start:]
    trough_idx = seg['dd'].idxmin()
    episodes.append((dd.loc[start, 'Date'], dd.loc[trough_idx, 'Date'], dd.iloc[-1]['Date'], seg['dd'].min()))

episodes_df = pd.DataFrame(episodes, columns=['dd_start', 'dd_trough', 'dd_end', 'depth']).sort_values('depth')
print("\nTop 8 short-vol book drawdown episodes (by depth):")
print(episodes_df.head(8).to_string(index=False))
episodes_df.to_csv(f"{OUT}/shortvol_drawdown_episodes.csv", index=False)

# gold return over each of the top episodes' start->trough window
print("\nGold return over the short-vol book's worst 5 episodes (dd_start -> dd_trough):")
top5 = episodes_df.head(5)
for _, r in top5.iterrows():
    win = m[(m['Date'] >= r['dd_start']) & (m['Date'] <= r['dd_trough'])]
    gold_cum = (1 + win['gold_ret']).prod() - 1
    sv_cum = (1 + win['sv_ret']).prod() - 1
    print(f"  {r['dd_start'].date()} -> {r['dd_trough'].date()}: sv book {sv_cum:+.2%} (dd {r['depth']:+.2%}), gold {gold_cum:+.2%}")

# ---------- Specific named crisis episodes ----------
def window_stats(name, d0, d1):
    win = m[(m['Date'] >= d0) & (m['Date'] <= d1)]
    if len(win) == 0:
        print(f"{name}: NO OVERLAP with short-vol book data")
        return
    sv_cum = (1 + win['sv_ret']).prod() - 1
    gold_cum = (1 + win['gold_ret']).prod() - 1
    print(f"{name} ({d0}->{d1}, n={len(win)} days): short-vol book {sv_cum:+.2%}, gold {gold_cum:+.2%}")

print("\nNamed crisis-episode check (short-vol book vs gold, SAME dates):")
window_stats("COVID crash", "2020-01-20", "2020-03-24")
window_stats("2022 H1 drawdown", "2022-01-01", "2022-06-30")

# ---------- (b) Blended-book simulation ----------
def perf_stats(ret_series, label):
    eq = (1 + ret_series).cumprod()
    n_years = len(ret_series) / 252
    cagr = eq.iloc[-1] ** (1 / n_years) - 1
    ann_vol = ret_series.std() * np.sqrt(252)
    sharpe = (ret_series.mean() * 252) / ann_vol if ann_vol > 0 else np.nan
    peak = eq.cummax()
    dd = (eq / peak - 1)
    maxdd = dd.min()
    calmar = cagr / abs(maxdd) if maxdd != 0 else np.nan
    return {'label': label, 'CAGR': cagr, 'AnnVol': ann_vol, 'Sharpe': sharpe, 'MaxDD': maxdd, 'Calmar': calmar}

results = [perf_stats(m['sv_ret'], 'short-vol book ALONE')]
for w in [0.05, 0.10, 0.15]:
    blend_ret = (1 - w) * m['sv_ret'] + w * m['gold_ret']
    results.append(perf_stats(blend_ret, f'blend {int(w*100)}% gold / {int((1-w)*100)}% short-vol (daily-rebalanced)'))

res_df = pd.DataFrame(results)
print("\nBlended-book comparison (full sample, daily-rebalanced weights):")
print(res_df.to_string(index=False))
res_df.to_csv(f"{OUT}/blended_book_comparison.csv", index=False)

# Also run the blend ONLY over the post-2021-05 "calibrated IV" era (audit's more reliable segment)
m_cal = m[m['Date'] >= '2021-05-01'].reset_index(drop=True)
results_cal = [perf_stats(m_cal['sv_ret'], 'short-vol book ALONE (calibrated-IV era, 2021-05+)')]
for w in [0.05, 0.10, 0.15]:
    blend_ret = (1 - w) * m_cal['sv_ret'] + w * m_cal['gold_ret']
    results_cal.append(perf_stats(blend_ret, f'blend {int(w*100)}% gold (calibrated-IV era, 2021-05+)'))
res_cal_df = pd.DataFrame(results_cal)
print("\nBlended-book comparison, CALIBRATED-IV ERA ONLY (2021-05 onward, audit's reliable segment):")
print(res_cal_df.to_string(index=False))
res_cal_df.to_csv(f"{OUT}/blended_book_comparison_calibrated_era.csv", index=False)

m.to_csv(f"{OUT}/merged_daily_series.csv", index=False)
print(f"\nSaved: merged_daily_series.csv, shortvol_drawdown_episodes.csv, blended_book_comparison.csv, blended_book_comparison_calibrated_era.csv in {OUT}")
