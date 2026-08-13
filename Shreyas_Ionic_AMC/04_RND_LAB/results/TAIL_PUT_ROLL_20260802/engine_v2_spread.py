"""TAIL_PUT_ROLL_20260802 -- v2: 5%-OTM long put / 10%-OTM short put (bear put spread), 6M tenor.
Same capping tension as IRONFLY_LADDER: the short 10%-OTM leg finances the hedge but CAPS payoff
at the 5pct-to-10pct band -- a real crash beyond 10% OTM (COVID fell ~38%) pays no more than the
spread width. Three exit/rollover conditions on the SAME structure, isolating the management rule:
1. EXPIRY       -- passive, hold to the spread's own 180d expiry.
2. ROLLOVER_3M  -- close+refresh every ~91 calendar days regardless of market moves.
3. SIGMA3       -- monitor daily; monetize (close at market) the FIRST day cumulative spot move
   since entry breaches -3 standard deviations (entry-date trailing-50d realized vol, no
   lookahead -- fixed at entry, not updated mid-hold); else fall back to EXPIRY. This is the
   "monetize the spike" tail-hedge management explicitly flagged as untested in prior work
   (MIDCAP_OTM_PUT_20260717).
"""
import time

import numpy as np
import pandas as pd

ALL_TRADED = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
              r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache"
              r"\nifty_optidx_all_traded.parquet")
SV_EXT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
          r"\Shreyas_Ionic_AMC\04_RND_LAB\results\IRONFLY_LADDER_20260802\cache\spot_vix_ext.parquet")
OUT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
       r"\Shreyas_Ionic_AMC\04_RND_LAB\results\TAIL_PUT_ROLL_20260802")

LEG_COST_RT = 1.77
N_LEGS = 2
COST_TOTAL = LEG_COST_RT * N_LEGS
TARGET_DTE = 180
LONG_OTM_FRAC = 0.95     # buy 5% OTM
SHORT_OTM_FRAC = 0.90    # sell 10% OTM
ROLL_CALDAYS = 91
SIGMA_TRIGGER = 3.0
LAST_OK = pd.Timestamp("2026-07-03")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


MONTHLY = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
           r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache"
           r"\nifty_optidx_monthly.parquet")
MONTHLY_EXP = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
               r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache"
               r"\monthly_expiry_list.parquet")

log("loading tables...")
# MONTHLY-only table (not all_traded/all expiries) -- a far-dated (~180d) weekly is essentially
# always illiquid (real depth builds up only in a contract's final weeks); the ORIGINAL engine's
# own convention (DTE>=30 uses monthly_tbl) applies even more strongly at 180 DTE. First attempt
# used all_traded and found near-zero fills at 5%/10% OTM across huge stretches (incl. all of
# COVID Jan-Jun 2020) -- root-caused to picking thin far-out weeklies; fixed here.
tbl_raw = pd.read_parquet(MONTHLY)
tbl_raw = tbl_raw[tbl_raw["OPTION_TYP"] == "PE"].drop_duplicates(
    subset=["EXPIRY_DT", "STRIKE_PR", "TIMESTAMP"], keep="first")
tbl = tbl_raw.set_index(["EXPIRY_DT", "STRIKE_PR", "TIMESTAMP"]).sort_index()
sv = pd.read_parquet(SV_EXT).set_index("date").sort_index()
trading_days = sv.index
all_exp = sorted(pd.read_parquet(MONTHLY_EXP)["expiry"])
log(f"PE rows (monthly-only) {len(tbl_raw):,} | trading days {len(trading_days)} | "
    f"monthly expiries {len(all_exp)}")


def on_or_after(d):
    pos = trading_days.searchsorted(d)
    return trading_days[pos] if pos < len(trading_days) else None


def trading_days_between(d0, d1):
    return trading_days.searchsorted(d1) - trading_days.searchsorted(d0)


def spot_on_or_before(d):
    pos = trading_days.searchsorted(d, side="right") - 1
    if pos < 0:
        return None
    return trading_days[pos], float(sv["spot_close"].iloc[pos])


def candidate_expiries(target_dte, avail_from, expiry_list, min_dte=30, band=60, max_n=4):
    """Every listed monthly expiry within +/-band days of target_dte, closest first -- try
    several, not just the single nearest, since the nearest-to-target contract is often the
    LEAST liquid (freshest-listed, open interest hasn't built up yet)."""
    cands = [(abs((e - avail_from).days - target_dte), e) for e in expiry_list
              if (e - avail_from).days >= min_dte and abs((e - avail_from).days - target_dte) <= band]
    cands.sort(key=lambda x: x[0])
    return [e for _, e in cands[:max_n]]


def find_strike_price(expiry, target_strike, avail_from, tol_days=10):
    for off in (0, -50, 50, -100, 100, -150, 150, -200, 200, -250, 250, -300, 300, -350, 350,
                -400, 400, -450, 450, -500, 500):
        K = target_strike + off
        try:
            s = tbl.loc[(expiry, K)]["CLOSE"]
        except KeyError:
            continue
        after = s.index[s.index >= avail_from]
        if len(after) == 0:
            continue
        d = after.min()
        if (d - avail_from).days > tol_days:
            continue
        return d, K, float(s.loc[d])
    return None


def get_close(expiry, strike, date, tol_days=5):
    try:
        s = tbl.loc[(expiry, strike)]["CLOSE"]
    except KeyError:
        return None
    after = s.index[s.index >= date]
    if len(after) == 0:
        return None
    d = after.min()
    if (d - date).days > tol_days:
        return None
    return d, float(s.loc[d])


def era_of(d):
    if d < pd.Timestamp("2019-02-01"):
        return "pre2019"
    if d < pd.Timestamp("2024-10-01"):
        return "2019_2024sep"
    return "2024oct_plus"


def open_spread(avail_from):
    ref = spot_on_or_before(avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    long_target = round(ref_spot * LONG_OTM_FRAC / 50) * 50
    short_target = round(ref_spot * SHORT_OTM_FRAC / 50) * 50
    for exp in candidate_expiries(TARGET_DTE, avail_from, all_exp):
        if exp > LAST_OK:
            continue
        r_long = find_strike_price(exp, long_target, avail_from)
        if r_long is None:
            continue
        entry_date, long_K, long_prem0 = r_long
        r_short = find_strike_price(exp, short_target, entry_date, tol_days=5)
        if r_short is None:
            continue
        # small (<=5 trading day) staggered-fill tolerance for the far, thinner short leg --
        # disclosed, not a same-bar requirement; entry_date/spot_entry anchor to the LONG leg's day
        _, short_K, short_prem0 = r_short
        spot_entry_res = spot_on_or_before(entry_date)
        if spot_entry_res is None:
            continue
        _, spot_entry = spot_entry_res
        dte_actual = (exp - entry_date).days
        if dte_actual < 30 or long_K <= short_K:
            continue
        break
    else:
        return None
    row_sv = sv.loc[entry_date] if entry_date in sv.index else None
    rv50 = (float(row_sv["rv50_ann"]) / 100.0
            if row_sv is not None and not pd.isna(row_sv.get("rv50_ann", np.nan)) else np.nan)
    daily_vol = rv50 / np.sqrt(252) if np.isfinite(rv50) else np.nan
    return dict(entry_date=entry_date, expiry=exp, long_K=long_K, short_K=short_K,
                long_prem0=long_prem0, short_prem0=short_prem0,
                net_debit0=long_prem0 - short_prem0, spot_entry=spot_entry,
                dte_actual=dte_actual, daily_vol_at_entry=daily_vol,
                long_otm_pct=(spot_entry - long_K) / spot_entry,
                short_otm_pct=(spot_entry - short_K) / spot_entry)


def _finalize(pos, exit_date, long_exit, short_exit, spot_exit, exit_type, trigger_z=np.nan):
    exit_value = long_exit - short_exit
    gross = exit_value - pos["net_debit0"]
    net = gross - COST_TOTAL
    max_gain_theoretical = (pos["long_K"] - pos["short_K"]) - pos["net_debit0"]
    if exit_type == "expiry_intrinsic" and gross > max_gain_theoretical + 1e-6:
        raise AssertionError(f"physical-bound violation: gross {gross:.3f} > max {max_gain_theoretical:.3f}")
    return dict(entry_date=pos["entry_date"], expiry=pos["expiry"], exit_date=exit_date,
                long_K=pos["long_K"], short_K=pos["short_K"], net_debit0=pos["net_debit0"],
                long_otm_pct=pos["long_otm_pct"], short_otm_pct=pos["short_otm_pct"],
                spot_entry=pos["spot_entry"], spot_exit=spot_exit, exit_value=exit_value,
                gross_pnl=gross, cost=COST_TOTAL, net_pnl=net,
                hold_days=(exit_date - pos["entry_date"]).days, exit_type=exit_type,
                trigger_z=trigger_z, era=era_of(pos["entry_date"]),
                heldout_2026=pos["entry_date"] >= pd.Timestamp("2026-01-01"))


def close_at_expiry(pos):
    spres = spot_on_or_before(pos["expiry"])
    if spres is None:
        return None
    _, spot_exit = spres
    long_exit = max(pos["long_K"] - spot_exit, 0.0)
    short_exit = max(pos["short_K"] - spot_exit, 0.0)
    return _finalize(pos, pos["expiry"], long_exit, short_exit, spot_exit, "expiry_intrinsic")


def close_at_market(pos, date, exit_type, trigger_z=np.nan):
    r_long = get_close(pos["expiry"], pos["long_K"], date)
    r_short = get_close(pos["expiry"], pos["short_K"], date)
    if r_long is None or r_short is None:
        return None
    exit_date = max(r_long[0], r_short[0])
    spres = spot_on_or_before(date)
    spot_exit = spres[1] if spres else np.nan
    return _finalize(pos, exit_date, r_long[1], r_short[1], spot_exit, exit_type, trigger_z)


def find_3sigma_trigger_day(pos):
    """Walk trading days from entry to expiry; return the first day the cumulative spot move
    breaches -3 sigma of the ENTRY-DATE trailing-50d vol (fixed at entry, no mid-hold update --
    avoids a subtle lookahead where the trigger threshold itself reacts to the crash it's
    supposed to detect). None if never triggered or vol unavailable at entry."""
    if not np.isfinite(pos["daily_vol_at_entry"]) or pos["daily_vol_at_entry"] <= 0:
        return None
    start_pos = trading_days.searchsorted(pos["entry_date"])
    end_pos = trading_days.searchsorted(pos["expiry"])
    for i in range(start_pos + 1, min(end_pos, len(trading_days))):
        d = trading_days[i]
        spot_t = float(sv["spot_close"].iloc[i])
        t_elapsed = i - start_pos
        z = (spot_t / pos["spot_entry"] - 1) / (pos["daily_vol_at_entry"] * np.sqrt(t_elapsed))
        if z <= -SIGMA_TRIGGER:
            return d, z
    return None


def run_cycles(exit_fn, max_cycles=500):
    trades = []
    avail_from = trading_days[0]
    guard = 0
    n_skip = 0
    while guard < max_cycles:
        guard += 1
        pos = open_spread(avail_from)
        if pos is None:
            nxt = on_or_after(avail_from + pd.Timedelta(days=21))
            if nxt is None or nxt > LAST_OK:
                break
            avail_from = nxt
            n_skip += 1
            continue
        t = exit_fn(pos)
        if t is None:
            nxt = on_or_after(pos["expiry"] + pd.Timedelta(days=1))
            if nxt is None or nxt > LAST_OK:
                break
            avail_from = nxt
            n_skip += 1
            continue
        trades.append(t)
        nxt = on_or_after(t["exit_date"] + pd.Timedelta(days=1))
        if nxt is None or nxt > LAST_OK:
            break
        avail_from = nxt
    return pd.DataFrame(trades), n_skip


def exit_expiry(pos):
    return close_at_expiry(pos)


def exit_rollover_3m(pos):
    roll_target = pos["entry_date"] + pd.Timedelta(days=ROLL_CALDAYS)
    if roll_target >= pos["expiry"]:
        return close_at_expiry(pos)
    roll_date = on_or_after(roll_target)
    if roll_date is None or roll_date > LAST_OK or roll_date >= pos["expiry"]:
        return close_at_expiry(pos)
    t = close_at_market(pos, roll_date, "rollover_3m")
    return t if t is not None else close_at_expiry(pos)


def exit_3sigma(pos):
    trig = find_3sigma_trigger_day(pos)
    if trig is None:
        return close_at_expiry(pos)
    trig_date, z = trig
    t = close_at_market(pos, trig_date, "sigma3_monetize", trigger_z=z)
    return t if t is not None else close_at_expiry(pos)


results = {}
for name, fn in (("expiry", exit_expiry), ("rollover_3m", exit_rollover_3m), ("sigma3", exit_3sigma)):
    log(f"running {name}...")
    df, n_skip = run_cycles(fn)
    df.to_csv(f"{OUT}\\checkpoints\\trades_spread_{name}.csv", index=False)
    results[name] = df
    if len(df):
        n_years = (df["exit_date"].max() - df["entry_date"].min()).days / 365.25
        log(f"  -> {len(df)} cycles (skipped {n_skip} illiquid windows), span {df['entry_date'].min().date()}"
            f"..{df['exit_date'].max().date()} ({n_years:.2f}yr), total {df['net_pnl'].sum():.1f} pts, "
            f"mean {df['net_pnl'].mean():.1f} pts/cycle, ann. {df['net_pnl'].sum() / n_years:.1f} pts/yr")
        if name == "sigma3":
            n_triggered = (df["exit_type"] == "sigma3_monetize").sum()
            log(f"  -> 3-sigma trigger fired in {n_triggered}/{len(df)} cycles")
    else:
        log(f"  -> 0 cycles (skipped {n_skip})")

log("DONE")
