# -*- coding: utf-8 -*-
"""build_abxy_showcase.py — render the ABXY Family SHOWCASE deck (aggressive IPS, demo-
labelled) for the Product Approval Committee / CEO review.
Usage: python build_abxy_showcase.py [TIER ...]   (default: HNI_DEEP)   -> ./out/
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.abxy_showcase import build_ctx
import engine

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


def main(tiers_):
    ctx = build_ctx()
    sfx = os.environ.get("PR_SUFFIX", "")
    for tier in tiers_:
        deck, manifest = engine.build(ctx, tier)
        path = os.path.join(OUT, f"ABXY_Showcase_{tier}{sfx}.pptx")
        for attempt in range(3):
            try:
                deck.save(path)
                break
            except PermissionError:
                path = path.replace(".pptx", f"_v{attempt + 2}.pptx")
        n = sum(c for _, c in manifest)
        print(f"\n=== {tier}: {n} slides -> {path}")
        for mid, c in manifest:
            print(f"    {mid}  x{c}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["HNI_DEEP"])
