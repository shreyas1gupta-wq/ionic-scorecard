"""
EARN_MOM_SWEEP_20260716 — shared backtest engine.
Owner: Arjun Rao (Head of Quant), build pass 2026-07-16. See SPEC.md for the full brief.

This is a CHEAP-TEST SCREEN (single PIT window) — NOT a certifiable Gate-4 backtest.
No walk-forward / DSR / PBO here. The whole point is: rank 30 combos vs a calendar-matched
random-entry placebo and flag artifacts, honestly.

DESIGN DECISIONS (read before trusting a number) -------------------------------------------
1. QUANTILE WINDOW = EXPANDING, causal, PIT-safe (SPEC.md sanctions this as the fallback,
   lines 49-52). For every event, "top-decile" etc. is computed as the percentile rank of its
   signal value among *strictly earlier* available_date events only (same-day events are
   blinded to each other — no intra-day peeking). Implemented via a Fenwick tree over
   coordinate-compressed values for O(n log n). Trailing-4Q was rejected: several signals
   (turnaround-adjacent sue, np_yoy>=100%) are too sparse in a rolling-4Q pool early in the
   sample (dense 2020-23, thin elsewhere per PROGRESS.md recon) to give a stable cutoff.
2. Percentiles are computed AFTER the N500 liquidity gate (see #4) — "top decile of investable
   earnings growers", not top decile of the full ~2,296-symbol fundamentals universe (which
   includes illiquid/untraded names the original PEAD kill was contaminated by).
3. DEDUP LANDMINE FOUND: unified_quarterly_pit.parquet has 1,278 EXACT (symbol, quarter_end)
   duplicate rows (kaggle vs screener source, same quarter, slightly different values). Left
   un-deduped, shift(4)/shift(1) row-position YoY math silently drifts off by fractions of a
   quarter (same class of corruption as the 17-month-gap lesson). FIX: dedupe keeping kaggle
   over screener before any shift-based signal math. See dedupe_fundamentals().
4. N500 GATE: for each event, membership tested against the most recent snapshot in the
   42-snapshot PIT file on/before available_date (never lookahead). Ticker-naming drift means
   ~90/1004 universe tickers (delistings/renames not aliased, e.g. ABAN, CADILAHC) never match
   the price panel — a real, disclosed coverage gap, not a bug we're hiding.
5. YoY/QoQ base-quarter matching: shift(4) rows within symbol (sorted by quarter_end) is
   ACCEPTED only if the calendar gap is 300-400 days (YoY) / 60-140 days (QoQ); else NaN. Even
   after dedup only ~69%/89% of shift(4)/shift(1) pairs satisfy this — remaining rows are
   genuine missing-quarter gaps and are correctly starved of a signal rather than silently
   mismatched.
6. SUE: rolling(window=8, min_periods=4).std() of the raw quarterly surprise (np_t - np_t-4q),
   ordered by quarter_end per symbol — standard SUE convention. PIT-safe: at quarter t we only
   use surprises up to and including t, which are all already known by available_date(t).
7. Entry = D0+1 close, D0 = first trading day >= available_date (per symbol's own trading
   calendar). `extra_lag_days` param added throughout purely to support the mandatory
   one_day_lag_test (entry_idx = D0_idx + 1 + extra_lag_days); does not touch anything else.
8. Placebo ("random-entry, same-calendar" control, K=200): for EACH real trade, the SAME
   symbol is kept (isolates "was the earnings-signal DAY special" from "was this a good stock
   to be in that year") but the entry day is redrawn uniformly at random from that symbol's
   trading days in the SAME CALENDAR YEAR as the real entry (falls back to year+/-1 if <5
   candidate days exist that year), held for the REAL trade's realized holding length (same
   censoring rule). This is done K=200 times for the whole combo; each resample's mean net
   return is one draw. placebo_mean/placebo_p95 are the mean/95th-pctile of those 200 draws —
   a permutation-style null, not a flat pool of random trades.
9. Portfolio NAV (secondary, 1x-cost only per OUTPUT CONTRACT): daily equal-weight mean of
   active positions' close-to-close returns; the full round-trip cost is deducted ONCE, on the
   entry-day return (not spread across holding days — see Arjun's Sharpe-7-10-artifact lesson;
   spreading OPTION returns across days is the landmine, but a daily mark-to-market NAV for a
   LONG-ONLY EQUITY book is the standard/correct construction since equity prices genuinely
   move every day. No separate cost deduction on exit day — it's already fully booked.)
10. cens_pct: a position is CENSORED only when the *data* runs out before the exit rule could
    fire (panel ends 2026-01-22) — marked at last available close. Reaching a rule's own design
    cap (e.g. dma:50's 252td cap, or fixed:63+stop:8 reaching day 63 without a stop) is a NORMAL
    exit, not censoring.
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve()
ROOT = _HERE.parents[4]                       # .../NIFTY 500
FIRM = _HERE.parents[3]                        # .../Shreyas_Ionic_AMC
LIB = _HERE.parents[2] / "lib"                 # .../04_RND_LAB/lib
sys.path.insert(0, str(LIB))
import guards as G                             # noqa: E402
import lookahead_audit as LA                    # noqa: E402

FUND_PATH = ROOT / "datasets" / "earnings_pit" / "unified_quarterly_pit.parquet"
PRICE_PATH = ROOT / "datasets" / "derived" / "pit_union_panel_v1" / "close_panel_price.parquet"
UNIVERSE_PATH = ROOT / "NIFTY500_TICKER_2005_2025_Final.xlsx"

COST_1X = 0.0067
COST_2X = 0.0107
PRICE_DATA_MAX = pd.Timestamp("2026-01-22")
PLACEBO_K = 200
RNG_SEED = 20260716

# ============================================================================
# Fenwick tree — causal (PIT-safe) expanding percentile rank
# ============================================================================
class _Fenwick:
    __slots__ = ("n", "t")

    def __init__(self, n: int):
        self.n = n
        self.t = [0] * (n + 1)

    def add(self, i: int, delta: int = 1) -> None:
        i += 1
        while i <= self.n:
            self.t[i] += delta
            i += i & (-i)

    def prefix(self, i: int) -> int:
        """Sum over compressed ranks [0..i] inclusive."""
        i += 1
        s = 0
        while i > 0:
            s += self.t[i]
            i -= i & (-i)
        return s


def expanding_causal_pctile(avail_date: pd.Series, value: pd.Series) -> np.ndarray:
    """Causal percentile rank in [0,1]: fraction of STRICTLY EARLIER available_date rows
    (by this same signal, non-NaN) with value <= this row's value. Same-day rows never see
    each other (no intra-day peeking). NaN where no valid prior history exists or value is NaN.
    """
    n = len(value)
    out = np.full(n, np.nan)
    vnp = value.to_numpy(dtype=float)
    valid_mask = ~np.isnan(vnp)
    idx_valid = np.where(valid_mask)[0]
    if len(idx_valid) == 0:
        return out
    vals = vnp[idx_valid]
    dates = pd.to_datetime(avail_date).to_numpy()[idx_valid]
    order = np.argsort(dates, kind="mergesort")  # stable -> preserves original tie order
    vals_o = vals[order]
    dates_o = dates[order]
    orig_idx_o = idx_valid[order]

    uniq = np.unique(vals_o)
    comp = np.searchsorted(uniq, vals_o)
    fw = _Fenwick(len(uniq))
    total = 0
    i = 0
    N = len(vals_o)
    while i < N:
        j = i
        while j < N and dates_o[j] == dates_o[i]:
            j += 1
        for k in range(i, j):
            if total > 0:
                out[orig_idx_o[k]] = fw.prefix(comp[k]) / total
        for k in range(i, j):
            fw.add(comp[k])
        total += (j - i)
        i = j
    return out


# ============================================================================
# Data loaders (module-level cache — load the 3 datasets ONCE per process)
# ============================================================================
_CACHE: dict = {}


def dedupe_fundamentals(fund: pd.DataFrame) -> pd.DataFrame:
    """LANDMINE FIX: 1,278 exact (symbol, quarter_end) dup rows (kaggle vs screener) corrupt
    shift(4)/shift(1) row-position math. Keep kaggle over screener, deterministic."""
    prio = {"kaggle": 0, "screener": 1}
    f = fund.copy()
    f["_sp"] = f["source"].map(prio).fillna(9)
    f = f.sort_values(["symbol", "quarter_end", "_sp"])
    f = f.drop_duplicates(subset=["symbol", "quarter_end"], keep="first").drop(columns="_sp")
    return f.reset_index(drop=True)


def load_universe() -> tuple[np.ndarray, list[set]]:
    """Returns (sorted snapshot_dates as datetime64[ns] array, list of member-sets aligned)."""
    df = pd.read_excel(UNIVERSE_PATH, sheet_name="Sheet1")
    df["snap_date"] = pd.to_datetime(df["Month-Year"], format="%b%Y") + pd.offsets.MonthEnd(0)
    snaps = sorted(df["snap_date"].unique())
    sets = []
    for s in snaps:
        sets.append(set(df.loc[df["snap_date"] == s, "Ticker"]))
    return np.array(snaps, dtype="datetime64[ns]"), sets


def n500_gate(events: pd.DataFrame, snap_dates: np.ndarray, snap_sets: list[set]) -> pd.Series:
    """PIT membership: most-recent snapshot ON/BEFORE available_date. Returns boolean mask."""
    avail_ns = pd.to_datetime(events["available_date"]).to_numpy(dtype="datetime64[ns]")
    snap_idx = np.searchsorted(snap_dates, avail_ns, side="right") - 1
    mask = np.zeros(len(events), dtype=bool)
    syms = events["symbol"].to_numpy()
    for idx in np.unique(snap_idx):
        if idx < 0:
            continue
        rows = snap_idx == idx
        members = snap_sets[idx]
        mask[rows] = pd.Series(syms[rows]).isin(members).to_numpy()
    return pd.Series(mask, index=events.index)


def compute_fund_signals(fund: pd.DataFrame) -> pd.DataFrame:
    """Per-event PIT earnings-momentum signals. See module docstring #3/#5/#6 for the
    dedup + gap-guard + SUE conventions."""
    fund = fund.sort_values(["symbol", "quarter_end"]).reset_index(drop=True)
    out_frames = []
    for sym, g in fund.groupby("symbol", sort=False):
        g = g.reset_index(drop=True)
        qe = g["quarter_end"]
        npf = g["net_profit"]
        sales = g["sales"]
        eps = g["eps"]
        opp = g["op_profit"]

        gap4 = (qe - qe.shift(4)).dt.days
        valid4 = gap4.between(300, 400)
        base4_np = npf.shift(4).where(valid4)
        base4_sales = sales.shift(4).where(valid4)
        base4_eps = eps.shift(4).where(valid4)
        base4_opp = opp.shift(4).where(valid4)

        np_yoy = np.where(base4_np > 0, (npf - base4_np) / base4_np.abs(), np.nan)
        eps_yoy = np.where(base4_eps > 0, (eps - base4_eps) / base4_eps.abs(), np.nan)
        sales_yoy = np.where(base4_sales > 0, (sales - base4_sales) / base4_sales.abs(), np.nan)

        opm_now = np.where(sales > 0, opp / sales, np.nan)
        opm_base = np.where(base4_sales > 0, base4_opp / base4_sales, np.nan)
        opm_delta = opm_now - opm_base

        gap1 = (qe - qe.shift(1)).dt.days
        valid1 = gap1.between(60, 140)
        base1_np = npf.shift(1).where(valid1)
        qoq = np.where(base1_np > 0, (npf - base1_np) / base1_np.abs(), np.nan)

        surprise = pd.Series(np.where(valid4, npf - base4_np, np.nan))
        sue_std = surprise.rolling(8, min_periods=4).std()
        sue = (surprise / sue_std).replace([np.inf, -np.inf], np.nan)

        turnaround = ((base4_np < 0) & (npf > 0)).fillna(False)
        np_yoy_s = pd.Series(np_yoy)
        accel = (np_yoy_s > np_yoy_s.shift(1)).fillna(False)

        g_out = g[["symbol", "company", "quarter_end", "available_date"]].copy()
        g_out["np_yoy"] = np_yoy
        g_out["eps_yoy"] = eps_yoy
        g_out["sales_yoy"] = sales_yoy
        g_out["opm_delta"] = opm_delta
        g_out["qoq"] = qoq
        g_out["sue"] = sue.to_numpy()
        g_out["turnaround"] = turnaround.to_numpy()
        g_out["accel"] = accel.to_numpy()
        out_frames.append(g_out)
    return pd.concat(out_frames, ignore_index=True)


def build_price_index(price: pd.DataFrame) -> dict:
    """Per-symbol arrays: dates, close, sma50, sma200, ret126, ret252, rollmax252, reaction."""
    price = price.sort_values(["symbol", "date"]).reset_index(drop=True)
    PX: dict = {}
    for sym, sub in price.groupby("symbol", sort=False):
        c = sub["close"].reset_index(drop=True)
        PX[sym] = dict(
            dates=sub["date"].to_numpy(dtype="datetime64[ns]"),
            close=c.to_numpy(dtype=float),
            sma50=c.rolling(50, min_periods=50).mean().to_numpy(),
            sma200=c.rolling(200, min_periods=200).mean().to_numpy(),
            ret126=(c / c.shift(126) - 1).to_numpy(),
            ret252=(c / c.shift(252) - 1).to_numpy(),
            rollmax252=c.rolling(252, min_periods=252).max().to_numpy(),
            reaction=(c / c.shift(1) - 1).to_numpy(),
            year=sub["date"].dt.year.to_numpy(),
        )
    return PX


def _attach_price_features(events: pd.DataFrame, PX: dict) -> pd.DataFrame:
    """For each eligible event: locate D0 (first trading day >= available_date) on that
    symbol's own calendar, require a next trading day exists (D0+1, for entry), and pull
    price-action features AS OF D0 (data <= D0 only)."""
    rows = []
    for r in events.itertuples(index=False):
        px = PX.get(r.symbol)
        if px is None:
            continue
        dates = px["dates"]
        avail_ns = np.datetime64(pd.Timestamp(r.available_date))
        d0 = int(np.searchsorted(dates, avail_ns, side="left"))
        if d0 >= len(dates) or d0 + 1 >= len(dates):
            continue  # no D0, or no next trading day to enter on
        close = px["close"]
        sma50 = px["sma50"][d0]
        sma200 = px["sma200"][d0]
        rollmax252 = px["rollmax252"][d0]
        c0 = close[d0]
        rows.append((
            r.symbol, r.company, r.quarter_end, r.available_date,
            r.np_yoy, r.eps_yoy, r.sales_yoy, r.opm_delta, r.qoq, r.sue,
            r.turnaround, r.accel,
            d0,
            (c0 > sma50) if not np.isnan(sma50) else np.nan,
            (c0 > sma200) if not np.isnan(sma200) else np.nan,
            px["ret126"][d0], px["ret252"][d0],
            px["reaction"][d0],
            (c0 / rollmax252) if not np.isnan(rollmax252) else np.nan,
        ))
    cols = ["symbol", "company", "quarter_end", "available_date",
            "np_yoy", "eps_yoy", "sales_yoy", "opm_delta", "qoq", "sue", "turnaround", "accel",
            "D0_idx", "above_50dma", "above_200dma", "ret_6m", "ret_12m", "reaction", "near_52w_high"]
    return pd.DataFrame(rows, columns=cols)


def get_master() -> dict:
    """Load everything ONCE per process, compute signals + percentiles + D0/price features.
    Cached at module level -> run.py loads data once no matter how many combo_ids it's given."""
    if "master" in _CACHE:
        return _CACHE["master"]

    fund_raw = pd.read_parquet(FUND_PATH)
    fund_raw["quarter_end"] = pd.to_datetime(fund_raw["quarter_end"])
    fund_raw["available_date"] = pd.to_datetime(fund_raw["available_date"])
    fund_dedup = dedupe_fundamentals(fund_raw)
    fund_sig = compute_fund_signals(fund_dedup)

    snap_dates, snap_sets = load_universe()
    elig_mask = n500_gate(fund_sig, snap_dates, snap_sets)
    events_elig = fund_sig[elig_mask].reset_index(drop=True)

    price = pd.read_parquet(PRICE_PATH)
    price["date"] = pd.to_datetime(price["date"])
    PX = build_price_index(price)

    events = _attach_price_features(events_elig, PX)

    # cross-sectional causal percentiles, computed on the N500-eligible + D0-resolvable set
    for sig in ("np_yoy", "eps_yoy", "sales_yoy", "sue", "qoq", "opm_delta", "ret_12m"):
        events[sig + "_pctile"] = expanding_causal_pctile(events["available_date"], events[sig])

    # PIT sanity: available_date must be <= D0's date (D0 is first day >= available_date, by
    # construction always true, but assert to catch any regression)
    d0_dates = np.array([PX[s]["dates"][int(i)] for s, i in zip(events["symbol"], events["D0_idx"])])
    events["_d0_date"] = d0_dates
    chk = pd.DataFrame({"available_date": events["available_date"], "action_date": events["_d0_date"]})
    G.assert_pit(chk, avail_col="available_date", act_col="action_date")

    _CACHE["master"] = dict(events=events, PX=PX,
                             n_fund_raw=len(fund_raw), n_fund_dedup=len(fund_dedup),
                             n_events_elig_n500=len(events_elig), n_events_final=len(events))
    return _CACHE["master"]


# ============================================================================
# Cut / filter evaluation
# ============================================================================
def _eval_signal_cut(events: pd.DataFrame, cut: tuple) -> pd.Series:
    kind = cut[0]
    if kind == "pctile":
        sig, thresh = cut[1], cut[2]
        return events[sig + "_pctile"] >= thresh
    if kind == "abs_ge":
        sig, thresh = cut[1], cut[2]
        return events[sig] >= thresh
    if kind == "bool":
        sig = cut[1]
        return events[sig].astype(bool)
    if kind == "or":
        masks = [_eval_signal_cut(events, c) for c in cut[1]]
        m = masks[0]
        for mm in masks[1:]:
            m = m | mm
        return m
    if kind == "and":
        masks = [_eval_signal_cut(events, c) for c in cut[1]]
        m = masks[0]
        for mm in masks[1:]:
            m = m & mm
        return m
    raise ValueError(f"unknown cut kind: {kind}")


def _eval_price_filter(events: pd.DataFrame, pf) -> pd.Series:
    if pf is None:
        return pd.Series(True, index=events.index)
    kind = pf[0]
    if kind == "above_50dma":
        return events["above_50dma"].fillna(False).astype(bool)
    if kind == "above_200dma":
        return events["above_200dma"].fillna(False).astype(bool)
    if kind == "ret_6m_pos":
        return events["ret_6m"] > 0
    if kind == "ret_12m_tophalf":
        return events["ret_12m_pctile"] >= 0.50
    if kind == "near_52w_high":
        return events["near_52w_high"] >= pf[1]
    if kind == "reaction_pos":
        return events["reaction"] > 0
    if kind == "reaction_gt":
        return events["reaction"] > pf[1]
    if kind == "and":
        masks = [_eval_price_filter(events, p) for p in pf[1]]
        m = masks[0]
        for mm in masks[1:]:
            m = m & mm
        return m
    raise ValueError(f"unknown price_filter kind: {pf}")


# ============================================================================
# Exit-rule resolution (vectorized-ish per event using precomputed PX arrays)
# ============================================================================
def _resolve_exit(px: dict, entry_idx: int, entry_price: float, hold: tuple) -> tuple[int, bool]:
    """Returns (exit_idx, censored). censored=True only if DATA ran out before the rule's
    own target could be reached (see module doc #10)."""
    dates = px["dates"]
    close = px["close"]
    last_idx = len(dates) - 1
    kind = hold[0]

    if kind == "fixed":
        n = hold[1]
        target = entry_idx + n
        if target > last_idx:
            return last_idx, True
        return target, False

    if kind == "dma":
        cap = entry_idx + 252
        sma50 = px["sma50"]
        scan_end = min(cap, last_idx)
        if scan_end <= entry_idx:
            return last_idx, (last_idx < cap)
        below = close[entry_idx + 1: scan_end + 1] < sma50[entry_idx + 1: scan_end + 1]
        below = np.where(np.isnan(sma50[entry_idx + 1: scan_end + 1]), False, below)
        if below.any():
            first = int(np.argmax(below))
            return entry_idx + 1 + first, False
        # no trigger within window: normal exit at cap unless data ran out first
        if cap > last_idx:
            return last_idx, True
        return cap, False

    if kind == "fixed_stop":
        n, stop_pct = hold[1], hold[2]
        cap = entry_idx + n
        scan_end = min(cap, last_idx)
        if scan_end <= entry_idx:
            return last_idx, (last_idx < cap)
        window = close[entry_idx + 1: scan_end + 1]
        hit = window <= entry_price * (1 - stop_pct)
        if hit.any():
            first = int(np.argmax(hit))
            return entry_idx + 1 + first, False
        if cap > last_idx:
            return last_idx, True
        return cap, False

    raise ValueError(f"unknown hold kind: {hold}")


def _trade_from_entry(px: dict, entry_idx: int, hold: tuple) -> dict | None:
    dates = px["dates"]
    close = px["close"]
    if entry_idx >= len(dates):
        return None
    entry_price = close[entry_idx]
    exit_idx, censored = _resolve_exit(px, entry_idx, entry_price, hold)
    exit_price = close[exit_idx]
    gross = exit_price / entry_price - 1
    return dict(entry_idx=entry_idx, exit_idx=exit_idx, entry_date=dates[entry_idx],
                exit_date=dates[exit_idx], gross_pct=gross, censored=censored)


# ============================================================================
# Placebo: calendar-matched random-entry control, K=200 resamples of the whole combo
# ============================================================================
def _placebo_distribution(ledger: pd.DataFrame, PX: dict, hold: tuple,
                           cost: float, k: int = PLACEBO_K, seed: int = RNG_SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(ledger)
    if n == 0:
        return np.array([])
    syms = ledger["symbol"].to_numpy()
    real_entry_idx = ledger["entry_idx"].to_numpy()
    hold_len = (ledger["exit_idx"] - ledger["entry_idx"]).to_numpy()
    real_year = pd.to_datetime(ledger["entry_date"]).dt.year.to_numpy()

    # precompute candidate index pools per (symbol, year) once
    pool_cache: dict = {}
    resample_means = np.empty(k)
    for kk in range(k):
        rets = np.empty(n)
        for i in range(n):
            sym = syms[i]
            px = PX[sym]
            yr = real_year[i]
            key = (sym, yr)
            pool = pool_cache.get(key)
            if pool is None:
                yrs = px["year"]
                cand = np.where(yrs == yr)[0]
                if len(cand) < 5:
                    cand = np.where((yrs >= yr - 1) & (yrs <= yr + 1))[0]
                pool_cache[key] = cand
                pool = cand
            if len(pool) == 0:
                rets[i] = np.nan
                continue
            j = rng.integers(0, len(pool))
            e_idx = int(pool[j])
            h = int(hold_len[i])
            last_idx = len(px["dates"]) - 1
            x_idx = min(e_idx + h, last_idx)
            if e_idx >= len(px["close"]):
                rets[i] = np.nan
                continue
            gross = px["close"][x_idx] / px["close"][e_idx] - 1
            rets[i] = gross - cost
        resample_means[kk] = np.nanmean(rets)
    return resample_means


# ============================================================================
# run_combo — the public entry point
# ============================================================================
def run_combo(cfg: dict, extra_lag_days: int = 0, compute_placebo: bool = True) -> dict:
    """cfg keys: combo_id, family, signal (str, descriptive), cut (tuple), price_filter
    (tuple|None), hold (tuple), sizing (optional 'surprise_weighted').
    Returns the OUTPUT CONTRACT dict + '_ledger' DataFrame + '_flags' list."""
    m = get_master()
    events, PX = m["events"], m["PX"]

    sig_mask = _eval_signal_cut(events, cfg["cut"])
    pf_mask = _eval_price_filter(events, cfg.get("price_filter"))
    sel = events[sig_mask & pf_mask].copy()

    trades = []
    for r in sel.itertuples(index=False):
        entry_idx = int(r.D0_idx) + 1 + extra_lag_days
        px = PX[r.symbol]
        t = _trade_from_entry(px, entry_idx, cfg["hold"])
        if t is None:
            continue
        gross = t["gross_pct"]
        net = gross - COST_1X
        net2x = gross - COST_2X
        trades.append(dict(
            symbol=r.symbol, avail_date=r.available_date,
            entry_idx=t["entry_idx"], exit_idx=t["exit_idx"],
            entry_date=t["entry_date"], exit_date=t["exit_date"],
            gross_pct=gross, net_pct=net, net_pct_2x=net2x,
            censored=t["censored"],
            surprise_weight=max(float(r.np_yoy), 0.0) if not np.isnan(r.np_yoy) else 0.0,
        ))

    ledger = pd.DataFrame(trades)
    combo_id = cfg["combo_id"]

    if len(ledger) == 0:
        row = _empty_contract_row(cfg)
        return {**row, "_ledger": ledger, "_flags": ["ZERO TRADES — cut/filter too strict or bad wiring"]}

    # PIT / same-bar guards on the realized ledger
    chk = pd.DataFrame({"available_date": ledger["avail_date"], "action_date": ledger["entry_date"]})
    G.assert_pit(chk, avail_col="available_date", act_col="action_date")
    G.assert_next_bar(ledger["avail_date"], ledger["entry_date"])
    G.assert_no_future_settlement(ledger, exit_col="exit_date", data_max_date=PRICE_DATA_MAX)

    net = ledger["net_pct"]
    n_trades = len(ledger)
    win_pct = float((net > 0).mean())
    mean_net = float(net.mean())
    median_net = float(net.median())
    sd = float(net.std(ddof=1)) if n_trades > 1 else np.nan
    t_stat = float(mean_net / (sd / np.sqrt(n_trades))) if sd and sd > 0 else np.nan
    sorted_net = net.sort_values(ascending=False)
    mean_ex_top1 = float(sorted_net.iloc[1:].mean()) if n_trades > 1 else np.nan
    mean_ex_top2 = float(sorted_net.iloc[2:].mean()) if n_trades > 2 else np.nan
    cens_pct = float(ledger["censored"].mean())
    mean_net_2x = float(ledger["net_pct_2x"].mean())

    sw = ledger["surprise_weight"]
    mean_net_sw = float((net * sw).sum() / sw.sum()) if sw.sum() > 0 else np.nan

    cagr = sharpe = maxdd = np.nan
    daily_ret = pd.Series(dtype=float)
    if compute_placebo:  # skip the expensive extras for the fast lag-test call
        daily_ret = _portfolio_daily_returns(ledger, PX, COST_1X)
        if len(daily_ret) > 5:
            eq = (1 + daily_ret).cumprod()
            yrs = max(len(daily_ret) / 252, 1e-9)
            cagr = float(eq.iloc[-1] ** (1 / yrs) - 1)
            sharpe = float(daily_ret.mean() / (daily_ret.std() + 1e-12) * np.sqrt(252))
            maxdd = float((eq / eq.cummax() - 1).min())

    placebo_mean = placebo_p95 = excess = np.nan
    beats_placebo95 = False
    if compute_placebo:
        dist = _placebo_distribution(ledger, PX, cfg["hold"], COST_1X)
        if len(dist) > 0:
            placebo_mean = float(np.nanmean(dist))
            placebo_p95 = float(np.nanpercentile(dist, 95))
            excess = mean_net - placebo_mean
            beats_placebo95 = bool(mean_net > placebo_p95)

    flags = []
    if compute_placebo:
        flags = G.degenerate_flags(daily_ret, ledger.rename(columns={"symbol": "sym"}),
                                    ret_col="net_pct", sym_col="sym")

    row = dict(
        combo_id=combo_id, family=cfg["family"], signal=cfg["signal"],
        cut=str(cfg["cut"]), price_filter=str(cfg.get("price_filter")), hold=str(cfg["hold"]),
        n_trades=n_trades, win_pct=win_pct, mean_net_pct=mean_net, median_net_pct=median_net,
        t_stat=t_stat, mean_ex_top1=mean_ex_top1, mean_ex_top2=mean_ex_top2, cens_pct=cens_pct,
        cagr=cagr, sharpe=sharpe, maxdd=maxdd,
        placebo_mean=placebo_mean, placebo_p95=placebo_p95,
        excess_vs_placebo_mean=excess, beats_placebo95=beats_placebo95,
        mean_net_pct_2x=mean_net_2x,
        mean_net_pct_sw=mean_net_sw if cfg.get("sizing") == "surprise_weighted" else np.nan,
    )
    return {**row, "_ledger": ledger, "_flags": flags}


def _empty_contract_row(cfg: dict) -> dict:
    return dict(
        combo_id=cfg["combo_id"], family=cfg["family"], signal=cfg["signal"],
        cut=str(cfg["cut"]), price_filter=str(cfg.get("price_filter")), hold=str(cfg["hold"]),
        n_trades=0, win_pct=np.nan, mean_net_pct=np.nan, median_net_pct=np.nan,
        t_stat=np.nan, mean_ex_top1=np.nan, mean_ex_top2=np.nan, cens_pct=np.nan,
        cagr=np.nan, sharpe=np.nan, maxdd=np.nan,
        placebo_mean=np.nan, placebo_p95=np.nan, excess_vs_placebo_mean=np.nan,
        beats_placebo95=False, mean_net_pct_2x=np.nan, mean_net_pct_sw=np.nan,
    )


def _portfolio_daily_returns(ledger: pd.DataFrame, PX: dict, cost: float) -> pd.Series:
    """Equal-weight daily NAV: for each trade, close-to-close returns on every held day;
    entry-day return has the full round-trip cost deducted once (see module doc #9)."""
    pieces = []
    for r in ledger.itertuples(index=False):
        px = PX[r.symbol]
        dates = px["dates"][r.entry_idx: r.exit_idx + 1]
        closes = px["close"][r.entry_idx: r.exit_idx + 1]
        if len(closes) < 2:
            continue
        rets = closes[1:] / closes[:-1] - 1
        rets = rets.copy()
        rets[0] -= cost
        pieces.append(pd.DataFrame({"date": dates[1:], "ret": rets}))
    if not pieces:
        return pd.Series(dtype=float)
    allp = pd.concat(pieces, ignore_index=True)
    daily = allp.groupby("date")["ret"].mean().sort_index()
    return daily


def run_one_day_lag_test(cfg: dict) -> dict:
    """Wraps engine calls for lookahead_audit.one_day_lag_test. Metric = mean_net_pct
    (aggregate per-trade edge) — a real edge decays gracefully, same-bar leakage collapses."""
    def _run(lag: int) -> float:
        r = run_combo(cfg, extra_lag_days=lag, compute_placebo=False)
        v = r["mean_net_pct"]
        return float(v) if v == v else 0.0  # NaN-safe
    return LA.one_day_lag_test(_run)
