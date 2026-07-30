"""RATIO CALENDAR / DIAGONAL -- NIFTY index, sell-near-month / buy-next-month.
Pre-registered design: Shreyas_Ionic_AMC/04_RND_LAB/results/RATIO_CALENDAR_20260730/PRE_REGISTRATION.md
Self-contained, no arguments. Writes all outputs to its own results dir. Queue contract per
BACKTEST_QUEUE_20260730/runner.py (SHARED_CONTEXT_20260729.md). ~140 pre-registered trial cells.

READ THE PRE-REG BEFORE TOUCHING THIS FILE. Nothing here should be re-tuned after seeing results --
that would violate D-035. If a bug is found, fix the bug; do not adjust a threshold to fix a number.
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
DATA = ROOT / "Shreyas_Ionic_AMC" / "05_DATA_OFFICE" / "data" / "fo_bhavcopy_hist"
TS_PATH = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "RATIO_CALENDAR_20260730" / "term_structure.csv"
OUT = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "RATIO_CALENDAR_20260730"
YEARS = list(range(2011, 2027))

LOT = 75            # [INFERENCE] current lot size applied uniformly for cost/margin comparability;
                     # historical lot sizes differed (50 pre-2015 era, other revisions) -- rupee
                     # figures in early years are illustrative; points/%-of-notional are load-bearing.
BROK_PER_LOT_SIDE = 25.0   # Rs25/lot/side, SHARED_CONTEXT authoritative
SLIP_FLOOR_PTS = 0.05      # 1 tick proxy
SLIP_PCT = 0.0025          # 0.25% premium, liquid ATM index tier, COST_STANDARDS
MARGIN_BOUNDS = {"5pct": 0.05, "10pct": 0.10}
HELD_OUT_START = pd.Timestamp("2026-01-01")   # do not select on this window; report separately

RATIOS = {"1x1": (1, 1), "2x1": (2, 1), "3x2": (3, 2)}
STRIKE_STRUCTS = ["ATM_ATM", "OTM25D_ATM"]
FILTERS = ["unconditional", "contango", "inversion", "topdecile", "inv_and_topdecile"]
EXIT_VARIANTS = {"expiry": 0, "1d_before": 1, "2d_before": 2, "3d_before": 3}

COLS = ["INSTRUMENT", "SYMBOL", "EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "CLOSE", "CONTRACTS", "TIMESTAMP"]


def log(msg):
    print(f"[{time.time()-T0:7.1f}s] {msg}", flush=True)


def parse_nse_date(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    out = pd.to_datetime(s, format="%d-%b-%Y", errors="coerce")
    bad = out.isna()
    if bad.any():
        out.loc[bad] = pd.to_datetime(s[bad], format="%d-%b-%y", errors="coerce")
    still_bad = out.isna()
    if still_bad.any():
        out.loc[still_bad] = pd.to_datetime(s[still_bad], format="mixed", dayfirst=True, errors="coerce")
    return out


def slip(px, side):
    """side='sell' (we receive less) or 'buy' (we pay more)."""
    s = max(SLIP_FLOOR_PTS, SLIP_PCT * px)
    return px - s if side == "sell" else px + s


# ---------------------------------------------------------------------------
# DATA LOADING -- one pass, whole archive, CE-only OPTIDX + FUTIDX (index for O(1) point lookups
# and a day-level grouping for ATM/OTM strike search). Small vs the full CE+PE archive.
# ---------------------------------------------------------------------------
def load_all():
    ce_frames, fut_frames = [], []
    for y in YEARS:
        df = pd.read_parquet(DATA / f"fo_idx_{y}.parquet", columns=COLS)
        df = df[df["SYMBOL"] == "NIFTY"]
        df = df.copy()
        df["EXPIRY_DT"] = parse_nse_date(df["EXPIRY_DT"])
        df["TIMESTAMP"] = parse_nse_date(df["TIMESTAMP"])
        ce = df[(df["INSTRUMENT"] == "OPTIDX") & (df["OPTION_TYP"] == "CE")]
        fut = df[df["INSTRUMENT"] == "FUTIDX"]
        ce_frames.append(ce[["EXPIRY_DT", "STRIKE_PR", "CLOSE", "CONTRACTS", "TIMESTAMP"]])
        fut_frames.append(fut[["EXPIRY_DT", "CLOSE", "TIMESTAMP"]])
        log(f"loaded {y}: ce {len(ce)} fut {len(fut)}")
    ce_all = pd.concat(ce_frames, ignore_index=True)
    fut_all = pd.concat(fut_frames, ignore_index=True)
    # dedup 2024-25 backfill/extend duplicates (same bug as build_term_structure.py)
    ce_all = ce_all.groupby(["EXPIRY_DT", "STRIKE_PR", "TIMESTAMP"], as_index=False).agg(
        CLOSE=("CLOSE", "mean"), CONTRACTS=("CONTRACTS", "max"))
    fut_all = fut_all.groupby(["EXPIRY_DT", "TIMESTAMP"], as_index=False)["CLOSE"].mean()
    log(f"total ce rows {len(ce_all)}, fut rows {len(fut_all)}")
    return ce_all, fut_all


class Market:
    def __init__(self, ce_all, fut_all):
        self.ce_idx = ce_all.set_index(["EXPIRY_DT", "STRIKE_PR"]).sort_index()
        self.fut_idx = fut_all.set_index(["EXPIRY_DT", "TIMESTAMP"])["CLOSE"].sort_index()
        # day-level view for ATM/OTM strike search: only CONTRACTS>0 rows matter for strike picking
        liq = ce_all[ce_all["CONTRACTS"] > 0]
        self.by_day = {k: v for k, v in liq.groupby(["EXPIRY_DT", "TIMESTAMP"])}
        self._ce_series_cache = {}
        # trading-day list per expiry (for "N days before expiry" in TRADING-day terms)
        self._expiry_days_cache = {}

    def ce_series(self, expiry, strike):
        key = (expiry, strike)
        if key not in self._ce_series_cache:
            try:
                sub = self.ce_idx.loc[(expiry, strike)]
            except KeyError:
                sub = pd.DataFrame(columns=["CLOSE", "CONTRACTS", "TIMESTAMP"])
            if isinstance(sub, pd.Series):
                sub = sub.to_frame().T
            self._ce_series_cache[key] = sub.set_index("TIMESTAMP")[["CLOSE", "CONTRACTS"]].sort_index()
        return self._ce_series_cache[key]

    def ce_price(self, day, expiry, strike, require_liquid=True):
        s = self.ce_series(expiry, strike)
        if day not in s.index:
            return None
        row = s.loc[day]
        if isinstance(row, pd.DataFrame):  # residual dup safety
            row = row.iloc[-1]
        if require_liquid and row["CONTRACTS"] <= 0:
            return None
        return float(row["CLOSE"])

    def fut_price(self, day, expiry):
        try:
            v = self.fut_idx.loc[(expiry, day)]
        except KeyError:
            return None
        if isinstance(v, pd.Series):
            v = v.iloc[-1]
        return float(v)

    def strikes_on_day(self, day, expiry):
        return self.by_day.get((expiry, day))

    def atm_pick(self, day, expiry, forward):
        g = self.strikes_on_day(day, expiry)
        if g is None or g.empty or forward is None:
            return None, None
        idx = (g["STRIKE_PR"] - forward).abs().idxmin()
        row = g.loc[idx]
        return float(row["STRIKE_PR"]), float(row["CLOSE"])

    def otm_delta_pick(self, day, expiry, forward, iv_atm, dte, target_delta=0.25):
        if forward is None or iv_atm is None or not np.isfinite(iv_atm) or iv_atm <= 0 or dte <= 0:
            return self.atm_pick(day, expiry, forward)
        T = dte / 365.0
        z = norm.ppf(target_delta)  # negative for target_delta<0.5
        k_theory = forward * np.exp(0.5 * iv_atm ** 2 * T - z * iv_atm * np.sqrt(T))
        g = self.strikes_on_day(day, expiry)
        if g is None or g.empty:
            return None, None
        idx = (g["STRIKE_PR"] - k_theory).abs().idxmin()
        row = g.loc[idx]
        return float(row["STRIKE_PR"]), float(row["CLOSE"])

    def expiry_trading_days(self, expiry):
        if expiry not in self._expiry_days_cache:
            try:
                sub = self.ce_idx.loc[expiry]
            except KeyError:
                sub = pd.DataFrame(columns=["TIMESTAMP"])
            days = sorted(pd.Index(sub.reset_index()["TIMESTAMP"]).dropna().unique()) if len(sub) else []
            self._expiry_days_cache[expiry] = days
        return self._expiry_days_cache[expiry]

    def exit_day(self, expiry, n_before):
        days = self.expiry_trading_days(expiry)
        if not days:
            return None
        if n_before == 0:
            return expiry if expiry in days else days[-1]
        idx = -(n_before + 1)
        if -idx > len(days):
            return None
        return days[idx]


# ---------------------------------------------------------------------------
# COST / MARGIN
# ---------------------------------------------------------------------------
def cost_and_margin(short_n, long_n, near_entry, near_exit, far_entry, far_far_exit, fwd_for_margin):
    """far_far_exit kept generically named far_exit at call site; returns dict of pnl/cost/margin."""
    gross_pts = short_n * (near_entry - near_exit) + long_n * (far_far_exit - far_entry)
    near_entry_f = slip(near_entry, "sell")
    near_exit_f = slip(near_exit, "buy")
    far_entry_f = slip(far_entry, "buy")
    far_exit_f = slip(far_far_exit, "sell")
    net_after_slip = short_n * (near_entry_f - near_exit_f) + long_n * (far_exit_f - far_entry_f)
    brokerage_pts = (BROK_PER_LOT_SIDE / LOT) * 2 * (short_n + long_n)
    net_pts = net_after_slip - brokerage_pts
    friction_pts = gross_pts - net_pts
    hedge_lots = min(short_n, long_n)
    excess_naked = max(short_n - long_n, 0)
    margins = {}
    for name, bound in MARGIN_BOUNDS.items():
        notional = fwd_for_margin * LOT
        margins[name] = bound * notional * hedge_lots + 0.10 * notional * excess_naked
    return dict(gross_pts=gross_pts, net_pts=net_pts, friction_pts=friction_pts,
                excess_naked_lots=excess_naked, **{f"margin_{k}": v for k, v in margins.items()},
                notional_1lot=fwd_for_margin * LOT)


# ---------------------------------------------------------------------------
# MAIN GRID A -- single adjacent-month cycle
# ---------------------------------------------------------------------------
def build_grid_a(mkt: Market, ts: pd.DataFrame):
    cyc = ts[ts["near_expiry"] != ts["near_expiry"].shift(1)].reset_index(drop=True)
    log(f"grid A: {len(cyc)} candidate cycle-start days")
    trades = []  # one row per (cycle, strike_struct, ratio, exit_variant)
    fails = {"no_near_entry": 0, "no_far_entry": 0, "no_near_exit": 0, "no_far_exit": 0, "no_exit_day": 0}
    for _, row in cyc.iterrows():
        day0, near_exp, far_exp = row["day"], row["near_expiry"], row["far_expiry"]
        for sstruct in STRIKE_STRUCTS:
            if sstruct == "ATM_ATM":
                k_near = row["near_strike"]
                near_entry_px = mkt.ce_price(day0, near_exp, k_near)
            else:
                k_near, near_entry_px = mkt.otm_delta_pick(day0, near_exp, row["fwd_near"], row["iv_near"], row["near_dte"])
            k_far = row["far_strike"]
            far_entry_px = mkt.ce_price(day0, far_exp, k_far)
            if near_entry_px is None:
                fails["no_near_entry"] += 1; continue
            if far_entry_px is None:
                fails["no_far_entry"] += 1; continue
            for exit_name, n_before in EXIT_VARIANTS.items():
                ex_day = mkt.exit_day(near_exp, n_before)
                if ex_day is None:
                    fails["no_exit_day"] += 1; continue
                if n_before == 0:
                    underlying_settle = mkt.fut_price(near_exp, near_exp)
                    near_exit_px = max((underlying_settle - k_near), 0.0) if underlying_settle is not None else None
                else:
                    near_exit_px = mkt.ce_price(ex_day, near_exp, k_near)
                if near_exit_px is None:
                    fails["no_near_exit"] += 1; continue
                far_exit_px = mkt.ce_price(ex_day, far_exp, k_far)
                if far_exit_px is None:
                    fails["no_far_exit"] += 1; continue
                for ratio_name, (short_n, long_n) in RATIOS.items():
                    r = cost_and_margin(short_n, long_n, near_entry_px, near_exit_px, far_entry_px, far_exit_px, row["fwd_near"])
                    trades.append(dict(
                        day0=day0, exit_day=ex_day, near_expiry=near_exp, far_expiry=far_exp,
                        strike_struct=sstruct, ratio=ratio_name, exit_variant=exit_name,
                        k_near=k_near, k_far=k_far, iv_spread=row["iv_spread"], iv_ratio=row["iv_ratio"],
                        near_iv_pct=row["near_iv_pct"], near_dte=row["near_dte"], far_dte=row["far_dte"],
                        **r,
                    ))
    log(f"grid A fails: {fails}")
    return pd.DataFrame(trades)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["f_unconditional"] = True
    df["f_contango"] = df["iv_spread"] < -0.02
    df["f_inversion"] = df["iv_spread"] > 0.02
    df["f_topdecile"] = df["near_iv_pct"] >= 90
    df["f_inv_and_topdecile"] = df["f_inversion"] & df["f_topdecile"]
    return df


# ---------------------------------------------------------------------------
# ROLL GRID B -- skip-one-month gap, 2 sub-cycles sharing one far leg, vs no-roll baseline
# ---------------------------------------------------------------------------
LOOKFORWARD_DAYS = 10  # bounded search for the 3rd-tier far leg to get listed (NSE typically runs
                        # only 3 concurrent monthly series; near3 -- 2 cycles out from near1 -- is
                        # OFTEN NOT YET LISTED on literally day0. A real trader would wait a few days
                        # for it to appear, not assume instant availability. Both legs (near1 AND
                        # near3) are entered TOGETHER on whichever day near3 first becomes tradeable.


def build_grid_b(mkt: Market, ts: pd.DataFrame, next_monthly: dict):
    cyc = ts[ts["near_expiry"] != ts["near_expiry"].shift(1)].reset_index(drop=True)
    rows = []
    fails = {"no_near3_mapping": 0, "near3_never_listed_in_window": 0, "no_near1_entry": 0,
              "no_exit_day": 0, "no_near1_exit_or_near3_mark": 0, "no_near2_entry": 0,
              "no_final_exit_day": 0, "no_near2_or_near3_exit": 0, "no_cycleA_far_leg": 0,
              "no_cycleB_fresh_legs": 0}
    for _, row in cyc.iterrows():
        day0 = row["day"]
        near1, near2 = row["near_expiry"], row["far_expiry"]
        near3 = next_monthly.get(near2)
        if near3 is None:
            fails["no_near3_mapping"] += 1; continue
        # bounded forward search: find the first trading day (within near1's own lifespan, starting
        # at day0) on which near3 is actually listed/tradeable; open BOTH legs there together.
        near1_days = [d for d in mkt.expiry_trading_days(near1) if d >= day0][:LOOKFORWARD_DAYS]
        entry_day, k_near3, near3_entry_px = None, None, None
        for d in near1_days:
            f3 = mkt.fut_price(d, near3)
            if f3 is None:
                continue
            k3, px3 = mkt.atm_pick(d, near3, f3)
            if px3 is not None:
                entry_day, k_near3, near3_entry_px = d, k3, px3
                break
        if entry_day is None:
            fails["near3_never_listed_in_window"] += 1; continue
        # near1 strike is fixed (ts row's ATM at day0); re-price it at the (possibly later) entry_day
        k_near1 = row["near_strike"]
        near1_entry_px = mkt.ce_price(entry_day, near1, k_near1)
        if near1_entry_px is None:
            fails["no_near1_entry"] += 1; continue
        for exit_name, n_before in EXIT_VARIANTS.items():
            ex_day_mid = mkt.exit_day(near1, n_before)
            if ex_day_mid is None:
                fails["no_exit_day"] += 1; continue
            if n_before == 0:
                u = mkt.fut_price(near1, near1)
                near1_exit_px = max(u - k_near1, 0.0) if u is not None else None
            else:
                near1_exit_px = mkt.ce_price(ex_day_mid, near1, k_near1)
            near3_mark_mid = mkt.ce_price(ex_day_mid, near3, k_near3)  # mark only, not traded (roll keeps it)
            if None in (near1_exit_px, near3_mark_mid):
                fails["no_near1_exit_or_near3_mark"] += 1; continue
            # --- ROLL: sub-cycle 2 -- sell fresh near2 at ex_day_mid against the SAME held near3
            fwd_near2_mid = mkt.fut_price(ex_day_mid, near2)
            k_near2, near2_entry_px = mkt.atm_pick(ex_day_mid, near2, fwd_near2_mid)
            if near2_entry_px is None:
                fails["no_near2_entry"] += 1; continue
            ex_day_final = mkt.exit_day(near2, n_before)
            if ex_day_final is None:
                fails["no_final_exit_day"] += 1; continue
            if n_before == 0:
                u2 = mkt.fut_price(near2, near2)
                near2_exit_px = max(u2 - k_near2, 0.0) if u2 is not None else None
            else:
                near2_exit_px = mkt.ce_price(ex_day_final, near2, k_near2)
            near3_exit_px = mkt.ce_price(ex_day_final, near3, k_near3)
            if None in (near2_exit_px, near3_exit_px):
                fails["no_near2_or_near3_exit"] += 1; continue

            # ROLL pnl (points, 1x1 ATM/ATM, short_n=long_n=1 each sub-cycle vs the SAME far)
            def rt(entry, exit_, side_entry, side_exit):
                return slip(entry, side_entry), slip(exit_, side_exit)
            n1e, n1x = rt(near1_entry_px, near1_exit_px, "sell", "buy")
            n2e, n2x = rt(near2_entry_px, near2_exit_px, "sell", "buy")
            f3e, f3x = rt(near3_entry_px, near3_exit_px, "buy", "sell")
            roll_net = (n1e - n1x) + (n2e - n2x) + (f3x - f3e) - (BROK_PER_LOT_SIDE / LOT) * 2 * 3
            roll_gross = (near1_entry_px - near1_exit_px) + (near2_entry_px - near2_exit_px) + (near3_exit_px - near3_entry_px)

            # NO-ROLL baseline: cycle A (near1/near2, flatten near2 at ex_day_mid) + cycle B (near2/near3 fresh at ex_day_mid)
            # cycle A entered on the SAME entry_day as the roll variant (fair comparison -- same fill days)
            k_near2_far = row["far_strike"]
            near2_far_entry_px = mkt.ce_price(entry_day, near2, k_near2_far)
            near2_far_exit_px = mkt.ce_price(ex_day_mid, near2, k_near2_far)  # cycle A's far-leg exit
            if None in (near2_far_entry_px, near2_far_exit_px):
                fails["no_cycleA_far_leg"] += 1; continue
            # cycle B: fresh near2(near)/near3(far) entered at ex_day_mid (near2 strike may differ from cycle A's far strike; re-pick ATM)
            k_near2_freshnear, near2_freshnear_entry = mkt.atm_pick(ex_day_mid, near2, fwd_near2_mid)
            fwd_near3_mid = mkt.fut_price(ex_day_mid, near3)
            k_near3_freshfar, near3_freshfar_entry = mkt.atm_pick(ex_day_mid, near3, fwd_near3_mid)
            if None in (near2_freshnear_entry, near3_freshfar_entry):
                fails["no_cycleB_fresh_legs"] += 1; continue
            if n_before == 0:
                u3 = mkt.fut_price(near2, near2)
                near2_freshnear_exit = max(u3 - k_near2_freshnear, 0.0) if u3 is not None else None
            else:
                near2_freshnear_exit = mkt.ce_price(ex_day_final, near2, k_near2_freshnear)
            near3_freshfar_exit = mkt.ce_price(ex_day_final, near3, k_near3_freshfar)
            if None in (near2_freshnear_exit, near3_freshfar_exit):
                fails["no_cycleB_fresh_legs"] += 1; continue

            a1e, a1x = rt(near1_entry_px, near1_exit_px, "sell", "buy")
            a2e, a2x = rt(near2_far_entry_px, near2_far_exit_px, "buy", "sell")
            b1e, b1x = rt(near2_freshnear_entry, near2_freshnear_exit, "sell", "buy")
            b2e, b2x = rt(near3_freshfar_entry, near3_freshfar_exit, "buy", "sell")
            noroll_net = (a1e - a1x) + (a2x - a2e) + (b1e - b1x) + (b2x - b2e) - (BROK_PER_LOT_SIDE / LOT) * 2 * 4
            noroll_gross = (near1_entry_px - near1_exit_px) + (near2_far_exit_px - near2_far_entry_px) + \
                           (near2_freshnear_entry - near2_freshnear_exit) + (near3_freshfar_exit - near3_freshfar_entry)

            notional = row["fwd_near"] * LOT
            rows.append(dict(
                day0=day0, entry_day=entry_day, near1=near1, near2=near2, near3=near3, exit_variant=exit_name,
                iv_spread=row["iv_spread"], near_iv_pct=row["near_iv_pct"],
                roll_gross_pts=roll_gross, roll_net_pts=roll_net,
                noroll_gross_pts=noroll_gross, noroll_net_pts=noroll_net,
                roll_friction_pts=roll_gross - roll_net, noroll_friction_pts=noroll_gross - noroll_net,
                margin_5pct=0.05 * notional, margin_10pct=0.10 * notional,
            ))
    log(f"grid B: {len(rows)} rows built, fails breakdown: {fails}")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# STATS
# ---------------------------------------------------------------------------
def nw_t(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def summarize_cell(sub: pd.DataFrame, pnl_col: str, margin_col: str, label: dict):
    if len(sub) == 0:
        return None
    ret = sub[pnl_col] * LOT / sub[margin_col]
    cum = ret.cumsum()
    running_max = cum.cummax()
    dd = (cum - running_max)
    win = (sub[pnl_col] > 0).mean()
    pf_num = sub.loc[sub[pnl_col] > 0, pnl_col].sum()
    pf_den = -sub.loc[sub[pnl_col] < 0, pnl_col].sum()
    pf = pf_num / pf_den if pf_den > 0 else np.nan
    return dict(**label, n=len(sub), mean_pts=sub[pnl_col].mean(), median_pts=sub[pnl_col].median(),
                win_rate=win, pf=pf, nw_t=nw_t(sub[pnl_col]), sum_return_on_margin=ret.sum(),
                mean_return_on_margin=ret.mean(), maxDD_on_margin=dd.min(), worst_trade_pts=sub[pnl_col].min())


def main():
    log("=== START ===")
    ts = pd.read_csv(TS_PATH, parse_dates=["day"])
    ts["near_expiry"] = pd.to_datetime(ts["near_expiry"])
    ts["far_expiry"] = pd.to_datetime(ts["far_expiry"])
    next_monthly = dict(zip(ts["near_expiry"], ts["far_expiry"]))

    ce_all, fut_all = load_all()
    mkt = Market(ce_all, fut_all)

    log("building grid A (main 120-cell grid) ...")
    ga = build_grid_a(mkt, ts)
    ga.to_csv(OUT / "grid_a_trades_raw.csv", index=False)
    ga = apply_filters(ga)

    build_split = ga["day0"] < HELD_OUT_START
    for split_name, split_mask in [("BUILD_2011_2025", build_split), ("HELDOUT_2026H1", ~build_split)]:
        rows_out = []
        gsub_split = ga[split_mask]
        for sstruct in STRIKE_STRUCTS:
            for ratio_name in RATIOS:
                for exit_name in EXIT_VARIANTS:
                    base = gsub_split[(gsub_split["strike_struct"] == sstruct) &
                                       (gsub_split["ratio"] == ratio_name) &
                                       (gsub_split["exit_variant"] == exit_name)]
                    for filt in FILTERS:
                        sub = base[base[f"f_{filt}"]]
                        for mname in MARGIN_BOUNDS:
                            r_net = summarize_cell(sub, "net_pts", f"margin_{mname}",
                                                    dict(strike_struct=sstruct, ratio=ratio_name,
                                                         exit_variant=exit_name, filter=filt, margin=mname, basis="NET"))
                            r_gross = summarize_cell(sub, "gross_pts", f"margin_{mname}",
                                                      dict(strike_struct=sstruct, ratio=ratio_name,
                                                           exit_variant=exit_name, filter=filt, margin=mname, basis="GROSS"))
                            if r_net:
                                # friction-as-%-of-gross is only a meaningful number when gross itself
                                # is positive (edge exists before costs); a negative-gross cell means
                                # the family lost money even before frictions, and the ratio's sign
                                # flips into nonsense -- report NaN there, not a misleading number.
                                gsum = sub["gross_pts"].sum()
                                r_net["friction_pct_of_gross"] = (
                                    100.0 * sub["friction_pts"].sum() / gsum if gsum > 0 else np.nan)
                                rows_out.append(r_net)
                            if r_gross:
                                rows_out.append(r_gross)
        pd.DataFrame(rows_out).to_csv(OUT / f"grid_a_summary_{split_name}.csv", index=False)
        log(f"{split_name}: {len(rows_out)} summary rows written")

    log("building grid B (roll vs no-roll, 20+20 cells) ...")
    gb = build_grid_b(mkt, ts, next_monthly)
    gb.to_csv(OUT / "grid_b_trades_raw.csv", index=False)
    if gb.empty:
        log("WARNING: grid B produced ZERO rows -- writing empty summary, see fails breakdown above")
        pd.DataFrame([]).to_csv(OUT / "grid_b_summary.csv", index=False)
        log("=== DONE (grid B empty) ===")
        return
    gb["f_unconditional"] = True
    gb["f_contango"] = gb["iv_spread"] < -0.02
    gb["f_inversion"] = gb["iv_spread"] > 0.02
    gb["f_topdecile"] = gb["near_iv_pct"] >= 90
    gb["f_inv_and_topdecile"] = gb["f_inversion"] & gb["f_topdecile"]
    b_build = gb["day0"] < HELD_OUT_START
    rows_out_b = []
    for split_name, mask in [("BUILD_2011_2025", b_build), ("HELDOUT_2026H1", ~b_build)]:
        gsub = gb[mask]
        for exit_name in EXIT_VARIANTS:
            base = gsub[gsub["exit_variant"] == exit_name]
            for filt in FILTERS:
                sub = base[base[f"f_{filt}"]]
                for variant, pnl_col in [("roll", "roll_net_pts"), ("noroll", "noroll_net_pts")]:
                    for mname in MARGIN_BOUNDS:
                        r = summarize_cell(sub, pnl_col, f"margin_{mname}",
                                            dict(split=split_name, exit_variant=exit_name, filter=filt,
                                                 variant=variant, margin=mname, basis="NET"))
                        if r:
                            gross_col = "roll_gross_pts" if variant == "roll" else "noroll_gross_pts"
                            fric_col = "roll_friction_pts" if variant == "roll" else "noroll_friction_pts"
                            gsum = sub[gross_col].sum()
                            r["friction_pct_of_gross"] = (100.0 * sub[fric_col].sum() / gsum
                                                           if gsum > 0 else np.nan)
                            rows_out_b.append(r)
    pd.DataFrame(rows_out_b).to_csv(OUT / "grid_b_summary.csv", index=False)
    log(f"grid B: {len(rows_out_b)} summary rows written")

    log("=== DONE ===")


if __name__ == "__main__":
    T0 = time.time()
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
else:
    T0 = time.time()
