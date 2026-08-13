"""OPTBUY_CONVEXITY_20260731 -- main engine.
Long ATM straddle, NON-OVERLAPPING monthly-cycle rolls, DTE sweep {15,30,45,60,90} calendar days,
hold-to-expiry (intrinsic settle from spot, never expiry-day SETTLE_PR) + one partial-hold (50%)
variant. No stops/trails/targets anywhere -> pathsafe's path-dependent machinery does not apply;
every P&L here is an exact entry-close-to-exit-close/intrinsic difference.
Writes one CSV of raw trades per arm to checkpoints/, so a crash loses at most the current arm.
"""
import gc
import time

import numpy as np
import pandas as pd

CACHE = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
         r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache")
CKPT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
        r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\checkpoints")

LEG_COST_RT = 1.77          # premium points round trip PER LEG (Rs25/lot/side, lot65, +0.5 slip/side)
LAST_OK = pd.Timestamp("2026-07-03")   # last date with spot/vix data


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_leg_table(fname):
    df = pd.read_parquet(f"{CACHE}\\{fname}")
    df = df.set_index(["EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "TIMESTAMP"]).sort_index()
    return df


log("loading tables...")
monthly_tbl = load_leg_table("nifty_optidx_monthly.parquet")
all_tbl = load_leg_table("nifty_optidx_all_traded.parquet")
sv = pd.read_parquet(f"{CACHE}\\spot_vix_daily.parquet").set_index("date").sort_index()
trading_days = sv.index
monthly_exp = sorted(pd.read_parquet(f"{CACHE}\\monthly_expiry_list.parquet")["expiry"])
all_exp = sorted(all_tbl.index.get_level_values(0).unique())
log(f"monthly_tbl {len(monthly_tbl):,} rows | all_tbl {len(all_tbl):,} rows | "
    f"trading days {len(trading_days)} | monthly expiries {len(monthly_exp)} | "
    f"all expiries {len(all_exp)}")


def next_trading_day(d, n=1):
    pos = trading_days.searchsorted(d)
    pos += n
    if pos >= len(trading_days):
        return None
    return trading_days[pos]


def spot_on_or_before(d):
    pos = trading_days.searchsorted(d, side="right") - 1
    if pos < 0:
        return None
    return trading_days[pos], float(sv["spot_close"].iloc[pos])


def find_target_expiry(target_dte, avail_from, expiry_list, min_dte=3, band_mult=3):
    best, bestdiff = None, 1e9
    for e in expiry_list:
        d = (e - avail_from).days
        if d < min_dte:
            continue
        if d > target_dte * band_mult + 30:
            break
        diff = abs(d - target_dte)
        if diff < bestdiff:
            bestdiff, best = diff, e
    return best


def find_entry(tbl, expiry, avail_from, ref_spot, tol_days=5):
    """Search forward from avail_from for the nearest ATM strike where BOTH legs traded
    on the SAME timestamp. Returns (entry_date, strike, ce_close, pe_close) or None."""
    strike0 = round(ref_spot / 50) * 50
    for off in (0, 50, -50, 100, -100, 150, -150, 200, -200):
        K = strike0 + off
        try:
            ce = tbl.loc[(expiry, K, "CE")]["CLOSE"]
            pe = tbl.loc[(expiry, K, "PE")]["CLOSE"]
        except KeyError:
            continue
        common = ce.index.intersection(pe.index)
        common = common[common >= avail_from]
        if len(common) == 0:
            continue
        d = common.min()
        if (d - avail_from).days > tol_days:
            continue
        return d, K, float(ce.loc[d]), float(pe.loc[d])
    return None


def find_exit_partial(tbl, expiry, strike, target_date, tol_days=5):
    try:
        ce = tbl.loc[(expiry, strike, "CE")]["CLOSE"]
        pe = tbl.loc[(expiry, strike, "PE")]["CLOSE"]
    except KeyError:
        return None
    common = ce.index.intersection(pe.index)
    common = common[common <= target_date]
    if len(common) == 0:
        return None
    d = common.max()
    if (target_date - d).days > tol_days:
        return None
    return d, float(ce.loc[d]), float(pe.loc[d])


def run_dte_arm(target_dte, tbl, expiry_universe, hold_frac=1.0, max_cycles=400):
    trades = []
    avail_from = trading_days[0]
    guard = 0
    while guard < max_cycles:
        guard += 1
        exp = find_target_expiry(target_dte, avail_from, expiry_universe)
        if exp is None or exp > LAST_OK:
            break
        ref = spot_on_or_before(avail_from)
        if ref is None:
            break
        _, ref_spot = ref
        res = find_entry(tbl, exp, avail_from, ref_spot)
        if res is None:
            nxt = next_trading_day(avail_from, 3)
            if nxt is None or nxt > LAST_OK:
                break
            avail_from = nxt
            continue
        entry_date, K, ce0, pe0 = res
        dte_actual = (exp - entry_date).days
        if dte_actual < 3:
            nxt = next_trading_day(exp, 1)
            if nxt is None or nxt > LAST_OK:
                break
            avail_from = nxt
            continue
        spot_entry_res = spot_on_or_before(entry_date)
        if spot_entry_res is None:
            avail_from = next_trading_day(exp, 1)
            if avail_from is None:
                break
            continue
        _, spot_entry = spot_entry_res

        if hold_frac >= 0.999:
            spres = spot_on_or_before(exp)
            if spres is None:
                nxt = next_trading_day(exp, 1)
                if nxt is None or nxt > LAST_OK:
                    break
                avail_from = nxt
                continue
            exit_date_used, spot_exit = spres
            ce_exit = max(spot_exit - K, 0.0)
            pe_exit = max(K - spot_exit, 0.0)
            hold_label = "expiry"
        else:
            exit_target = entry_date + pd.Timedelta(days=int(round(dte_actual * hold_frac)))
            r2 = find_exit_partial(tbl, exp, K, exit_target)
            if r2 is None:
                nxt = next_trading_day(exp, 1)
                if nxt is None or nxt > LAST_OK:
                    break
                avail_from = nxt
                continue
            exit_date_used, ce_exit, pe_exit = r2
            se = spot_on_or_before(exit_date_used)
            spot_exit = se[1] if se else np.nan
            hold_label = f"partial{hold_frac:.2f}"

        entry_premium = ce0 + pe0
        exit_value = ce_exit + pe_exit
        entry_intrinsic = abs(spot_entry - K)
        exit_intrinsic = abs(spot_exit - K) if not np.isnan(spot_exit) else np.nan
        gross = exit_value - entry_premium
        cost_straddle = 2 * LEG_COST_RT
        net = gross - cost_straddle

        if entry_date < pd.Timestamp("2019-02-01"):
            era = "pre2019"
        elif entry_date < pd.Timestamp("2024-10-01"):
            era = "2019_2024sep"
        else:
            era = "2024oct_plus"
        heldout = entry_date >= pd.Timestamp("2026-01-01")

        row = sv.loc[entry_date] if entry_date in sv.index else None
        vix_pct = float(row["vix_pct_trail"]) if row is not None and not pd.isna(row.get("vix_pct_trail", np.nan)) else np.nan
        rv_pct = float(row["rv20_pct_trail"]) if row is not None and not pd.isna(row.get("rv20_pct_trail", np.nan)) else np.nan
        vix_lvl = float(row["vix_close"]) if row is not None else np.nan

        trades.append(dict(
            target_dte=target_dte, hold_label=hold_label, entry_date=entry_date, expiry=exp,
            exit_date=exit_date_used, dte_actual=dte_actual,
            hold_days_actual=(exit_date_used - entry_date).days,
            strike=K, spot_entry=spot_entry, spot_exit=spot_exit,
            ce_entry=ce0, pe_entry=pe0, ce_exit=ce_exit, pe_exit=pe_exit,
            entry_premium=entry_premium, exit_value=exit_value,
            entry_intrinsic=entry_intrinsic, exit_intrinsic=exit_intrinsic,
            gross_pnl=gross, cost_straddle=cost_straddle, net_pnl=net,
            era=era, heldout_2026=heldout, vix_pct_trail=vix_pct, rv20_pct_trail=rv_pct,
            vix_close=vix_lvl,
        ))
        nxt = next_trading_day(exit_date_used, 1)
        if nxt is None or nxt > LAST_OK:
            break
        avail_from = nxt
    return pd.DataFrame(trades)


def main():
    all_trades = []
    for target_dte in (15, 30, 45, 60, 90):
        if target_dte == 15:
            tbl, universe = all_tbl, all_exp
        else:
            tbl, universe = monthly_tbl, monthly_exp
        log(f"running DTE={target_dte} hold=expiry universe={'all' if target_dte==15 else 'monthly'} ...")
        df = run_dte_arm(target_dte, tbl, universe, hold_frac=1.0)
        log(f"  -> {len(df)} trades, mean net {df['net_pnl'].mean():.2f} pts" if len(df) else "  -> 0 trades")
        df.to_csv(f"{CKPT}\\trades_dte{target_dte}_expiry.csv", index=False)
        all_trades.append(df)
        gc.collect()

    log("running DTE=45 partial-hold (50%) ...")
    df_partial = run_dte_arm(45, monthly_tbl, monthly_exp, hold_frac=0.5)
    log(f"  -> {len(df_partial)} trades, mean net {df_partial['net_pnl'].mean():.2f} pts" if len(df_partial) else "  -> 0 trades")
    df_partial.to_csv(f"{CKPT}\\trades_dte45_partial50.csv", index=False)

    combo = pd.concat(all_trades, ignore_index=True)
    combo.to_csv(f"{CKPT}\\trades_all_expiry_arms.csv", index=False)
    log("DONE — all arms checkpointed to checkpoints/")


if __name__ == "__main__":
    main()
