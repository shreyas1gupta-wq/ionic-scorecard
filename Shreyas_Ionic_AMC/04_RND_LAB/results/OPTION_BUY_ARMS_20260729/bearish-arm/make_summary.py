"""ARM 2 (BEARISH) step 4: aggregate every banked cell, apply the pre-registered gates,
and emit the arm verdict + the tables SUMMARY.md needs.

SELECTION RULE (fixed here before the full grid was read, and it is BUILD-ONLY so it never
touches the held-out set): among cells with build `filled >= 30`, rank by build `net_total`
descending; the top cell is reported as `best_config`. If it does not pass the gates that is
stated plainly. Ranking one winner out of 126 pre-registered cells is selection-biased BY
CONSTRUCTION -- that is exactly why the held-out 2026 H1 number is reported for it.

Outputs: arm_verdict.json, cell_table.csv, best_cell_monthly.csv
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BUILD_END = pd.Timestamp("2025-12-31 23:59")


def main() -> int:
    cells = {}
    for f in sorted(glob.glob(str(HERE / "cells_*.json"))):
        cells.update(json.loads(Path(f).read_text(encoding="utf-8")))
    print(f"[cells] {len(cells)} of 126 pre-registered cells banked")

    rows = []
    for k, v in cells.items():
        b, fw, g = v["build"], v["forward"], v["gate"]
        rows.append(dict(
            label=k, trigger=v["trigger"], dte=v["dte"], offset=v["offset"], exit=v["exit"],
            b_signals=b.get("signals"), b_n=b.get("filled"),
            b_fill_rate=b.get("fill_rate"), b_tradeable_fill_rate=b.get("tradeable_fill_rate"),
            b_frictionless=b.get("frictionless_gross"), b_gross=b.get("gross_total"),
            b_net=b.get("net_total"), b_costs=b.get("costs_total"),
            b_wr_net=b.get("wr_net"), b_pf_net=b.get("pf_net"), b_pf_gross=b.get("pf_gross"),
            b_ret_pct_net=b.get("ret_pct_net_mean"), b_t=b.get("t_stat_net"),
            b_t_nw=b.get("t_stat_nw"), b_top1=b.get("top1_profit_share"),
            b_zerovol=b.get("zero_vol_entry_frac"), b_prem=b.get("mean_entry_premium"),
            b_months=b.get("n_months"), b_mpos_g=b.get("months_pos_gross"),
            b_mpos_n=b.get("months_pos_net"),
            f_n=fw.get("filled"), f_net=fw.get("net_total"), f_gross=fw.get("gross_total"),
            f_frictionless=fw.get("frictionless_gross"), f_ret_pct_net=fw.get("ret_pct_net_mean"),
            verdict=g.get("verdict"), passed=g.get("pass"),
            g1=g.get("g1_build_net_positive"), g2=g.get("g2_forward_sign_holds"),
            g3=g.get("g3_no_trade_over_30pct"), g4=g.get("g4_fills_credible"),
        ))
    t = pd.DataFrame(rows)
    t = t.sort_values("b_net", ascending=False)
    t.to_csv(HERE / "cell_table.csv", index=False)

    judged = t[t.verdict != "INSUFFICIENT_N"]
    npos = int((judged.b_net > 0).sum())
    npass = int(judged.passed.fillna(False).sum())

    print(f"\n[grid] judged cells={len(judged)}  insufficient_n={len(t)-len(judged)}  "
          f"build-net-positive={npos}  FULL PASS={npass}")
    print("\n=== TOP 12 CELLS BY BUILD NET ===")
    cols = ["label", "b_n", "b_frictionless", "b_gross", "b_net", "b_t", "b_top1",
            "f_n", "f_net", "verdict"]
    print(judged.head(12)[cols].to_string(index=False))
    print("\n=== BOTTOM 5 ===")
    print(judged.tail(5)[cols].to_string(index=False))

    # ---- per-trigger aggregate (mean across that trigger's 18 cells) ------------
    agg = judged.groupby("trigger").agg(
        cells=("label", "count"), n_median=("b_n", "median"),
        build_net_mean=("b_net", "mean"), build_net_median=("b_net", "median"),
        cells_build_net_pos=("b_net", lambda s: int((s > 0).sum())),
        fless_mean=("b_frictionless", "mean"),
        t_mean=("b_t", "mean"),
        fwd_net_mean=("f_net", "mean"),
        cells_fwd_net_pos=("f_net", lambda s: int((s > 0).sum())),
    ).round(1)
    print("\n=== PER-TRIGGER (mean over that trigger's cells) ===")
    print(agg.to_string())

    # ---- marginals: does moneyness / DTE change the answer? ---------------------
    for key in ("offset", "dte", "exit"):
        m = judged.groupby(key).agg(cells=("label", "count"),
                                    build_net_mean=("b_net", "mean"),
                                    fless_mean=("b_frictionless", "mean"),
                                    prem_mean=("b_prem", "mean"),
                                    fwd_net_mean=("f_net", "mean")).round(1)
        print(f"\n=== MARGINAL BY {key.upper()} ===")
        print(m.to_string())

    # ---- best cell (build-only selection rule) ---------------------------------
    best = judged.iloc[0]
    stem = f"{best.dte}_{best.offset}_{best['exit']}"
    tr = pd.read_csv(HERE / f"trades_{stem}.csv", parse_dates=["signal_t", "entry_t", "exit_t"])
    f = tr[(tr.status == "filled") & (tr.tag == best.trigger)].copy()
    f["month"] = pd.to_datetime(f["exit_t"]).dt.to_period("M").astype(str)
    f["split"] = np.where(pd.to_datetime(f["signal_t"]) <= BUILD_END, "build", "forward")
    mo = f.groupby(["split", "month"]).agg(
        trades=("net_pnl", "size"),
        frictionless=("net_pnl", lambda s: np.nan),
        gross=("gross", "sum"), net=("net_pnl", "sum"), costs=("costs", "sum")).drop(
        columns=["frictionless"]).round(0)
    mo.to_csv(HERE / "best_cell_monthly.csv")
    print(f"\n=== BEST CELL (build-net rank #1 of {len(judged)}): {best.label} ===")
    print(mo.to_string())

    out = {
        "cells_banked": len(cells), "cells_preregistered": 126,
        "cells_judged": len(judged), "cells_insufficient_n": int(len(t) - len(judged)),
        "cells_build_net_positive": npos, "cells_full_pass": npass,
        "any_net_positive_build": bool(npos > 0),
        "arm_verdict": "SURVIVES_NEEDS_VERIFY" if npass > 0 else "KILLED",
        "best_cell": {k: (None if pd.isna(v) else v) for k, v in best.to_dict().items()},
        "per_trigger": json.loads(agg.reset_index().to_json(orient="records")),
        "marginal_offset": json.loads(judged.groupby("offset")[
            ["b_net", "b_frictionless", "b_prem", "f_net"]].mean().round(1)
            .reset_index().to_json(orient="records")),
        "marginal_dte": json.loads(judged.groupby("dte")[
            ["b_net", "b_frictionless", "b_prem", "f_net"]].mean().round(1)
            .reset_index().to_json(orient="records")),
        "marginal_exit": json.loads(judged.groupby("exit")[
            ["b_net", "b_frictionless", "b_prem", "f_net"]].mean().round(1)
            .reset_index().to_json(orient="records")),
        "mechanism": {
            "cells_frictionless_gross_positive": int((judged.b_frictionless > 0).sum()),
            "cells_gross_positive": int((judged.b_gross > 0).sum()),
            "cells_net_positive": int((judged.b_net > 0).sum()),
            "note": "frictionless>0 but net<0 => cost/skew failure. frictionless<0 => the "
                    "directional/theta edge is simply absent and no cost model is to blame.",
        },
        "forward_2026H1": {
            "cells_with_ge5_forward_trades": int((judged.f_n >= 5).sum()),
            "cells_forward_net_positive": int((judged.f_net > 0).sum()),
            "forward_net_sum_all_cells": round(float(judged.f_net.sum()), 2),
        },
    }
    (HERE / "arm_verdict.json").write_text(json.dumps(out, indent=2, default=str),
                                           encoding="utf-8")
    print(f"\n==== ARM VERDICT: {out['arm_verdict']} ====")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
