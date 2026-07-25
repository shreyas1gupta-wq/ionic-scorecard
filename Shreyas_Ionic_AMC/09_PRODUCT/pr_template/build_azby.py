# -*- coding: utf-8 -*-
"""build_azby.py — render the AZBY Family demo across tiers.
Usage: python build_azby.py [TIER ...]   (default: all three)  ·  outputs to ./out/
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.azby_family import build_ctx
import engine

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


def main(tiers_):
    ctx = build_ctx()
    for tier in tiers_:
        deck, manifest = engine.build(ctx, tier)
        path = os.path.join(OUT, f"ABXY_Family_{tier}.pptx")
        deck.save(path)
        n = sum(c for _, c in manifest)
        print(f"\n=== {tier}: {n} slides -> {path}")
        for mid, c in manifest:
            print(f"    {mid}  x{c}")


if __name__ == "__main__":
    tiers_ = sys.argv[1:] or ["HNI_DEEP", "STANDARD", "RM_SIMPLE"]
    main(tiers_)
