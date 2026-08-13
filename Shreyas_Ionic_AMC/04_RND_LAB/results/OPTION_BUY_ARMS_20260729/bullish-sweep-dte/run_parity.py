"""Prove the speed patch (global strike-pruned expiry store + chronological chunking)
is RESULT-NEUTRAL before it is used for the grid. Pre-registration section 8.

Three tables are compared, cell by cell, on a real config:
  A = unmodified harness store (2-entry LRU, all strikes), signals in one call
  B = patched global pruned store, signals in one call
  C = patched global pruned store, signals split into calendar-year chunks

A vs B tests the pruning. B vs C tests the chunking. Any mismatch => patch discarded.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT))
import arm1_lib as L                                     # noqa: E402
import opt_pl as H                                       # noqa: E402

LOG = []


def say(s=""):
    print(s, flush=True)
    LOG.append(str(s))


def _as_str(x: pd.Series) -> np.ndarray:
    """NaN-safe stringification. NOTE (amendment 1): the first version of this test
    compared `xa.astype(str) != xb.astype(str)` directly. Under pandas' NA-aware str
    dtype that comparison PROPAGATES NA, so every missing-vs-missing cell was counted
    as a difference and the patch was wrongly reported as failing. The bug was in the
    test, not in the store; missing values are collapsed to a sentinel here."""
    o = x.astype(object).where(x.notna(), "<MISSING>")
    return np.array([str(v) for v in o])


def cmp_tables(a: pd.DataFrame, b: pd.DataFrame, na: str, nb: str) -> bool:
    ok = True
    if len(a) != len(b):
        say(f"  FAIL {na} vs {nb}: row counts {len(a)} vs {len(b)}")
        return False
    a = a.reset_index(drop=True)
    b = b.reset_index(drop=True)
    for c in H._TRADE_COLS:
        xa, xb = a[c], b[c]
        nan_mismatch = int((xa.isna().values != xb.isna().values).sum())
        if pd.api.types.is_numeric_dtype(xa) and pd.api.types.is_numeric_dtype(xb):
            d = (xa.astype(float) - xb.astype(float)).abs()
            bad = int((d.fillna(0) > 0).sum())
            if bad or nan_mismatch:
                say(f"  FAIL col {c}: {bad} value diffs (max {d.max():.3e}), "
                    f"{nan_mismatch} missing-pattern diffs")
                ok = False
        else:
            neq = int((_as_str(xa) != _as_str(xb)).sum())
            if neq or nan_mismatch:
                say(f"  FAIL col {c}: {neq} differing entries, "
                    f"{nan_mismatch} missing-pattern diffs")
                ok = False
    if ok:
        say(f"  PASS {na} vs {nb}: all {len(H._TRADE_COLS)} columns identical "
            f"on {len(a)} rows (exact, 0.00e+00)")
    return ok


if __name__ == "__main__":
    say("=== PATCH PARITY TEST (must pass before the grid runs) ===")
    sigs = L.build_signals()
    t1 = L.split(sigs["T1_sweep_priorday_reclaim"], L.BUILD_START, L.BUILD_END)
    say(f"T1 build signals: {len(t1)}  {t1['t'].min()} .. {t1['t'].max()}")
    say(f"T2 build signals: {len(L.split(sigs['T2_sweep_intraday_continue'], L.BUILD_START, L.BUILD_END))}")

    # A representative config that exercises strikes 2 ITM (the widest strike request),
    # a stop/target exit and a mid DTE bucket. Subsample to keep the SLOW unpatched
    # run affordable: every 4th signal of 2023-2024.
    d = pd.to_datetime(t1["t"]).dt.date
    sub = t1[(d >= pd.Timestamp("2023-01-01").date()) & (d <= pd.Timestamp("2024-12-31").date())]
    sub = sub.iloc[::4].reset_index(drop=True)
    cfg = H.OptCfg(min_dte=2, max_dte=3, strike_offset=-2, **L.BASE,
                   target_pct=1.00, stop_pct=0.35, trail_pct=None)
    say(f"config: {cfg.min_dte}-{cfg.max_dte} DTE, offset {cfg.strike_offset} (2 ITM), "
        f"stop35/tgt100, flat 15:25 | {len(sub)} signals")

    say("\n[A] unmodified harness store (2-entry LRU, ALL strikes) ...")
    import time
    t0 = time.time()
    A = H.run_signals(sub, cfg)
    ta = time.time() - t0
    say(f"    {ta:.1f}s  filled {int((A.status=='filled').sum())}/{len(A)}")

    say("\n[B] patched global store, pruned to the grid's exact strike set ...")
    need = L.needed_strikes([t1])
    say(f"    needed-strike map: {len(need)} expiries, "
        f"{np.mean([len(v) for v in need.values()]):.1f} strikes/expiry avg")
    st = L.install_global_store(needed=need, maxsize=40)
    t0 = time.time()
    B = H.run_signals(sub, cfg)
    tb = time.time() - t0
    say(f"    {tb:.1f}s  filled {int((B.status=='filled').sum())}/{len(B)}  "
        f"(parquet reads {st.reads})")
    okAB = cmp_tables(A, B, "A unpatched", "B pruned-global")

    say("\n[C] same store, signals chunked by calendar year ...")
    parts = []
    for yr in (2023, 2024):
        p = sub[pd.to_datetime(sub["t"]).dt.year == yr]
        if len(p):
            parts.append(H.run_signals(p, cfg))
    C = pd.concat(parts, ignore_index=True)
    okBC = cmp_tables(B, C, "B one-call", "C year-chunked")

    say("\n[speed] a second pass with the store already warm:")
    t0 = time.time()
    H.run_signals(sub, cfg)
    say(f"    {time.time()-t0:.1f}s  (vs {ta:.1f}s unpatched cold) "
        f"-> {ta/max(time.time()-t0,1e-9):.0f}x")

    verdict = "PATCH ACCEPTED" if (okAB and okBC) else "PATCH REJECTED -- run the grid slow"
    say(f"\nVERDICT: {verdict}")
    (OUT / "PATCH_PARITY.txt").write_text("\n".join(LOG), encoding="utf-8")
