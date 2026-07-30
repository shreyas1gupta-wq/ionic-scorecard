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
# one-off client call). Anand Reddy: the fund cost/TER slide stays pulled per-client -- per-fund
# TER in this ctx was a flat placeholder (0.55 for every fund), not researched real data, so the
# slide would show incorrect fund costs (cost.py is ALSO globally cut in engine.py as of
# 2026-07-27, making this redundant belt-and-suspenders, kept for clarity). ips_summary is no
# longer skipped here (2026-07-28): the v2 rebuild shows real live-computed Current values and
# an honest TBD/Pending treatment for a no-IPS-on-file client, so it's informative again.
for _base in ("RM_SIMPLE", "STANDARD", "HNI_DEEP"):
    _t = dict(T.TIERS[_base])
    _t["skip_core"] = set(_t.get("skip_core", set())) | {"cost"}
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
