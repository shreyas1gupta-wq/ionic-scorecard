"""ARM 2 (BEARISH) step 2: real 1-min option P&L for every pre-registered cell.

Buys NIFTY weekly PUTS on the bearish triggers from gen_signals.py, using the shared,
independently validated harness (OPTION_PL_HARNESS_20260729/opt_pl.py). No formula proxies:
every rupee comes from a real traded 1-min option print (or, on expiry, cash settlement at
intrinsic from the underlying -- landmine #9).

EFFICIENCY NOTE: all 7 triggers are passed to ONE run_signals() call per
(DTE window x strike offset x exit set) config, tagged, then split by tag afterwards. This
is EXACTLY equivalent to 7 separate calls because allow_opposite_signal_exit=False and
no_overlap=False make every signal independent -- the only cross-signal state in the harness
is `busy_until` (no_overlap) and the opposite-signal exit. It saves ~7x the parquet reads.

Outputs (this folder):
  trades_<dte>_<off>_<exit>.csv   full per-signal rows (filled AND rejected) for every config
  cell_results.json               every cell's build/forward metrics + gate verdicts
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parents[1] / "OPTION_PL_HARNESS_20260729"
sys.path.insert(0, str(HARNESS))
import opt_pl as H                                                    # noqa: E402

BUILD_END = pd.Timestamp("2025-12-31 23:59")

DTE_WINDOWS = {"dte0_1": (0, 1), "dte2_3": (2, 3), "dte4_7": (4, 7)}
OFFSETS = {"ITM1": -1, "ATM": 0, "OTM1": +1}
EXITS = {
    "E1_tgt50_stop30": dict(target_pct=0.50, stop_pct=0.30),
    "E2_hold_1525": dict(target_pct=None, stop_pct=None),
}
INSUFFICIENT_N = 30          # pre-registered floor for a cell to be judged at all


def base_cfg(dte, off, exitkw):
    lo, hi = dte
    return H.OptCfg(
        min_dte=lo, max_dte=hi, strike_offset=off,
        max_hold_days=0, squareoff_hhmm="15:25",
        expiry_handling="trade_out",        # intraday caller: keep real 15:25 prints
        allow_opposite_signal_exit=False, no_overlap=False,
        lots=1, cost_model="cost_standards", slippage_mode="dynamic",
        exclude_zero_volume=True, max_entry_lag_min=5,
        **exitkw,
    )


def metrics(f: pd.DataFrame, n_sig: int, n_no_expiry: int = 0) -> dict:
    """Build/forward metrics on a FILLED subset. GROSS and NET kept separate (D-035).
    `fless` = frictionless gross from the raw prints, which is what tells us whether a
    failure is directional/theta or cost/skew."""
    tradeable = max(n_sig - int(n_no_expiry), 0)
    m = {"signals": int(n_sig), "filled": int(len(f)),
         "fill_rate": round(len(f) / n_sig, 4) if n_sig else None,
         "no_expiry_in_window": int(n_no_expiry), "tradeable_signals": tradeable,
         "tradeable_fill_rate": round(len(f) / tradeable, 4) if tradeable else None}
    if f.empty:
        return m
    g, n = f["gross"], f["net_pnl"]
    fless = (f["exit_px_raw"] - f["entry_px_raw"]) * f["qty"]
    wn, ln = n[n > 0], n[n <= 0]
    wg, lg = g[g > 0], g[g <= 0]
    r = f["ret_pct_net"]
    rg = f["ret_pct_gross"]
    m.update(
        frictionless_gross=round(float(fless.sum()), 2),
        gross_total=round(float(g.sum()), 2),
        net_total=round(float(n.sum()), 2),
        costs_total=round(float(f["costs"].sum()), 2),
        net_mean=round(float(n.mean()), 2),
        wr_gross=round(float((g > 0).mean()), 4), wr_net=round(float((n > 0).mean()), 4),
        pf_gross=(round(float(wg.sum() / abs(lg.sum())), 4) if lg.sum() != 0 else None),
        pf_net=(round(float(wn.sum() / abs(ln.sum())), 4) if ln.sum() != 0 else None),
        ret_pct_net_mean=round(float(r.mean()), 6),
        ret_pct_gross_mean=round(float(rg.mean()), 6),
        t_stat_net=(round(float(r.mean() / r.std() * np.sqrt(len(r))), 4)
                    if r.std() > 0 else None),
        t_stat_nw=round(float(nw_t(r.values)), 4),
        mean_entry_premium=round(float(f["entry_fill"].mean()), 2),
        mean_hold_min=round(float(f["hold_min"].mean()), 1),
        zero_vol_entry_frac=round(float((f["entry_vol"] == 0).mean()), 5),
        thin_entry_frac=round(float(f["entry_thin"].fillna(False).astype(bool).mean()), 5),
        entry_lag_p95=round(float(f["entry_lag_min"].quantile(0.95)), 2),
        exit_reasons=f["exit_reason"].value_counts().to_dict(),
    )
    pos = float(n[n > 0].sum())
    m["gross_profit_pos"] = round(pos, 2)
    m["top1_profit_share"] = round(float(n.max() / pos), 4) if pos > 0 else None
    mm = f.copy()
    mm["month"] = pd.to_datetime(mm["exit_t"]).dt.to_period("M")
    gm = mm.groupby("month")[["gross", "net_pnl"]].sum()
    m["n_months"] = int(len(gm))
    m["months_pos_gross"] = int((gm["gross"] > 0).sum())
    m["months_pos_net"] = int((gm["net_pnl"] > 0).sum())
    return m


def nw_t(x, lags: int = 5) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return np.nan
    d = x - x.mean()
    var = (d @ d) / n
    for L in range(1, min(lags, n - 1) + 1):
        var += 2 * (1 - L / (lags + 1)) * ((d[L:] @ d[:-L]) / n)
    return x.mean() / np.sqrt(var / n) if var > 0 else np.nan


def gate(b: dict, fw: dict) -> dict:
    """The four pre-registered pass conditions (PRE_REGISTRATION.md section 6)."""
    if b.get("filled", 0) < INSUFFICIENT_N:
        return {"verdict": "INSUFFICIENT_N", "pass": False,
                "note": f"build filled={b.get('filled', 0)} < {INSUFFICIENT_N}"}
    g1 = bool(b.get("net_total", -1) > 0 and (b.get("t_stat_net") or -1) > 0)
    fwn = fw.get("filled", 0)
    if fwn < 5:
        g2, g2note = False, f"forward filled={fwn} (<5) -> INCONCLUSIVE, not a pass"
    else:
        g2 = bool(fw.get("net_total", 0) >= 0)
        g2note = f"forward net Rs.{fw.get('net_total')}"
    t1 = b.get("top1_profit_share")
    g3 = bool(t1 is not None and t1 <= 0.30)
    # AMENDMENT-2: the fill-rate leg is computed on TRADEABLE signals only, i.e. after
    # removing `no_expiry_in_dte_window` rejects, which are a weekly-expiry-CALENDAR fact
    # (a 2-3 DTE window simply does not exist on most days) and say nothing about fill
    # credibility. Raw fill_rate is still reported. See PRE_REGISTRATION.md AMENDMENT-2.
    g4 = bool(b.get("zero_vol_entry_frac", 1) <= 0.02
              and (b.get("tradeable_fill_rate") or 0) >= 0.70)
    return {"g1_build_net_positive": g1, "g2_forward_sign_holds": g2, "g2_note": g2note,
            "g3_no_trade_over_30pct": g3, "g4_fills_credible": g4,
            "pass": bool(g1 and g2 and g3 and g4),
            "verdict": "PASS" if (g1 and g2 and g3 and g4) else "FAIL"}


def main() -> int:
    sig = pd.read_csv(HERE / "bearish_signals.csv", parse_dates=["t"])
    sig = sig[["t", "direction", "tag"]].sort_values("t").reset_index(drop=True)
    assert (sig["direction"] == -1).all(), "arm 2 is bearish-only"
    print(f"[signals] {len(sig)} bearish signals, {sig.tag.nunique()} triggers", flush=True)

    results = {}
    t_all = time.time()
    for ename, ekw in EXITS.items():
        for dname, dte in DTE_WINDOWS.items():
            for oname, off in OFFSETS.items():
                cfg = base_cfg(dte, off, ekw)
                stem = f"{dname}_{oname}_{ename}"
                cfile = HERE / f"cells_{stem}.json"
                tfile = HERE / f"trades_{stem}.csv"
                # ---- RESUME: this run gets killed by disk contention with sibling agents,
                #      so every config banks its own trades CSV + cells JSON and is skipped
                #      on restart. Nothing is ever recomputed or lost.
                if cfile.exists() and tfile.exists():
                    results.update(json.loads(cfile.read_text(encoding="utf-8")))
                    print(f"  [skip, done] {stem}", flush=True)
                    continue
                t0 = time.time()
                if tfile.exists():          # trades banked by a killed run: re-score only
                    tr = pd.read_csv(tfile, parse_dates=["signal_t", "entry_t", "exit_t"])
                    print(f"  [rescore from banked CSV] {stem}", flush=True)
                else:
                    tr = H.run_signals(sig, cfg)
                    tr.to_csv(tfile, index=False)
                el = time.time() - t0
                cells_here = {}
                for tag in sorted(sig["tag"].unique()):
                    sub = tr[tr["tag"] == tag]
                    fl = sub[sub["status"] == "filled"]
                    bmask = pd.to_datetime(sub["signal_t"]) <= BUILD_END
                    b_all, f_all = sub[bmask], sub[~bmask]
                    nx_b = int((b_all["reject_reason"] == "no_expiry_in_dte_window").sum())
                    nx_f = int((f_all["reject_reason"] == "no_expiry_in_dte_window").sum())
                    b = metrics(fl[pd.to_datetime(fl["signal_t"]) <= BUILD_END], len(b_all), nx_b)
                    fw = metrics(fl[pd.to_datetime(fl["signal_t"]) > BUILD_END], len(f_all), nx_f)
                    label = f"{tag}|{dname}|{oname}|{ename}"
                    rej = sub[sub["status"] == "rejected"]["reject_reason"].value_counts().to_dict()
                    cells_here[label] = {"label": label, "trigger": tag, "dte": dname,
                                         "offset": oname, "exit": ename,
                                         "build": b, "forward": fw,
                                         "reject_reasons": rej, "gate": gate(b, fw)}
                    v = cells_here[label]["gate"]["verdict"]
                    print(f"  {label:66s} n={b.get('filled',0):5d} "
                          f"net={b.get('net_total',float('nan')):>11,.0f} "
                          f"gross={b.get('gross_total',float('nan')):>11,.0f} "
                          f"fless={b.get('frictionless_gross',float('nan')):>11,.0f} "
                          f"t={str(b.get('t_stat_net')):>8s} {v}", flush=True)
                cfile.write_text(json.dumps(cells_here, indent=2, default=str), encoding="utf-8")
                results.update(cells_here)
                print(f"  [{stem}] {el:.0f}s  banked", flush=True)

    (HERE / "cell_results.json").write_text(json.dumps(results, indent=2, default=str),
                                            encoding="utf-8")
    npass = sum(1 for v in results.values() if v["gate"]["pass"])
    nposb = sum(1 for v in results.values()
                if (v["build"].get("net_total") or -1) > 0
                and v["gate"]["verdict"] != "INSUFFICIENT_N")
    print(f"\n==== cells={len(results)}  build-net-positive={nposb}  FULL PASS={npass} "
          f"  ({time.time()-t_all:.0f}s) ====", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
