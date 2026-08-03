"""TAIL_PUT_ROLL_20260802 -- v3: 1x5%-OTM SHORT put / 2x10%-OTM LONG put (ratio backspread).
Unlike the capped spread (v2), this is CONVEX beyond the 10% strike: payoff at expiry, S=spot:
  S >= 5%K: both worthless, net = -net_debit (or +net_credit if it prices to a credit)
  10%K <= S < 5%K: short leg ITM, longs still worthless -> WORST zone, loss grows as S falls
  S < 10%K: 2*(10%K-S) - (5%K-S) = (2*10%K - 5%K) - S -- GROWS UNBOUNDED as S falls further.
Tests at 180d AND 365d tenor, HELD TO EXPIRY (base case; no roll variant requested for this leg
structure). Reuses the monthly-only-table fix from v2 (thin far-dated weeklies caused the
original COVID-skipping bug).
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
SHORT_OTM_FRAC = 0.95    # sell 1x 5% OTM
LONG_OTM_FRAC = 0.90     # buy 2x 10% OTM
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
log(f"PE rows {len(tbl_raw):,} | monthly expiries {len(all_exp)}")


def on_or_after(d):
    pos = trading_days.searchsorted(d)
    return trading_days[pos] if pos < len(trading_days) else None


def spot_on_or_before(d):
    pos = trading_days.searchsorted(d, side="right") - 1
    if pos < 0:
        return None
    return trading_days[pos], float(sv["spot_close"].iloc[pos])


def candidate_expiries(target_dte, avail_from, expiry_list, min_dte=30, band=75, max_n=4):
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


def era_of(d):
    if d < pd.Timestamp("2019-02-01"):
        return "pre2019"
    if d < pd.Timestamp("2024-10-01"):
        return "2019_2024sep"
    return "2024oct_plus"


def open_backspread(avail_from, target_dte):
    ref = spot_on_or_before(avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    short_target = round(ref_spot * SHORT_OTM_FRAC / 50) * 50
    long_target = round(ref_spot * LONG_OTM_FRAC / 50) * 50
    for exp in candidate_expiries(target_dte, avail_from, all_exp):
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
        if dte_actual < target_dte * 0.7 or short_K <= long_K:
            continue
        break
    else:
        return None
    net_debit0 = short_prem0 - 2 * long_prem0   # NEGATIVE = net CREDIT received
    return dict(entry_date=entry_date, expiry=exp, short_K=short_K, long_K=long_K,
                short_prem0=short_prem0, long_prem0=long_prem0, net_debit0=net_debit0,
                spot_entry=spot_entry, dte_actual=dte_actual,
                short_otm_pct=(spot_entry - short_K) / spot_entry,
                long_otm_pct=(spot_entry - long_K) / spot_entry)


def close_at_expiry(pos):
    spres = spot_on_or_before(pos["expiry"])
    if spres is None:
        return None
    _, spot_exit = spres
    short_payoff = max(pos["short_K"] - spot_exit, 0.0)
    long_payoff = max(pos["long_K"] - spot_exit, 0.0)
    exit_value = 2 * long_payoff - short_payoff
    gross = exit_value - pos["net_debit0"]
    net = gross - 3 * LEG_COST_RT  # 3 legs total (1 short + 2 long)
    return dict(entry_date=pos["entry_date"], expiry=pos["expiry"], exit_date=pos["expiry"],
                short_K=pos["short_K"], long_K=pos["long_K"], net_debit0=pos["net_debit0"],
                short_otm_pct=pos["short_otm_pct"], long_otm_pct=pos["long_otm_pct"],
                spot_entry=pos["spot_entry"], spot_exit=spot_exit, exit_value=exit_value,
                gross_pnl=gross, cost=3 * LEG_COST_RT, net_pnl=net,
                era=era_of(pos["entry_date"]), heldout_2026=pos["entry_date"] >= pd.Timestamp("2026-01-01"))


def run_backspread(target_dte, max_cycles=200):
    trades = []
    avail_from = trading_days[0]
    guard = 0
    n_skip = 0
    while guard < max_cycles:
        guard += 1
        pos = open_backspread(avail_from, target_dte)
        if pos is None:
            nxt = on_or_after(avail_from + pd.Timedelta(days=21))
            if nxt is None or nxt > LAST_OK:
                break
            avail_from = nxt
            n_skip += 1
            continue
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


for tenor_name, target_dte in (("6M", 180), ("1Y", 365)):
    log(f"running backspread @ {tenor_name} ({target_dte}d)...")
    df, n_skip = run_backspread(target_dte)
    df.to_csv(f"{OUT}\\checkpoints\\trades_backspread_{tenor_name}.csv", index=False)
    if len(df):
        n_years = (df["exit_date"].max() - df["entry_date"].min()).days / 365.25
        log(f"  -> {len(df)} cycles (skipped {n_skip}), span {df['entry_date'].min().date()}"
            f"..{df['exit_date'].max().date()} ({n_years:.2f}yr)")
        log(f"  -> mean net_debit0 (neg=credit): {df['net_debit0'].mean():.1f} pts | "
            f"total net {df['net_pnl'].sum():.1f} | ann. {df['net_pnl'].sum()/n_years:.1f} pts/yr")
        best = df.loc[df["net_pnl"].idxmax()]
        worst = df.loc[df["net_pnl"].idxmin()]
        log(f"  -> best cycle: entry {best['entry_date'].date()} net={best['net_pnl']:.1f} "
            f"(spot {best['spot_entry']:.0f}->{best['spot_exit']:.0f})")
        log(f"  -> worst cycle: entry {worst['entry_date'].date()} net={worst['net_pnl']:.1f} "
            f"(spot {worst['spot_entry']:.0f}->{worst['spot_exit']:.0f})")
    else:
        log(f"  -> 0 cycles (skipped {n_skip})")

log("DONE")
