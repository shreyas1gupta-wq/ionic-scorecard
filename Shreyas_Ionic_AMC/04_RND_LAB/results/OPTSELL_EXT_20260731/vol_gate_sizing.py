"""
Vol-ML-gated S1-F sizing overlay. Pre-registered in PRE_REGISTRATION.md.
No chain.py / RAM-heavy loading needed -- both inputs are already-computed small daily series.
"""
import pandas as pd
import numpy as np

ROOT = "c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results"
OUT = "c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/OPTSELL_EXT_20260731"

# ---- 1. Load H3 predictions, build one row per calendar day = LAST available reading that day ----
p = pd.read_parquet(f"{ROOT}/REGIME_ML_20260730/oos_predictions.parquet").reset_index().rename(columns={'t':'ts'})
p['date'] = pd.to_datetime(p['ts'].dt.date)
p = p.dropna(subset=['p_H3_vol3_HIGH'])
last_per_day = p.sort_values('ts').groupby('date')['p_H3_vol3_HIGH'].last().reset_index()
last_per_day = last_per_day.sort_values('date').reset_index(drop=True)

# expanding no-lookahead tercile cutpoints computed on this full series (min 250 prior obs)
def expanding_tercile(series, min_obs=250):
    vals = series.values
    lo = np.full(len(vals), np.nan)
    hi = np.full(len(vals), np.nan)
    for i in range(len(vals)):
        if i < min_obs:
            continue
        hist = vals[:i]  # strictly prior, no lookahead
        lo[i] = np.quantile(hist, 1/3)
        hi[i] = np.quantile(hist, 2/3)
    return lo, hi

lo_cut, hi_cut = expanding_tercile(last_per_day['p_H3_vol3_HIGH'])
last_per_day['lo_cut'] = lo_cut
last_per_day['hi_cut'] = hi_cut
last_per_day['tercile'] = np.select(
    [last_per_day['p_H3_vol3_HIGH'] <= last_per_day['lo_cut'],
     last_per_day['p_H3_vol3_HIGH'] >= last_per_day['hi_cut']],
    ['LOW', 'HIGH'], default='MID')
last_per_day.loc[last_per_day['lo_cut'].isna(), 'tercile'] = np.nan

# signal for date t = PRIOR day's reading (shift by one row in the observed-day sequence)
last_per_day['signal_for_next_day'] = last_per_day['tercile'].shift(1)
last_per_day['signal_date'] = last_per_day['date']  # the day the reading is FROM
sig = last_per_day[['date', 'signal_for_next_day']].rename(columns={'date': 'reading_date'})

# ---- 2. Load S1-F realised daily P&L ----
b = pd.read_csv(f"{ROOT}/STACKED_BOOK_20260711/book_daily_pnl.csv")
b = b.rename(columns={'Unnamed: 0': 'date'})
b['date'] = pd.to_datetime(b['date'])
s1f = b[b['s1f'] != 0][['date', 's1f']].reset_index(drop=True).sort_values('date').reset_index(drop=True)
print(f"S1-F trade days: {len(s1f)}  span {s1f['date'].min().date()}..{s1f['date'].max().date()}")

# ---- 3. Join: for each S1-F trade date, find the most recent reading STRICTLY BEFORE that date ----
sig_sorted = sig.dropna(subset=['signal_for_next_day']).sort_values('reading_date').reset_index(drop=True)
sig_sorted['reading_date'] = sig_sorted['reading_date'].astype('datetime64[ns]')
s1f['date'] = s1f['date'].astype('datetime64[ns]')
merged = pd.merge_asof(s1f.sort_values('date'), sig_sorted, left_on='date', right_on='reading_date',
                        direction='backward', allow_exact_matches=False)
merged = merged.dropna(subset=['signal_for_next_day']).reset_index(drop=True)
print(f"S1-F trade days with a valid causal signal: {len(merged)} (dropped {len(s1f)-len(merged)} for no-prior-reading, all near series start)")
print(merged['signal_for_next_day'].value_counts())

# ---- 4. Apply sizing rule ----
mult_primary = {'LOW': 2.0, 'MID': 1.0, 'HIGH': 0.5}
mult_skip    = {'LOW': 2.0, 'MID': 1.0, 'HIGH': 0.0}
merged['pnl_baseline'] = merged['s1f']
merged['pnl_gated']    = merged['s1f'] * merged['signal_for_next_day'].map(mult_primary)
merged['pnl_gated_skip'] = merged['s1f'] * merged['signal_for_next_day'].map(mult_skip)

def metrics(pnl, label, span_days_per_year=252):
    pnl = pnl.values
    n = len(pnl)
    cum = np.cumsum(pnl)
    nav0 = 100000.0  # reference NAV base for CAGR/DD %, arbitrary but consistent across both series
    nav = nav0 + cum
    years = n / 63.0  # ~63 S1-F trade days/yr (weekly 0DTE, matches n~204/4.96y elsewhere)
    total_ret = (nav[-1] - nav0) / nav0
    cagr = (1 + total_ret) ** (1 / years) - 1 if years > 0 else np.nan
    peak = np.maximum.accumulate(nav)
    dd = (nav - peak) / peak
    maxdd = dd.min()
    mean = pnl.mean()
    sd = pnl.std(ddof=1)
    sharpe = mean / sd * np.sqrt(63) if sd > 0 else np.nan  # ann. on ~63 trade-days/yr
    t = mean / (sd / np.sqrt(n)) if sd > 0 else np.nan
    win = (pnl > 0).mean()
    gains = pnl[pnl > 0].sum()
    losses = -pnl[pnl < 0].sum()
    pf = gains / losses if losses > 0 else np.nan
    print(f"{label:22s} n={n:4d} mean_Rs={mean:9.1f} CAGR={cagr*100:6.2f}% maxDD={maxdd*100:6.2f}% "
          f"Sharpe={sharpe:5.2f} t={t:5.2f} win={win*100:5.1f}% PF={pf:5.2f} sumRs={cum[-1]:10.0f}")
    return dict(label=label, n=n, mean_Rs=mean, cagr=cagr, maxdd=maxdd, sharpe=sharpe, t=t, win=win, pf=pf, sum_Rs=cum[-1])

print("\n#### FULL SPAN 2022-01..2025-12 ####")
r_base = metrics(merged['pnl_baseline'], "baseline_1x")
r_gate = metrics(merged['pnl_gated'], "gated_2x/1x/0.5x")
r_skip = metrics(merged['pnl_gated_skip'], "gated_2x/1x/0x_skip")

print("\n#### SPLIT: build 2022-2023 vs recent 2024-2025 ####")
for era_name, era_mask in [("2022-2023", merged['date'] < '2024-01-01'), ("2024-2025", merged['date'] >= '2024-01-01')]:
    sub = merged[era_mask]
    print(f"-- {era_name} (n={len(sub)}) --")
    metrics(sub['pnl_baseline'], "baseline_1x")
    metrics(sub['pnl_gated'], "gated_2x/1x/0.5x")

print("\n#### by tercile: mean realised S1-F P&L (pre-multiplier) per bucket, both eras ####")
print(merged.groupby('signal_for_next_day')['s1f'].agg(['count', 'mean', 'std']).to_string())
print("-- 2022-2023 --")
print(merged[merged['date'] < '2024-01-01'].groupby('signal_for_next_day')['s1f'].agg(['count', 'mean']).to_string())
print("-- 2024-2025 --")
print(merged[merged['date'] >= '2024-01-01'].groupby('signal_for_next_day')['s1f'].agg(['count', 'mean']).to_string())

# ---- 5. Placebo: block-permute the tercile labels (block=10 trade days), 500 draws ----
rng = np.random.default_rng(42)
labels = merged['signal_for_next_day'].values
s1f_vals = merged['s1f'].values
n = len(labels)
block = 10
n_blocks = int(np.ceil(n / block))
block_idx = np.arange(n) // block

real_cagr_uplift = r_gate['cagr'] - r_base['cagr']
placebo_uplifts = []
uniq_blocks = np.unique(block_idx)
for draw in range(500):
    perm_order = rng.permutation(uniq_blocks)
    new_labels = np.empty(n, dtype=object)
    for new_b, old_b in zip(uniq_blocks, perm_order):
        mask_new = block_idx == new_b
        mask_old = block_idx == old_b
        # align lengths (last block may be short)
        L = min(mask_new.sum(), mask_old.sum())
        new_labels[np.where(mask_new)[0][:L]] = labels[np.where(mask_old)[0][:L]]
    # any leftover unfilled (shouldn't happen since same block structure) -> fallback MID
    for i in range(n):
        if new_labels[i] is None:
            new_labels[i] = 'MID'
    mult = np.array([mult_primary[l] for l in new_labels])
    pnl_perm = s1f_vals * mult
    # quick cagr calc inline (same convention)
    nav0 = 100000.0
    cum = np.cumsum(pnl_perm)
    nav = nav0 + cum
    years = n / 63.0
    total_ret = (nav[-1] - nav0) / nav0
    cagr_perm = (1 + total_ret) ** (1 / years) - 1
    cagr_base = r_base['cagr']
    placebo_uplifts.append(cagr_perm - cagr_base)

placebo_uplifts = np.array(placebo_uplifts)
p95 = np.quantile(placebo_uplifts, 0.95)
pctile_of_real = (placebo_uplifts < real_cagr_uplift).mean()
print(f"\n#### PLACEBO (block=10, 500 draws) ####")
print(f"real CAGR uplift = {real_cagr_uplift*100:.2f}pp | placebo p95 = {p95*100:.2f}pp | "
      f"placebo mean = {placebo_uplifts.mean()*100:.2f}pp | real beats {pctile_of_real*100:.1f}% of placebo draws")

merged.to_csv(f"{OUT}/vol_gate_s1f_joined.csv", index=False)
summary_rows = [r_base, r_gate, r_skip]
pd.DataFrame(summary_rows).to_csv(f"{OUT}/vol_gate_summary.csv", index=False)
with open(f"{OUT}/vol_gate_placebo.txt", "w") as f:
    f.write(f"real_cagr_uplift_pp={real_cagr_uplift*100:.4f}\n")
    f.write(f"placebo_p95_pp={p95*100:.4f}\n")
    f.write(f"placebo_mean_pp={placebo_uplifts.mean()*100:.4f}\n")
    f.write(f"real_beats_pct_of_placebo={pctile_of_real*100:.2f}\n")
print("\nSaved: vol_gate_s1f_joined.csv, vol_gate_summary.csv, vol_gate_placebo.txt")
