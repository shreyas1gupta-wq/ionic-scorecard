# -*- coding: utf-8 -*-
"""build_talaulikar.py — render the Talaulikar family NDPMS review deck.
Usage: python build_talaulikar.py [TIER ...] (default: HNI_DEEP)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.talaulikar_family import build_ctx
import engine
import tiers as T

for _base in ("RM_SIMPLE", "STANDARD", "HNI_DEEP"):
    _t = dict(T.TIERS[_base])
    _t["skip_core"] = set(_t.get("skip_core", set())) | {"cost"}
    T.TIERS[f"TALAULIKAR_{_base}"] = _t

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


def main(tiers_):
    ctx = build_ctx()
    sfx = os.environ.get("PR_SUFFIX", "")
    for tier in tiers_:
        deck, manifest = engine.build(ctx, f"TALAULIKAR_{tier}")
        path = os.path.join(OUT, f"Talaulikar_{tier}{sfx}.pptx")
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
    tiers_ = sys.argv[1:] or ["HNI_DEEP"]
    main(tiers_)
