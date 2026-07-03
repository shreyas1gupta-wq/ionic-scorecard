"""BT-11 + COST-11 -- honest monthly-rebalance backtest of the SIG-11 Track-2 signal stack.

Track-2 is the LOW-CAPITAL momentum machine (Rs 10L notional book), NOT the Rs 1cr options book.

Design (per D-M3 build spec + RESEARCH_SOP DENOMINATOR RULE + COST_STANDARDS):
  - Monthly rebalance 2016 -> latest data (DATA_MAX_DATE = 2026-01-22).
  - At each month-end: take ALL_PASS names (sig11 8-criteria Minervini + 12-1 momentum
    + RS percentile + breakout-vol), rank by composite score, hold top-N (N=10 and N=20),
    equal-weight, NEXT-DAY-OPEN entry (no same-bar, L5).
  - Position cap 10% each; if fewer than N pass, hold CASH for the shortfall (that IS the
    signal -- never pad with non-passing names).
  - Exit on next rebalance (v1 shipped = rebalance-only; see VERDICT.md note on trailing stop).
  - COST-11: COST_STANDARDS all-in equity DELIVERY costs per side + a 2x stress column.
  - Honest reporting: CAGR, max DD, monthly Sharpe, rupee P&L on Rs 10L book, per-year table.
  - MANDATORY pre-IC shuffle: same portfolio with the ALL_PASS gate SHUFFLED (random same-size
    draws from the PIT universe each month), N shuffles, percentile of the real strategy.
  - Regime slices: 2018 smallcap crash, 2020 COVID, 2022 rate shock, 2024, 2025-26.

NO LOOK-AHEAD:
  - Features built once over the full panel with RIGHT-CLOSED rolling windows (a feature at
    date t uses only rows <= t). Equivalence to sig11.compute_signals() is ASSERTED on sample
    dates before the run (guard: _assert_engine_matches_sig11).
  - RS percentile recomputed per month over THAT month's PIT universe only (data11.pit_universe).
  - Entry at t+1 OPEN using the panel's own open column; a name with no t+1 open print is skipped.
  - Composite score for ranking uses only asof-date features (rs_pct, mom_blend, breakout_vol).

Run: PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python bt11.py [--shuffles N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib"))
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\track2"))
import guards as G  # noqa  (landmine guards mandatory in every entry point)
import data11 as D11
import sig11 as S11

OUTDIR = os.path.join(ROOT, r"results\T2-SIG11\20260704_bt11")

# ---- run parameters (FROZEN; anything not here is frozen-by-doctrine in sig11) ----
START = pd.Timestamp("2016-01-01")
END = D11.DATA_MAX_DATE                    # 2026-01-22 (post-IST-fix)
NOTIONAL = 1_000_000.0 * 10.0 / 10.0       # Rs 10,00,000 = Rs 10L Track-2 book
NOTIONAL = 1_000_000.0                     # explicit: Rs 10 lakh
POS_CAP = 0.10                             # 10% each (== equal weight at N=10; binding cap at N<10)
TOP_NS = [10, 20]
SLIPPAGE_SMALLCAP_BPS = 35.0               # COST_STANDARDS small-cap one-way slippage floor
COST_SEED = 20260704
DEFAULT_SHUFFLES = 100

# ---- COST-11: COST_STANDARDS equity-DELIVERY all-in, expressed per side of traded value ----
# Fixed per-order: brokerage Rs 20/order. Percentage-of-value stack differs buy vs sell.
BROKERAGE_PER_ORDER = 20.0
EXCH_TXN = 0.00297e-2      # 0.00297% NSE equity
SEBI = 10.0 / 1e7         # Rs 10 / crore = 1e-6 of turnover
GST = 0.18                # on (brokerage + exch_txn + SEBI)
STT_DELIVERY = 0.1e-2     # 0.1% BOTH sides (delivery)
STAMP_BUY = 0.015e-2      # 0.015% delivery buy only


def side_cost_frac(is_buy: bool, trade_value: float) -> float:
    """All-in cost for ONE side as a FRACTION of that side's traded value, per COST_STANDARDS
    equity-delivery stack. Slippage handled separately (applied to fill price). Brokerage is a
    flat Rs 20 that we express as a fraction of this order's value (small orders -> higher %)."""
    if trade_value <= 0:
        return 0.0
    brokerage = BROKERAGE_PER_ORDER
    exch = EXCH_TXN * trade_value
    sebi = SEBI * trade_value
    gst = GST * (brokerage + exch + sebi)
    stt = STT_DELIVERY * trade_value            # both sides
    stamp = STAMP_BUY * trade_value if is_buy else 0.0
    total = brokerage + exch + sebi + gst + stt + stamp
    return total / trade_value


# ---------------------------------------------------------------------------
# Feature build (ONCE over full panel; right-closed rolling => PIT-safe by construction)
# ---------------------------------------------------------------------------
def build_full_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute sig11's per-symbol technical features across the ENTIRE panel in one pass.
    Reuses sig11._compute_symbol_features (same frozen constants). Right-closed rolling means
    a feature at date t is a function only of rows <= t -> appending future rows cannot change
    it (prefix equality), so computing once == computing per-asof-date, for the criteria that
    do NOT depend on the cross-section. The cross-sectional piece (rs_pct) is recomputed per
    month over that month's PIT universe (see compute_month_signals)."""
    parts = []
    for _, g in panel.sort_values(["symbol", "date"]).groupby("symbol", sort=False):
        parts.append(S11._compute_symbol_features(g))
    feats = pd.concat(parts, ignore_index=True)
    return feats


def _criteria_noncross(snap: pd.DataFrame) -> pd.DataFrame:
    """Criteria c1..c7 (all non-cross-sectional) computed on a per-date snapshot of features.
    Mirrors sig11.compute_signals exactly."""
    c1 = (snap["close"] > snap["ma150"]) & (snap["close"] > snap["ma200"])
    c2 = snap["ma150"] > snap["ma200"]
    c3 = snap["ma200"] > snap["ma200_ago"]
    c4 = (snap["ma50"] > snap["ma150"]) & (snap["ma150"] > snap["ma200"])
    c5 = snap["close"] > snap["ma50"]
    c6 = snap["close"] >= (1.0 + S11.PCT_ABOVE_52W_LOW) * snap["lo_252"]
    c7 = snap["close"] >= (1.0 - S11.PCT_WITHIN_52W_HIGH) * snap["hi_252"]
    out = pd.DataFrame({
        "c1_close_above_150_200": c1, "c2_150_above_200": c2, "c3_200ma_rising": c3,
        "c4_50_above_150_above_200": c4, "c5_close_above_50": c5,
        "c6_above_52w_low": c6, "c7_within_52w_high": c7,
    }, index=snap.index)
    return out


def compute_month_signals(feats_by_date: dict, asof: pd.Timestamp) -> pd.DataFrame:
    """Reproduce sig11.compute_signals(panel, asof) using the pre-built full-panel features.
    Returns the asof-date snapshot restricted to that month's PIT universe, with c1..c8,
    ALL_PASS, rs_pct, mom_blend, breakout_vol_flag, price_floor_ok, composite_score."""
    if asof not in feats_by_date:
        return pd.DataFrame()
    snap = feats_by_date[asof].copy()
    universe = D11.pit_universe(asof)
    snap = snap[snap["symbol"].isin(universe)]
    if snap.empty:
        return snap
    snap["price_floor_ok"] = snap["close"] >= D11.PRICE_FLOOR

    crit = _criteria_noncross(snap)
    for c in crit.columns:
        snap[c] = crit[c].fillna(False).astype(bool)

    # cross-sectional RS percentile over THIS PIT snapshot only
    snap["mom_blend"] = S11.RS_BLEND_W12 * snap["mom_12_1"] + (1 - S11.RS_BLEND_W12) * snap["mom_6_1"]
    valid = snap["mom_blend"].notna()
    snap["rs_pct"] = np.nan
    if valid.sum() > 1:
        snap.loc[valid, "rs_pct"] = snap.loc[valid, "mom_blend"].rank(pct=True) * 100.0
    elif valid.sum() == 1:
        snap.loc[valid, "rs_pct"] = 100.0
    snap["c8_rs_pct_ge70"] = (snap["rs_pct"] >= S11.RS_PCT_GATE).fillna(False).astype(bool)

    snap["ALL_PASS"] = snap[S11.CRITERION_COLS].all(axis=1)

    # composite ranking score: RS percentile (primary) + normalized momentum + breakout-vol nudge.
    # Higher = stronger leader. All inputs are asof-date only (no lookahead).
    mb = snap["mom_blend"]
    mb_norm = (mb - mb.min()) / (mb.max() - mb.min() + 1e-12) * 100.0
    snap["composite_score"] = (
        snap["rs_pct"].fillna(0.0)
        + 0.25 * mb_norm.fillna(0.0)
        + 5.0 * snap["breakout_vol_flag"].astype(float)
    )
    return snap.sort_values("symbol").reset_index(drop=True)


def _assert_engine_matches_sig11(panel, feats_by_date, sample_dates):
    """GUARD: prove the fast pre-built-feature path reproduces sig11.compute_signals()
    exactly on sample month-ends (ALL_PASS set + rs_pct)."""
    for d in sample_dates:
        if d not in feats_by_date:
            continue
        ref = S11.compute_signals(panel, d)
        mine = compute_month_signals(feats_by_date, d)
        ref_pass = set(ref.loc[ref["ALL_PASS"], "symbol"])
        mine_pass = set(mine.loc[mine["ALL_PASS"], "symbol"])
        assert ref_pass == mine_pass, (
            f"ENGINE MISMATCH {d.date()}: ALL_PASS sets differ "
            f"(ref {len(ref_pass)} vs mine {len(mine_pass)}; "
            f"sym-diff {sorted(ref_pass ^ mine_pass)[:5]})")
        # rs_pct equality on shared symbols
        m = ref[["symbol", "rs_pct"]].merge(mine[["symbol", "rs_pct"]], on="symbol", suffixes=("_r", "_m"))
        both = m.dropna()
        if len(both):
            maxdiff = (both["rs_pct_r"] - both["rs_pct_m"]).abs().max()
            assert maxdiff < 1e-6, f"ENGINE MISMATCH {d.date()}: rs_pct maxdiff {maxdiff}"
    print(f"[guard] engine matches sig11.compute_signals on {len(sample_dates)} sample dates")


# ---------------------------------------------------------------------------
# Portfolio backtest (monthly rebalance, next-day-open, rebalance-only exit)
# ---------------------------------------------------------------------------
def month_end_trading_dates(all_dates: pd.DatetimeIndex, start, end) -> list:
    """Last available TRADING date in each calendar month within [start, end]."""
    d = pd.Series(all_dates)
    d = d[(d >= start) & (d <= end)]
    grp = d.groupby([d.dt.year, d.dt.month]).max()
    return sorted(grp.tolist())


def next_open_map(panel: pd.DataFrame) -> dict:
    """For each (symbol) an ordered array of (date, open) so we can find the FIRST trading
    date strictly AFTER a given asof date and its open (the next-day-open entry, L5-clean)."""
    m = {}
    for sym, g in panel.sort_values("date").groupby("symbol", sort=False):
        m[sym] = (g["date"].to_numpy(), g["open"].to_numpy(dtype="float64"),
                  g["close"].to_numpy(dtype="float64"))
    return m


def _next_open(entry_book: dict, sym: str, asof: pd.Timestamp):
    """First (date, open) strictly after asof for sym, else (None, None)."""
    if sym not in entry_book:
        return None, None
    dates, opens, _ = entry_book[sym]
    idx = np.searchsorted(dates, np.datetime64(asof), side="right")
    if idx >= len(dates):
        return None, None
    return pd.Timestamp(dates[idx]), float(opens[idx])


def _open_on_or_after(entry_book: dict, sym: str, target: pd.Timestamp):
    """First (date, open) on-or-after target for sym (exit fill), else (None, None)."""
    if sym not in entry_book:
        return None, None
    dates, opens, _ = entry_book[sym]
    idx = np.searchsorted(dates, np.datetime64(target), side="left")
    if idx >= len(dates):
        return None, None
    return pd.Timestamp(dates[idx]), float(opens[idx])


def run_backtest(panel, feats_by_date, entry_book, rebal_dates, top_n,
                 selector, cost_mult=1.0, notional=NOTIONAL):
    """Monthly-rebalance, equal-weight (capped 10%), next-day-open entry, rebalance-only exit.

    selector(asof) -> list of chosen symbols (ranked, already length<=top_n). Cash for shortfall.
    cost_mult: 1.0 = COST_STANDARDS; 2.0 = stress column.
    Returns (period_records_df, trades_df). P&L booked in EXIT period (denominator rule).
    """
    equity = notional
    equity_curve = []          # (rebal_date, equity_at_entry_of_this_period)
    period_records = []        # per rebalance period
    trades = []

    prev_positions = {}        # sym -> {'entry_date','entry_px_net','shares','value_gross'}

    for i, asof in enumerate(rebal_dates):
        chosen = selector(asof, top_n)
        # entry fills at next trading day's open
        entries = {}
        for sym in chosen:
            edate, eopen = _next_open(entry_book, sym, asof)
            if edate is None or not np.isfinite(eopen) or eopen <= 0:
                continue  # no tradable next-day open -> skip (honest: cannot fill)
            entries[sym] = (edate, eopen)

        n_filled = len(entries)
        # equal weight across the SLOTS (top_n), NOT across filled names: shortfall -> cash.
        # This is the honest low-capital rule: fewer than N passing => hold cash.
        capital_per_slot = notional_slot = equity / top_n
        # position cap 10% each: at N=10 slot==10%; at N=20 slot==5% (both <=cap, fine).
        capital_per_slot = min(capital_per_slot, POS_CAP * equity)

        # ---- exit the PREVIOUS period's book at THIS rebalance's next-day open ----
        # (rebalance-only exit: sell everything, re-enter the new chosen set)
        period_pl = 0.0
        period_cost = 0.0
        exit_target = None
        if prev_positions:
            for sym, pos in prev_positions.items():
                # exit fill = open on the entry date of the NEW period (same day we re-enter),
                # i.e. first trading day strictly after asof -> use next_open as the exit stamp.
                xdate, xopen = _next_open(entry_book, sym, asof)
                if xdate is None or not np.isfinite(xopen) or xopen <= 0:
                    # cannot get an exit print: mark at last known close (conservative, rare)
                    _, _, closes = entry_book.get(sym, (None, None, None))
                    xopen = pos["entry_px_gross"] if closes is None else float(closes[-1])
                    xdate = asof
                shares = pos["shares"]
                exit_value = shares * xopen
                # sell-side costs (slippage + charges) applied to exit
                slip = SLIPPAGE_SMALLCAP_BPS / 1e4 * cost_mult
                exit_fill_px = xopen * (1.0 - slip)
                exit_value_net = shares * exit_fill_px
                sell_charges = side_cost_frac(False, exit_value_net) * cost_mult * exit_value_net
                proceeds = exit_value_net - sell_charges
                cost_this = (exit_value - exit_value_net) + sell_charges
                pl = proceeds - pos["cost_basis"]
                period_pl += pl
                period_cost += pos["buy_cost"] + cost_this
                trades.append({
                    "symbol": sym, "entry_date": pos["entry_date"], "entry_px_net": pos["entry_px_net"],
                    "exit_date": xdate, "exit_px_net": exit_fill_px, "shares": shares,
                    "cost_basis": pos["cost_basis"], "proceeds": proceeds, "pl": pl,
                    "ret": pl / pos["cost_basis"] if pos["cost_basis"] > 0 else 0.0,
                    "hold_days": (xdate - pos["entry_date"]).days,
                })
            equity += period_pl  # realize into equity at exit

        # ---- enter the NEW book ----
        new_positions = {}
        capital_per_slot = min(equity / top_n, POS_CAP * equity)
        for sym, (edate, eopen) in entries.items():
            slip = SLIPPAGE_SMALLCAP_BPS / 1e4 * cost_mult
            buy_fill_px = eopen * (1.0 + slip)
            shares = capital_per_slot / buy_fill_px
            gross = shares * eopen
            slip_cost = shares * (buy_fill_px - eopen)
            buy_charges = side_cost_frac(True, shares * buy_fill_px) * cost_mult * (shares * buy_fill_px)
            cost_basis = shares * buy_fill_px + buy_charges
            new_positions[sym] = {
                "entry_date": edate, "entry_px_gross": eopen, "entry_px_net": buy_fill_px,
                "shares": shares, "cost_basis": cost_basis,
                "buy_cost": slip_cost + buy_charges,
            }
        prev_positions = new_positions

        period_records.append({
            "rebal_date": asof, "n_chosen": len(chosen), "n_filled": n_filled,
            "equity_after_exit": equity, "period_realized_pl": period_pl,
            "period_cost": period_cost, "cash_slots": top_n - n_filled,
        })

    # close the final open book at the last available data date (book the final period)
    if prev_positions:
        final_pl = 0.0
        for sym, pos in prev_positions.items():
            _, _, closes = entry_book.get(sym, (None, None, None))
            xopen = float(closes[-1]) if closes is not None and len(closes) else pos["entry_px_gross"]
            xdate = END
            shares = pos["shares"]
            slip = SLIPPAGE_SMALLCAP_BPS / 1e4 * cost_mult
            exit_fill_px = xopen * (1.0 - slip)
            proceeds = shares * exit_fill_px
            sell_charges = side_cost_frac(False, proceeds) * cost_mult * proceeds
            proceeds -= sell_charges
            pl = proceeds - pos["cost_basis"]
            final_pl += pl
            trades.append({
                "symbol": sym, "entry_date": pos["entry_date"], "entry_px_net": pos["entry_px_net"],
                "exit_date": xdate, "exit_px_net": exit_fill_px, "shares": shares,
                "cost_basis": pos["cost_basis"], "proceeds": proceeds, "pl": pl,
                "ret": pl / pos["cost_basis"] if pos["cost_basis"] > 0 else 0.0,
                "hold_days": (xdate - pos["entry_date"]).days,
            })
        equity += final_pl
        period_records.append({
            "rebal_date": END, "n_chosen": 0, "n_filled": 0,
            "equity_after_exit": equity, "period_realized_pl": final_pl,
            "period_cost": 0.0, "cash_slots": top_n,
        })

    return pd.DataFrame(period_records), pd.DataFrame(trades)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def compute_metrics(period_df, trades_df, notional=NOTIONAL, label=""):
    """CAGR, max DD, monthly Sharpe, rupee P&L on the Rs 10L book, per-year table.
    Equity series = book value at each rebalance (after that period's realized P&L)."""
    if period_df.empty:
        return {}
    eq = period_df["equity_after_exit"].to_numpy(dtype="float64")
    dates = pd.to_datetime(period_df["rebal_date"])
    # prepend the starting notional as period-0
    eq_full = np.concatenate([[notional], eq])
    months = len(eq)
    yrs = (dates.iloc[-1] - dates.iloc[0]).days / 365.25
    yrs = max(yrs, 1e-9)
    final_eq = eq[-1]
    cagr = (final_eq / notional) ** (1.0 / yrs) - 1.0

    # monthly returns from the realized-equity path
    monthly_ret = pd.Series(eq_full).pct_change().dropna()
    sharpe = (monthly_ret.mean() / (monthly_ret.std(ddof=1) + 1e-12) * np.sqrt(12)
              if len(monthly_ret) > 2 else float("nan"))

    running_max = np.maximum.accumulate(eq_full)
    dd = eq_full / running_max - 1.0
    max_dd = float(dd.min())

    total_pl = final_eq - notional
    total_cost = float(period_df["period_cost"].sum())

    # per-year table (book P&L attributed to the year the period was BOOKED -- exit period)
    per_year = {}
    if not trades_df.empty:
        t = trades_df.copy()
        t["exit_year"] = pd.to_datetime(t["exit_date"]).dt.year
        for yr, g in t.groupby("exit_year"):
            per_year[int(yr)] = {
                "n_trades": int(len(g)),
                "rupee_pl": round(float(g["pl"].sum()), 2),
                "avg_trade_ret_pct": round(float(g["ret"].mean()) * 100, 3),
                "win_rate_pct": round(float((g["pl"] > 0).mean()) * 100, 2),
            }
    # per-year book return from equity path (period rebal_date year)
    py2 = {}
    pe = period_df.copy()
    pe["yr"] = pd.to_datetime(pe["rebal_date"]).dt.year
    prev = notional
    for yr, g in pe.groupby("yr"):
        start_eq = prev
        end_eq = g["equity_after_exit"].iloc[-1]
        py2[int(yr)] = round((end_eq / start_eq - 1.0) * 100, 3)
        prev = end_eq

    return {
        "label": label,
        "years": round(yrs, 3),
        "n_rebalances": int(months),
        "start_notional_rupees": round(notional, 2),
        "final_equity_rupees": round(float(final_eq), 2),
        "total_pl_rupees": round(float(total_pl), 2),
        "total_cost_rupees": round(total_cost, 2),
        "cagr_pct": round(cagr * 100, 3),
        "max_drawdown_pct": round(max_dd * 100, 3),
        "monthly_sharpe": round(float(sharpe), 3),
        "n_trades": int(len(trades_df)),
        "avg_cash_slots": round(float(period_df["cash_slots"].mean()), 2),
        "per_year_trade_pl": per_year,
        "per_year_book_return_pct": py2,
    }


def regime_slices(trades_df, notional=NOTIONAL):
    """Book P&L (rupee + %) by regime window, attributed to EXIT date (booked in exit period)."""
    windows = {
        "2018_smallcap_crash": ("2018-01-01", "2018-12-31"),
        "2020_covid": ("2020-01-01", "2020-12-31"),
        "2022_rate_shock": ("2022-01-01", "2022-12-31"),
        "2024": ("2024-01-01", "2024-12-31"),
        "2025_26": ("2025-01-01", "2026-12-31"),
    }
    out = {}
    if trades_df.empty:
        return out
    t = trades_df.copy()
    t["exit_date"] = pd.to_datetime(t["exit_date"])
    for name, (a, b) in windows.items():
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        g = t[(t["exit_date"] >= a) & (t["exit_date"] <= b)]
        if len(g) == 0:
            out[name] = {"n_trades": 0, "rupee_pl": 0.0, "pct_of_notional": 0.0, "avg_trade_ret_pct": None}
            continue
        out[name] = {
            "n_trades": int(len(g)),
            "rupee_pl": round(float(g["pl"].sum()), 2),
            "pct_of_notional": round(float(g["pl"].sum()) / notional * 100, 3),
            "avg_trade_ret_pct": round(float(g["ret"].mean()) * 100, 3),
            "win_rate_pct": round(float((g["pl"] > 0).mean()) * 100, 2),
        }
    return out


# ---------------------------------------------------------------------------
# Selectors: real (ALL_PASS ranked) and shuffle (random PIT-universe draws)
# ---------------------------------------------------------------------------
def make_real_selector(feats_by_date):
    cache = {}
    def selector(asof, top_n):
        if asof not in cache:
            cache[asof] = compute_month_signals(feats_by_date, asof)
        sig = cache[asof]
        if sig.empty:
            return []
        passed = sig[sig["ALL_PASS"] & sig["price_floor_ok"]].copy()
        passed = passed.sort_values("composite_score", ascending=False)
        return passed["symbol"].head(top_n).tolist()
    return selector


def build_shuffle_pools(feats_by_date):
    """Precompute the price-floor-eligible PIT pool per month ONCE (heavy: months x universe).
    Returned as python lists so the per-shuffle selector can use fast rng.choice on an ndarray
    without rebuilding the pool. Call once, reuse across all shuffles."""
    pools = {}
    for asof, snap in feats_by_date.items():
        universe = D11.pit_universe(asof)
        s = snap[snap["symbol"].isin(universe)]
        s = s[s["close"] >= D11.PRICE_FLOOR]
        pools[asof] = s["symbol"].to_numpy()
    return pools


def make_shuffle_selector(pools, rng, real_counts):
    """Random same-SIZE draws from the (precomputed) PIT pool each month -- the null. Size per
    month = the number of names the REAL strategy actually held that month (so shuffle and real
    hold the same count, cash for the same shortfall). `pools` from build_shuffle_pools()."""
    def selector(asof, top_n):
        want = real_counts.get((asof, top_n), 0)
        if want <= 0 or asof not in pools:
            return []
        pool = pools[asof]
        if len(pool) == 0:
            return []
        k = min(want, len(pool))
        idx = rng.choice(len(pool), size=k, replace=False)
        return pool[idx].tolist()
    return selector


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shuffles", type=int, default=DEFAULT_SHUFFLES)
    args = ap.parse_args()

    t0 = time.time()
    print("[1/7] loading panel ...")
    panel = D11.load_panel()
    all_dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    print(f"    panel rows={len(panel):,} symbols={panel['symbol'].nunique():,} "
          f"dates {all_dates.min().date()}->{all_dates.max().date()}")

    print("[2/7] building features once over full panel ...")
    feats = build_full_features(panel)
    feats["date"] = pd.to_datetime(feats["date"])
    feats_by_date = {d: g.reset_index(drop=True) for d, g in feats.groupby("date")}
    print(f"    feature rows={len(feats):,}")

    rebal_dates = month_end_trading_dates(all_dates, START, END)
    print(f"[3/7] rebalance month-ends: {len(rebal_dates)} "
          f"({rebal_dates[0].date()} -> {rebal_dates[-1].date()})")

    # GUARD: fast engine must match sig11.compute_signals exactly
    print("[4/7] engine-equivalence guard ...")
    sample = [d for d in rebal_dates if d.year in (2018, 2020, 2023, 2025)][:4]
    _assert_engine_matches_sig11(panel, feats_by_date, sample)

    entry_book = next_open_map(panel)

    # ---- BASE RUN: real selector, both N, both cost multipliers ----
    print("[5/7] base runs (real ALL_PASS selector) ...")
    real_selector = make_real_selector(feats_by_date)
    metrics = {}
    real_counts = {}   # (asof, top_n) -> actual filled count, for the shuffle to match size
    trades_store = {}
    for top_n in TOP_NS:
        for mult, tag in [(1.0, "cost1x"), (2.0, "cost2x")]:
            pr, tr = run_backtest(panel, feats_by_date, entry_book, rebal_dates,
                                  top_n, real_selector, cost_mult=mult)
            key = f"N{top_n}_{tag}"
            metrics[key] = compute_metrics(pr, tr, label=key)
            metrics[key]["regime_slices"] = regime_slices(tr)
            trades_store[key] = tr
            if mult == 1.0:
                # record REAL filled counts per month for shuffle size-matching
                for _, row in pr.iterrows():
                    real_counts[(row["rebal_date"], top_n)] = int(row["n_filled"])
            print(f"    {key}: CAGR {metrics[key]['cagr_pct']}%  MaxDD {metrics[key]['max_drawdown_pct']}%  "
                  f"Sharpe {metrics[key]['monthly_sharpe']}  finalRs {metrics[key]['final_equity_rupees']:,.0f}  "
                  f"trades {metrics[key]['n_trades']}")

    # checkpoint metrics NOW (before shuffle) per spec
    with open(os.path.join(OUTDIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"    [checkpoint] metrics.json written ({time.time()-t0:.0f}s)")

    # per-year CSV
    rows = []
    for key, m in metrics.items():
        for yr, v in m.get("per_year_trade_pl", {}).items():
            rows.append({"strategy": key, "year": yr, **v})
    pd.DataFrame(rows).to_csv(os.path.join(OUTDIR, "per_year.csv"), index=False)
    # save trades for the headline configs
    for key, tr in trades_store.items():
        tr.to_csv(os.path.join(OUTDIR, f"trades_{key}.csv"), index=False)

    # ---- SHUFFLE (mandatory pre-IC) : cost-1x, both N ----
    n_shuf = args.shuffles
    print(f"[6/7] shuffle null: {n_shuf} shuffles per N (cost 1x, size-matched to real) ...")
    shuffle_results = {}
    for top_n in TOP_NS:
        real_cagr = metrics[f"N{top_n}_cost1x"]["cagr_pct"]
        real_final = metrics[f"N{top_n}_cost1x"]["final_equity_rupees"]
        cagrs = []
        finals = []
        for s in range(n_shuf):
            rng = np.random.default_rng(COST_SEED + s * 7919 + top_n)
            sel = make_shuffle_selector(feats_by_date, rng, real_counts)
            pr, tr = run_backtest(panel, feats_by_date, entry_book, rebal_dates,
                                  top_n, sel, cost_mult=1.0)
            mm = compute_metrics(pr, tr)
            cagrs.append(mm.get("cagr_pct", float("nan")))
            finals.append(mm.get("final_equity_rupees", float("nan")))
            if (s + 1) % 10 == 0:
                print(f"    N{top_n} shuffle {s+1}/{n_shuf} ...")
        cagrs = np.array(cagrs, dtype="float64")
        pct = float((cagrs < real_cagr).mean() * 100.0)
        shuffle_results[f"N{top_n}"] = {
            "n_shuffles": n_shuf,
            "real_cagr_pct": real_cagr,
            "real_final_equity_rupees": real_final,
            "shuffle_cagr_mean_pct": round(float(np.nanmean(cagrs)), 3),
            "shuffle_cagr_median_pct": round(float(np.nanmedian(cagrs)), 3),
            "shuffle_cagr_p95_pct": round(float(np.nanpercentile(cagrs, 95)), 3),
            "shuffle_cagr_max_pct": round(float(np.nanmax(cagrs)), 3),
            "real_percentile_vs_shuffles": round(pct, 2),
            "beats_shuffle_mean_by_pct_per_yr": round(real_cagr - float(np.nanmean(cagrs)), 3),
        }
        print(f"    N{top_n}: real CAGR {real_cagr}% vs shuffle mean "
              f"{shuffle_results[f'N{top_n}']['shuffle_cagr_mean_pct']}% "
              f"-> percentile {pct:.1f}")

    with open(os.path.join(OUTDIR, "shuffle_percentile.json"), "w") as f:
        json.dump(shuffle_results, f, indent=2, default=str)
    print("    [checkpoint] shuffle_percentile.json written")

    # ---- config.json (params + data snapshot) ----
    cfg = {
        "run_id": "20260704_bt11",
        "strategy": "T2-SIG11 monthly-rebalance momentum portfolio",
        "shipped": "v1 REBALANCE-ONLY exit (no trailing stop) -- see VERDICT.md",
        "params": {
            "start": str(START.date()), "end": str(END.date()),
            "notional_rupees": NOTIONAL, "top_ns": TOP_NS, "pos_cap": POS_CAP,
            "entry": "next-day-open (L5-clean)", "exit": "next rebalance (rebalance-only)",
            "slippage_smallcap_bps_oneway": SLIPPAGE_SMALLCAP_BPS,
            "cost_stack": "COST_STANDARDS equity-delivery (brokerage Rs20/order, STT 0.1% both sides, "
                          "exch 0.00297%, GST 18%, SEBI Rs10/cr, stamp 0.015% buy) + slippage; 2x stress column",
            "shuffles": n_shuf, "seed": COST_SEED,
        },
        "data_snapshot": {
            "panel_path": D11.PANEL_PATH,
            "panel_rows": int(len(panel)),
            "panel_symbols": int(panel["symbol"].nunique()),
            "panel_date_max": str(all_dates.max().date()),
            "data_max_date_guard": str(D11.DATA_MAX_DATE.date()),
            "pit_xlsx": D11.PIT_XLSX,
            "n_rebalances": len(rebal_dates),
        },
        "frozen_constants": {
            "MA": [S11.MA_SHORT, S11.MA_MID, S11.MA_LONG],
            "RS_PCT_GATE": S11.RS_PCT_GATE, "RS_BLEND_W12": S11.RS_BLEND_W12,
            "PRICE_FLOOR": D11.PRICE_FLOOR,
        },
    }
    with open(os.path.join(OUTDIR, "config.json"), "w") as f:
        json.dump(cfg, f, indent=2, default=str)

    print(f"[7/7] DONE in {time.time()-t0:.0f}s. Outputs in {OUTDIR}")
    return metrics, shuffle_results


if __name__ == "__main__":
    main()
