# -*- coding: utf-8 -*-
"""mf_sell_score_sensitivity.py — the substitute for a backtest (FM #17, Principal 2026-08-06:
"we cannot backtest this"). Sweeps every numeric parameter in mf_sell_score.CONFIG and
core_satellite.CONFIG +-20% against a real book and counts how many Sell/Discretion/Hold band
calls move. A parameter whose +-20% swing changes nothing is not worth arguing about; one that
flips many calls needs the FM's sign-off before this ships against a real client.

[INFERENCE]: this run is against the ABXY demo book (data/azby_family.py, 11 funds, SYNTHETIC —
see that file's own header). The SHAPE and DIRECTION of each parameter's sensitivity is
informative; exact counts should be re-run once a real ACE-matched client book flows through this
module — there is no trading history to size these numbers against (that is the whole reason this
script exists instead of a backtest), only a real portfolio to test them on.

Run: python mf_sell_score_sensitivity.py
     PYTHONIOENCODING=utf-8 "<python>" mf_sell_score_sensitivity.py
Writes: 09_PRODUCT/pr_template/out/mf_sell_score_sensitivity.csv
"""
import os
import sys
import csv as _csv

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PRT = os.path.abspath(os.path.join(_SCRIPTS_DIR, "..", "pr_template"))
if _PRT not in sys.path:
    sys.path.insert(0, _PRT)

from data import azby_family          # noqa: E402  (demo book — see module docstring)
from lib import mf_sell_score as S    # noqa: E402
from lib import core_satellite as C   # noqa: E402

OUT_CSV = os.path.join(_PRT, "out", "mf_sell_score_sensitivity.csv")
PERTURB = (("-20%", 0.8), ("+20%", 1.2))


def _bands(cfg):
    """Fresh ctx every call — score_all() mutates fund dicts in place, and a fresh build is
    cheap and removes any doubt about cross-run contamination."""
    ctx = azby_family.build_ctx()
    summary = S.score_all(ctx, cfg=cfg)
    bands = {f["name"]: (f["sell_score"]["band"] if f["sell_score"] else "gated") for f in ctx["funds"]}
    return bands, summary


def sweep_mf_sell_score():
    baseline, base_summary = _bands(S.CONFIG)
    rows = []
    for key, val in S.CONFIG.items():
        if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
            continue
        for direction, mult in PERTURB:
            cfg2 = dict(S.CONFIG)
            new_val = val * mult
            if key.endswith("_YEARS") or key.endswith("_HORIZONS"):
                new_val = max(1, int(round(new_val)))  # whole-number params stay whole numbers
            cfg2[key] = new_val
            perturbed, _ = _bands(cfg2)
            n_changed = sum(1 for k in baseline if baseline[k] != perturbed.get(k))
            rows.append({"module": "mf_sell_score", "parameter": key,
                         "baseline_value": val, "direction": direction,
                         "perturbed_value": round(new_val, 4) if isinstance(new_val, float) else new_val,
                         "n_funds_total": len(baseline), "n_band_changes": n_changed,
                         "pct_changed": round(100.0 * n_changed / len(baseline), 1) if baseline else 0.0})
    return rows, baseline, base_summary


def sweep_core_satellite():
    ctx = azby_family.build_ctx()
    base = C.book_split(ctx["funds"])
    rows = []
    for key in ("TARGET_CORE_PCT", "BAND_PP"):
        val = C.CONFIG[key]
        for direction, mult in PERTURB:
            cfg2 = dict(C.CONFIG)
            cfg2[key] = val * mult
            res = C.book_split(ctx["funds"], cfg=cfg2)
            flipped = res["within_guidance_band"] != base["within_guidance_band"]
            rows.append({"module": "core_satellite", "parameter": key, "baseline_value": val,
                         "direction": direction, "perturbed_value": round(cfg2[key], 2),
                         "n_funds_total": len(ctx["funds"]), "n_band_changes": int(flipped),
                         "pct_changed": (f"within_guidance_band flips to {res['within_guidance_band']}"
                                         if flipped else "no flip")})
    # the #1 midcap correction itself, quantified on this book (not a +-20% nudge -- a straight
    # "what if we hadn't corrected it" comparison, since that correction is a category
    # membership, not a continuous number)
    cfg_reversed = dict(C.CONFIG)
    cfg_reversed["CORE_CATEGORIES"] = frozenset(C.CONFIG["CORE_CATEGORIES"] - {"mid"})
    cfg_reversed["SATELLITE_KEYWORDS"] = C.CONFIG["SATELLITE_KEYWORDS"] + ("mid",)
    res_rev = C.book_split(ctx["funds"], cfg=cfg_reversed)
    rows.append({"module": "core_satellite", "parameter": "CORE_CATEGORIES (midcap membership)",
                 "baseline_value": "mid=core (ruling)", "direction": "reverse the #1 correction",
                 "perturbed_value": "mid=satellite",
                 "n_funds_total": len(ctx["funds"]), "n_band_changes": "n/a",
                 "pct_changed": f"core% {base['core_pct']}->{res_rev['core_pct']}, "
                                f"gap_pp {base['gap_pp']}->{res_rev['gap_pp']}"})
    return rows, base


def main():
    rows1, baseline, base_summary = sweep_mf_sell_score()
    rows2, cs_base = sweep_core_satellite()
    all_rows = rows1 + rows2

    print(f"BASELINE — ABXY demo book, [INFERENCE] synthetic, n={len(baseline)} funds:")
    print(f"  sell_score bands: sell={base_summary['n_sell']} discretion={base_summary['n_discretion']} "
          f"hold={base_summary['n_hold']} gated={base_summary['n_gated']} no_score={base_summary['n_no_score']}")
    print(f"  escalations raised: {len(base_summary['escalations'])}")
    print(f"  core/satellite: {cs_base['core_pct']}% core vs {cs_base['target_core_pct']}% target "
          f"(gap {cs_base['gap_pp']}pp, within guidance band: {cs_base['within_guidance_band']})")
    print()
    header = ["module", "parameter", "baseline_value", "direction", "perturbed_value",
              "n_funds_total", "n_band_changes", "pct_changed"]
    widths = [14, 24, 16, 10, 14, 8, 8, 44]
    print(" | ".join(h.ljust(w) for h, w in zip(header, widths)))
    for r in all_rows:
        print(" | ".join(str(r[h]).ljust(w) for h, w in zip(header, widths)))

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nWritten: {OUT_CSV}")


if __name__ == "__main__":
    main()
