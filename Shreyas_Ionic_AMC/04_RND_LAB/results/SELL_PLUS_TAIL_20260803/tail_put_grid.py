"""SELL_PLUS_TAIL_20260803 -- step 3: long-put tail overlay grid.

Single long PE leg (NOT a spread -- task explicitly asks for a "long-put tail overlay", and
PROTECTIVE_PUT's own finding is that the plain long put beats the 1x1 spread as a hedge candidate:
cheaper AND keeps the uncapped tail payoff). Held to EXPIRY (passive) -- TAIL_PUT_ROLL's own finding
that rolling more often is 6.6x WORSE, so the roll-frequency question is already closed; expiry-hold
is the management rule carried into this build.

Sweep: OTM_FRAC in {0.97,0.95,0.93,0.90} (3/5/7/10% OTM) x TARGET_DTE in {30,90,180} (1M/3M/6M).
Monthly-only table, multi-candidate expiry search (engine_v2_spread.py's pattern, reused) --
required per the TAIL_PUT_ROLL landmine: the all-expiries table silently skips illiquid just-listed
far weeklies across all of Jan-Jun 2020 and a 2.5yr 2023-2025 stretch.

Costs: brokerage+slippage (1.77pt RT, matching TAIL_PUT_ROLL/PROTECTIVE_PUT convention) + exercise
STT (buyer side, on INTRINSIC, only when the put finishes ITM at expiry) -- old 0.125%, new 0.15%
(Budget 2026). No premium-side STT: that levy is SELLER-side only; buying to open a put is exempt.
"""
import time
import numpy as np
import pandas as pd
from pathlib import Path

MONTHLY = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
           r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache"
           r"\nifty_optidx_monthly.parquet")
MONTHLY_EXP = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
               r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache"
               r"\monthly_expiry_list.parquet")
SV = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
      r"\Shreyas_Ionic_AMC\04_RND_LAB\results\IRONFLY_LADDER_20260802\cache\spot_vix_ext.parquet")
OUT = Path(__file__).parent
LAST_OK = pd.Timestamp("2026-06-30")

LEG_COST_RT = 1.77
STT_EXERCISE_OLD, STT_EXERCISE_NEW = 0.00125, 0.0015
COVID_WINDOW = (pd.Timestamp("2020-02-01"), pd.Timestamp("2020-06-30"))


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
log(f"PE rows {len(tbl_raw):,} | trading days {len(trading_days)} | monthly expiries {len(all_exp)}")


def on_or_after(d):
    pos = trading_days.searchsorted(d)
    return trading_days[pos] if pos < len(trading_days) else None


def spot_on_or_before(d):
    pos = trading_days.searchsorted(d, side="right") - 1
    if pos < 0:
        return None
    return trading_days[pos], float(sv["spot_close"].iloc[pos])


def candidate_expiries(target_dte, avail_from, expiry_list, min_dte=20, band=45, max_n=4):
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


def open_put(avail_from, target_dte, otm_frac):
    ref = spot_on_or_before(avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    target_strike = round(ref_spot * otm_frac / 50) * 50
    for exp in candidate_expiries(target_dte, avail_from, all_exp):
        if exp > LAST_OK:
            continue
        r = find_strike_price(exp, target_strike, avail_from)
        if r is None:
            continue
        entry_date, K, prem0 = r
        dte_actual = (exp - entry_date).days
        if dte_actual < target_dte * 0.55:
            continue
        break
    else:
        return None
    spot_entry_res = spot_on_or_before(entry_date)
    if spot_entry_res is None:
        return None
    _, spot_entry = spot_entry_res
    return dict(entry_date=entry_date, expiry=exp, strike=K, target_strike=target_strike,
                prem0=prem0, spot_entry=spot_entry, dte_actual=dte_actual,
                actual_otm_pct=(spot_entry - K) / spot_entry)


def close_at_expiry(pos):
    spres = spot_on_or_before(pos["expiry"])
    if spres is None:
        return None
    _, spot_exit = spres
    payoff = max(pos["strike"] - spot_exit, 0.0)
    gross = payoff - pos["prem0"]
    stt_old = STT_EXERCISE_OLD * payoff
    stt_new = STT_EXERCISE_NEW * payoff
    net_old = gross - LEG_COST_RT - stt_old
    net_new = gross - LEG_COST_RT - stt_new
    return dict(entry_date=pos["entry_date"], expiry=pos["expiry"], exit_date=pos["expiry"],
                strike=pos["strike"], target_strike=pos["target_strike"],
                actual_otm_pct=pos["actual_otm_pct"], spot_entry=pos["spot_entry"],
                spot_exit=spot_exit, prem0=pos["prem0"], payoff=payoff, gross_pnl=gross,
                stt_old=stt_old, stt_new=stt_new, net_pnl_old_stt=net_old, net_pnl_new_stt=net_new,
                hold_days=(pos["expiry"] - pos["entry_date"]).days, itm=payoff > 0,
                era=era_of(pos["entry_date"]), heldout_2026=pos["entry_date"] >= pd.Timestamp("2026-01-01"))


def run_cycles(target_dte, otm_frac, max_cycles=400):
    trades = []
    avail_from = trading_days[0]
    guard, n_skip = 0, 0
    while guard < max_cycles:
        guard += 1
        pos = open_put(avail_from, target_dte, otm_frac)
        if pos is None:
            nxt = on_or_after(avail_from + pd.Timedelta(days=14))
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


TENORS = {"1M": 30, "3M": 90, "6M": 180}
MONEYNESS = {"3pct": 0.97, "5pct": 0.95, "7pct": 0.93, "10pct": 0.90}

summary_rows = []
for tname, tdte in TENORS.items():
    for mname, ofrac in MONEYNESS.items():
        log(f"running {tname}/{mname} (dte~{tdte}, otm_frac={ofrac})...")
        df, n_skip = run_cycles(tdte, ofrac)
        cfg = f"{tname}_{mname}"
        df.to_csv(OUT / "checkpoints" / f"tail_trades_{cfg}.csv", index=False)
        if len(df) == 0:
            log(f"  -> 0 cycles (skipped {n_skip})")
            continue
        n_years = (df["exit_date"].max() - df["entry_date"].min()).days / 365.25
        ann_cost_old = df["net_pnl_old_stt"].sum() / n_years
        ann_cost_new = df["net_pnl_new_stt"].sum() / n_years
        # COVID cycle: any cycle whose life [entry,expiry] overlaps Feb-Jun 2020
        covid_mask = (df["expiry"] >= COVID_WINDOW[0]) & (df["entry_date"] <= COVID_WINDOW[1])
        covid_cycles = df[covid_mask]
        covid_payoff_new = covid_cycles["net_pnl_new_stt"].sum() if len(covid_cycles) else np.nan
        covid_n = len(covid_cycles)
        log(f"  -> {len(df)} cycles (skipped {n_skip}), span {df['entry_date'].min().date()}"
            f"..{df['exit_date'].max().date()} ({n_years:.2f}yr), "
            f"ann.cost(old STT)={ann_cost_old:.2f} ann.cost(new STT)={ann_cost_new:.2f} pts/yr, "
            f"COVID cycles={covid_n} payoff={covid_payoff_new}")
        summary_rows.append(dict(
            tenor=tname, moneyness=mname, target_dte=tdte, otm_frac=ofrac, n_cycles=len(df),
            n_skip=n_skip, span_yr=n_years,
            entry_first=df["entry_date"].min(), exit_last=df["exit_date"].max(),
            mean_actual_otm_pct=df["actual_otm_pct"].mean(),
            mean_net_pnl_new_stt=df["net_pnl_new_stt"].mean(),
            ann_cost_old_stt_pts=ann_cost_old, ann_cost_new_stt_pts=ann_cost_new,
            n_itm_cycles=int(df["itm"].sum()), covid_n_cycles=covid_n,
            covid_payoff_new_stt_pts=covid_payoff_new,
            covid_entry_dates=";".join(str(d.date()) for d in covid_cycles["entry_date"]) if covid_n else "",
        ))

S = pd.DataFrame(summary_rows)
S.to_csv(OUT / "checkpoints" / "tail_put_grid_summary.csv", index=False)
log("wrote checkpoints/tail_put_grid_summary.csv")
log("DONE")
