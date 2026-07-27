# -*- coding: utf-8 -*-
"""build_anand_reddy.py — render the REAL first-client review deck.
Usage: python build_anand_reddy.py [TIER ...] (default: RM_SIMPLE)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.anand_reddy import build_ctx
import engine

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


def main(tiers_):
    ctx = build_ctx()
    sfx = os.environ.get("PR_SUFFIX", "")
    for tier in tiers_:
        deck, manifest = engine.build(ctx, tier)
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
