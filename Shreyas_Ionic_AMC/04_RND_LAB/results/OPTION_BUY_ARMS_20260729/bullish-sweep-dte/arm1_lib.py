"""ARM 1 (bullish sweep x DTE x moneyness) -- shared plumbing.

Pre-registered in PRE_REGISTRATION.md (written before any cell ran).

Nothing here re-implements a signal or a fill:
  * signals come from `sweep_signals()` imported VERBATIM from
    04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py
  * option P&L comes from the shared validated harness `opt_pl.py`
    (04_RND_LAB/results/OPTION_PL_HARNESS_20260729/)

The ONLY modification to the harness is a speed patch to its expiry cache (see
`install_global_store`), declared in PRE_REGISTRATION.md section 8 and proved
result-neutral by `run_parity.py`.
"""
from __future__ import annotations

import datetime as dt
import gc
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- paths
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
            r"\NIFTY 500")
HARNESS = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/OPTION_PL_HARNESS_20260729"
SIGBUD = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729/signal_budget"
OUT = Path(__file__).resolve().parent

sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(SIGBUD))

import opt_pl as H                                     # noqa: E402
import chain                                           # noqa: E402
from measure_signal_budget import sweep_signals        # noqa: E402  (VERBATIM reuse)
from stage1_signal_test import resample, nw_tstat      # noqa: E402  (VERBATIM reuse)

# --------------------------------------------------------------------------- windows
BUILD_START = dt.date(2021, 5, 24)
BUILD_END = dt.date(2025, 12, 31)
FWD_START = dt.date(2026, 1, 1)
FWD_END = dt.date(2026, 6, 30)
CAPITAL = 3_00_000.0
STEP_PTS = H.STEP        # NIFTY strike step (50) -- taken from the harness, not assumed


# ============================================================ 1. SIGNALS
def build_signals() -> dict[str, pd.DataFrame]:
    """T1/T2 sweep triggers over the FULL history, columns t/direction/tag.

    `sweep_signals` is computed per-day off 15-min bars with a PIT-safe
    (cummax().shift(2)) intraday reference and clipped to 09:20-14:30, exactly as
    when the spot-level signal budget was measured. `t` stays the SIGNAL BAR's own
    stamp -- the harness fills at the next bar.
    """
    spot = H.load_spot()                       # pre-open 09:00-09:07 bars already removed
    bars15 = resample(spot[["open", "high", "low", "close"]], "15min")
    sw = sweep_signals(bars15)
    out = {}
    for key, name in [("priorday_reclaim", "T1_sweep_priorday_reclaim"),
                      ("intraday_continue", "T2_sweep_intraday_continue")]:
        s = sw[key].copy()
        s = s.rename(columns={"dir": "direction"})
        s["tag"] = name
        out[name] = s.sort_values("t").reset_index(drop=True)[["t", "direction", "tag"]]
    return out


def split(sig: pd.DataFrame, lo: dt.date, hi: dt.date) -> pd.DataFrame:
    d = pd.to_datetime(sig["t"]).dt.date
    return sig[(d >= lo) & (d <= hi)].reset_index(drop=True)


# ============================================================ 2. SPEED PATCH
SNAP_SLACK_STEPS = 4     # >= |max offset| (2); 4 steps = 200 pts of slack


def needed_strikes(sig_frames: list[pd.DataFrame]) -> dict[dt.date, set[int]]:
    """For every expiry, the exact set of strikes this grid could ever request.

    The harness sets atm = round(spot_at_signal/50)*50 and asks for
    atm + offset*50*direction with offset in {-2,-1,0,+1}, i.e. never more than 2 steps
    (100 pts) from the ATM. Keeping atm +/- SNAP_SLACK_STEPS steps therefore provably
    contains the exact requested strike for every cell, with 2 spare steps so the
    harness's nearest-listed snap can never be pushed outside the cached set.
    `run_parity.py` proves this empirically rather than trusting the argument.
    """
    sp = H.load_spot()
    sp_idx = sp.index.values
    sp_close = sp["close"].values
    sp_dates = np.array([d for d in sp.index.date])
    out: dict[dt.date, set[int]] = {}
    seen: dict[tuple, int] = {}
    for sig in sig_frames:
        for t0 in pd.to_datetime(sig["t"]):
            day = t0.date()
            j = np.searchsorted(sp_idx, np.datetime64(t0), side="right") - 1
            if j < 0 or sp_dates[j] != day:
                continue
            atm = int(round(float(sp_close[j]) / STEP_PTS) * STEP_PTS)
            for _, lo, hi in DTE_BUCKETS:
                key = (day, lo, hi)
                if key in seen:
                    exp = seen[key]
                else:
                    exp = chain.nearest_expiry(day, lo, hi)
                    seen[key] = exp
                if exp is None:
                    continue
                s = out.setdefault(exp, set())
                for k in range(atm - SNAP_SLACK_STEPS * STEP_PTS,
                               atm + SNAP_SLACK_STEPS * STEP_PTS + 1, STEP_PTS):
                    s.add(int(k))
    return out


class _GlobalStore(H._ExpiryStore):
    """Shared expiry cache, tightly strike-pruned. PRE_REGISTRATION section 8.

    Two differences vs the harness store, both speed-only:
      (a) a larger FIFO cache, so an expiry frame is read from parquet once and then
          reused by every config in the chunk instead of once per config;
      (b) only the strikes in `needed[exp]` are kept in memory (see `needed_strikes`).
    Prices stay float64 -- no dtype narrowing, so no rounding drift is introduced.
    Memory is the binding constraint on this laptop (~15.6 GB total, a few GB free),
    which is why the pruning is by exact strike set rather than a wide price band.
    """

    def __init__(self, maxsize: int = 60, needed: dict | None = None):
        super().__init__(maxsize=maxsize)
        self.needed = needed
        self.reads = 0
        self.mem_retries = 0

    def get(self, exp: dt.date) -> pd.DataFrame:
        if exp in self._d:
            return self._d[exp]
        # A MemoryError here would be caught by the harness and turned into a
        # `expiry_read_error:MemoryError` REJECT -- i.e. a machine limit would silently
        # masquerade as an untradeable signal and bias the sample. Seen once in a smoke
        # run on this 15.6 GB laptop. So: evict, gc, retry; and if it still fails, raise
        # loudly instead of letting it become a data point.
        raw = None
        for attempt in range(3):
            try:
                raw = chain.load_expiry(exp)
                break
            except MemoryError:
                self.mem_retries += 1
                chain.load_expiry.cache_clear()
                self.clear()
                gc.collect()
        if raw is None:
            raise MemoryError(f"could not read expiry {exp} after 3 attempts")
        chain.load_expiry.cache_clear()
        self.reads += 1
        df = raw[["t", "open", "high", "low", "close", "volume",
                  "open_interest", "trading_day", "strike", "option_type"]]
        if self.needed is not None:
            ks = self.needed.get(exp)
            df = df[df["strike"].isin(ks)] if ks else df.iloc[0:0]
        df = df.copy().set_index(["strike", "option_type"]).sort_index()
        self._d[exp] = df
        self._order.append(exp)
        while len(self._order) > self.maxsize:
            self._d.pop(self._order.pop(0), None)
        return df

    def clear(self):
        self._d.clear(); self._order.clear(); self._days.clear()


_STORE: _GlobalStore | None = None


def install_global_store(needed: dict | None = None, maxsize: int = 60) -> _GlobalStore:
    """Point the harness at one shared store. Returns it so a caller can .clear()."""
    global _STORE
    _STORE = _GlobalStore(maxsize=maxsize, needed=needed)
    H._ExpiryStore = lambda maxsize=2: _STORE          # noqa: ARG005
    return _STORE


# ============================================================ 3. GRID
DTE_BUCKETS = [("dte0-1", 0, 1), ("dte2-3", 2, 3), ("dte4-7", 4, 7)]
OFFSETS = [(-2, "ITM2"), (-1, "ITM1"), (0, "ATM"), (+1, "OTM1")]
EXITS = [
    ("flat1525", dict(target_pct=None, stop_pct=None, trail_pct=None)),
    ("stop35tgt100", dict(target_pct=1.00, stop_pct=0.35, trail_pct=None)),
    ("trail35", dict(target_pct=None, stop_pct=None, trail_pct=0.35)),
]

BASE = dict(max_hold_days=0, squareoff_hhmm="15:25", expiry_handling="trade_out",
            allow_opposite_signal_exit=False, lots=1)
PROBE = dict(max_hold_days=5, squareoff_hhmm="15:25", expiry_handling="settle_intrinsic",
             allow_opposite_signal_exit=False, lots=1, trail_pct=0.35,
             target_pct=None, stop_pct=None)


def grid(trigger: str) -> list[tuple[str, "H.OptCfg"]]:
    cells = []
    for dname, dlo, dhi in DTE_BUCKETS:
        for off, oname in OFFSETS:
            for ename, ek in EXITS:
                cells.append((f"{trigger}|{dname}|{oname}|{ename}",
                              H.OptCfg(min_dte=dlo, max_dte=dhi, strike_offset=off,
                                       **BASE, **ek)))
    return cells


def probe_grid(trigger: str) -> list[tuple[str, "H.OptCfg"]]:
    cells = []
    for dname, dlo, dhi in DTE_BUCKETS:
        for off, oname in OFFSETS:
            cells.append((f"{trigger}|{dname}|{oname}|trail35_hold5d",
                          H.OptCfg(min_dte=dlo, max_dte=dhi, strike_offset=off, **PROBE)))
    return cells


# ============================================================ 4. METRICS
def metrics(filled: pd.DataFrame, n_sig: int, reject_counts: dict, label: str) -> dict:
    """Everything the pass bar and the schema need, all computed. No estimates.

    Takes the FILLED rows plus the signal count and reject tally separately, so a long
    chunked run never has to hold every rejected row in memory. Nothing is silently
    dropped: n_sig == filled + sum(reject_counts) is asserted by the caller.
    """
    f = filled.copy()
    m = {"label": label, "signals": int(n_sig), "filled": int(len(f)),
         "fill_rate": (len(f) / n_sig) if n_sig else float("nan"),
         "reject_reasons": dict(reject_counts)}
    if f.empty:
        return m
    g, n = f["gross"].astype(float), f["net_pnl"].astype(float)
    r = f["ret_pct_net"].astype(float)
    wg, lg = g[g > 0], g[g <= 0]
    wn, ln = n[n > 0], n[n <= 0]
    # frictionless gross (no slippage, no statutory cost) -- diagnoses cost-vs-edge
    fg = ((f["exit_px_raw"].astype(float) - f["entry_px_raw"].astype(float))
          * f["qty"].astype(float))
    f["_month"] = pd.to_datetime(f["exit_t"]).dt.to_period("M")
    gm = f.groupby("_month")[["gross", "net_pnl"]].sum()
    dd = f.sort_values("exit_t")
    daily = dd.groupby(pd.to_datetime(dd["exit_t"]).dt.date)["net_pnl"].sum()
    eq = CAPITAL + daily.cumsum()
    m.update(
        gross_total=float(g.sum()), net_total=float(n.sum()),
        costs_total=float(f["costs"].sum()), frictionless_gross_total=float(fg.sum()),
        gross_mean=float(g.mean()), net_mean=float(n.mean()),
        wr_gross=float((g > 0).mean()), wr_net=float((n > 0).mean()),
        pf_gross=float(wg.sum() / abs(lg.sum())) if lg.sum() != 0 else float("inf"),
        pf_net=float(wn.sum() / abs(ln.sum())) if ln.sum() != 0 else float("inf"),
        ret_pct_net_mean=float(r.mean()),
        t_simple=float(r.mean() / r.std() * np.sqrt(len(r))) if r.std() > 0 else float("nan"),
        t_nw=float(nw_tstat(r.values)),
        best=float(n.max()), worst=float(n.min()),
        top1_profit_share=float(n.max() / wn.sum()) if wn.sum() > 0 else float("nan"),
        months_total=int(len(gm)),
        months_pos_gross=int((gm["gross"] > 0).sum()),
        months_pos_net=int((gm["net_pnl"] > 0).sum()),
        total_ret_on_capital=float(n.sum() / CAPITAL),
        maxdd=float(((eq - eq.cummax()) / eq.cummax()).min()),
        zero_vol_entry_frac=float((f["entry_vol"].astype(float) == 0).mean()),
        thin_entry_frac=float(f["entry_thin"].fillna(False).astype(bool).mean()),
        thin_exit_frac=float(f["exit_thin"].fillna(False).astype(bool).mean()),
        stale_exit_frac=float(f["exit_stale"].fillna(False).astype(bool).mean()),
        cash_settled_frac=float(f["cash_settled"].fillna(False).astype(bool).mean()),
        entry_lag_mean=float(f["entry_lag_min"].astype(float).mean()),
        entry_lag_p95=float(f["entry_lag_min"].astype(float).quantile(0.95)),
        avg_entry_px=float(f["entry_fill"].astype(float).mean()),
        avg_hold_min=float(f["hold_min"].astype(float).mean()),
        avg_hold_days=float(f["hold_days"].astype(float).mean()),
        avg_dte=float(f["dte_entry"].astype(float).mean()),
        exit_reasons=f["exit_reason"].value_counts().to_dict(),
    )
    return m


def pass_bar(bm: dict, fm: dict) -> dict:
    """The four pre-registered gates. bm = build metrics, fm = forward metrics."""
    filled_b = bm.get("filled", 0)
    p1 = bool(filled_b and bm.get("net_total", -1) > 0)
    fwd_n = fm.get("net_total", None) if fm.get("filled", 0) else None
    p2 = bool(fwd_n is not None and fwd_n >= 0)
    p3 = bool(filled_b and np.isfinite(bm.get("top1_profit_share", np.nan))
              and bm["top1_profit_share"] <= 0.30)
    p4 = bool(filled_b and bm.get("zero_vol_entry_frac", 1) <= 0.02
              and bm.get("thin_entry_frac", 1) <= 0.20
              and bm.get("fill_rate", 0) >= 0.80)
    return {"P1_build_net_positive": p1, "P2_forward_sign_holds": p2,
            "P3_not_concentrated": p3, "P4_fills_credible": p4,
            "PASS": bool(p1 and p2 and p3 and p4),
            "forward_net": fwd_n, "forward_filled": int(fm.get("filled", 0))}
