# -*- coding: utf-8 -*-
"""build_anand_reddy.py — render the REAL first-client review deck.
Usage: python build_anand_reddy.py [TIER ...] (default: RM_SIMPLE)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.anand_reddy import build_ctx
import engine
import tiers as T

# Client-specific tier variants, registered at runtime (never edit the shared tiers.py for a
# one-off client call). Anand Reddy (2026-07-27): (1) the fund cost/TER slide is pulled --
# per-fund TER in this ctx was a flat placeholder (0.55 for every fund), not researched real
# data, so the slide would show incorrect fund costs; (2) the IPS-summary slide is pulled --
# there is no real IPS for this first-review client, and a page that just says "not yet on
# file" repeatedly reads as broken/incomplete rather than informative (ctx['ips'] itself is
# untouched, other modules that reference it -- exec_summary, concentration_risk, snapshot --
# already handle the no-IPS case honestly).
for _base in ("RM_SIMPLE", "STANDARD", "HNI_DEEP"):
    _t = dict(T.TIERS[_base])
    _t["skip_core"] = set(_t.get("skip_core", set())) | {"cost", "ips_summary"}
    T.TIERS[f"ANANDREDDY_{_base}"] = _t

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


def main(tiers_):
    ctx = build_ctx()
    sfx = os.environ.get("PR_SUFFIX", "")
    for tier in tiers_:
        deck, manifest = engine.build(ctx, f"ANANDREDDY_{tier}")
        path = os.path.join(OUT, f"AnandReddy_{tier}{sfx}.pptx")
        for attempt in range(3):
            try:
                deck.save(path)
                break
            except PermissionError:
                path = path.replace(".pptx", "_v2.pptx") if attempt == 0 else path.replace(f"_v{attempt+1}.pptx", f"_v{attempt+2}.pptx")
        n = sum(c for _, c in manifest)
        print(f"\n=== {tier}: {n} slides -> {path}")
        for mid, c in manifest:
            print(f"    {mid}  x{c}")


if __name__ == "__main__":
    tiers_ = sys.argv[1:] or ["RM_SIMPLE"]
    main(tiers_)
