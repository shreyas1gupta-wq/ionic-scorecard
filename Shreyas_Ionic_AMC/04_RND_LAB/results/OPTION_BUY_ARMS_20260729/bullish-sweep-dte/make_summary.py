"""Assemble SUMMARY.md + best_config.json from the banked grid JSONs.

Reads only what the grid wrote. Computes every number; nothing is typed in by hand.
Selection is on BUILD ONLY -- the forward column is reported next to it, never ranked on.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT))

DTE_ORDER = ["dte0-1", "dte2-3", "dte4-7"]
OFF_ORDER = ["ITM2", "ITM1", "ATM", "OTM1"]
EX_ORDER = ["flat1525", "stop35tgt100", "trail35", "trail35_hold5d"]


def load(p: str) -> dict:
    f = OUT / p
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def frame(build: dict, fwd: dict, family: str) -> pd.DataFrame:
    rows = []
    for lab, bm in build.items():
        trig, dte, off, ex = lab.split("|")
        fm = fwd.get(lab, {})
        r = {"label": lab, "family": family, "trigger": trig[:2], "dte": dte,
             "off": off, "exit": ex,
             "n_sig": bm.get("signals"), "n": bm.get("filled"),
             "fill_rate": bm.get("fill_rate"),
             "gross": bm.get("gross_total"), "net": bm.get("net_total"),
             "costs": bm.get("costs_total"),
             "fgross": bm.get("frictionless_gross_total"),
             "pf_g": bm.get("pf_gross"), "pf_n": bm.get("pf_net"),
             "wr_g": bm.get("wr_gross"), "wr_n": bm.get("wr_net"),
             "ret": bm.get("ret_pct_net_mean"), "t_nw": bm.get("t_nw"),
             "t_s": bm.get("t_simple"),
             "top1": bm.get("top1_profit_share"),
             "mpg": bm.get("months_pos_gross"), "mpn": bm.get("months_pos_net"),
             "mtot": bm.get("months_total"), "maxdd": bm.get("maxdd"),
             "zvol": bm.get("zero_vol_entry_frac"), "thin": bm.get("thin_entry_frac"),
             "lag": bm.get("entry_lag_mean"), "px": bm.get("avg_entry_px"),
             "dte_avg": bm.get("avg_dte"), "hold": bm.get("avg_hold_min"),
             "f_n": fm.get("filled"), "f_net": fm.get("net_total"),
             "f_gross": fm.get("gross_total"), "f_pf": fm.get("pf_net"),
             "f_ret": fm.get("ret_pct_net_mean"),
             "exit_reasons": bm.get("exit_reasons", {}),
             "reject_reasons": bm.get("reject_reasons", {})}
        rows.append(r)
    return pd.DataFrame(rows)


def fmt(x, nd=0, pct=False, plus=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    if pct:
        return f"{x*100:+.1f}%" if plus else f"{x*100:.1f}%"
    s = f"{x:+,.{nd}f}" if plus else f"{x:,.{nd}f}"
    return s


def gates(row) -> tuple[dict, bool]:
    p1 = bool(row["net"] is not None and row["net"] > 0)
    p2 = bool(row["f_n"] and row["f_net"] is not None and row["f_net"] >= 0)
    p3 = bool(row["top1"] is not None and np.isfinite(row["top1"]) and row["top1"] <= 0.30)
    p4 = bool(row["zvol"] is not None and row["zvol"] <= 0.02
              and row["thin"] is not None and row["thin"] <= 0.20
              and row["fill_rate"] is not None and row["fill_rate"] >= 0.80)
    return {"P1": p1, "P2": p2, "P3": p3, "P4": p4}, (p1 and p2 and p3 and p4)


def table(df: pd.DataFrame, cols: list[tuple[str, str]], sort="net") -> list[str]:
    d = df.sort_values(sort, ascending=False)
    head = "| " + " | ".join(c[0] for c in cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    out = [head, sep]
    for _, r in d.iterrows():
        out.append("| " + " | ".join(c[1](r) for c in cols) + " |")
    return out


CELL_COLS = [
    ("cell", lambda r: f"{r['trigger']} {r['dte']} {r['off']} {r['exit']}"),
    ("n", lambda r: f"{int(r['n'])}" if r['n'] else "0"),
    ("fill", lambda r: fmt(r['fill_rate'], pct=True)),
    ("frictionless gross Rs", lambda r: fmt(r['fgross'], plus=True)),
    ("gross Rs", lambda r: fmt(r['gross'], plus=True)),
    ("costs Rs", lambda r: fmt(r['costs'])),
    ("NET Rs", lambda r: fmt(r['net'], plus=True)),
    ("net/trade", lambda r: fmt(r['ret'], pct=True, plus=True)),
    ("t(NW)", lambda r: fmt(r['t_nw'], 2, plus=True)),
    ("PF net", lambda r: fmt(r['pf_n'], 2)),
    ("WR net", lambda r: fmt(r['wr_n'], pct=True)),
    ("mo+ g/n", lambda r: f"{int(r['mpg'])}/{int(r['mpn'])} of {int(r['mtot'])}"
     if r['mtot'] else "n/a"),
    ("top1", lambda r: fmt(r['top1'], pct=True)),
    ("fwd n", lambda r: f"{int(r['f_n'])}" if r['f_n'] else "0"),
    ("fwd NET Rs", lambda r: fmt(r['f_net'], plus=True)),
    ("gates", lambda r: "".join(k for k, v in gates(r)[0].items() if v) or "-"),
]

if __name__ == "__main__":
    b1, b2 = load("grid_build_T1.json"), load("grid_build_T2.json")
    f1, f2 = load("grid_forward_T1.json"), load("grid_forward_T2.json")
    bp, fp = load("grid_build_probe.json"), load("grid_forward_probe.json")
    prim = pd.concat([frame(b1, f1, "primary"), frame(b2, f2, "primary")], ignore_index=True)
    prob = frame(bp, fp, "probe")
    allc = pd.concat([prim, prob], ignore_index=True)
    allc["PASS"] = [gates(r)[1] for _, r in allc.iterrows()]
    allc.to_csv(OUT / "all_cells.csv", index=False)

    L = []
    A = L.append
    A("# ARM 1 — BULLISH SWEEP x DTE x MONEYNESS: option-buying expression")
    A("")
    A("Pre-registration: `PRE_REGISTRATION.md` (written before the first cell ran). "
      "Harness: `OPTION_PL_HARNESS_20260729/opt_pl.py`. "
      "Patch parity proof: `PATCH_PARITY.txt`, `verify_probe_chunk.py`.")
    A("")
    A(f"**Honest trials: {len(allc)} build cells** "
      f"({int((allc.family=='primary').sum())} primary + {int((allc.family=='probe').sum())} "
      "multi-day probe). All P&L is measured on real 1-min option prints — no IV assumed, "
      "no required-move formula anywhere (Principal's method law).")
    A("")

    # ---------------- headline
    p1 = allc[allc.net > 0]
    passing = allc[allc.PASS]
    A("## 1. Headline")
    A("")
    A(f"- Cells with BUILD net > 0 after real costs: **{len(p1)} of {len(allc)}**")
    A(f"- Cells passing ALL FOUR pre-registered gates: **{len(passing)} of {len(allc)}**")
    tot_g = allc[allc.family == "primary"].gross.sum()
    tot_n = allc[allc.family == "primary"].net.sum()
    tot_c = allc[allc.family == "primary"].costs.sum()
    tot_f = allc[allc.family == "primary"].fgross.sum()
    A(f"- Summed across the 72 primary cells: frictionless gross Rs.{tot_f:,.0f}, "
      f"post-slippage gross Rs.{tot_g:,.0f}, costs Rs.{tot_c:,.0f}, "
      f"**net Rs.{tot_n:,.0f}**")
    A("")

    # ---------------- DTE gradient (the question asked)
    A("## 2. DTE gradient (the Principal's question), primary grid")
    A("")
    A("Aggregated over the 4 moneyness x 3 exit cells inside each DTE bucket. "
      "`ret/trade` is the mean per-trade net return (the trustworthy metric — lot size is "
      "pinned at 75 across 2021-26, so rupee totals are a scaled quantity).")
    A("")
    for trig in ["T1", "T2"]:
        d = prim[prim.trigger == trig]
        if d.empty:
            continue
        A(f"### {trig} = " + ("sweep_priorday_reclaim (spot: +10.03 pts, t=3.10, n=1775)"
                             if trig == "T1" else
                             "sweep_intraday_continue (spot: +6.52 pts, t=2.94, n=5836)"))
        A("")
        A("| DTE | cells | trades | avg entry premium Rs | frictionless gross Rs | gross Rs | "
          "costs Rs | NET Rs | ret/trade net | median t(NW) | cells net>0 |")
        A("|---|---|---|---|---|---|---|---|---|---|---|")
        for dte in DTE_ORDER:
            g = d[d.dte == dte]
            if g.empty:
                continue
            A(f"| {dte} | {len(g)} | {int(g.n.sum())} | {g.px.mean():,.1f} | "
              f"{g.fgross.sum():+,.0f} | {g.gross.sum():+,.0f} | {g.costs.sum():,.0f} | "
              f"**{g.net.sum():+,.0f}** | {g.ret.mean()*100:+.2f}% | "
              f"{g.t_nw.median():+.2f} | {int((g.net>0).sum())}/{len(g)} |")
        A("")

    A("### Moneyness gradient (primary grid, both triggers pooled)")
    A("")
    A("| offset | cells | trades | avg entry premium Rs | gross Rs | NET Rs | ret/trade net | "
      "median t(NW) | cells net>0 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for off in OFF_ORDER:
        g = prim[prim.off == off]
        if g.empty:
            continue
        A(f"| {off} | {len(g)} | {int(g.n.sum())} | {g.px.mean():,.1f} | {g.gross.sum():+,.0f} | "
          f"**{g.net.sum():+,.0f}** | {g.ret.mean()*100:+.2f}% | {g.t_nw.median():+.2f} | "
          f"{int((g.net>0).sum())}/{len(g)} |")
    A("")
    A("### Exit-rule gradient")
    A("")
    A("| exit | cells | trades | avg hold min | gross Rs | NET Rs | ret/trade net | "
      "median t(NW) | cells net>0 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for ex in EX_ORDER:
        g = allc[allc.exit == ex]
        if g.empty:
            continue
        A(f"| {ex} | {len(g)} | {int(g.n.sum())} | {g.hold.mean():,.0f} | {g.gross.sum():+,.0f} | "
          f"**{g.net.sum():+,.0f}** | {g.ret.mean()*100:+.2f}% | {g.t_nw.median():+.2f} | "
          f"{int((g.net>0).sum())}/{len(g)} |")
    A("")

    # ---------------- full cell tables
    A("## 3. Every cell, ranked on BUILD net (selection on build only)")
    A("")
    A("`gates` letters = which of the four pre-registered gates that cell passes "
      "(P1 build net>0, P2 forward net>=0, P3 top trade <=30% of gross profit, "
      "P4 fills credible).")
    A("")
    A("### 3a. Primary grid (72 cells, all intraday)")
    A("")
    L.extend(table(prim, CELL_COLS))
    A("")
    A("### 3b. Multi-day probe (12 cells, T1, trail-35% held up to 5 calendar days)")
    A("")
    L.extend(table(prob, CELL_COLS))
    A("")

    # ---------------- best cell detail
    best = allc.sort_values("net", ascending=False).iloc[0]
    g, ok = gates(best)
    A("## 4. Best BUILD cell in detail")
    A("")
    A(f"**{best['label']}**")
    A("")
    A(f"- trades {int(best['n'])} of {int(best['n_sig'])} signals "
      f"(fill rate {best['fill_rate']*100:.1f}%)")
    A(f"- frictionless gross Rs.{best['fgross']:+,.0f} -> post-slippage gross "
      f"Rs.{best['gross']:+,.0f} -> costs Rs.{best['costs']:,.0f} -> "
      f"**net Rs.{best['net']:+,.0f}**")
    A(f"- per-trade net {best['ret']*100:+.2f}%, t(NW) {best['t_nw']:+.2f}, "
      f"t(iid) {best['t_s']:+.2f}")
    A(f"- PF gross {best['pf_g']:.2f} / PF net {best['pf_n']:.2f}; "
      f"WR gross {best['wr_g']*100:.1f}% / WR net {best['wr_n']*100:.1f}%")
    A(f"- months positive: GROSS {int(best['mpg'])}/{int(best['mtot'])} "
      f"({best['mpg']/best['mtot']*100:.1f}%) vs NET {int(best['mpn'])}/{int(best['mtot'])} "
      f"({best['mpn']/best['mtot']*100:.1f}%)")
    A(f"- top trade = {best['top1']*100:.1f}% of gross profit; maxDD on Rs.3L "
      f"{best['maxdd']*100:.1f}%")
    A(f"- liquidity: zero-volume entries {best['zvol']*100:.2f}%, thin entries "
      f"{best['thin']*100:.2f}%, mean entry lag {best['lag']:.2f} min")
    A(f"- exits: {best['exit_reasons']}")
    A(f"- rejects: {best['reject_reasons']}")
    A(f"- HELD-OUT 2026 H1: {int(best['f_n']) if best['f_n'] else 0} trades, "
      f"net Rs.{best['f_net']:+,.0f}" if best['f_n'] else "- HELD-OUT 2026 H1: no fills")
    A(f"- gates: {g} -> **{'PASS' if ok else 'FAIL'}**")
    A("")

    js = {"best_label": best["label"], "gates": g, "PASS": bool(ok),
          "row": {k: (None if (isinstance(v, float) and not np.isfinite(v)) else v)
                  for k, v in best.items() if k not in ("exit_reasons", "reject_reasons")},
          "n_cells": int(len(allc)), "n_p1": int(len(p1)), "n_pass": int(len(passing)),
          "passing_labels": passing.label.tolist(),
          "primary_totals": {"frictionless_gross": float(tot_f), "gross": float(tot_g),
                             "costs": float(tot_c), "net": float(tot_n)}}
    (OUT / "best_config.json").write_text(json.dumps(js, indent=1, default=str), encoding="utf-8")
    (OUT / "SUMMARY.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote SUMMARY.md ({len(L)} lines), all_cells.csv, best_config.json")
    print(f"cells {len(allc)} | net>0 {len(p1)} | PASS {len(passing)}")
    print(f"best: {best['label']} net {best['net']:+,.0f} t {best['t_nw']:+.2f} "
          f"fwd {best['f_net']}")
