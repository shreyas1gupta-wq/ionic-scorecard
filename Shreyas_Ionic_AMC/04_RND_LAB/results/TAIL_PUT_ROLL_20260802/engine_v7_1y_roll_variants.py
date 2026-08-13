"""TAIL_PUT_ROLL_20260802 -- v7: 1Y backspread (sell 1x5% OTM, buy 2x10% OTM), roll-before-expiry.
Real 2016-2026 option data. 4 variants: hold-to-expiry (baseline, already in v3) vs roll at
1/2/3 months before the position's own expiry (close at market, reopen a fresh 1Y backspread
immediately). Tests whether avoiding the low-vega tail (per the vega finding this session) pays
off net of the extra round-trip cost.
"""
import time

import numpy as np
import pandas as pd

MONTHLY = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
           r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache"
           r"\nifty_optidx_monthly.parquet")
MONTHLY_EXP = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
               r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache"
               r"\monthly_expiry_list.parquet")
SV = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
      r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache\spot_vix_daily.parquet")
OUT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
       r"\Shreyas_Ionic_AMC\04_RND_LAB\results\TAIL_PUT_ROLL_20260802")

LEG_COST_RT = 1.77
SHORT_OTM_FRAC = 0.95
LONG_OTM_FRAC = 0.90
TARGET_DTE = 365
LAST_OK = pd.Timestamp("2026-07-03")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log("loading tables...")
tbl_raw = pd.read_parquet(MONTHLY)
tbl_raw = tbl_raw[tbl_raw["OPTION_TYP"] == "PE"].drop_duplicates(
    subset=["EXPIRY_DT", "STRIKE_PR", "TIMESTAMP"], keep="first")
tbl = tbl_raw.set_index(["EXPIRY_DT", "STRIKE_PR", "TIMESTAMP"]).sort_index()
sv = pd.read_parquet(SV).set_index("date").sort_index()
trading_days = sv.index
all_exp = sorted(pd.read_parquet(MONTHLY_EXP)["expiry"])


def on_or_after(d):
    pos = trading_days.searchsorted(d)
    return trading_days[pos] if pos < len(trading_days) else None


def spot_on_or_before(d):
    pos = trading_days.searchsorted(d, side="right") - 1
    if pos < 0:
        return None
    return trading_days[pos], float(sv["spot_close"].iloc[pos])


def candidate_expiries(target_dte, avail_from, band=75, max_n=4):
    cands = [(abs((e - avail_from).days - target_dte), e) for e in all_exp
             if (e - avail_from).days >= 30 and abs((e - avail_from).days - target_dte) <= band]
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


def era_of(d):
    if d < pd.Timestamp("2019-02-01"):
        return "pre2019"
    if d < pd.Timestamp("2024-10-01"):
        return "2019_2024sep"
    return "2024oct_plus"


def open_backspread(avail_from):
    ref = spot_on_or_before(avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    short_target = round(ref_spot * SHORT_OTM_FRAC / 50) * 50
    long_target = round(ref_spot * LONG_OTM_FRAC / 50) * 50
    for exp in candidate_expiries(TARGET_DTE, avail_from):
        if exp > LAST_OK:
            continue
        r_short = find_strike_price(exp, short_target, avail_from)
        if r_short is None:
            continue
        entry_date, short_K, short_prem0 = r_short
        r_long = find_strike_price(exp, long_target, entry_date, tol_days=5)
        if r_long is None:
            continue
        _, long_K, long_prem0 = r_long
        spot_entry_res = spot_on_or_before(entry_date)
        if spot_entry_res is None:
            continue
        _, spot_entry = spot_entry_res
        dte_actual = (exp - entry_date).days
        if dte_actual < TARGET_DTE * 0.7 or short_K <= long_K:
            continue
        break
    else:
        return None
    net_debit0 = short_prem0 - 2 * long_prem0
    return dict(entry_date=entry_date, expiry=exp, short_K=short_K, long_K=long_K,
                short_prem0=short_prem0, long_prem0=long_prem0, net_debit0=net_debit0,
                spot_entry=spot_entry, dte_actual=dte_actual)


def _finalize(pos, exit_date, exit_value, spot_exit, exit_type):
    gross = exit_value - pos["net_debit0"]
    net = gross - 3 * LEG_COST_RT
    return dict(entry_date=pos["entry_date"], expiry=pos["expiry"], exit_date=exit_date,
                short_K=pos["short_K"], long_K=pos["long_K"], net_debit0=pos["net_debit0"],
                spot_entry=pos["spot_entry"], spot_exit=spot_exit, exit_value=exit_value,
                gross_pnl=gross, cost=3 * LEG_COST_RT, net_pnl=net, exit_type=exit_type,
                era=era_of(pos["entry_date"]),
                heldout_2026=pos["entry_date"] >= pd.Timestamp("2026-01-01"))


def close_at_expiry(pos):
    spres = spot_on_or_before(pos["expiry"])
    if spres is None:
        return None
    _, spot_exit = spres
    short_payoff = max(pos["short_K"] - spot_exit, 0.0)
    long_payoff = max(pos["long_K"] - spot_exit, 0.0)
    exit_value = 2 * long_payoff - short_payoff
    return _finalize(pos, pos["expiry"], exit_value, spot_exit, "expiry_intrinsic")


def close_at_market(pos, close_date):
    def get_close(strike, date, tol_days=5):
        try:
            s = tbl.loc[(pos["expiry"], strike)]["CLOSE"]
        except KeyError:
            return None
        after = s.index[s.index >= date]
        if len(after) == 0:
            return None
        d = after.min()
        if (d - date).days > tol_days:
            return None
        return d, float(s.loc[d])

    r_short = get_close(pos["short_K"], close_date)
    r_long = get_close(pos["long_K"], close_date)
    if r_short is None or r_long is None:
        return None
    exit_date = max(r_short[0], r_long[0])
    exit_value = 2 * r_long[1] - r_short[1]
    spres = spot_on_or_before(close_date)
    spot_exit = spres[1] if spres else np.nan
    return _finalize(pos, exit_date, exit_value, spot_exit, "early_market_close")


def run(roll_days_before_expiry, max_cycles=200):
    """roll_days_before_expiry=None -> hold to expiry."""
    trades = []
    avail_from = trading_days[0]
    guard = 0
    n_skip = 0
    while guard < max_cycles:
        guard += 1
        pos = open_backspread(avail_from)
        if pos is None:
            nxt = on_or_after(avail_from + pd.Timedelta(days=21))
            if nxt is None or nxt > LAST_OK:
                break
            avail_from = nxt
            n_skip += 1
            continue
        if roll_days_before_expiry is not None:
            roll_target = pos["expiry"] - pd.Timedelta(days=roll_days_before_expiry)
            roll_date = on_or_after(roll_target) if roll_target > pos["entry_date"] else None
            t = close_at_market(pos, roll_date) if roll_date is not None and roll_date < pos["expiry"] else None
            if t is None:
                t = close_at_expiry(pos)
        else:
            t = close_at_expiry(pos)
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


variants = [("hold_to_expiry", None), ("roll_3mo_before", 90), ("roll_2mo_before", 60), ("roll_1mo_before", 30)]
summary = []
for name, roll_days in variants:
    log(f"running {name}...")
    df, n_skip = run(roll_days)
    df.to_csv(f"{OUT}\\checkpoints\\trades_1y_{name}.csv", index=False)
    if len(df):
        n_years = (df["exit_date"].max() - df["entry_date"].min()).days / 365.25
        mean, sd, n = df["net_pnl"].mean(), df["net_pnl"].std(ddof=1), len(df)
        t_stat = mean / (sd / np.sqrt(n)) if n > 1 and sd > 0 else np.nan
        ann = df["net_pnl"].sum() / n_years
        log(f"  -> n={n} (skip={n_skip}) span={n_years:.1f}yr total={df['net_pnl'].sum():.1f} "
            f"ann={ann:.1f}pts/yr mean={mean:.1f} t={t_stat:.2f}")
        summary.append(dict(variant=name, n=n, n_skip=n_skip, years=n_years,
                             total=df["net_pnl"].sum(), ann_pts_yr=ann, mean=mean, t_stat=t_stat))
    else:
        log(f"  -> 0 cycles (skip={n_skip})")
        summary.append(dict(variant=name, n=0, n_skip=n_skip))

pd.DataFrame(summary).to_csv(f"{OUT}\\1y_roll_variants_summary.csv", index=False)
log("DONE")
