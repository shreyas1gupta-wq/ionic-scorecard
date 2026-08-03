"""IRONFLY_LADDER_20260802 -- step 3: ladder backtest engine.
32 cells = 4 OTM distances x 2 roll-modes x 4 filters, using the shared schedule.parquet
(roll dates + ATM entry + filter flags) from step 2.

LAYER mode: rungs are fully independent (no interaction between them) -- each rung's entry and
exit is computed directly from its own schedule row + its own expiry. No day-by-day state needed.

REPLACE mode: requires sequential state, since whether to force-close the current rung depends on
whether the NEXT scheduled entry's filter passes -- walked roll-date by roll-date.

Payoff (verified in PRE_REGISTRATION.md before this code was written): defined-risk long iron
butterfly. max loss = net debit paid (at S=ATM strike); max gain = distance - net_debit (at or
beyond either wing). Enforced as a hard assertion on every expiry-intrinsic exit (not on
early-market-close exits, where extrinsic value is still in play and the bound does not strictly
apply).
"""
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
                    r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib")
import guards as G  # noqa: E402  (Gate-4 requirement; see FINDINGS.md for which helpers apply)

ALL_TRADED = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
              r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache"
              r"\nifty_optidx_all_traded.parquet")
BASE = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
        r"\Shreyas_Ionic_AMC\04_RND_LAB\results\IRONFLY_LADDER_20260802")
SCHED = f"{BASE}\\cache\\schedule.parquet"
SV_EXT = f"{BASE}\\cache\\spot_vix_ext.parquet"
CKPT = f"{BASE}\\checkpoints"

LEG_COST_RT = 1.77          # pts round trip per leg (COST_STANDARDS-derived, matches OPTBUY_CONVEXITY)
N_LEGS = 4
COST_TOTAL = LEG_COST_RT * N_LEGS
OTM_DISTANCES = [100, 150, 200, 300]
ROLL_MODES = ["layer", "replace"]
FILTERS = ["filter_unconditional", "filter_iv_lt_rv50", "filter_iv_lt_garch", "filter_iv_pct_low"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log("loading tables...")
tbl_raw = pd.read_parquet(ALL_TRADED)
n0 = len(tbl_raw)
tbl_raw = tbl_raw.drop_duplicates(subset=["EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "TIMESTAMP"], keep="first")
if n0 != len(tbl_raw):
    log(f"deduped {n0 - len(tbl_raw)} exact-duplicate rows (known 2024-07-01..05 bhavcopy double-print)")
tbl = tbl_raw.set_index(["EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "TIMESTAMP"]).sort_index()
sched = pd.read_parquet(SCHED)
sv = pd.read_parquet(SV_EXT).set_index("date").sort_index()
trading_days = sv.index
log(f"tbl {len(tbl):,} rows | schedule {len(sched)} roll dates "
    f"({sched['roll_date'].min().date()}..{sched['roll_date'].max().date()})")


def spot_on_or_before(d):
    pos = trading_days.searchsorted(d, side="right") - 1
    if pos < 0:
        return None
    return trading_days[pos], float(sv["spot_close"].iloc[pos])


def get_price(expiry, strike, opt_type, date, tol_days=3):
    """CLOSE at (expiry,strike,type) on/after date (CONTRACTS>0 already gated upstream),
    fallback forward up to tol_days trading days. Returns (used_date, price) or None."""
    try:
        s = tbl.loc[(expiry, strike, opt_type)]["CLOSE"]
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


def open_leg_prices(row, distance):
    """OTM CE/PE prices at this schedule row's roll_date. ATM legs already validated in step 2."""
    entry_date, expiry, K = row["roll_date"], row["expiry"], row["atm_strike"]
    r_otm_ce = get_price(expiry, K + distance, "CE", entry_date)
    r_otm_pe = get_price(expiry, K - distance, "PE", entry_date)
    if r_otm_ce is None or r_otm_pe is None:
        return None
    _, otm_ce0 = r_otm_ce
    _, otm_pe0 = r_otm_pe
    return dict(entry_date=entry_date, expiry=expiry, atm_strike=K, distance=distance,
                ce0=row["ce0"], pe0=row["pe0"], otm_ce0=otm_ce0, otm_pe0=otm_pe0,
                spot_entry=row["spot_entry"])


def _finalize(rung, exit_date, ce_exit, pe_exit, otm_ce_exit, otm_pe_exit, spot_exit, exit_type):
    entry_value = rung["ce0"] + rung["pe0"] - rung["otm_ce0"] - rung["otm_pe0"]
    exit_value = ce_exit + pe_exit - otm_ce_exit - otm_pe_exit
    gross = exit_value - entry_value
    net = gross - COST_TOTAL
    return dict(entry_date=rung["entry_date"], expiry=rung["expiry"], exit_date=exit_date,
                atm_strike=rung["atm_strike"], distance=rung["distance"],
                spot_entry=rung["spot_entry"], spot_exit=spot_exit,
                entry_value=entry_value, exit_value=exit_value, gross_pnl=gross,
                cost=COST_TOTAL, net_pnl=net, exit_type=exit_type,
                era=era_of(rung["entry_date"]),
                heldout_2026=rung["entry_date"] >= pd.Timestamp("2026-01-01"))


def close_at_expiry_intrinsic(rung):
    spres = spot_on_or_before(rung["expiry"])
    if spres is None:
        return None
    _, spot_exit = spres
    K, d = rung["atm_strike"], rung["distance"]
    ce_exit = max(spot_exit - K, 0.0)
    pe_exit = max(K - spot_exit, 0.0)
    otm_ce_exit = max(spot_exit - (K + d), 0.0)
    otm_pe_exit = max((K - d) - spot_exit, 0.0)
    t = _finalize(rung, rung["expiry"], ce_exit, pe_exit, otm_ce_exit, otm_pe_exit,
                  spot_exit, "expiry_intrinsic")
    # L7b-equivalent hard physical bound (point-denominated, per-trade -- see FINDINGS.md for why
    # this is implemented directly rather than via guards.assert_physical_bounds, whose signature
    # assumes a single uniform FRACTIONAL bound across a return series, not a per-trade point bound)
    max_gain = t["distance"] - t["entry_value"]
    if t["gross_pnl"] > max_gain + 1e-6:
        raise AssertionError(f"L7b physical-bound violation: gross {t['gross_pnl']:.3f} > "
                              f"max_gain {max_gain:.3f} on {t['entry_date']}")
    return t


def close_at_market(rung, close_date):
    r_ce = get_price(rung["expiry"], rung["atm_strike"], "CE", close_date)
    r_pe = get_price(rung["expiry"], rung["atm_strike"], "PE", close_date)
    r_otm_ce = get_price(rung["expiry"], rung["atm_strike"] + rung["distance"], "CE", close_date)
    r_otm_pe = get_price(rung["expiry"], rung["atm_strike"] - rung["distance"], "PE", close_date)
    if any(r is None for r in (r_ce, r_pe, r_otm_ce, r_otm_pe)):
        return None
    _, ce_exit = r_ce
    _, pe_exit = r_pe
    _, otm_ce_exit = r_otm_ce
    _, otm_pe_exit = r_otm_pe
    spres = spot_on_or_before(close_date)
    spot_exit = spres[1] if spres else np.nan
    return _finalize(rung, close_date, ce_exit, pe_exit, otm_ce_exit, otm_pe_exit,
                      spot_exit, "early_market_close")


def run_layer(distance, filter_col):
    trades = []
    n_skip_data = 0
    for _, row in sched[sched[filter_col]].iterrows():
        rung = open_leg_prices(row, distance)
        if rung is None:
            n_skip_data += 1
            continue
        t = close_at_expiry_intrinsic(rung)
        if t is None:
            n_skip_data += 1
            continue
        trades.append(t)
    return pd.DataFrame(trades), n_skip_data


def run_replace(distance, filter_col):
    trades = []
    current = None
    n_skip_data = 0
    for _, row in sched.iterrows():
        roll_date = row["roll_date"]
        if current is not None and current["expiry"] <= roll_date:
            t = close_at_expiry_intrinsic(current)
            if t is not None:
                trades.append(t)
            current = None
        if row[filter_col]:
            if current is not None:
                t = close_at_market(current, roll_date)
                if t is None:
                    n_skip_data += 1
                    continue  # can't price the forced close -- keep holding, retry next roll date
                trades.append(t)
                current = None
            rung = open_leg_prices(row, distance)
            if rung is not None:
                current = rung
            else:
                n_skip_data += 1
        # else: filter fails -> hold current (if any) untouched, re-check next roll date
    if current is not None:
        log(f"    1 rung still open at data end ({current['entry_date'].date()}) -- excluded from stats")
    return pd.DataFrame(trades), n_skip_data


def summarize(tag, distance, mode, filt, df, n_skip_data):
    n = len(df)
    row = dict(cell=tag, distance=distance, roll_mode=mode, filter=filt, n=n, n_skip_data=n_skip_data)
    if n == 0:
        return row
    x = df["net_pnl"].to_numpy()
    mean = x.mean()
    sd = x.std(ddof=1) if n > 1 else np.nan
    t_stat = mean / (sd / np.sqrt(n)) if n > 1 and sd > 0 else np.nan
    row.update(mean_net=mean, sd_net=sd, t_stat=t_stat, win_pct=(x > 0).mean(),
               top1_concentration=(df["net_pnl"].clip(lower=0).max() / df["net_pnl"].clip(lower=0).sum()
                                    if df["net_pnl"].clip(lower=0).sum() > 0 else np.nan))
    for era in ("pre2019", "2019_2024sep", "2024oct_plus"):
        sub = df[df.era == era]["net_pnl"]
        row[f"n_{era}"] = len(sub)
        row[f"mean_{era}"] = sub.mean() if len(sub) else np.nan
    ho = df[df.heldout_2026]["net_pnl"]
    row["n_heldout2026"] = len(ho)
    row["mean_heldout2026"] = ho.mean() if len(ho) else np.nan
    return row


cells = []
for distance in OTM_DISTANCES:
    for mode in ROLL_MODES:
        for filt in FILTERS:
            fn = run_layer if mode == "layer" else run_replace
            df, n_skip = fn(distance, filt)
            tag = f"d{distance}_{mode}_{filt.replace('filter_', '')}"
            df.to_csv(f"{CKPT}\\trades_{tag}.csv", index=False)
            r = summarize(tag, distance, mode, filt, df, n_skip)
            cells.append(r)
            if r["n"] > 0:
                log(f"{tag}: n={r['n']} mean={r['mean_net']:.2f} t={r['t_stat']:.2f} "
                    f"win={r['win_pct']:.1%} skip_data={n_skip}")
            else:
                log(f"{tag}: 0 trades (skip_data={n_skip})")

cells_df = pd.DataFrame(cells)
cells_df.to_csv(f"{BASE}\\cells.csv", index=False)
log(f"DONE -- all {len(cells_df)} cells written to cells.csv")
