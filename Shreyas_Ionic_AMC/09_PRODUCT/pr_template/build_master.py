# -*- coding: utf-8 -*-
"""build_master.py — ONE master library pptx: every template slide (full HNI_DEEP superset)
+ the whole chart library + a style/component reference. -> out/AZBY_MASTER_LIBRARY.pptx"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.azby_family import build_ctx
import engine
from gallery import add_chart_gallery, add_style_reference

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)


def main():
    ctx = build_ctx()
    deck, manifest = engine.build(ctx, "HNI_DEEP", verbose=False)   # all 38 templates in context
    module_slides = sum(c for _, c in manifest)
    g = add_chart_gallery(deck)                                     # every graph
    y = add_style_reference(deck)                                   # palette / pills / tables
    sfx = os.environ.get("PR_SUFFIX", "")
    path = os.path.join(OUT, f"NDPMS_TEMPLATE_MASTER{sfx}.pptx")
    deck.save(path)
    total = len(deck.prs.slides)
    print(f"MASTER LIBRARY: {total} slides -> {path}")
    print(f"  · {module_slides} template slides (all 38 modules, HNI_DEEP superset)")
    print(f"  · {g - 1} chart-gallery graphics + 1 divider")
    print(f"  · {y} style/component reference slides")


if __name__ == "__main__":
    main()
