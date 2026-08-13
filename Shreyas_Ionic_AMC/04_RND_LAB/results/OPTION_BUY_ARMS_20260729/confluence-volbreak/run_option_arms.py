"""ARM 3 step 2: REAL option P&L for every pre-registered cell x config.

Uses the shared validated harness (OPTION_PL_HARNESS_20260729/opt_pl.py) verbatim.
No fill logic, no cost model and no signal generator is re-implemented here.

Pre-registration: PRE_REGISTRATION.md sections 4 and 5 (written before any run).

Outputs
  trades/<cell>__<config>__<split>.csv     per-trade rows (filled AND rejected)
  option_results.json                      metrics per cell x config x split
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
SIGDIR = OUT / "signals"
TRDIR = OUT / "trades"
TRDIR.mkdir(exist_ok=True)

RESULTS = OUT.parent.parent
sys.path.insert(0, str(RESULTS / "OPTION_PL_HARNESS_20260729"))
import opt_pl as H                                # noqa: E402

BUILD_END = dt.date(2025, 12, 31)
SUBSAMPLE_MAX = 4000          # PRE_REGISTRATION section 4 compute rule
SUBSAMPLE_SEED = 0

# ---- the pre-registered config grid (PRE_REGISTRATION section 4) -------------
CONFIGS = {
    "C1_ATM_hold1525": H.OptCfg(
        min_dte=1, max_dte=7, strike_offset=0,
        max_hold_days=0, squareoff_hhmm="15:25",
        lots=1, allow_opposite_signal_exit=False),
    "C2_ATM_tgt50_stp30": H.OptCfg(
        min_dte=1, max_dte=7, strike_offset=0,
        target_pct=0.50, stop_pct=0.30,
        max_hold_days=0, squareoff_hhmm="15:25",
        lots=1, allow_opposite_signal_exit=False),
    "C3_ITM2_hold1525": H.OptCfg(
        min_dte=1, max_dte=7, strike_offset=-2,
        max_hold_days=0, squareoff_hhmm="15:25",
        lots=1, allow_opposite_signal_exit=False),
    "C4_ATM_0dte_hold1525": H.OptCfg(
        min_dte=0, max_dte=7, strike_offset=0,
        max_hold_days=0, squareoff_hhmm="15:25",
        expiry_handling="trade_out",
        lots=1, allow_opposite_signal_exit=False),
}

CAPITAL = 3_00_000.0


def load_cell(label: str) -> pd.DataFrame:
    df = pd.read_csv(SIGDIR / f"{label}.csv", parse_dates=["t"])
    df["date"] = df["t"].dt.date
    return df


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return df[df["date"] <= BUILD_END].copy(), df[df["date"] > BUILD_END].copy()


def subsample(df: pd.DataFrame, label: str) -> tuple[pd.DataFrame, int, bool]:
    """PRE-REGISTERED compute rule: build cells > SUBSAMPLE_MAX are uniformly subsampled
    with a FIXED seed, identically across configs. True n is always reported."""
    n_true = len(df)
    if n_true <= SUBSAMPLE_MAX:
        return df, n_true, False
    rng = np.random.default_rng(SUBSAMPLE_SEED)
    idx = np.sort(rng.choice(n_true, SUBSAMPLE_MAX, replace=False))
    return df.iloc[idx].copy(), n_true, True


def month_stats(tr: pd.DataFrame) -> dict:
    f = tr[tr["status"] == "filled"]
    if f.empty:
        return {"n_months": 0, "months_pos_gross": 0, "months_pos_net": 0}
    m = f.copy()
    m["month"] = pd.to_datetime(m["exit_t"]).dt.to_period("M")
    g = m.groupby("month")[["gross", "net_pnl"]].sum()
    return {"n_months": int(len(g)),
            "months_pos_gross": int((g["gross"] > 0).sum()),
            "months_pos_net": int((g["net_pnl"] > 0).sum()),
            "frac_months_pos_gross": round(float((g["gross"] > 0).mean()), 4),
            "frac_months_pos_net": round(float((g["net_pnl"] > 0).mean()), 4)}


def conc_stats(tr: pd.DataFrame) -> dict:
    """Concentration on GROSS profit (pre-registered bar: no single trade > 30%)."""
    f = tr[tr["status"] == "filled"]
    if f.empty:
        return {"top1_share_gross_profit": None, "top1_share_net_profit": None,
                "largest_day_share": None}
    out = {}
    for col, key in (("gross", "top1_share_gross_profit"), ("net_pnl", "top1_share_net_profit")):
        pos = f.loc[f[col] > 0, col].sum()
        out[key] = round(float(f[col].max() / pos), 4) if pos > 0 else None
    d = f.groupby(pd.to_datetime(f["exit_t"]).dt.date)["net_pnl"].sum()
    tot = d.sum()
    out["largest_day_share"] = round(float(d.abs().max() / abs(tot)), 4) if tot else None
    return out


def evaluate(label: str, cfgname: str, cfg, sigs: pd.DataFrame, spl: str,
             save: bool = True) -> dict:
    if sigs.empty:
        return {"cell": label, "config": cfgname, "split": spl, "n_signals": 0}
    t0 = time.time()
    # RESUME: a completed run's per-trade CSV is the authoritative artifact. Metrics are
    # pure functions of it, so recompute from disk instead of re-running the fill engine.
    # Makes the grid crash-safe (this job segfaulted once under memory pressure).
    cache = TRDIR / f"{label}__{cfgname}__{spl}.csv"
    if cache.exists():
        tr = pd.read_csv(cache, parse_dates=["signal_t", "entry_t", "exit_t"])
        if len(tr) == len(sigs):
            m = H.summarize(tr, "", capital=CAPITAL, quiet=True)
            fr = H.fill_report(tr, quiet=True)
            m.update(month_stats(tr)); m.update(conc_stats(tr))
            m["fill"] = {k: fr.get(k) for k in
                         ("rejected", "reject_reasons", "entry_lag_min_mean",
                          "zero_vol_entry_frac", "thin_entry_frac", "oi_zero_entry_frac",
                          "slip_mult_gt1_frac")}
            m["cell"], m["config"], m["split"] = label, cfgname, spl
            m["runtime_s"], m["from_cache"] = 0.0, True
            print(f"  {label:20s} {cfgname:22s} {spl:7s} [cached] filled "
                  f"{m['filled']:5d}/{len(tr):5d} net {m.get('net_total', 0):>12,.0f}",
                  flush=True)
            return m
        print(f"  [stale cache ignored] {cache.name}: {len(tr)} rows vs {len(sigs)} signals",
              flush=True)
    tr = H.run_signals(sigs[["t", "direction"]], cfg)
    m = H.summarize(tr, f"{label} | {cfgname} | {spl}", capital=CAPITAL, quiet=True)
    fr = H.fill_report(tr, quiet=True)
    m.update(month_stats(tr))
    m.update(conc_stats(tr))
    m["fill"] = {k: fr.get(k) for k in
                 ("rejected", "reject_reasons", "entry_lag_min_mean", "zero_vol_entry_frac",
                  "thin_entry_frac", "oi_zero_entry_frac", "slip_mult_gt1_frac")}
    m["cell"], m["config"], m["split"] = label, cfgname, spl
    m["runtime_s"] = round(time.time() - t0, 1)
    if save:
        tr.to_csv(TRDIR / f"{label}__{cfgname}__{spl}.csv", index=False)
    f = tr[tr.status == "filled"]
    print(f"  {label:20s} {cfgname:22s} {spl:7s} filled {len(f):5d}/{len(tr):5d} "
          f"gross {m.get('gross_total', 0):>12,.0f} net {m.get('net_total', 0):>12,.0f} "
          f"ret/tr {m.get('ret_pct_net_mean', float('nan')):+.2%} "
          f"t={m.get('ret_pct_net_t', float('nan')):+.2f} ({m['runtime_s']}s)", flush=True)
    return m


def main():
    have = {p.stem for p in SIGDIR.glob("*.csv")}
    if len(sys.argv) > 1:
        cells = [c for c in sys.argv[1].split(",") if c in have]   # keep caller's order
    else:
        cells = sorted(have)
    tag = sys.argv[2] if len(sys.argv) > 2 else "option_results"
    # argv[3] = optional comma-list of config ids. One config per PROCESS keeps peak memory
    # flat -- long multi-cell processes segfaulted (exit 139) after ~4 big runs.
    want_cfg = sys.argv[3].split(",") if len(sys.argv) > 3 else list(CONFIGS)
    cfg_items = [(k, v) for k, v in CONFIGS.items() if k in want_cfg]
    print(f"[cells] {len(cells)}: {cells}", flush=True)

    report = {"pre_registration": "PRE_REGISTRATION.md",
              "configs": {k: {f: getattr(v, f) for f in
                              ("min_dte", "max_dte", "strike_offset", "target_pct", "stop_pct",
                               "max_hold_days", "squareoff_hhmm", "expiry_handling",
                               "cost_model", "slippage_pct", "slippage_mode", "lots",
                               "exclude_zero_volume", "no_overlap")}
                          for k, v in CONFIGS.items()},
              "subsample_rule": {"max_build_signals": SUBSAMPLE_MAX, "seed": SUBSAMPLE_SEED},
              "runs": []}

    for label in cells:
        df = load_cell(label)
        b, fw = split(df)
        bs, n_true, subbed = subsample(b, label)
        print(f"\n=== {label}  build n={n_true}"
              f"{f' -> subsampled {len(bs)}' if subbed else ''}  forward n={len(fw)} ===",
              flush=True)
        for cfgname, cfg in cfg_items:
            r = evaluate(label, cfgname, cfg, bs, "build")
            r["n_signals_build_true"] = n_true
            r["subsampled"] = subbed
            report["runs"].append(r)
            rf = evaluate(label, cfgname, cfg, fw, "forward")
            rf["n_signals_build_true"] = n_true
            report["runs"].append(rf)
        (OUT / f"{tag}.json").write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"\n[done] {len(report['runs'])} runs -> {tag}.json", flush=True)


if __name__ == "__main__":
    sys.exit(main())
