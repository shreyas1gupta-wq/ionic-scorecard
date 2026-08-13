"""
Reversal check (firm standing convention: auto-test the reverse of a strongly-negative result,
only when the effect looks DIRECTIONAL not cost-dominated). The primary vol-gate rule (sell more on
predicted-LOW, less on predicted-HIGH) was DEAD (placebo pctile 9.2%, real uplift -5.95pp vs placebo
mean +3.98pp). The raw tercile table showed mean S1-F P&L INCREASING with predicted-vol tercile
(HIGH 4021 > LOW 1516 > MID 233 Rs/day) -- the opposite sign from the intuitive rule. Test the
REVERSED sizing rule: size UP on predicted-HIGH, DOWN on predicted-LOW.
"""
import pandas as pd
import numpy as np

OUT = "c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/OPTSELL_EXT_20260731"
merged = pd.read_csv(f"{OUT}/vol_gate_s1f_joined.csv", parse_dates=['date'])

mult_reversed = {'HIGH': 2.0, 'MID': 1.0, 'LOW': 0.5}
merged['pnl_reversed'] = merged['s1f'] * merged['signal_for_next_day'].map(mult_reversed)

def metrics(pnl, label):
    pnl = pnl.values
    n = len(pnl)
    cum = np.cumsum(pnl)
    nav0 = 100000.0
    nav = nav0 + cum
    years = n / 63.0
    total_ret = (nav[-1] - nav0) / nav0
    cagr = (1 + total_ret) ** (1 / years) - 1
    peak = np.maximum.accumulate(nav)
    dd = (nav - peak) / peak
    maxdd = dd.min()
    mean = pnl.mean()
    sd = pnl.std(ddof=1)
    sharpe = mean / sd * np.sqrt(63) if sd > 0 else np.nan
    t = mean / (sd / np.sqrt(n)) if sd > 0 else np.nan
    win = (pnl > 0).mean()
    gains = pnl[pnl > 0].sum()
    losses = -pnl[pnl < 0].sum()
    pf = gains / losses if losses > 0 else np.nan
    print(f"{label:22s} n={n:4d} mean_Rs={mean:9.1f} CAGR={cagr*100:7.2f}% maxDD={maxdd*100:6.2f}% "
          f"Sharpe={sharpe:5.2f} t={t:5.2f} win={win*100:5.1f}% PF={pf:5.2f} sumRs={cum[-1]:10.0f}")
    return dict(label=label, n=n, mean_Rs=mean, cagr=cagr, maxdd=maxdd, sharpe=sharpe, t=t, win=win, pf=pf, sum_Rs=cum[-1])

print("#### FULL SPAN 2022-2025 -- baseline vs REVERSED gate (2x HIGH / 1x MID / 0.5x LOW) ####")
r_base = metrics(merged['pnl_baseline'], "baseline_1x")
r_rev = metrics(merged['pnl_reversed'], "reversed_gate")

print("\n#### split eras ####")
for era_name, mask in [("2022-2023", merged['date'] < '2024-01-01'), ("2024-2025", merged['date'] >= '2024-01-01')]:
    sub = merged[mask]
    print(f"-- {era_name} (n={len(sub)}) --")
    metrics(sub['pnl_baseline'], "baseline_1x")
    metrics(sub['pnl_reversed'], "reversed_gate")

# placebo, same block-permutation scheme
rng = np.random.default_rng(7)
labels = merged['signal_for_next_day'].values
s1f_vals = merged['s1f'].values
n = len(labels)
block = 10
block_idx = np.arange(n) // block
uniq_blocks = np.unique(block_idx)
real_uplift = r_rev['cagr'] - r_base['cagr']
placebo_uplifts = []
for draw in range(500):
    perm_order = rng.permutation(uniq_blocks)
    new_labels = np.empty(n, dtype=object)
    for new_b, old_b in zip(uniq_blocks, perm_order):
        mask_new = block_idx == new_b
        mask_old = block_idx == old_b
        L = min(mask_new.sum(), mask_old.sum())
        new_labels[np.where(mask_new)[0][:L]] = labels[np.where(mask_old)[0][:L]]
    for i in range(n):
        if new_labels[i] is None:
            new_labels[i] = 'MID'
    mult = np.array([mult_reversed[l] for l in new_labels])
    pnl_perm = s1f_vals * mult
    cum = np.cumsum(pnl_perm)
    nav = 100000.0 + cum
    years = n / 63.0
    cagr_perm = (1 + (nav[-1]-100000.0)/100000.0) ** (1/years) - 1
    placebo_uplifts.append(cagr_perm - r_base['cagr'])
placebo_uplifts = np.array(placebo_uplifts)
p95 = np.quantile(placebo_uplifts, 0.95)
pctile_of_real = (placebo_uplifts < real_uplift).mean()
print(f"\n#### PLACEBO (block=10, 500 draws) ####")
print(f"real CAGR uplift = {real_uplift*100:.2f}pp | placebo p95 = {p95*100:.2f}pp | "
      f"placebo mean = {placebo_uplifts.mean()*100:.2f}pp | real beats {pctile_of_real*100:.1f}% of placebo draws")

pd.DataFrame([r_base, r_rev]).to_csv(f"{OUT}/vol_gate_reversed_summary.csv", index=False)
with open(f"{OUT}/vol_gate_reversed_placebo.txt", "w") as f:
    f.write(f"real_cagr_uplift_pp={real_uplift*100:.4f}\nplacebo_p95_pp={p95*100:.4f}\n"
            f"placebo_mean_pp={placebo_uplifts.mean()*100:.4f}\nreal_beats_pct_of_placebo={pctile_of_real*100:.2f}\n")
print("saved vol_gate_reversed_summary.csv, vol_gate_reversed_placebo.txt")
