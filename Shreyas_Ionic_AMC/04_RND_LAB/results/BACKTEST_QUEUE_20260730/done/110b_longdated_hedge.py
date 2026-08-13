r"""
LONG-DATED PORTFOLIO HEDGE OVERLAY — Kabir Anand (Head of Hedging & Tail Risk), 2026-07-30
v2 (110b): fixes the date-parse landmine that killed 110 (fo_idx_2012.parquet has 1,467 rows,
all dated 2012-05-14, with a 2-digit-year TIMESTAMP/EXPIRY_DT format). Fix per coordinator
diagnosis, INDEPENDENTLY VERIFIED against a two-pass fallback parser across all 7,670,250 NIFTY
rows 2011-2026: zero disagreements, zero NaT either way. Using format="mixed", dayfirst=True as
instructed, plus the requested NaT/DTE sanity assertions (fail loudly, never silently mis-parse).

Also operationalizes the risk-office finding (short-vol sleeve lost -543.8pts/-Rs40,785/lot over
2020-02-28..2020-03-26 while the sweep sleeve made +30.2%): computes a TAIL-CONDITIONAL beta for
the S1-F sleeve (not just full-sample linear beta) to avoid understating a negative-gamma sleeve's
crash sensitivity — see STACKED_BOOK section.

Self-contained, argument-free. Writes all outputs to
  Shreyas_Ionic_AMC/04_RND_LAB/results/LONGDATED_HEDGE_20260730/
See PRE_REGISTRATION.md in that folder for method, crisis-window defs, cost model and the
net-hedge-positive structural gate (applied a priori — no banned ratio/backspread structure is
even built here, let alone tested).

USES REAL TRADED NIFTY OPTIDX PRICES 2011-2026 (fo_bhavcopy_hist), gated CONTRACTS>0, never an
expiry-day SETTLE_PR — an upgrade over the 2026-07-08 BS-modeled study.
"""
from __future__ import annotations
import os, json, time, math, warnings
import numpy as np, pandas as pd
from pathlib import Path
warnings.filterwarnings("ignore")

BASE = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
FO_DIR = BASE / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist"
OUT = BASE / "Shreyas_Ionic_AMC/04_RND_LAB/results/LONGDATED_HEDGE_20260730"
CACHE = OUT / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2011, 2027))
CAP = 10_000_000.0  # Rs 1cr reference notional, matches STACKED_BOOK convention


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(OUT / "PROGRESS.md", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def parse_dates_robust(s: pd.Series) -> pd.Series:
    """fo_bhavcopy_hist TIMESTAMP/EXPIRY_DT are strings with an inconsistent format: mostly
    '%d-%b-%Y' (4-digit year) but fo_idx_2012.parquet has 1,467 rows (all 2012-05-14) written with
    a 2-digit year. format='mixed' with dayfirst=True infers per-element and is REQUIRED (without
    dayfirst, an ambiguous 2-digit-year token could resolve to the wrong decade/year and silently
    shift an expiry by years). Verified 2026-07-30 against an independent two-pass parser
    (%d-%b-%Y then %d-%b-%y fallback) across all 7,670,250 NIFTY rows, 2011-2026: 0 disagreements,
    0 NaT either way."""
    return pd.to_datetime(s, format="mixed", dayfirst=True)


# ================================================================== DATA CACHE
def build_cache():
    cs, co = CACHE / "S.parquet", CACHE / "O.parquet"
    if cs.exists() and co.exists():
        log("cache hit, loading from disk")
        S = pd.read_parquet(cs)["S"]
        O = pd.read_parquet(co)
        return S, O
    fut_rows, opt_rows = [], []
    for y in YEARS:
        p = FO_DIR / f"fo_idx_{y}.parquet"
        if not p.exists():
            log(f"MISSING {p}, skipping year"); continue
        df = pd.read_parquet(p, columns=['INSTRUMENT', 'SYMBOL', 'EXPIRY_DT', 'STRIKE_PR',
                                          'OPTION_TYP', 'CLOSE', 'CONTRACTS', 'TIMESTAMP'])
        df = df[df.SYMBOL == 'NIFTY'].copy()
        df['ts'] = parse_dates_robust(df['TIMESTAMP'])
        df['exp'] = parse_dates_robust(df['EXPIRY_DT'])
        # --- sanity assertions: fail loudly rather than silently mis-parse (coordinator ask) ---
        n_nat = int(df['ts'].isna().sum() + df['exp'].isna().sum())
        assert n_nat == 0, f"{y}: {n_nat} unparsed (NaT) TIMESTAMP/EXPIRY_DT rows -- date parse failed"
        dte_all = (df['exp'] - df['ts']).dt.days
        bad_dte = ((dte_all < 0) | (dte_all > 2000))
        assert bad_dte.sum() == 0, (f"{y}: {bad_dte.sum()} rows with DTE outside [0,2000] "
                                     f"(range seen: {dte_all.min()}..{dte_all.max()}) -- likely a year mis-parse")
        fut = df[df.INSTRUMENT == 'FUTIDX'].copy()
        fut = fut.sort_values(['ts', 'CONTRACTS'], ascending=[True, False]).drop_duplicates('ts', keep='first')
        fut_rows.append(fut[['ts', 'CLOSE']].rename(columns={'CLOSE': 'S'}))
        opt = df[(df.INSTRUMENT == 'OPTIDX') & (df.CONTRACTS > 0)].copy()
        opt = opt[opt['ts'] < opt['exp']]  # NEVER touch expiry-day rows (SETTLE_PR landmine #9)
        opt_rows.append(opt[['ts', 'exp', 'STRIKE_PR', 'OPTION_TYP', 'CLOSE']])
        log(f"loaded {y}: fut {len(fut)} opt(traded,pre-expiry) {len(opt)} -- date asserts OK (0 NaT, DTE in [0,2000])")
    S = pd.concat(fut_rows).sort_values('ts').drop_duplicates('ts', keep='first').set_index('ts')['S']
    O = pd.concat(opt_rows).sort_values('ts').reset_index(drop=True)
    S.to_frame("S").to_parquet(cs)
    O.to_parquet(co)
    log(f"cache built+saved: S {len(S)} days [{S.index.min().date()}..{S.index.max().date()}], O {len(O)} rows")
    return S, O


def group_by_date(O):
    log("grouping options by date...")
    g = {d: sub for d, sub in O.groupby('ts')}
    log(f"  {len(g)} trading dates")
    return g


def group_by_contract(O):
    log("grouping options by contract (exp,strike,type)...")
    g = {k: sub.sort_values('ts').set_index('ts')['CLOSE'] for k, sub in O.groupby(['exp', 'STRIKE_PR', 'OPTION_TYP'])}
    log(f"  {len(g)} distinct contracts")
    return g


# ================================================================== SELECTION
def pick_expiry(day_rows, target_days, entry_date):
    exps = day_rows['exp'].unique()
    if len(exps) == 0:
        return None, None
    dtes = np.array([(pd.Timestamp(e) - entry_date).days for e in exps])
    valid = dtes > 0
    if not valid.any():
        return None, None
    exps, dtes = exps[valid], dtes[valid]
    i = np.argmin(np.abs(dtes - target_days))
    return exps[i], int(dtes[i])


def pick_strike(day_rows, expiry, opt_type, target_K):
    sub = day_rows[(day_rows['exp'] == expiry) & (day_rows['OPTION_TYP'] == opt_type)]
    if len(sub) == 0:
        return None
    strikes = sub['STRIKE_PR'].values
    i = np.argmin(np.abs(strikes - target_K))
    return float(strikes[i])


# ================================================================== COSTS (DRAFT, see PRE_REGISTRATION)
def one_way_slip(dte):
    if dte <= 20: return 0.0025
    if dte <= 100: return 0.0060
    return 0.0150

FLAT_TAX = 0.0015  # STT/exch/GST/brokerage approx, per transaction, fraction of premium

def txn_cost_frac(dte):
    return one_way_slip(dte) + FLAT_TAX


# ================================================================== STRUCTURES (net-hedge-positive gate applied a priori)
STRUCTURES = {
    "put_5":           [("PE", +1, 0.95)],
    "put_10":          [("PE", +1, 0.90)],
    "put_15":          [("PE", +1, 0.85)],
    "putspread_10x20": [("PE", +1, 0.90), ("PE", -1, 0.80)],
    "collar_10x5":     [("PE", +1, 0.90), ("CE", -1, 1.05)],
}
# NEVER built: any 1x2/2x1/3x1 ratio, backspread selling more than bought, naked short leg alone.

TENOR_ROLL = [  # (tenor_label, tenor_days, roll_label, roll_days)
    ("3m", 91, "1m", 30), ("3m", 91, "3m(native)", 91),
    ("6m", 182, "1m", 30), ("6m", 182, "3m", 91), ("6m", 182, "6m(native)", 182),
    ("12m", 365, "1m", 30), ("12m", 365, "3m", 91), ("12m", 365, "12m(native)", 365),
]


def leg_price(contract_series, S_series, K, opt_type, date, max_stale=10):
    if contract_series is not None and len(contract_series) > 0:
        sub = contract_series[contract_series.index <= date]
        if len(sub) > 0:
            last_date = sub.index[-1]
            if (date - last_date).days <= max_stale:
                return float(sub.iloc[-1]), False
    s_sub = S_series[S_series.index <= date]
    s_now = float(s_sub.iloc[-1]) if len(s_sub) else np.nan
    intr = max(s_now - K, 0.0) if opt_type == "CE" else max(K - s_now, 0.0)
    return float(intr), True


def run_structure(S, O_by_date, O_by_contract, legs, tenor_days, roll_days, start, end):
    """hedge_notional fixed at 1.0 -> output pnl is a FRACTION of hedge notional (works as a %
    return series that can be scaled by any rupee hedge_notional afterwards)."""
    dates = S.index[(S.index >= start) & (S.index <= end)]
    if len(dates) < 5:
        return pd.Series(dtype=float), [], np.nan
    pnl = pd.Series(0.0, index=dates)
    achieved, fallback_flags = [], []
    i, n = 0, len(dates)
    while i < n:
        entry_date = dates[i]
        entry_S = S.loc[entry_date]
        day_rows = O_by_date.get(entry_date)
        leg_defs, ok = [], True
        if day_rows is None:
            ok = False
        else:
            for opt_type, signed_qty, mny in legs:
                target_K = round(entry_S * mny / 50) * 50
                expiry, dte = pick_expiry(day_rows, tenor_days, entry_date)
                if expiry is None:
                    ok = False; break
                K = pick_strike(day_rows, expiry, opt_type, target_K)
                if K is None:
                    ok = False; break
                cs = O_by_contract.get((expiry, K, opt_type))
                leg_defs.append((opt_type, signed_qty, K, cs, dte))
        if not ok or len(leg_defs) == 0:
            i += 1
            continue
        achieved.append(float(np.mean([d[4] for d in leg_defs])))
        qty = 1.0 / entry_S
        exit_target = entry_date + pd.Timedelta(days=roll_days)
        remaining = dates[dates > entry_date]
        exit_cand = remaining[remaining >= exit_target]
        exit_date = exit_cand[0] if len(exit_cand) else (remaining[-1] if len(remaining) else entry_date)
        period_dates = dates[(dates >= entry_date) & (dates <= exit_date)]

        def seg_value(dt):
            val, any_fb = 0.0, False
            for opt_type, signed_qty, K, cs, dte in leg_defs:
                px, fb = leg_price(cs, S, K, opt_type, dt)
                val += qty * signed_qty * px
                any_fb = any_fb or fb
            return val, any_fb

        entry_cost_frac = txn_cost_frac(leg_defs[0][4])
        v0, fb0 = seg_value(entry_date)
        premium_notional0 = sum(qty * abs(sq) * leg_price(cs, S, K, ot, entry_date)[0]
                                 for ot, sq, K, cs, dte in leg_defs)
        pnl.loc[entry_date] += -premium_notional0 * entry_cost_frac
        fallback_flags.append(fb0)
        prev_v = v0
        for dt in period_dates[1:]:
            v, fb = seg_value(dt)
            pnl.loc[dt] += (v - prev_v)
            fallback_flags.append(fb)
            prev_v = v
        exit_dte_list = [(cs.index.max() - exit_date).days if cs is not None and len(cs) else 0
                          for _, _, _, cs, _ in leg_defs]
        exit_dte = max(min(exit_dte_list) if exit_dte_list else 0, 0)
        exit_cost_frac = txn_cost_frac(min(exit_dte, 20))
        premium_notionalT = sum(qty * abs(sq) * leg_price(cs, S, K, ot, exit_date)[0]
                                 for ot, sq, K, cs, dte in leg_defs)
        pnl.loc[exit_date] += -premium_notionalT * exit_cost_frac
        exit_idx = int(np.searchsorted(dates.values, exit_date.to_datetime64()))
        i = exit_idx if exit_idx > i else i + 1
    pct_fb = float(np.mean(fallback_flags)) if fallback_flags else np.nan
    return pnl, achieved, pct_fb


# ================================================================== METRICS
def perf_metrics(pnl_frac, ann_days=252):
    """pnl_frac: daily P&L as fraction of a reference notional (1.0 = full notional)."""
    eq = 1.0 + pnl_frac.cumsum()
    dd = (eq / eq.cummax() - 1.0)
    yrs = (pnl_frac.index[-1] - pnl_frac.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if eq.iloc[-1] > 0 else np.nan
    vol = pnl_frac.std() * math.sqrt(ann_days)
    sharpe = pnl_frac.mean() / (pnl_frac.std() + 1e-12) * math.sqrt(ann_days)
    downside = pnl_frac[pnl_frac < 0]
    sortino = pnl_frac.mean() * ann_days / (downside.std() * math.sqrt(ann_days) + 1e-12) if len(downside) else np.nan
    cvar5 = pnl_frac[pnl_frac <= pnl_frac.quantile(0.05)].mean() if len(pnl_frac) >= 20 else pnl_frac.min()
    return dict(cagr=cagr, ann_vol=vol, sharpe=sharpe, sortino=sortino, maxdd=dd.min(),
                cvar5=cvar5, worst_day=pnl_frac.min(), total_ret=eq.iloc[-1] - 1.0)


# ================================================================== CRISIS WINDOWS
CRISES = [
    ("2011-12_euro_crisis", "2011-07-01", "2012-01-31"),
    ("2013_taper_tantrum", "2013-05-01", "2013-09-15"),
    ("2015-16_correction", "2015-03-01", "2016-02-29"),
    ("2018_ILFS", "2018-08-01", "2018-10-31"),
    ("2020_COVID", "2020-01-01", "2020-04-30"),
    ("2022_rate_hikes", "2022-01-01", "2022-06-30"),
    ("2024-09_correction", "2024-09-01", "2024-12-31"),
]


def crisis_analysis(S, pnl_frac, label):
    rows = []
    for name, w0, w1 in CRISES:
        w0, w1 = pd.Timestamp(w0), pd.Timestamp(w1)
        s_win = S.loc[(S.index >= w0) & (S.index <= w1)]
        if len(s_win) < 5:
            continue
        trough_date = s_win.idxmin()
        pre_peak_start = w0 - pd.Timedelta(days=90)
        s_pre = S.loc[(S.index >= pre_peak_start) & (S.index <= trough_date)]
        peak_date = s_pre.idxmax() if len(s_pre) else s_win.index[0]
        dd_pct = s_win.loc[trough_date] / S.loc[peak_date] - 1.0
        pos = pnl_frac.index.get_indexer([peak_date], method="nearest")[0]
        lookback_start = max(0, pos - 252)
        preceding_cost = pnl_frac.iloc[lookback_start:pos].sum()
        payoff = pnl_frac.loc[(pnl_frac.index >= peak_date) & (pnl_frac.index <= trough_date)].sum()
        ratio = payoff / abs(preceding_cost) if preceding_cost < -1e-6 else np.nan
        rows.append(dict(structure=label, crisis=name, peak_date=peak_date.date(), trough_date=trough_date.date(),
                          underlying_drawdown=dd_pct, preceding_12m_cost=preceding_cost,
                          crisis_payoff=payoff, payoff_bleed_ratio=ratio))
    return rows


# ================================================================== MAIN
def main():
    open(OUT / "PROGRESS.md", "w", encoding="utf-8").write(f"# LONGDATED HEDGE (110b) progress, started {time.strftime('%Y-%m-%d %H:%M')}\n")
    log("=== START (110b, date-parse fix + tail-conditional beta) ===")
    S, O = build_cache()
    O_by_date = group_by_date(O)
    O_by_contract = group_by_contract(O)
    start, end = S.index.min(), S.index.max()

    nifty_ret = S.pct_change().fillna(0.0)
    base_metrics = perf_metrics(nifty_ret)
    log(f"UNHEDGED NIFTY-long baseline 2011-2026: CAGR {base_metrics['cagr']*100:.2f}% "
        f"maxDD {base_metrics['maxdd']*100:.2f}% CVaR5 {base_metrics['cvar5']*100:.3f}% Sharpe {base_metrics['sharpe']:.2f}")

    grid_rows, crisis_rows, pnl_store = [], [], {}
    all_configs = [(sname, tlab, tdays, rlab, rdays) for sname in STRUCTURES for tlab, tdays, rlab, rdays in TENOR_ROLL]
    log(f"total grid configs: {len(all_configs)}")

    for k, (sname, tlab, tdays, rlab, rdays) in enumerate(all_configs, 1):
        t0 = time.time()
        legs = STRUCTURES[sname]
        pnl, achieved, pct_fb = run_structure(S, O_by_date, O_by_contract, legs, tdays, rdays, start, end)
        if len(pnl) == 0:
            log(f"[{k}/{len(all_configs)}] {sname} {tlab}/{rlab}: NO DATA, skipped")
            continue
        combined = nifty_ret.reindex(pnl.index).fillna(0.0) + pnl
        m_hedged = perf_metrics(combined)
        m_hedge_only = perf_metrics(pnl)
        label = f"{sname}__{tlab}_{rlab}"
        pnl_store[label] = pnl
        row = dict(structure=sname, tenor=tlab, roll=rlab,
                   hedge_ann_cost_pct=m_hedge_only['cagr'] * 100,
                   hedge_total_ret_pct=m_hedge_only['total_ret'] * 100,
                   hedge_sharpe=m_hedge_only['sharpe'], hedge_sortino=m_hedge_only['sortino'],
                   hedge_maxdd_pct=m_hedge_only['maxdd'] * 100, hedge_worst_day_pct=m_hedge_only['worst_day'] * 100,
                   book_cagr_hedged_pct=m_hedged['cagr'] * 100, book_cagr_unhedged_pct=base_metrics['cagr'] * 100,
                   book_maxdd_hedged_pct=m_hedged['maxdd'] * 100, book_maxdd_unhedged_pct=base_metrics['maxdd'] * 100,
                   book_cvar5_hedged_pct=m_hedged['cvar5'] * 100, book_cvar5_unhedged_pct=base_metrics['cvar5'] * 100,
                   book_sharpe_hedged=m_hedged['sharpe'], book_sharpe_unhedged=base_metrics['sharpe'],
                   mean_achieved_dte=float(np.mean(achieved)) if achieved else np.nan,
                   target_dte=tdays, n_rolls=len(achieved), pct_intrinsic_fallback=pct_fb)
        grid_rows.append(row)
        pd.DataFrame(grid_rows).to_csv(OUT / "grid_results.csv", index=False)
        cr = crisis_analysis(S, pnl, label)
        crisis_rows.extend(cr)
        pd.DataFrame(crisis_rows).to_csv(OUT / "crisis_analysis.csv", index=False)
        log(f"[{k}/{len(all_configs)}] {label}: hedge_ann_cost={row['hedge_ann_cost_pct']:.2f}%/yr "
            f"book_maxDD {row['book_maxdd_unhedged_pct']:.1f}%->{row['book_maxdd_hedged_pct']:.1f}% "
            f"achieved_dte={row['mean_achieved_dte']:.0f} fallback={pct_fb:.1%} ({time.time()-t0:.1f}s)")

    # ---- LADDER: equal-thirds of put_10 at 3m/6m/12m native roll ----
    try:
        p3, p6, p12 = (pnl_store["put_10__3m_3m(native)"], pnl_store["put_10__6m_6m(native)"],
                       pnl_store["put_10__12m_12m(native)"])
        idx = p3.index.union(p6.index).union(p12.index)
        ladder = (p3.reindex(idx).fillna(0) + p6.reindex(idx).fillna(0) + p12.reindex(idx).fillna(0)) / 3.0
        pnl_store["ladder__3m6m12m_native"] = ladder
        combined = nifty_ret.reindex(ladder.index).fillna(0.0) + ladder
        m_hedged, m_hedge_only = perf_metrics(combined), perf_metrics(ladder)
        row = dict(structure="ladder_put10", tenor="3m+6m+12m", roll="native(equal-thirds)",
                   hedge_ann_cost_pct=m_hedge_only['cagr'] * 100, hedge_total_ret_pct=m_hedge_only['total_ret'] * 100,
                   hedge_sharpe=m_hedge_only['sharpe'], hedge_sortino=m_hedge_only['sortino'],
                   hedge_maxdd_pct=m_hedge_only['maxdd'] * 100, hedge_worst_day_pct=m_hedge_only['worst_day'] * 100,
                   book_cagr_hedged_pct=m_hedged['cagr'] * 100, book_cagr_unhedged_pct=base_metrics['cagr'] * 100,
                   book_maxdd_hedged_pct=m_hedged['maxdd'] * 100, book_maxdd_unhedged_pct=base_metrics['maxdd'] * 100,
                   book_cvar5_hedged_pct=m_hedged['cvar5'] * 100, book_cvar5_unhedged_pct=base_metrics['cvar5'] * 100,
                   book_sharpe_hedged=m_hedged['sharpe'], book_sharpe_unhedged=base_metrics['sharpe'],
                   mean_achieved_dte=np.nan, target_dte=np.nan, n_rolls=np.nan, pct_intrinsic_fallback=np.nan)
        grid_rows.append(row)
        pd.DataFrame(grid_rows).to_csv(OUT / "grid_results.csv", index=False)
        cr = crisis_analysis(S, ladder, "ladder__3m6m12m_native")
        crisis_rows.extend(cr)
        pd.DataFrame(crisis_rows).to_csv(OUT / "crisis_analysis.csv", index=False)
        log("ladder combo done")
    except KeyError as e:
        log(f"ladder skipped, missing piece {e}")

    # ================================================================== STACKED_BOOK overlay (real book, 2022-2025)
    log("=== STACKED_BOOK overlay ===")
    book_path = BASE / "Shreyas_Ionic_AMC/04_RND_LAB/results/STACKED_BOOK_20260711/book_daily_pnl.csv"
    book = pd.read_csv(book_path, index_col=0, parse_dates=True)
    book_ret = (book["total"] / CAP)
    nifty_ret_book_win = nifty_ret.reindex(book_ret.index).fillna(0.0)

    def ols_beta(y_ret, x_ret):
        x, y = x_ret.values, y_ret.values
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 10:
            return np.nan
        return float(np.cov(x[mask], y[mask])[0, 1] / np.var(x[mask]))

    beta_total = ols_beta(book_ret, nifty_ret_book_win)
    s1f_ret = book["s1f"] / CAP
    beta_s1f_full = ols_beta(s1f_ret, nifty_ret_book_win)
    tail_thresh = nifty_ret_book_win.quantile(0.05)
    tail_mask = nifty_ret_book_win <= tail_thresh
    beta_s1f_tail = ols_beta(s1f_ret[tail_mask], nifty_ret_book_win[tail_mask]) if tail_mask.sum() >= 10 else np.nan
    log(f"BOOK beta to NIFTY (full-sample, whole book): {beta_total:.3f}")
    log(f"S1-F (short-vol sleeve) beta to NIFTY: full-sample {beta_s1f_full:.3f} vs "
        f"TAIL-conditional (worst 5% NIFTY days, n={int(tail_mask.sum())}) {beta_s1f_tail:.3f} "
        f"-- risk-office flagged this sleeve's COVID-window loss (-543.8pts/-Rs40,785/lot, 2020-02-28..03-26) "
        f"as disproportionate; a linear full-sample beta on a negative-gamma sleeve UNDERSTATES crash-day "
        f"sensitivity by construction (small on calm days, large on tail days) -- report BOTH, size hedge to "
        f"the larger (more negative) of the two, never the full-sample number alone.")
    # recommended hedge notional: whichever exposure measure implies MORE protection needed (conservative)
    beta_effective = beta_total if abs(beta_total) >= abs(beta_s1f_tail) or not np.isfinite(beta_s1f_tail) else beta_s1f_tail
    hedge_notional_book = beta_effective * CAP

    # in-sample check: which sleeve drives the book's own worst days (2022-2025)?
    worst10 = book["total"].nsmallest(10)
    sleeve_contrib_worst10 = book.loc[worst10.index, ["midsmall", "breakout", "s1f", "b1b"]].sum()
    log(f"book's worst-10 days (2022-2025) sleeve contribution (Rs): {sleeve_contrib_worst10.round(0).to_dict()}")

    book_test_rows = []
    for label in ["put_10__12m_12m(native)", "put_10__6m_6m(native)", "putspread_10x20__12m_12m(native)",
                  "collar_10x5__12m_12m(native)", "ladder__3m6m12m_native"]:
        if label not in pnl_store:
            continue
        pnl = pnl_store[label]
        pnl_book_win = pnl.reindex(book.index).fillna(0.0)
        hedge_rupee = pnl_book_win * hedge_notional_book
        book_hedged_total = book["total"] + hedge_rupee
        eq_before = CAP + book["total"].cumsum()
        eq_after = CAP + book_hedged_total.cumsum()
        dd_before = (eq_before / eq_before.cummax() - 1).min()
        dd_after = (eq_after / eq_after.cummax() - 1).min()
        ret_before, ret_after = book["total"] / CAP, book_hedged_total / CAP
        cvar_before = ret_before[ret_before <= ret_before.quantile(0.05)].mean()
        cvar_after = ret_after[ret_after <= ret_after.quantile(0.05)].mean()
        yrs = (book.index[-1] - book.index[0]).days / 365.25
        cagr_before = (eq_before.iloc[-1] / CAP) ** (1 / yrs) - 1
        cagr_after = (eq_after.iloc[-1] / CAP) ** (1 / yrs) - 1
        sharpe_before = ret_before.mean() / ret_before.std() * math.sqrt(252)
        sharpe_after = ret_after.mean() / ret_after.std() * math.sqrt(252)
        annual_hedge_cost_rupee = hedge_rupee.sum() / yrs
        book_test_rows.append(dict(overlay=label, beta_total_used=beta_total, beta_s1f_full=beta_s1f_full,
                                    beta_s1f_tail=beta_s1f_tail, beta_effective_used=beta_effective,
                                    hedge_notional_rupee=hedge_notional_book,
                                    annual_cost_rupee=annual_hedge_cost_rupee, annual_cost_pct_of_nav=annual_hedge_cost_rupee / CAP * 100,
                                    cagr_before_pct=cagr_before * 100, cagr_after_pct=cagr_after * 100,
                                    maxdd_before_pct=dd_before * 100, maxdd_after_pct=dd_after * 100,
                                    cvar5_before_pct=cvar_before * 100, cvar5_after_pct=cvar_after * 100,
                                    sharpe_before=sharpe_before, sharpe_after=sharpe_after))
        log(f"  {label}: cost {annual_hedge_cost_rupee/CAP*100:.2f}%/yr NAV, maxDD {dd_before*100:.1f}%->{dd_after*100:.1f}%, "
            f"CVaR5 {cvar_before*100:.2f}%->{cvar_after*100:.2f}%, CAGR {cagr_before*100:.1f}%->{cagr_after*100:.1f}%")
    pd.DataFrame(book_test_rows).to_csv(OUT / "stacked_book_overlay.csv", index=False)

    json.dump(dict(baseline_2011_2026=base_metrics, beta_total=beta_total, beta_s1f_full=beta_s1f_full,
                    beta_s1f_tail=beta_s1f_tail, beta_effective_used=beta_effective,
                    hedge_notional_book=hedge_notional_book, sleeve_contrib_worst10=sleeve_contrib_worst10.to_dict(),
                    n_configs=len(all_configs), completed=time.strftime("%Y-%m-%d %H:%M:%S")),
              open(OUT / "run_meta.json", "w"), indent=2, default=str)
    log("=== ALL DONE ===")


if __name__ == "__main__":
    main()
