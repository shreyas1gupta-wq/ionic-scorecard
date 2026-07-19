"""
Incremental-value test (ALPHA_RANKER) -- Arjun Rao (Quant Head), 2026-07-17.

Question (RP-17 book-level incremental value, applied at the composite-leg
level per this tick's task): starting from the BASE 1Y composite as described
in FINAL_MODEL.md S2 -- EY + sector-relative residual momentum + MA-65 slope +
QMJ -- does adding each CANDIDATE leg {net-issuance, asset-growth, CFO/PAT
authenticity, seasonality, DCF} improve the composite's IC_IR / monotonicity /
net-of-cost return by a MEANINGFUL margin, AND is the leg's marginal
correlation to the base composite < 0.6 (i.e. not just a re-weighted EY/QMJ)?

No new lookahead surface: every leg reused verbatim from the cached
capstone_legs.parquet (already-PIT-audited builders from run_capstone.py).
This script only recombines and re-evaluates via the shared harness.

Decision thresholds (disclosed, [INFERENCE] -- not in FND_harness.md, chosen
here to operationalize "meaningful margin"):
  EARNS A SLOT if corr_to_base < 0.6 AND at least one of:
    - delta IC_IR >= +0.03 (absolute)
    - delta monotonicity >= +0.02 (absolute)
    - delta net_of_cost_ann_return >= +0.01 (1pp annualized, v2 per-trade basis)
  Else REDUNDANT/NO-ADD.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
from harness import evaluate, _normalize_factor  # noqa: E402
import run_long_confirm as LC  # noqa: E402

LEGS_CACHE = RND_DIR / "panel" / "capstone_legs.parquet"
CARDS_DIR = RND_DIR / "cards"
REPORTS_DIR = RND_DIR / "reports"
HORIZON = "1Y"

BASE_LEGS = ["value_EY", "mom_resid_peer", "trend_ma65_slope", "quality_QMJ"]
CANDIDATES = {
    "bs_issuance": "net-issuance",
    "bs_asset_growth": "asset-growth",
    "quality_cfo_pat": "CFO/PAT authenticity",
    "seasonality": "seasonality",
    "value_dcf_revgap": "DCF",
}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_legs() -> dict:
    df = pd.read_parquet(LEGS_CACHE)
    legs = {}
    for name, g in df.groupby("leg"):
        s = g.set_index(["date", "symbol"])["value"].rename("factor")
        legs[name] = s
    return legs


def rank_avg(legs: dict, names: list) -> pd.Series:
    frames = []
    for n in names:
        r = legs[n].rename("factor").reset_index()
        r.columns = ["date", "symbol", n]
        r[n] = r.groupby("date")[n].rank(pct=True)
        frames.append(r.set_index(["date", "symbol"])[n])
    wide = pd.concat(frames, axis=1)
    combo = wide.mean(axis=1, skipna=True)
    n_present = wide.notna().sum(axis=1)
    combo = combo.where(n_present >= min(2, len(names)))
    return combo.dropna().rename("factor")


def avg_spearman(a: pd.Series, b: pd.Series, min_names: int = 20) -> tuple[float, int]:
    sa = a.rename("a").reset_index(); sa.columns = ["date", "symbol", "a"]
    sb = b.rename("b").reset_index(); sb.columns = ["date", "symbol", "b"]
    m = sa.merge(sb, on=["date", "symbol"], how="inner")
    corrs = []
    for _, g in m.groupby("date"):
        if len(g) < min_names:
            continue
        rho, _ = stats.spearmanr(g["a"], g["b"])
        if rho == rho:
            corrs.append(rho)
    return (float(np.mean(corrs)) if corrs else float("nan")), len(corrs)


def eval_composite(fid: str, factor: pd.Series, panel: pd.DataFrame) -> dict:
    existing = CARDS_DIR / f"{fid}.json"
    if existing.exists():
        c = json.loads(existing.read_text(encoding="utf-8"))
        if c.get("status") == "OK":
            log(f"  RESUME {fid}")
            return c
    return evaluate(factor, HORIZON, return_basis="resid", factor_id=fid,
                     panel=panel, panel_source="real_panel_long_capstone",
                     family="INCR", write_card=True, cards_dir=CARDS_DIR)


HORIZON_YEARS = {"1M": 1 / 12, "1Y": 1.0, "5Y": 5.0}


def net_v2(card: dict) -> float:
    ann_old = card.get("long_short", {}).get("ann_return_LS", np.nan)
    cost_drag = card.get("costs", {}).get("ann_cost_drag", 0.0)
    if ann_old is None or not np.isfinite(ann_old):
        return float("nan")
    gross_v2 = (ann_old / 12.0) / HORIZON_YEARS[HORIZON]
    return gross_v2 - (cost_drag if cost_drag is not None and np.isfinite(cost_drag) else 0.0)


def summarize(fid, card):
    ic = card.get("ic", {})
    dec = card.get("deciles", {})
    return {
        "factor_id": fid, "ic_ir": ic.get("ic_ir"), "ic_mean": ic.get("ic_mean"),
        "mono": dec.get("monotonicity"), "net_v2": net_v2(card),
        "turnover": card.get("turnover", {}).get("avg_top_decile_turnover"),
        "dsr": card.get("dsr", {}).get("dsr"), "pbo": card.get("pbo", {}).get("pbo"),
        "lag_delta": card.get("lag_test", {}).get("lag_test_delta"),
        "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
        "verdict": card.get("verdict"),
    }


def main():
    log("Loading panel_long + cached capstone legs...")
    panel, close, bench = LC.load_all()
    legs = load_legs()
    log(f"panel_long: {panel.shape}, legs cached: {list(legs.keys())}")

    missing = [l for l in BASE_LEGS if l not in legs]
    if missing:
        raise RuntimeError(f"base legs missing from cache: {missing}")

    log("Evaluating BASE composite (EY + mom_resid_peer + trend_ma65_slope + quality_QMJ) at 1Y...")
    base_factor = rank_avg(legs, BASE_LEGS)
    base_card = eval_composite("INCR_BASE4_1Y", base_factor, panel)
    base_summary = summarize("INCR_BASE4_1Y", base_card)
    log(f"  BASE -> {base_summary}")

    rows = [{"leg": "BASE (EY+mom+MA65+QMJ)", **base_summary,
             "delta_ic_ir": 0.0, "delta_mono": 0.0, "delta_net_v2": 0.0,
             "corr_to_base": None, "earns_slot": "N/A (base)"}]

    for leg_col, leg_label in CANDIDATES.items():
        if leg_col not in legs:
            log(f"  SKIP {leg_col}: not in cache")
            continue
        log(f"Evaluating BASE + {leg_label} ({leg_col}) at 1Y...")
        combo_factor = rank_avg(legs, BASE_LEGS + [leg_col])
        fid = f"INCR_BASE4_plus_{leg_col}_1Y"
        card = eval_composite(fid, combo_factor, panel)
        s = summarize(fid, card)

        corr, n_dates = avg_spearman(legs[leg_col], base_factor)

        d_ic_ir = s["ic_ir"] - base_summary["ic_ir"] if s["ic_ir"] is not None and base_summary["ic_ir"] is not None else float("nan")
        d_mono = s["mono"] - base_summary["mono"] if s["mono"] is not None and base_summary["mono"] is not None else float("nan")
        d_net = s["net_v2"] - base_summary["net_v2"] if np.isfinite(s["net_v2"]) and np.isfinite(base_summary["net_v2"]) else float("nan")

        meaningful = (
            (np.isfinite(d_ic_ir) and d_ic_ir >= 0.03) or
            (np.isfinite(d_mono) and d_mono >= 0.02) or
            (np.isfinite(d_net) and d_net >= 0.01)
        )
        orthogonal = np.isfinite(corr) and abs(corr) < 0.6
        earns = bool(meaningful and orthogonal)

        row = {"leg": leg_label, **s,
               "delta_ic_ir": d_ic_ir, "delta_mono": d_mono, "delta_net_v2": d_net,
               "corr_to_base": corr, "corr_n_dates": n_dates,
               "earns_slot": earns}
        rows.append(row)
        log(f"  -> {leg_label}: dIC_IR={d_ic_ir:.4f} dMono={d_mono:.4f} dNet_v2={d_net:.4f} "
            f"corr_to_base={corr:.3f} earns_slot={earns}")

    out = pd.DataFrame(rows)
    out_path = REPORTS_DIR / "incremental_value.csv"
    out.to_csv(out_path, index=False)
    log(f"Wrote {out_path}")

    # per-leg cards (RP task deliverable: rnd/cards/INCR_*.json) --
    # the harness already wrote INCR_BASE4_1Y.json + INCR_BASE4_plus_<leg>_1Y.json
    # via write_card=True above; write one extra summary card per candidate.
    CARDS_DIR2 = RND_DIR / "cards"
    for row in rows[1:]:
        leg_col = [k for k, v in CANDIDATES.items() if v == row["leg"]][0]
        card_out = {
            "leg": row["leg"], "leg_col": leg_col, "horizon": HORIZON,
            "base_ic_ir": base_summary["ic_ir"], "with_leg_ic_ir": row["ic_ir"],
            "delta_ic_ir": row["delta_ic_ir"], "delta_mono": row["delta_mono"],
            "delta_net_v2": row["delta_net_v2"], "corr_to_base": row["corr_to_base"],
            "corr_n_dates": row.get("corr_n_dates"), "earns_slot": row["earns_slot"],
            "decision_rule": "earns_slot iff |corr_to_base|<0.6 AND (dIC_IR>=0.03 OR dMono>=0.02 OR dNet_v2>=0.01)",
        }
        (CARDS_DIR2 / f"INCR_{leg_col}_1Y.json").write_text(
            json.dumps(card_out, indent=2, default=str), encoding="utf-8")
    log("Wrote INCR_*.json cards")
    log("DONE.")


if __name__ == "__main__":
    main()
