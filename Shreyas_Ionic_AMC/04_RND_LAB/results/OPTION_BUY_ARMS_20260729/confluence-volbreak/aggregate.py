"""ARM 3 step 4: merge every run JSON into one table + apply the PRE-REGISTERED pass bar.

Pass bar (PRE_REGISTRATION section 5), all four required:
  1. build net_total > 0
  2. forward net_total >= 0  (forward n < 10 => UNDERPOWERED, not a pass)
  3. top1 share of GROSS profit <= 0.30
  4. zero-volume entry fill fraction <= 0.05

Outputs: all_runs.csv, verdict.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
def main():
    src = sorted(OUT.glob("probe.json")) + sorted(OUT.glob("res_*.json"))
    runs, cfgmeta = [], {}
    for p in src:
        name = p.name
        j = json.loads(p.read_text(encoding="utf-8"))
        cfgmeta.update(j.get("configs", {}))
        for r in j.get("runs", []):
            r["_src"] = name
            runs.append(r)
    if not runs:
        raise SystemExit("no run JSONs found")

    rows = []
    for r in runs:
        if not r.get("filled"):
            rows.append({"cell": r.get("cell"), "config": r.get("config"),
                         "split": r.get("split"), "signals": r.get("n_signals", 0),
                         "filled": 0, "_src": r["_src"]})
            continue
        rows.append({
            "cell": r["cell"], "config": r["config"], "split": r["split"],
            "n_signals_true_build": r.get("n_signals_build_true"),
            "subsampled": r.get("subsampled"),
            "signals": r["signals"], "filled": r["filled"],
            "fill_rate": round(r["fill_rate"], 4),
            "gross": round(r["gross_total"], 0), "net": round(r["net_total"], 0),
            "costs": round(r["costs_total"], 0),
            "net_mean": round(r["net_mean"], 1),
            "ret_pct_net_mean": round(r["ret_pct_net_mean"], 5),
            "t": round(r["ret_pct_net_t"], 3) if r.get("ret_pct_net_t") is not None else None,
            "wr_gross": round(r["wr_gross"], 4), "wr_net": round(r["wr_net"], 4),
            "pf_gross": round(r["pf_gross"], 3), "pf_net": round(r["pf_net"], 3),
            "top1_gross": r.get("top1_share_gross_profit"),
            "top1_net": r.get("top1_share_net_profit"),
            "largest_day_share": r.get("largest_day_share"),
            "n_months": r.get("n_months"), "mo_pos_gross": r.get("months_pos_gross"),
            "mo_pos_net": r.get("months_pos_net"),
            "zero_vol_entry": round(r.get("zero_vol_entry_frac", np.nan), 5),
            "thin_entry": round(r.get("thin_entry_frac", np.nan), 5),
            "maxdd": round(r["maxdd"], 4) if r.get("maxdd") is not None else None,
            "avg_hold_min": round(r["avg_hold_min"], 1),
            "rejected": (r.get("fill") or {}).get("rejected"),
            "_src": r["_src"],
        })
    df = pd.DataFrame(rows).drop_duplicates(["cell", "config", "split"], keep="last")
    df = df.sort_values(["cell", "config", "split"])
    df.to_csv(OUT / "all_runs.csv", index=False)

    # ---- pass bar
    b = df[df.split == "build"].set_index(["cell", "config"])
    f = df[df.split == "forward"].set_index(["cell", "config"])
    verdicts = []
    for key, br in b.iterrows():
        if not br.get("filled"):
            continue
        fr = f.loc[key] if key in f.index else None
        fwd_net = float(fr["net"]) if fr is not None and fr.get("filled") else None
        fwd_filled = int(fr["filled"]) if fr is not None and fr.get("filled") else 0
        c1 = bool(br["net"] > 0)
        if fwd_filled < 10:
            c2, c2note = False, f"UNDERPOWERED forward n={fwd_filled}"
        else:
            c2, c2note = bool(fwd_net >= 0), f"forward net {fwd_net:,.0f}"
        t1 = br.get("top1_gross")
        c3 = bool(t1 is not None and t1 <= 0.30)
        zv = br.get("zero_vol_entry")
        c4 = bool(zv is not None and zv <= 0.05)
        verdicts.append({
            "cell": key[0], "config": key[1],
            "build_net": float(br["net"]), "build_gross": float(br["gross"]),
            "build_filled": int(br["filled"]), "forward_net": fwd_net,
            "forward_filled": fwd_filled,
            "c1_build_net_positive": c1, "c2_forward_sign_ok": c2, "c2_note": c2note,
            "c3_no_trade_gt30pct": c3, "top1_gross_share": t1,
            "c4_fills_credible": c4, "zero_vol_entry_frac": zv,
            "PASS": bool(c1 and c2 and c3 and c4),
        })
    v = pd.DataFrame(verdicts).sort_values("build_net", ascending=False)
    v.to_csv(OUT / "pass_bar.csv", index=False)

    n_pass = int(v["PASS"].sum())
    any_net_pos = bool((v["build_net"] > 0).any())
    out = {
        "n_runs": int(len(df)),
        "n_cell_config_pairs": int(len(v)),
        "n_pass": n_pass,
        "any_build_net_positive": any_net_pos,
        "cells_with_positive_build_net": v.loc[v.build_net > 0,
                                               ["cell", "config", "build_net"]].to_dict("records"),
        "verdict": "SURVIVES_NEEDS_VERIFY" if n_pass else "KILLED",
        "best_by_build_net": v.iloc[0].to_dict() if len(v) else None,
    }
    (OUT / "verdict.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    pd.set_option("display.width", 250, "display.max_columns", 50, "display.max_rows", 300)
    print(df[["cell", "config", "split", "filled", "gross", "net", "ret_pct_net_mean", "t",
              "pf_net", "top1_gross", "mo_pos_net", "n_months", "zero_vol_entry"]].to_string(index=False))
    print("\n==== PASS BAR ====")
    print(v[["cell", "config", "build_net", "forward_net", "forward_filled",
             "c1_build_net_positive", "c2_forward_sign_ok", "c3_no_trade_gt30pct",
             "c4_fills_credible", "PASS"]].to_string(index=False))
    print(f"\nVERDICT: {out['verdict']}  ({n_pass} of {len(v)} cell-config pairs pass)")


if __name__ == "__main__":
    main()
