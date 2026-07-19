"""
AMF_PINE_BT_20260716 — NIFTY500 PIT universe backtest of "Adaptive Momentum Fusion"
(long-only), per SPEC.md. DESK-100. Sonnet tier (D-036).

Execution mechanics (no-lookahead):
  - confirm bar T (bull/bear/zero cross using close[T]); ENTER/EXIT at close[T+1].
  - "state[T]" = confirmed decision (1=want-long) as of close T, to be EXECUTED at T+1.
  - holding_flag[t] = state[t-2] (shares bought at T+1 close earn their first daily
    return on T+2; the transaction day itself, T+1, earns nothing).
  - trades table built from state 0->1 / 1->0 transitions -> transaction index = t+1.
  - cost (0.67% RT, also 1.07%, also 2x) booked ENTIRELY on the EXIT bar (never spread
    across holding days -- firm lesson 2026-07, Sharpe-7-10 artifact).

PIT universe: entries require current-bar eligibility; a forced-exit event is injected
the instant a name drops out of the NIFTY500 PIT snapshot (no phantom holding of
excluded names). Positions/trades are only generated for dates >= 2015-01-01 (pre-2015
history is used ONLY to let the recursive engine converge -- entry/exit triggers are
masked to zero before 2015-01-01, so the first realized trade requires a genuine
in-window crossover, never a carried-over pre-window state).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
import guards as G  # noqa: E402
import lookahead_audit as LA  # noqa: E402
from amf_engine import compute_amf  # noqa: E402

PANEL_PATH = ROOT / "datasets" / "derived" / "pit_union_panel_v1" / "close_panel_price.parquet"
UNIV_PATH = ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx"
BENCH_PATH = ROOT / "datasets" / "index_daily" / "nse_official_all_indices.parquet"

BT_START = pd.Timestamp("2015-01-01")
BT_END = pd.Timestamp("2026-01-22")

COST_RT = 0.0067
COST_RT_HI = 0.0107
COST_RT_2X = COST_RT * 2

FAST_LEN, SLOW_LEN, SIGNAL_LEN, PHASE = 8, 21, 7, 0.7
ENGINES = ["Efficiency", "Momentum"]
MODES = ["MACD", "PPO"]
VARIANTS = ["V1", "V2", "V3"]

RNG = np.random.default_rng(42)
PLACEBO_K = 250


# ---------------------------------------------------------------- data loading
def load_universe():
    uni = pd.read_excel(UNIV_PATH, sheet_name="Sheet1")
    uni["snap_date"] = pd.to_datetime(uni["Month-Year"], format="%b%Y")
    snap_dates = np.sort(uni["snap_date"].unique())
    members = {d: set(uni.loc[uni["snap_date"] == d, "Ticker"]) for d in snap_dates}
    return snap_dates, members


def eligibility_mask(dates: np.ndarray, symbol: str, snap_dates: np.ndarray, members: dict) -> np.ndarray:
    idx = np.searchsorted(snap_dates, dates, side="right") - 1
    out = np.zeros(len(dates), dtype=bool)
    valid = idx >= 0
    snaps_for_row = np.where(valid, idx, 0)
    for si in np.unique(snaps_for_row[valid]):
        sd = snap_dates[si]
        rows = valid & (snaps_for_row == si)
        out[rows] = symbol in members[sd]
    return out


def load_benchmark():
    df = pd.read_parquet(BENCH_PATH)
    b = df[df["index_name"] == "Nifty 500"].copy()
    b["date"] = pd.to_datetime(b["date"])
    b = b.sort_values("date").drop_duplicates("date")
    b = b[(b["date"] >= BT_START) & (b["date"] <= BT_END)].reset_index(drop=True)
    return b[["date", "close"]]


def load_panel():
    df = pd.read_parquet(PANEL_PATH, columns=["date", "symbol", "close"])
    df["date"] = pd.to_datetime(df["date"])
    return df


# ---------------------------------------------------------------- signal construction per (engine,mode,variant)
def variant_events(r: dict, osc: np.ndarray, variant: str):
    """Return (entry_cond, exit_cond) raw boolean arrays (pre-eligibility, pre-window mask)."""
    if variant == "V1":
        return r["bull_cross"].copy(), r["bear_cross"].copy()
    if variant == "V2":
        entry = r["bull_cross"] & (osc > 0)
        exit_ = r["bear_cross"] | (osc < 0)
        return entry, exit_
    if variant == "V3":
        return r["zero_bull"].copy(), r["zero_bear"].copy()
    raise ValueError(variant)


def build_state(entry_cond: np.ndarray, exit_cond: np.ndarray, eligible: np.ndarray,
                 in_window: np.ndarray) -> np.ndarray:
    n = len(entry_cond)
    eligible_prev = np.roll(eligible, 1)
    eligible_prev[0] = eligible[0]
    forced_exit = eligible_prev & (~eligible)
    entry_final = entry_cond & eligible & in_window
    exit_final = (exit_cond | forced_exit) & in_window

    raw = np.full(n, np.nan)
    raw[entry_final] = 1.0
    raw[exit_final & ~entry_final] = 0.0  # entry priority if both true same bar (shouldn't co-occur, safety)
    s = pd.Series(raw).ffill().fillna(0.0).values
    return s  # confirmed decision as of bar close t


def extract_trades(state: np.ndarray, close: np.ndarray, dates: np.ndarray, symbol: str):
    """diff-based event extraction. Returns list of dict rows (trades) + open (censored) trade if any."""
    n = len(state)
    d = np.diff(state, prepend=state[0] if n else 0.0)
    entry_idx = np.where(d == 1.0)[0]  # state[t]=1 confirmed at bar t -> executes at t+1
    exit_idx = np.where(d == -1.0)[0]
    entry_tx = entry_idx + 1
    exit_tx = exit_idx + 1
    entry_tx = entry_tx[entry_tx < n]
    exit_tx = exit_tx[exit_tx < n]

    trades = []
    ei = 0
    xi = 0
    open_entry = None
    # walk chronologically pairing each entry with the next exit after it
    events = sorted([(t, "E") for t in entry_tx] + [(t, "X") for t in exit_tx])
    cur_entry = None
    for t, kind in events:
        if kind == "E":
            if cur_entry is None:
                cur_entry = t
        else:  # X
            if cur_entry is not None:
                trades.append((cur_entry, t))
                cur_entry = None
    is_open = cur_entry is not None
    open_trade = (cur_entry, n - 1) if is_open else None
    return trades, open_trade


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    out_dir = HERE
    print("[load] panel/universe/benchmark ...")
    panel = load_panel()
    snap_dates, members = load_universe()
    bench = load_benchmark()
    all_tickers = set().union(*members.values())
    panel_syms = set(panel["symbol"].unique())
    overlap = sorted(all_tickers & panel_syms)
    missing = sorted(all_tickers - panel_syms)
    print(f"[data] panel rows={len(panel)} symbols={len(panel_syms)} "
          f"universe tickers={len(all_tickers)} overlap={len(overlap)} missing={len(missing)}")
    with open(out_dir / "missing_tickers.txt", "w") as f:
        f.write("\n".join(missing))

    panel = panel[panel["symbol"].isin(overlap)].sort_values(["symbol", "date"])
    by_sym = {sym: g.reset_index(drop=True) for sym, g in panel.groupby("symbol", sort=False)}

    cells = [(e, m, v) for e in ENGINES for m in MODES for v in VARIANTS]
    print(f"[grid] {len(cells)} cells: {cells}")

    # daily portfolio return accumulators: dict[(e,m,v)] -> dict[date]-> list of (net_ret_that_day)
    bt_dates = pd.bdate_range(BT_START, BT_END)  # trading-day proxy; will restrict to panel's actual dates later
    all_trades = {c: [] for c in cells}
    # per-cell per-date lists of daily returns (gross, cost-normal, cost-hi) for equal-weight NAV
    daily_gross = {c: {} for c in cells}
    daily_net = {c: {} for c in cells}
    daily_net_hi = {c: {} for c in cells}
    daily_net_2x = {c: {} for c in cells}
    n_eligible_by_date = {}  # date -> count of eligible names that day (for exposure calc), computed once

    n_sym_done = 0
    for sym, g in by_sym.items():
        dates = g["date"].values
        close = g["close"].values.astype(float)
        n = len(close)
        if n < 60:
            continue
        eligible = eligibility_mask(dates, sym, snap_dates, members)
        in_window = (dates >= np.datetime64(BT_START)) & (dates <= np.datetime64(BT_END))
        if not in_window.any():
            continue

        # accumulate eligible-name counts per date (once per symbol, independent of cell)
        elig_dates = dates[eligible & in_window]
        for dd in elig_dates:
            n_eligible_by_date[dd] = n_eligible_by_date.get(dd, 0) + 1

        day_ret = np.empty(n)
        day_ret[:] = np.nan
        day_ret[1:] = close[1:] / close[:-1] - 1.0

        for engine in ENGINES:
            for mode in MODES:
                r = compute_amf(close, fast_len=FAST_LEN, slow_len=SLOW_LEN, signal_len=SIGNAL_LEN,
                                 phase=PHASE, engine=engine, mode=mode)
                osc = r["osc"]
                for variant in VARIANTS:
                    entry_cond, exit_cond = variant_events(r, osc, variant)
                    state = build_state(entry_cond, exit_cond, eligible, in_window)
                    trades, open_trade = extract_trades(state, close, dates, sym)
                    cell = (engine, mode, variant)

                    for (ei, xi) in trades:
                        entry_date = dates[ei]
                        exit_date = dates[xi]
                        entry_price = close[ei]
                        exit_price = close[xi]
                        gross_ret = exit_price / entry_price - 1.0
                        hold_d = xi - ei
                        all_trades[cell].append((sym, str(entry_date)[:10], str(exit_date)[:10],
                                                   entry_price, exit_price, hold_d, gross_ret, False))
                        # portfolio daily contributions: days (ei, xi] i.e. index ei+1..xi
                        for t in range(ei + 1, xi + 1):
                            dd = dates[t]
                            gr = day_ret[t]
                            if not np.isfinite(gr):
                                continue
                            daily_gross[cell].setdefault(dd, []).append(gr)
                            net = gr - (COST_RT if t == xi else 0.0)
                            daily_net[cell].setdefault(dd, []).append(net)
                            net_hi = gr - (COST_RT_HI if t == xi else 0.0)
                            daily_net_hi[cell].setdefault(dd, []).append(net_hi)
                            net_2x = gr - (COST_RT_2X if t == xi else 0.0)
                            daily_net_2x[cell].setdefault(dd, []).append(net_2x)

                    if open_trade is not None:
                        ei, xi = open_trade
                        entry_date = dates[ei]
                        exit_date = dates[xi]  # last available bar, censored mark
                        entry_price = close[ei]
                        exit_price = close[xi]
                        gross_ret = exit_price / entry_price - 1.0
                        hold_d = xi - ei
                        all_trades[cell].append((sym, str(entry_date)[:10], str(exit_date)[:10],
                                                   entry_price, exit_price, hold_d, gross_ret, True))
                        for t in range(ei + 1, xi + 1):
                            dd = dates[t]
                            gr = day_ret[t]
                            if not np.isfinite(gr):
                                continue
                            daily_gross[cell].setdefault(dd, []).append(gr)
                            # censored (still open): no exit cost booked yet, only entry-side already sunk
                            # (we do not re-charge entry here; entry cost is charged at trade-open time in
                            # the per-trade ledger's net_pct via mean_net_pct only for closed trades)
                            daily_net[cell].setdefault(dd, []).append(gr)
                            daily_net_hi[cell].setdefault(dd, []).append(gr)
                            daily_net_2x[cell].setdefault(dd, []).append(gr)

        n_sym_done += 1
        if n_sym_done % 100 == 0:
            print(f"[progress] {n_sym_done}/{len(by_sym)} symbols, {time.time()-t0:.1f}s elapsed")

    print(f"[compute] done all symbols in {time.time()-t0:.1f}s")

    # ---------------- build per-cell results ----------------
    results_rows = []
    for cell in cells:
        engine, mode, variant = cell
        trades = all_trades[cell]
        tdf = pd.DataFrame(trades, columns=["symbol", "entry_date", "exit_date", "entry_price",
                                             "exit_price", "hold_d", "gross_ret", "is_open"])
        ledger_path = out_dir / f"ledger_{engine}_{mode}_{variant}.csv"
        tdf.to_csv(ledger_path, index=False)

        closed = tdf[~tdf["is_open"]].copy()
        closed["net_ret"] = closed["gross_ret"] - COST_RT
        n_trades = len(closed)
        if n_trades > 0:
            win_pct = (closed["net_ret"] > 0).mean() * 100
            mean_net_pct = closed["net_ret"].mean() * 100
            std = closed["net_ret"].std(ddof=1) if n_trades > 1 else 0.0
            t_stat = (closed["net_ret"].mean() / (std / np.sqrt(n_trades))) if std > 0 else np.nan
            avg_hold_d = closed["hold_d"].mean()
        else:
            win_pct = mean_net_pct = t_stat = avg_hold_d = np.nan

        # placebo: same holding-length random entry, drawn from same symbol universe/date range
        placebo_rets = []
        if n_trades > 0:
            hold_choices = closed["hold_d"].values
            sym_choices = closed["symbol"].values
            n_draw = max(PLACEBO_K, n_trades)
            for _ in range(n_draw):
                k = RNG.integers(0, n_trades)
                sym_p = sym_choices[k]
                hd = int(hold_choices[k])
                g = by_sym.get(sym_p)
                if g is None or hd <= 0 or len(g) <= hd + 2:
                    continue
                dts = g["date"].values
                mask_w = (dts >= np.datetime64(BT_START)) & (dts <= np.datetime64(BT_END))
                idxs = np.where(mask_w)[0]
                idxs = idxs[idxs + hd < len(g)]
                if len(idxs) == 0:
                    continue
                start = RNG.choice(idxs)
                cl = g["close"].values
                p_gross = cl[start + hd] / cl[start] - 1.0
                placebo_rets.append(p_gross - COST_RT)
            placebo_mean = float(np.mean(placebo_rets)) * 100 if placebo_rets else np.nan
        else:
            placebo_mean = np.nan
        beats_placebo = bool(mean_net_pct > placebo_mean) if (n_trades > 0 and np.isfinite(placebo_mean)) else False

        # ---------------- portfolio NAV (equal-weight among currently-long names) ----------------
        dg = daily_gross[cell]
        dn = daily_net[cell]
        dnhi = daily_net_hi[cell]
        dn2x = daily_net_2x[cell]
        all_dates_cell = sorted(set(dg.keys()) | set(n_eligible_by_date.keys()))
        nav_dates = []
        port_ret = []
        port_ret_hi = []
        port_ret_2x = []
        exposure_frac = []
        turnover_events = []
        prev_names_count = 0
        for dd in sorted(dg.keys()):
            rets = dn.get(dd, [])
            rets_hi = dnhi.get(dd, [])
            rets_2x = dn2x.get(dd, [])
            if not rets:
                continue
            nav_dates.append(dd)
            port_ret.append(np.mean(rets))
            port_ret_hi.append(np.mean(rets_hi))
            port_ret_2x.append(np.mean(rets_2x))
            n_names = len(rets)
            n_elig = n_eligible_by_date.get(dd, np.nan)
            exposure_frac.append(n_names / n_elig if (n_elig and n_elig > 0) else np.nan)

        if len(port_ret) > 5:
            pr = pd.Series(port_ret, index=pd.to_datetime(nav_dates)).sort_index()
            pr_hi = pd.Series(port_ret_hi, index=pd.to_datetime(nav_dates)).sort_index()
            pr_2x = pd.Series(port_ret_2x, index=pd.to_datetime(nav_dates)).sort_index()
            eq = (1 + pr).cumprod()
            yrs = (pr.index[-1] - pr.index[0]).days / 365.25
            cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else np.nan
            sharpe = pr.mean() / (pr.std() + 1e-12) * np.sqrt(252)
            dd_series = eq / eq.cummax() - 1
            maxdd = dd_series.min()
            eq_2x = (1 + pr_2x).cumprod()
            cagr_2x = eq_2x.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else np.nan
            exposure_pct = float(np.nanmean(exposure_frac)) * 100 if exposure_frac else np.nan

            # turnover: annualized one-way, from count of trade entries/exits vs avg number of names held
            avg_n_held = np.mean([len(dn.get(dd, [])) for dd in nav_dates]) if nav_dates else np.nan
            n_entries = n_trades + int(closed.shape[0] == n_trades) * 0  # n_trades already = entries realized
            n_years_bt = yrs if yrs > 0 else np.nan
            turnover = (n_trades / n_years_bt / avg_n_held) if (avg_n_held and avg_n_held > 0 and n_years_bt) else np.nan
        else:
            cagr = sharpe = maxdd = cagr_2x = exposure_pct = turnover = np.nan

        # benchmark CAGR over same overlap window
        bench_w = bench[(bench["date"] >= (pr.index[0] if len(port_ret) > 5 else BT_START)) &
                         (bench["date"] <= (pr.index[-1] if len(port_ret) > 5 else BT_END))]
        if len(bench_w) > 5:
            byrs = (bench_w["date"].iloc[-1] - bench_w["date"].iloc[0]).days / 365.25
            bench_cagr = (bench_w["close"].iloc[-1] / bench_w["close"].iloc[0]) ** (1 / byrs) - 1 if byrs > 0 else np.nan
        else:
            bench_cagr = np.nan
        vs_benchmark_cagr = (cagr - bench_cagr) if (np.isfinite(cagr) if isinstance(cagr, float) else False) and np.isfinite(bench_cagr) else np.nan

        results_rows.append(dict(
            engine=engine, mode=mode, variant=variant, n_trades=n_trades,
            win_pct=round(win_pct, 2) if np.isfinite(win_pct) else np.nan,
            mean_net_pct=round(mean_net_pct, 4) if np.isfinite(mean_net_pct) else np.nan,
            t_stat=round(t_stat, 3) if np.isfinite(t_stat) else np.nan,
            avg_hold_d=round(avg_hold_d, 1) if np.isfinite(avg_hold_d) else np.nan,
            exposure_pct=round(exposure_pct, 2) if np.isfinite(exposure_pct) else np.nan,
            cagr=round(cagr * 100, 2) if isinstance(cagr, float) and np.isfinite(cagr) else np.nan,
            sharpe=round(sharpe, 3) if isinstance(sharpe, float) and np.isfinite(sharpe) else np.nan,
            maxdd=round(maxdd * 100, 2) if isinstance(maxdd, float) and np.isfinite(maxdd) else np.nan,
            turnover=round(turnover, 2) if isinstance(turnover, float) and np.isfinite(turnover) else np.nan,
            placebo_mean=round(placebo_mean, 4) if np.isfinite(placebo_mean) else np.nan,
            beats_placebo=beats_placebo,
            cagr_2x=round(cagr_2x * 100, 2) if isinstance(cagr_2x, float) and np.isfinite(cagr_2x) else np.nan,
            vs_benchmark_cagr=round(vs_benchmark_cagr * 100, 2) if isinstance(vs_benchmark_cagr, float) and np.isfinite(vs_benchmark_cagr) else np.nan,
        ))
        print(f"[cell] {engine}/{mode}/{variant}: n_trades={n_trades} cagr={results_rows[-1]['cagr']} "
              f"sharpe={results_rows[-1]['sharpe']} vs_bench={results_rows[-1]['vs_benchmark_cagr']}")

        # save NAV series for default cell for later inspection
        if len(port_ret) > 5:
            pr.to_frame("ret").to_csv(out_dir / f"nav_{engine}_{mode}_{variant}.csv")

    res_df = pd.DataFrame(results_rows)
    res_df.to_csv(out_dir / "results.csv", index=False)
    print(f"[done] results.csv written -- {time.time()-t0:.1f}s total")
    print(res_df.to_string())


if __name__ == "__main__":
    main()
