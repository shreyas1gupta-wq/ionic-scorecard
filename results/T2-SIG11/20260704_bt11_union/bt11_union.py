"""BT-11 UNION RE-RUN -- BT-11 engine re-pointed at the PIT UNION RETURN panel to quantify how
much of the strategy's early-era edge was SURVIVORSHIP (the HF panel was survivor-holed pre-2018).

This is results/T2-SIG11/20260704_bt11/bt11.py with a MINIMAL, LOUD set of changes:
  * PRICE SOURCE  = union RETURN panel (close-only) via data11_union  [was: HF panel via data11]
  * FILLS         = NEXT-DAY CLOSE (union has no open)                [was: next-day OPEN]
  * FEATURES      = reuse sig11._compute_symbol_features UNCHANGED (frozen constants). volume is
                    spliced from HF where available; union-only names -> breakout_vol_flag False
                    (a +5 composite NUDGE only, never a hard gate).
  * UNIVERSE      = data11_union.pit_universe (alias-mapped PIT, Mar/Sep snapshots).
  * START         = 2014-01 (union early-era coverage fixed). 2014-2015 are NEW (no HF comparison).
  * ADV/liquidity = original bt11 selection applied NO ADV gate (only ALL_PASS + price_floor);
                    we match that. We separately REPORT the volume-coverage of chosen names
                    (the "liquidity gate both ways" read the brief asked for).

Everything else -- monthly rebalance, top-N in {10,20}, 1x/2x COST_STANDARDS, exit-period P&L
booking, size-matched shuffle null (50 draws, 1x) -- is IDENTICAL to bt11.py.

NO LOOK-AHEAD (unchanged doctrine): right-closed rolling features (prefix equality), RS percentile
recomputed per month over that month's PIT snapshot only, fills strictly at t+1.

Run: PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python bt11_union.py [--shuffles N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
RUNDIR = os.path.join(ROOT, r"results\T2-SIG11\20260704_bt11_union")
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib"))
sys.path.insert(0, RUNDIR)                                             # our union data11
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\track2"))  # sig11 (features)
import guards as G  # noqa
import data11_union as D11   # UNION loader (close-only return panel)
import sig11 as S11          # frozen feature/criteria constants -- reused UNCHANGED

OUTDIR = RUNDIR

# ---- run parameters (FROZEN; identical to bt11.py except START) ----
START = pd.Timestamp("2014-01-01")         # EXTENDED from 2016-01 (union early-era coverage fixed)
OLD_START = pd.Timestamp("2016-01-01")     # for the like-for-like delta window
END = D11.DATA_MAX_DATE                     # 2026-01-22
NOTIONAL = 1_000_000.0                      # Rs 10 lakh Track-2 book
POS_CAP = 0.10
TOP_NS = [10, 20]
SLIPPAGE_SMALLCAP_BPS = 35.0
COST_SEED = 20260704
DEFAULT_SHUFFLES = 50                        # brief: 50 draws at 1x (matches old run)

# ---- COST-11 (IDENTICAL to bt11.py) ----
BROKERAGE_PER_ORDER = 20.0
EXCH_TXN = 0.00297e-2
SEBI = 10.0 / 1e7
GST = 0.18
STT_DELIVERY = 0.1e-2
STAMP_BUY = 0.015e-2


def side_cost_frac(is_buy: bool, trade_value: float) -> float:
    if trade_value <= 0:
        return 0.0
    brokerage = BROKERAGE_PER_ORDER
    exch = EXCH_TXN * trade_value
    sebi = SEBI * trade_value
    gst = GST * (brokerage + exch + sebi)
    stt = STT_DELIVERY * trade_value
    stamp = STAMP_BUY * trade_value if is_buy else 0.0
    return (brokerage + exch + sebi + gst + stt + stamp) / trade_value


# ---------------------------------------------------------------------------
# Feature build (ONCE over full panel; right-closed rolling => PIT-safe by construction)
# reuse sig11._compute_symbol_features UNCHANGED (frozen). Union-only names have volume=NaN
# -> breakout_vol_flag=False (sig11 fillna(False)); this is the only union-schema effect and it
# can only make composite_score LOWER (never fabricates ALL_PASS -- breakout is not a criterion).
# ---------------------------------------------------------------------------
def build_full_features(panel: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for _, g in panel.sort_values(["symbol", "date"]).groupby("symbol", sort=False):
        parts.append(S11._compute_symbol_features(g))
    return pd.concat(parts, ignore_index=True)


def _criteria_noncross(snap: pd.DataFrame) -> pd.DataFrame:
    c1 = (snap["close"] > snap["ma150"]) & (snap["close"] > snap["ma200"])
    c2 = snap["ma150"] > snap["ma200"]
    c3 = snap["ma200"] > snap["ma200_ago"]
    c4 = (snap["ma50"] > snap["ma150"]) & (snap["ma150"] > snap["ma200"])
    c5 = snap["close"] > snap["ma50"]
    c6 = snap["close"] >= (1.0 + S11.PCT_ABOVE_52W_LOW) * snap["lo_252"]
    c7 = snap["close"] >= (1.0 - S11.PCT_WITHIN_52W_HIGH) * snap["hi_252"]
    return pd.DataFrame({
        "c1_close_above_150_200": c1, "c2_150_above_200": c2, "c3_200ma_rising": c3,
        "c4_50_above_150_above_200": c4, "c5_close_above_50": c5,
        "c6_above_52w_low": c6, "c7_within_52w_high": c7,
    }, index=snap.index)


def compute_month_signals(feats_by_date: dict, asof: pd.Timestamp) -> pd.DataFrame:
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
    snap["mom_blend"] = S11.RS_BLEND_W12 * snap["mom_12_1"] + (1 - S11.RS_BLEND_W12) * snap["mom_6_1"]
    valid = snap["mom_blend"].notna()
    snap["rs_pct"] = np.nan
    if valid.sum() > 1:
        snap.loc[valid, "rs_pct"] = snap.loc[valid, "mom_blend"].rank(pct=True) * 100.0
    elif valid.sum() == 1:
        snap.loc[valid, "rs_pct"] = 100.0
    snap["c8_rs_pct_ge70"] = (snap["rs_pct"] >= S11.RS_PCT_GATE).fillna(False).astype(bool)
    snap["ALL_PASS"] = snap[S11.CRITERION_COLS].all(axis=1)
    mb = snap["mom_blend"]
    mb_norm = (mb - mb.min()) / (mb.max() - mb.min() + 1e-12) * 100.0
    snap["composite_score"] = (
        snap["rs_pct"].fillna(0.0) + 0.25 * mb_norm.fillna(0.0)
        + 5.0 * snap["breakout_vol_flag"].astype(float))
    return snap.sort_values("symbol").reset_index(drop=True)


def _assert_engine_matches_features(panel, feats_by_date, sample_dates):
    """D-028 GUARD (union variant): the fast pre-built-feature path must reproduce a from-scratch
    sig11._compute_symbol_features build restricted to date<=asof, for the ALL_PASS set + rs_pct.
    We do NOT call S11.compute_signals here because it uses the HF data11.pit_universe internally;
    the union universe lives in data11_union. So we recompute the reference with the SAME frozen
    feature fn + the union universe -- proving the only thing that could differ (prefix equality of
    right-closed rolling features + the cross-sectional RS rank) is identical."""
    for d in sample_dates:
        if d not in feats_by_date:
            continue
        hist = panel[panel["date"] <= d]
        universe = D11.pit_universe(d)
        hist = hist[hist["symbol"].isin(universe)]
        parts = [S11._compute_symbol_features(g)
                 for _, g in hist.sort_values(["symbol", "date"]).groupby("symbol", sort=False)]
        ref_feats = pd.concat(parts, ignore_index=True)
        ref_feats["date"] = pd.to_datetime(ref_feats["date"])
        ref = ref_feats[ref_feats["date"] == d].copy()
        # criteria + rs on ref
        crit = _criteria_noncross(ref)
        for c in crit.columns:
            ref[c] = crit[c].fillna(False).astype(bool)
        ref["mom_blend"] = S11.RS_BLEND_W12 * ref["mom_12_1"] + (1 - S11.RS_BLEND_W12) * ref["mom_6_1"]
        valid = ref["mom_blend"].notna()
        ref["rs_pct"] = np.nan
        if valid.sum() > 1:
            ref.loc[valid, "rs_pct"] = ref.loc[valid, "mom_blend"].rank(pct=True) * 100.0
        ref["c8_rs_pct_ge70"] = (ref["rs_pct"] >= S11.RS_PCT_GATE).fillna(False).astype(bool)
        ref["ALL_PASS"] = ref[S11.CRITERION_COLS].all(axis=1)
        mine = compute_month_signals(feats_by_date, d)
        ref_pass = set(ref.loc[ref["ALL_PASS"], "symbol"])
        mine_pass = set(mine.loc[mine["ALL_PASS"], "symbol"])
        assert ref_pass == mine_pass, (
            f"ENGINE MISMATCH {d.date()}: ALL_PASS ref {len(ref_pass)} vs mine {len(mine_pass)}; "
            f"diff {sorted(ref_pass ^ mine_pass)[:5]}")
        m = ref[["symbol", "rs_pct"]].merge(mine[["symbol", "rs_pct"]], on="symbol", suffixes=("_r", "_m"))
        both = m.dropna()
        if len(both):
            assert (both["rs_pct_r"] - both["rs_pct_m"]).abs().max() < 1e-6, \
                f"ENGINE MISMATCH {d.date()}: rs_pct differs"
    print(f"[guard] fast engine == from-scratch features on {len(sample_dates)} sample dates (union)")


# ---------------------------------------------------------------------------
# Portfolio backtest -- FILLS AT NEXT-DAY CLOSE (union is close-only; deviation from bt11's open)
# ---------------------------------------------------------------------------
def month_end_trading_dates(all_dates, start, end) -> list:
    d = pd.Series(all_dates)
    d = d[(d >= start) & (d <= end)]
    grp = d.groupby([d.dt.year, d.dt.month]).max()
    return sorted(grp.tolist())


def next_close_map(panel: pd.DataFrame) -> dict:
    """Per symbol: (dates[], close[], has_volume[]). Fills use CLOSE (deviation)."""
    m = {}
    for sym, g in panel.sort_values("date").groupby("symbol", sort=False):
        m[sym] = (g["date"].to_numpy(),
                  g["close"].to_numpy(dtype="float64"),
                  g["has_volume"].to_numpy(dtype=bool))
    return m


def _next_close(entry_book: dict, sym: str, asof: pd.Timestamp):
    """First (date, close, has_volume) strictly AFTER asof (next-day-CLOSE fill), else (None,...)."""
    if sym not in entry_book:
        return None, None, None
    dates, closes, hasvol = entry_book[sym]
    idx = np.searchsorted(dates, np.datetime64(asof), side="right")
    if idx >= len(dates):
        return None, None, None
    return pd.Timestamp(dates[idx]), float(closes[idx]), bool(hasvol[idx])


def run_backtest(panel, feats_by_date, entry_book, rebal_dates, top_n,
                 selector, cost_mult=1.0, notional=NOTIONAL):
    """Monthly-rebalance, equal-weight (capped 10%), NEXT-DAY-CLOSE entry, rebalance-only exit.
    P&L booked in the EXIT period (denominator rule). Identical to bt11.run_backtest EXCEPT fills
    use CLOSE (next_close_map / _next_close) rather than open. Also tracks vol-coverage of fills."""
    equity = notional
    period_records = []
    trades = []
    prev_positions = {}

    for i, asof in enumerate(rebal_dates):
        chosen = selector(asof, top_n)
        entries = {}
        n_novol = 0
        for sym in chosen:
            edate, eclose, ehasvol = _next_close(entry_book, sym, asof)
            if edate is None or not np.isfinite(eclose) or eclose <= 0:
                continue
            entries[sym] = (edate, eclose)
            if not ehasvol:
                n_novol += 1
        n_filled = len(entries)

        # ---- exit previous book at THIS rebalance's next-day CLOSE ----
        period_pl = 0.0
        period_cost = 0.0
        if prev_positions:
            for sym, pos in prev_positions.items():
                xdate, xclose, _ = _next_close(entry_book, sym, asof)
                if xdate is None or not np.isfinite(xclose) or xclose <= 0:
                    _, closes, _ = entry_book.get(sym, (None, None, None))
                    xclose = pos["entry_px_gross"] if closes is None else float(closes[-1])
                    xdate = asof
                shares = pos["shares"]
                exit_value = shares * xclose
                slip = SLIPPAGE_SMALLCAP_BPS / 1e4 * cost_mult
                exit_fill_px = xclose * (1.0 - slip)
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
                    "entry_has_vol": pos["has_vol"],
                })
            equity += period_pl

        # ---- enter new book ----
        new_positions = {}
        capital_per_slot = min(equity / top_n, POS_CAP * equity)
        for sym, (edate, eclose) in entries.items():
            _, _, ehasvol = _next_close(entry_book, sym, asof)
            slip = SLIPPAGE_SMALLCAP_BPS / 1e4 * cost_mult
            buy_fill_px = eclose * (1.0 + slip)
            shares = capital_per_slot / buy_fill_px
            slip_cost = shares * (buy_fill_px - eclose)
            buy_charges = side_cost_frac(True, shares * buy_fill_px) * cost_mult * (shares * buy_fill_px)
            cost_basis = shares * buy_fill_px + buy_charges
            new_positions[sym] = {
                "entry_date": edate, "entry_px_gross": eclose, "entry_px_net": buy_fill_px,
                "shares": shares, "cost_basis": cost_basis,
                "buy_cost": slip_cost + buy_charges, "has_vol": bool(ehasvol),
            }
        prev_positions = new_positions

        period_records.append({
            "rebal_date": asof, "n_chosen": len(chosen), "n_filled": n_filled,
            "n_filled_novol": n_novol,
            "equity_after_exit": equity, "period_realized_pl": period_pl,
            "period_cost": period_cost, "cash_slots": top_n - n_filled,
        })

    # close final open book at last data date
    if prev_positions:
        final_pl = 0.0
        for sym, pos in prev_positions.items():
            _, closes, _ = entry_book.get(sym, (None, None, None))
            xclose = float(closes[-1]) if closes is not None and len(closes) else pos["entry_px_gross"]
            xdate = END
            shares = pos["shares"]
            slip = SLIPPAGE_SMALLCAP_BPS / 1e4 * cost_mult
            exit_fill_px = xclose * (1.0 - slip)
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
                "hold_days": (xdate - pos["entry_date"]).days, "entry_has_vol": pos["has_vol"],
            })
        equity += final_pl
        period_records.append({
            "rebal_date": END, "n_chosen": 0, "n_filled": 0, "n_filled_novol": 0,
            "equity_after_exit": equity, "period_realized_pl": final_pl,
            "period_cost": 0.0, "cash_slots": top_n,
        })
    return pd.DataFrame(period_records), pd.DataFrame(trades)


# ---------------------------------------------------------------------------
# Metrics -- identical to bt11.compute_metrics + a from-start-year window helper for the delta
# ---------------------------------------------------------------------------
def compute_metrics(period_df, trades_df, notional=NOTIONAL, label="", cagr_from=None):
    if period_df.empty:
        return {}
    pe = period_df.copy()
    pe["rebal_date"] = pd.to_datetime(pe["rebal_date"])
    # optional CAGR window (for like-for-like 2016-start comparison against the old run):
    if cagr_from is not None:
        sub = pe[pe["rebal_date"] >= pd.Timestamp(cagr_from)]
        if len(sub) >= 2:
            base_eq_row = pe[pe["rebal_date"] < pd.Timestamp(cagr_from)]
            base_eq = base_eq_row["equity_after_exit"].iloc[-1] if len(base_eq_row) else notional
            eq_w = sub["equity_after_exit"].to_numpy(dtype="float64")
            yrs_w = max((sub["rebal_date"].iloc[-1] - sub["rebal_date"].iloc[0]).days / 365.25, 1e-9)
            cagr_win = (eq_w[-1] / base_eq) ** (1.0 / yrs_w) - 1.0
        else:
            cagr_win = float("nan")
    eq = pe["equity_after_exit"].to_numpy(dtype="float64")
    dates = pe["rebal_date"]
    eq_full = np.concatenate([[notional], eq])
    yrs = max((dates.iloc[-1] - dates.iloc[0]).days / 365.25, 1e-9)
    final_eq = eq[-1]
    cagr = (final_eq / notional) ** (1.0 / yrs) - 1.0
    monthly_ret = pd.Series(eq_full).pct_change().dropna()
    sharpe = (monthly_ret.mean() / (monthly_ret.std(ddof=1) + 1e-12) * np.sqrt(12)
              if len(monthly_ret) > 2 else float("nan"))
    running_max = np.maximum.accumulate(eq_full)
    max_dd = float((eq_full / running_max - 1.0).min())
    total_pl = final_eq - notional
    total_cost = float(pe["period_cost"].sum())

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
                "pct_entries_no_vol": round(float((~g["entry_has_vol"]).mean()) * 100, 2)
                if "entry_has_vol" in g else None,
            }
    py2 = {}
    pe["yr"] = dates.dt.year
    prev = notional
    for yr, g in pe.groupby("yr"):
        end_eq = g["equity_after_exit"].iloc[-1]
        py2[int(yr)] = round((end_eq / prev - 1.0) * 100, 3)
        prev = end_eq

    out = {
        "label": label, "years": round(yrs, 3), "n_rebalances": int(len(eq)),
        "start_notional_rupees": round(notional, 2),
        "final_equity_rupees": round(float(final_eq), 2),
        "total_pl_rupees": round(float(total_pl), 2),
        "total_cost_rupees": round(total_cost, 2),
        "cagr_pct": round(cagr * 100, 3),
        "max_drawdown_pct": round(max_dd * 100, 3),
        "monthly_sharpe": round(float(sharpe), 3),
        "n_trades": int(len(trades_df)),
        "avg_cash_slots": round(float(pe["cash_slots"].mean()), 2),
        "pct_fills_no_vol_overall": round(float(pe["n_filled_novol"].sum()) /
                                          max(float(pe["n_filled"].sum()), 1) * 100, 2),
        "per_year_trade_pl": per_year,
        "per_year_book_return_pct": py2,
    }
    if cagr_from is not None:
        out[f"cagr_pct_from_{pd.Timestamp(cagr_from).year}"] = round(cagr_win * 100, 3)
    return out


def regime_slices(trades_df, notional=NOTIONAL):
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
            out[name] = {"n_trades": 0, "rupee_pl": 0.0, "pct_of_notional": 0.0}
            continue
        out[name] = {
            "n_trades": int(len(g)), "rupee_pl": round(float(g["pl"].sum()), 2),
            "pct_of_notional": round(float(g["pl"].sum()) / notional * 100, 3),
            "avg_trade_ret_pct": round(float(g["ret"].mean()) * 100, 3),
            "win_rate_pct": round(float((g["pl"] > 0).mean()) * 100, 2),
        }
    return out


# ---------------------------------------------------------------------------
# Selectors (identical logic to bt11)
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
    pools = {}
    for asof, snap in feats_by_date.items():
        universe = D11.pit_universe(asof)
        s = snap[snap["symbol"].isin(universe)]
        s = s[s["close"] >= D11.PRICE_FLOOR]
        pools[asof] = s["symbol"].to_numpy()
    return pools


def make_shuffle_selector(pools, rng, real_counts):
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
    print("[1/7] loading UNION panel (frozen copy) ...")
    panel = D11.load_panel()
    all_dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    print(f"    panel rows={len(panel):,} symbols={panel['symbol'].nunique():,} "
          f"dates {all_dates.min().date()}->{all_dates.max().date()} "
          f"has_vol={100*panel['has_volume'].mean():.1f}%")

    print("[2/7] building features once over full panel ...")
    feats = build_full_features(panel)
    feats["date"] = pd.to_datetime(feats["date"])
    feats_by_date = {d: g.reset_index(drop=True) for d, g in feats.groupby("date")}
    print(f"    feature rows={len(feats):,}")

    rebal_dates = month_end_trading_dates(all_dates, START, END)
    print(f"[3/7] rebalance month-ends: {len(rebal_dates)} "
          f"({rebal_dates[0].date()} -> {rebal_dates[-1].date()})  START={START.date()}")

    print("[4/7] D-028 engine-equivalence guard (union) ...")
    sample = [d for d in rebal_dates if d.year in (2015, 2018, 2020, 2023, 2025)][:4]
    _assert_engine_matches_features(panel, feats_by_date, sample)

    entry_book = next_close_map(panel)

    print("[5/7] base runs (real ALL_PASS selector, next-day-CLOSE fills) ...")
    real_selector = make_real_selector(feats_by_date)
    metrics = {}
    real_counts = {}
    trades_store = {}
    for top_n in TOP_NS:
        for mult, tag in [(1.0, "cost1x"), (2.0, "cost2x")]:
            pr, tr = run_backtest(panel, feats_by_date, entry_book, rebal_dates,
                                  top_n, real_selector, cost_mult=mult)
            key = f"N{top_n}_{tag}"
            metrics[key] = compute_metrics(pr, tr, label=key, cagr_from=OLD_START)
            metrics[key]["regime_slices"] = regime_slices(tr)
            trades_store[key] = tr
            if mult == 1.0:
                for _, row in pr.iterrows():
                    real_counts[(row["rebal_date"], top_n)] = int(row["n_filled"])
            print(f"    {key}: CAGR(full {START.year}+) {metrics[key]['cagr_pct']}%  "
                  f"CAGR(from 2016) {metrics[key].get('cagr_pct_from_2016')}%  "
                  f"MaxDD {metrics[key]['max_drawdown_pct']}%  Sharpe {metrics[key]['monthly_sharpe']}  "
                  f"finalRs {metrics[key]['final_equity_rupees']:,.0f}  trades {metrics[key]['n_trades']}  "
                  f"novolfills {metrics[key]['pct_fills_no_vol_overall']}%")

    with open(os.path.join(OUTDIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"    [checkpoint] metrics.json written ({time.time()-t0:.0f}s)")

    rows = []
    for key, m in metrics.items():
        for yr, v in m.get("per_year_trade_pl", {}).items():
            rows.append({"strategy": key, "year": yr, **v})
    pd.DataFrame(rows).to_csv(os.path.join(OUTDIR, "per_year_union.csv"), index=False)
    for key, tr in trades_store.items():
        tr.to_csv(os.path.join(OUTDIR, f"trades_{key}.csv"), index=False)

    n_shuf = args.shuffles
    print(f"[6/7] shuffle null: {n_shuf} shuffles per N (cost 1x, size-matched) ...")
    shuffle_pools = build_shuffle_pools(feats_by_date)
    shuffle_results = {}
    for top_n in TOP_NS:
        real_cagr = metrics[f"N{top_n}_cost1x"]["cagr_pct"]
        real_final = metrics[f"N{top_n}_cost1x"]["final_equity_rupees"]
        cagrs = []
        for s in range(n_shuf):
            rng = np.random.default_rng(COST_SEED + s * 7919 + top_n)
            sel = make_shuffle_selector(shuffle_pools, rng, real_counts)
            pr, tr = run_backtest(panel, feats_by_date, entry_book, rebal_dates,
                                  top_n, sel, cost_mult=1.0)
            mm = compute_metrics(pr, tr)
            cagrs.append(mm.get("cagr_pct", float("nan")))
            if (s + 1) % 10 == 0:
                print(f"    N{top_n} shuffle {s+1}/{n_shuf} ...")
        cagrs = np.array(cagrs, dtype="float64")
        pct = float((cagrs < real_cagr).mean() * 100.0)
        shuffle_results[f"N{top_n}"] = {
            "n_shuffles": n_shuf, "real_cagr_pct": real_cagr,
            "real_final_equity_rupees": real_final,
            "shuffle_cagr_mean_pct": round(float(np.nanmean(cagrs)), 3),
            "shuffle_cagr_median_pct": round(float(np.nanmedian(cagrs)), 3),
            "shuffle_cagr_p95_pct": round(float(np.nanpercentile(cagrs, 95)), 3),
            "shuffle_cagr_max_pct": round(float(np.nanmax(cagrs)), 3),
            "shuffle_cagr_min_pct": round(float(np.nanmin(cagrs)), 3),
            "real_percentile_vs_shuffles": round(pct, 2),
            "beats_shuffle_mean_by_pct_per_yr": round(real_cagr - float(np.nanmean(cagrs)), 3),
        }
        print(f"    N{top_n}: real CAGR {real_cagr}% vs shuffle mean "
              f"{shuffle_results[f'N{top_n}']['shuffle_cagr_mean_pct']}% -> pct {pct:.1f}")

    with open(os.path.join(OUTDIR, "shuffle_percentile.json"), "w") as f:
        json.dump(shuffle_results, f, indent=2, default=str)
    print("    [checkpoint] shuffle_percentile.json written")

    cfg = {
        "run_id": "20260704_bt11_union",
        "strategy": "T2-SIG11 monthly-rebalance momentum -- RE-RUN on PIT UNION RETURN panel",
        "purpose": "quantify survivorship bias in BT-11 early-era edge (HF panel was survivor-holed pre-2018)",
        "panel_version": D11.PANEL_VERSION,
        "panel_basis": "RETURN (dividend-adjusted / total-return); close-only",
        "deviations_from_bt11": {
            "price_source": "PIT union RETURN panel (was: HF panel)",
            "fills": "NEXT-DAY CLOSE (union has no open; was: next-day OPEN) -- stated loudly",
            "volume": "spliced from HF where available; union-only names breakout_vol_flag=False (nudge only)",
            "adv_liquidity_gate": "original bt11 selection had NO ADV gate (ALL_PASS+price_floor only); matched. "
                                  "vol-coverage of chosen names reported separately (liquidity both-ways).",
            "start": f"{START.date()} (extended from 2016-01; 2014-2015 NEW, no HF comparison)",
        },
        "params": {
            "start": str(START.date()), "old_comparison_start": str(OLD_START.date()),
            "end": str(END.date()), "notional_rupees": NOTIONAL, "top_ns": TOP_NS, "pos_cap": POS_CAP,
            "entry": "next-day-CLOSE (L5-clean, close-only panel)", "exit": "next rebalance (rebalance-only)",
            "slippage_smallcap_bps_oneway": SLIPPAGE_SMALLCAP_BPS,
            "cost_stack": "COST_STANDARDS equity-delivery + slippage; 2x stress column (identical to bt11)",
            "shuffles": n_shuf, "seed": COST_SEED,
        },
        "data_snapshot": {
            "panel_path": D11.PANEL_PATH,
            "panel_md5": "9f5b5d42159ff810e8d554bbab35499c",
            "panel_rows": int(len(panel)), "panel_symbols": int(panel["symbol"].nunique()),
            "panel_date_max": str(all_dates.max().date()),
            "has_volume_pct": round(100 * float(panel["has_volume"].mean()), 2),
            "pit_xlsx": D11.PIT_XLSX, "n_rebalances": len(rebal_dates),
            "sources": {k: int(v) for k, v in panel["source"].value_counts().items()},
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
