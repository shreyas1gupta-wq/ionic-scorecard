"""
Build a pool of random (entry_day, exit_day) candidates matched on hold-length (2/3/5 trading
sessions) drawn from QUIET weeks -- outside a +/-5 trading-session buffer of any scheduled event
(BUDGET/FED/RBI/ELECTION) and outside any top10-earnings cluster window. This is the placebo
control Arm B did not run. Step 1 of 2: build candidates only (cheap, no chain.py).
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\buying")
import numpy as np
import pandas as pd
import chain

ARMB = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_VOLEXPANSION_20260731"
OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTSELL_EXT_20260731\event_reversal"

# ---- trading day calendar from the real spot index (same source Arm B's extractor uses) ----
idx = chain.load_index()
idx["day"] = pd.to_datetime(idx["trading_day"]) if "trading_day" in idx.columns else pd.to_datetime(idx.index)
trading_days = pd.Series(sorted(idx["day"].dt.normalize().unique()))
print(f"[cal] {len(trading_days)} distinct trading days, {trading_days.min().date()}..{trading_days.max().date()}")

# restrict to the window where HF weekly-option coverage is usable and leaves room for exit+expiry
LO = pd.Timestamp("2021-06-07")
HI = pd.Timestamp("2026-05-15")
cal = trading_days[(trading_days >= LO) & (trading_days <= HI)].reset_index(drop=True)
print(f"[cal] usable range {cal.min().date()}..{cal.max().date()}, n={len(cal)}")

# ---- exclusion mask: +/-5 trading sessions around any scheduled event, + earnings clusters ----
ev = pd.read_csv(f"{ARMB}/events_scheduled.csv", parse_dates=["date"])
ec = pd.read_csv(f"{ARMB}/earnings_clusters.csv", parse_dates=["start", "end"]) if len(open(f"{ARMB}/earnings_clusters.csv").read().strip()) > 10 else pd.DataFrame(columns=["start","end"])
print(f"[excl] {len(ev)} scheduled events, {len(ec)} earnings clusters")

cal_pos = {d: i for i, d in enumerate(cal)}
excluded = np.zeros(len(cal), dtype=bool)
BUF = 5
for d in ev["date"]:
    # find nearest cal index >= d (or <= d) to anchor the session-buffer even if d itself isn't a session
    pos_candidates = np.searchsorted(cal.values, np.datetime64(d))
    lo = max(0, pos_candidates - BUF)
    hi = min(len(cal), pos_candidates + BUF + 1)
    excluded[lo:hi] = True
for _, r in ec.iterrows():
    mask = (cal >= r["start"] - pd.Timedelta(days=2)) & (cal <= r["end"] + pd.Timedelta(days=2))
    excluded |= mask.values

quiet = cal[~excluded].reset_index(drop=True)
print(f"[excl] {excluded.sum()} of {len(cal)} trading days excluded (event-proximate); {len(quiet)} quiet days remain")

# ---- draw random entries per hold-length bucket, using trading-session offsets on the FULL cal ----
rng = np.random.default_rng(20260731)

def draw_bucket(hold_sessions, n_draw, label):
    # require BOTH entry and exit position to be non-excluded (entry alone is not sufficient --
    # a straddle sold entry-to-exit must have the WHOLE window clear of event contamination)
    quiet_positions = [cal_pos[d] for d in quiet
                        if (cal_pos[d] + hold_sessions) < len(cal)
                        and not excluded[cal_pos[d] + hold_sessions]]
    chosen_pos = rng.choice(quiet_positions, size=min(n_draw, len(quiet_positions)), replace=False)
    rows = []
    for p in chosen_pos:
        entry = cal.iloc[p]
        exit_ = cal.iloc[p + hold_sessions]
        rows.append(dict(cell=label, entry_day=entry, exit_day=exit_, event_day=entry,
                          note=f"placebo quiet-week, hold={hold_sessions} sessions"))
    return pd.DataFrame(rows)

pool_2d = draw_bucket(2, 80, "PLACEBO_2D")   # matches EVENT_BUDGET hold
pool_3d = draw_bucket(3, 120, "PLACEBO_3D")  # matches EVENT_FED hold
pool_5d = draw_bucket(5, 80, "PLACEBO_5D")   # matches IV_TERM_CHEAP hold

pool = pd.concat([pool_2d, pool_3d, pool_5d], ignore_index=True)
print(f"[pool] built {len(pool)} placebo candidates: {pool.groupby('cell').size().to_dict()}")

# sanity: confirm zero overlap with excluded window (entry AND exit both check)
bad = 0
excl_set = set(cal[excluded])
for _, r in pool.iterrows():
    if r["entry_day"] in excl_set or r["exit_day"] in excl_set:
        bad += 1
print(f"[sanity] {bad} pool rows with entry/exit landing on an excluded day (should be 0 or very few from buffer edge)")

pool.to_csv(f"{OUT}/placebo_candidates.csv", index=False)
print(f"[done] wrote {OUT}/placebo_candidates.csv")
