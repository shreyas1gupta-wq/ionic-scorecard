"""
Secondary cross-check: realfill_deltahedged_nifty.csv (weekly-expiry delta-hedged 0DTE/DTE1 straddle,
2021-05->2026-05, no COVID coverage but real per-expiry volatility incl a -4.2% worst week) vs gold's
return over the SAME expiry-to-expiry window. This series has materially larger swings than the daily
v2_portfolio_daily.csv book (per-expiry std 0.81% vs the daily book's near-flat full-AUM-diluted moves)
-- used to sanity-check whether the primary daily-book conclusion is an artifact of that book's own
capital-denomination choice.
"""
import pandas as pd
import numpy as np

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\GOLD_SHORTVOL_DIVERSIFIER_20260718"

sv = pd.read_csv(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\results\realfill_deltahedged_nifty.csv")
sv['expiry'] = pd.to_datetime(sv['expiry'])
sv = sv.sort_values('expiry').reset_index(drop=True)
sv['sv_ret'] = sv['net_lot'] * sv['lots'] / sv['cap']
sv['entry'] = sv['expiry'].shift(1)
sv.loc[0, 'entry'] = sv.loc[0, 'expiry'] - pd.Timedelta(days=7)

g = pd.read_parquet(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\datasets\etf_gold_silver\goldbees_daily_ext.parquet")
g = g.rename(columns={'timestamp': 'Date'})
g['Date'] = pd.to_datetime(g['Date'])
g = g.sort_values('Date').reset_index(drop=True)
g = g.set_index('Date')['close']

def gold_window_ret(d0, d1):
    win = g[(g.index > d0) & (g.index <= d1)]
    if len(win) < 1:
        return np.nan
    # cumulative return from last price <= d0 to last price <= d1
    prior = g[g.index <= d0]
    if len(prior) == 0:
        return np.nan
    p0 = prior.iloc[-1]
    p1 = win.iloc[-1]
    return p1 / p0 - 1

sv['gold_ret'] = [gold_window_ret(r['entry'], r['expiry']) for _, r in sv.iterrows()]
sv = sv.dropna(subset=['gold_ret', 'sv_ret'])

print(f"Weekly book n={len(sv)}, {sv['expiry'].min().date()} -> {sv['expiry'].max().date()}")
print(f"Full-sample corr(sv_ret, gold_ret): {sv['sv_ret'].corr(sv['gold_ret']):.4f}")

worst = sv.nsmallest(10, 'sv_ret')[['expiry', 'sv_ret', 'gold_ret', 'move_pct']]
print("\nWorst 10 weeks for the delta-hedged book (expiry, sv_ret, gold_ret, underlying move_pct):")
print(worst.to_string(index=False))
worst.to_csv(f"{OUT}/weekly_worst10_deltahedged.csv", index=False)

sv_down = sv[sv['sv_ret'] < 0]
print(f"\nOn the book's LOSS weeks (n={len(sv_down)}): mean sv_ret={sv_down['sv_ret'].mean():.4%}, "
      f"mean gold_ret={sv_down['gold_ret'].mean():.4%}, gold win-rate={ (sv_down['gold_ret']>0).mean():.1%}")

# blended Sharpe/Calmar, weekly, annualize with sqrt(52)
def perf_stats_weekly(ret, label):
    eq = (1 + ret).cumprod()
    n_years = len(ret) / 52
    cagr = eq.iloc[-1] ** (1 / n_years) - 1
    ann_vol = ret.std() * np.sqrt(52)
    sharpe = ret.mean() * 52 / ann_vol
    peak = eq.cummax()
    maxdd = (eq / peak - 1).min()
    calmar = cagr / abs(maxdd) if maxdd != 0 else np.nan
    return {'label': label, 'CAGR': cagr, 'AnnVol': ann_vol, 'Sharpe': sharpe, 'MaxDD': maxdd, 'Calmar': calmar}

results = [perf_stats_weekly(sv['sv_ret'], 'delta-hedged weekly book ALONE')]
for w in [0.05, 0.10, 0.15]:
    blend = (1 - w) * sv['sv_ret'] + w * sv['gold_ret']
    results.append(perf_stats_weekly(blend, f'blend {int(w*100)}% gold / weekly book'))
res_df = pd.DataFrame(results)
print("\nBlended weekly-book comparison:")
print(res_df.to_string(index=False))
res_df.to_csv(f"{OUT}/weekly_blended_comparison.csv", index=False)

# 2022 H1 specific window on the weekly book
w22 = sv[(sv['expiry'] >= '2022-01-01') & (sv['expiry'] <= '2022-06-30')]
print(f"\n2022 H1 on weekly delta-hedged book: sv cum {(1+w22['sv_ret']).prod()-1:+.2%} over {len(w22)} expiries, "
      f"gold cum over same weeks {(1+w22['gold_ret']).prod()-1:+.2%}")
