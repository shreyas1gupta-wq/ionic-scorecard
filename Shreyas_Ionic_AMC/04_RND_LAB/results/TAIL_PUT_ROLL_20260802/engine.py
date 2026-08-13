"""TAIL_PUT_ROLL_20260802 -- long NIFTY 10%-OTM put, 6M tenor, ROLL every ~3M vs NO_ROLL
(hold to own expiry). Single leg, reuses the shared option-chain cache.
"""
import time

import numpy as np
import pandas as pd

ALL_TRADED = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
              r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache"
              r"\nifty_optidx_all_traded.parquet")
SV = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
      r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache\spot_vix_daily.parquet")
OUT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
       r"\Shreyas_Ionic_AMC\04_RND_LAB\results\TAIL_PUT_ROLL_20260802")

LEG_COST_RT = 1.77
TARGET_DTE = 180
OTM_FRAC = 0.90            # strike = spot * 0.90 (10% OTM put)
ROLL_CALDAYS = 91
LAST_OK = pd.Timestamp("2026-07-03")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log("loading tables...")
tbl_raw = pd.read_parquet(ALL_TRADED)
tbl_raw = tbl_raw[tbl_raw["OPTION_TYP"] == "PE"].drop_duplicates(
    subset=["EXPIRY_DT", "STRIKE_PR", "TIMESTAMP"], keep="first")
tbl = tbl_raw.set_index(["EXPIRY_DT", "STRIKE_PR", "TIMESTAMP"]).sort_index()
sv = pd.read_parquet(SV).set_index("date").sort_index()
trading_days = sv.index
all_exp = sorted(tbl_raw["EXPIRY_DT"].unique())
log(f"PE rows {len(tbl_raw):,} | trading days {len(trading_days)} | expiries {len(all_exp)}")


def on_or_after(d):
    pos = trading_days.searchsorted(d)
    return trading_days[pos] if pos < len(trading_days) else None


def spot_on_or_before(d):
    pos = trading_days.searchsorted(d, side="right") - 1
    if pos < 0:
        return None
    return trading_days[pos], float(sv["spot_close"].iloc[pos])


def find_target_expiry(target_dte, avail_from, expiry_list, min_dte=30, band_mult=2.0):
    best, bestdiff = None, 1e9
    for e in expiry_list:
        d = (e - avail_from).days
        if d < min_dte:
            continue
        if d > target_dte * band_mult:
            break
        diff = abs(d - target_dte)
        if diff < bestdiff:
            bestdiff, best = diff, e
    return best


def find_put_entry(expiry, avail_from, ref_spot, tol_days=7):
    """Nearest listed strike to ref_spot*OTM_FRAC with CONTRACTS>0 on/after avail_from.
    Returns (entry_date, strike, target_strike, close_price) or None."""
    target_strike = round(ref_spot * OTM_FRAC / 50) * 50
    for off in (0, -50, 50, -100, 100, -150, 150, -200, 200, -250, 250):
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
        return d, K, target_strike, float(s.loc[d])
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


def open_put(avail_from):
    exp = find_target_expiry(TARGET_DTE, avail_from, all_exp)
    if exp is None or exp > LAST_OK:
        return None
    ref = spot_on_or_before(avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    res = find_put_entry(exp, avail_from, ref_spot)
    if res is None:
        return None
    entry_date, K, target_K, prem0 = res
    spot_entry_res = spot_on_or_before(entry_date)
    if spot_entry_res is None:
        return None
    _, spot_entry = spot_entry_res
    dte_actual = (exp - entry_date).days
    if dte_actual < 30:
        return None
    return dict(entry_date=entry_date, expiry=exp, strike=K, target_strike=target_K,
                prem0=prem0, spot_entry=spot_entry, dte_actual=dte_actual,
                actual_otm_pct=(spot_entry - K) / spot_entry)


def close_at_expiry_intrinsic(pos):
    spres = spot_on_or_before(pos["expiry"])
    if spres is None:
        return None
    _, spot_exit = spres
    payoff = max(pos["strike"] - spot_exit, 0.0)
    return _finalize(pos, pos["expiry"], payoff, spot_exit, "expiry_intrinsic")


def close_at_market(pos, close_date):
    r = get_close(pos["expiry"], pos["strike"], close_date)
    if r is None:
        return None
    exit_date, price = r
    spres = spot_on_or_before(close_date)
    spot_exit = spres[1] if spres else np.nan
    return _finalize(pos, exit_date, price, spot_exit, "early_market_close")


def _finalize(pos, exit_date, exit_value, spot_exit, exit_type):
    gross = exit_value - pos["prem0"]
    net = gross - LEG_COST_RT
    hold_days = (exit_date - pos["entry_date"]).days
    return dict(entry_date=pos["entry_date"], expiry=pos["expiry"], exit_date=exit_date,
                strike=pos["strike"], target_strike=pos["target_strike"],
                actual_otm_pct=pos["actual_otm_pct"], spot_entry=pos["spot_entry"],
                spot_exit=spot_exit, prem0=pos["prem0"], exit_value=exit_value,
                gross_pnl=gross, cost=LEG_COST_RT, net_pnl=net, hold_days=hold_days,
                exit_type=exit_type, era=era_of(pos["entry_date"]),
                heldout_2026=pos["entry_date"] >= pd.Timestamp("2026-01-01"))


def run_no_roll(max_cycles=60):
    trades = []
    avail_from = trading_days[0]
    guard = 0
    while guard < max_cycles:
        guard += 1
        pos = open_put(avail_from)
        if pos is None:
            nxt = on_or_after(avail_from + pd.Timedelta(days=14))
            if nxt is None or nxt > LAST_OK:
                break
            avail_from = nxt
            continue
        t = close_at_expiry_intrinsic(pos)
        if t is None:
            nxt = on_or_after(pos["expiry"] + pd.Timedelta(days=1))
            if nxt is None or nxt > LAST_OK:
                break
            avail_from = nxt
            continue
        trades.append(t)
        nxt = on_or_after(t["exit_date"] + pd.Timedelta(days=1))
        if nxt is None or nxt > LAST_OK:
            break
        avail_from = nxt
    return pd.DataFrame(trades)


def run_roll_3m(max_cycles=90):
    trades = []
    avail_from = trading_days[0]
    guard = 0
    while guard < max_cycles:
        guard += 1
        pos = open_put(avail_from)
        if pos is None:
            nxt = on_or_after(avail_from + pd.Timedelta(days=14))
            if nxt is None or nxt > LAST_OK:
                break
            avail_from = nxt
            continue
        roll_target = pos["entry_date"] + pd.Timedelta(days=ROLL_CALDAYS)
        if roll_target >= pos["expiry"]:
            t = close_at_expiry_intrinsic(pos)
        else:
            roll_date = on_or_after(roll_target)
            if roll_date is None or roll_date > LAST_OK or roll_date >= pos["expiry"]:
                t = close_at_expiry_intrinsic(pos)
            else:
                t = close_at_market(pos, roll_date)
                if t is None:
                    t = close_at_expiry_intrinsic(pos)   # couldn't price the roll -- hold to expiry instead
        if t is None:
            nxt = on_or_after(avail_from + pd.Timedelta(days=95))
            if nxt is None or nxt > LAST_OK:
                break
            avail_from = nxt
            continue
        trades.append(t)
        nxt = on_or_after(t["exit_date"] + pd.Timedelta(days=1))
        if nxt is None or nxt > LAST_OK:
            break
        avail_from = nxt
    return pd.DataFrame(trades)


log("running NO_ROLL (hold to own 6M expiry)...")
no_roll = run_no_roll()
no_roll.to_csv(f"{OUT}\\checkpoints\\trades_no_roll.csv", index=False)
log(f"  -> {len(no_roll)} cycles, mean net {no_roll['net_pnl'].mean():.2f} pts, "
    f"total {no_roll['net_pnl'].sum():.2f} pts")

log("running ROLL_3M (close+refresh every ~3 months)...")
roll_3m = run_roll_3m()
roll_3m.to_csv(f"{OUT}\\checkpoints\\trades_roll_3m.csv", index=False)
log(f"  -> {len(roll_3m)} cycles, mean net {roll_3m['net_pnl'].mean():.2f} pts, "
    f"total {roll_3m['net_pnl'].sum():.2f} pts")

# actual OTM% sanity check (per MIDCAP_OTM_PUT's honest-fill disclosure convention)
for name, df in (("no_roll", no_roll), ("roll_3m", roll_3m)):
    log(f"{name}: actual entry OTM%% mean={df['actual_otm_pct'].mean():.3%} "
        f"min={df['actual_otm_pct'].min():.3%} max={df['actual_otm_pct'].max():.3%}")

log("DONE")
