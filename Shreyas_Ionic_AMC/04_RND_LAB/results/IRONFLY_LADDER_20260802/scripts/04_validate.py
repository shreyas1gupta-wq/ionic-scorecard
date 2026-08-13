"""IRONFLY_LADDER_20260802 -- step 4: validation battery.
1. Static lookahead-leak scan (lookahead_audit.audit_code) on both engine scripts.
2. One-day-lag test on the single best cell (d300_layer_iv_lt_garch, the only cell with a
   nominally positive mean) -- sanity check only, not a claimed edge.
3. 500x random-cycle placebo for every gated cell at distance=300 (the only distance with any
   near-zero-or-positive unconditional reading; narrower distances are already cleanly negative
   and do not need a placebo to be killed).
4. Honest Bonferroni context against the wider option-buying family (~1,872 nominal cells already
   run per VALIDATION_DEBTS_20260731, this grid's 32 cells ADDED on top).
"""
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                    r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib")
from pathlib import Path
import guards as G  # noqa: E402
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                    r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib")
import lookahead_audit as LA  # noqa: E402

BASE = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
        r"\Shreyas_Ionic_AMC\04_RND_LAB\results\IRONFLY_LADDER_20260802")
SCRIPTS = f"{BASE}\\scripts"
CKPT = f"{BASE}\\checkpoints"
SCHED = f"{BASE}\\cache\\schedule.parquet"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------- 1. static code audit ----------
log("=== static lookahead-leak scan ===")
findings = []
for fname in ("02_build_schedule.py", "03_ladder_backtest.py"):
    findings += LA.audit_code(Path(f"{SCRIPTS}\\{fname}"))
print(LA.report(findings))
log(f"static scan: {len(findings)} findings (see above)")

# ---------- 2. one-day-lag test on the single best cell ----------
log("=== one-day-lag test: d300_layer_iv_lt_garch (the only cell with a positive mean) ===")
sched = pd.read_parquet(SCHED)


def run_with_lag(extra_lag_days):
    """Re-derive the iv_lt_garch filter pass/fail using GARCH/IV/RV values computed as if
    everything were known extra_lag_days LATER than actually available -- approximated here by
    shifting the filter-decision INPUTS by extra_lag_days rows in the schedule's own chronological
    order (a coarser proxy than re-running full IV/GARCH computation with a shifted cutoff, but
    sufficient to catch a same-bar/full-sample-style leak: a real edge should degrade gracefully,
    a leak should collapse). If extra_lag_days=0, use the actual as-computed columns."""
    d = sched.copy()
    if extra_lag_days > 0:
        d["iv"] = d["iv"].shift(extra_lag_days)
        d["garch_fc"] = d["garch_fc"].shift(extra_lag_days)
    passed = (d["iv"] < d["garch_fc"]).fillna(False)
    trades = pd.read_csv(f"{CKPT}\\trades_d300_layer_iv_lt_garch.csv")
    # approximate: re-weight by which roll_dates would still pass under the lagged filter
    d_dates = set(d.loc[passed, "roll_date"].astype(str))
    trades["entry_date_str"] = pd.to_datetime(trades["entry_date"]).astype(str)
    sub = trades[trades["entry_date_str"].isin(d_dates)]
    return float(sub["net_pnl"].sum()) if len(sub) else 0.0


try:
    lag_result = LA.one_day_lag_test(run_with_lag)
    print(LA.report([], lag_collapse=lag_result))
except Exception as e:
    lag_result = None
    log(f"one-day-lag test skipped: {e}")

# ---------- 3. placebo for distance=300 gated cells ----------
log("=== 500x random-cycle placebo, distance=300 gated cells ===")
rng = np.random.default_rng(20260802)
N_PLACEBO = 500
placebo_rows = []
for filt in ("iv_lt_rv50", "iv_lt_garch", "iv_pct_low"):
    tag = f"d300_layer_{filt}"
    trades = pd.read_csv(f"{CKPT}\\trades_{tag}.csv")
    n_obs = len(trades)
    observed_mean = trades["net_pnl"].mean()
    # unconditional pool = ALL d300 layer trades ever opened (same distance/roll-mode, matched on
    # count, NOT on the filter) -- the unconditional cell IS this pool
    pool = pd.read_csv(f"{CKPT}\\trades_d300_layer_unconditional.csv")
    pool_vals = pool["net_pnl"].to_numpy()
    if n_obs == 0 or len(pool_vals) < n_obs:
        log(f"{tag}: insufficient pool for placebo (n_obs={n_obs}, pool={len(pool_vals)})")
        continue
    null_means = np.array([rng.choice(pool_vals, size=n_obs, replace=False).mean()
                            for _ in range(N_PLACEBO)])
    pct_rank = float((null_means < observed_mean).mean())
    placebo_rows.append(dict(cell=tag, n=n_obs, observed_mean=observed_mean,
                              placebo_mean=null_means.mean(), placebo_pctrank=pct_rank,
                              placebo_p_twosided=2 * min(pct_rank, 1 - pct_rank)))
    log(f"{tag}: observed_mean={observed_mean:.2f} placebo_mean={null_means.mean():.2f} "
        f"pctrank={pct_rank:.3f} p={2 * min(pct_rank, 1 - pct_rank):.3f}")

pd.DataFrame(placebo_rows).to_csv(f"{BASE}\\placebo_d300.csv", index=False)

# ---------- 4. honest Bonferroni context ----------
log("=== honest multiple-comparison context ===")
best_t = 1.11  # d300_layer_iv_lt_garch, from cells.csv
n_prior_family = 1872
n_this_grid = 32
n_total_nominal = n_prior_family + n_this_grid
# Bonferroni bar approximation: t required for p<0.05/N two-sided, using normal approx
from scipy import stats
bonf_t_required = stats.norm.ppf(1 - 0.05 / (2 * n_total_nominal))
log(f"best cell t={best_t} vs Bonferroni-required t~={bonf_t_required:.2f} "
    f"(N_nominal={n_total_nominal}, matches ballpark of the firm's own m=150-481 bars elsewhere)")
log("DONE")
