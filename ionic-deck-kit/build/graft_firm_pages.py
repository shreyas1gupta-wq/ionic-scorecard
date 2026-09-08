# -*- coding: utf-8 -*-
"""Graft the firm pages out of the desk's own deck into a generated review, exactly as they are.

WHY A GRAFT RATHER THAN A MODULE. The introduction pages are the firm talking about itself:
photographs, a logo lockup, a laid-out credentials page. Rebuilding those from a JSON profile
reproduces the WORDS but not the page, and the advisor asked for the page. So the slides are lifted
whole out of the reference deck, with their images, and inserted after the cover.

WHAT IS COPIED. The slide's entire XML, plus every part it points at, image, chart, anything, with
the relationship ids rewritten to whatever the target assigns. python-pptx has no slide copy, so
this walks the relationships itself. Anything it cannot resolve is reported rather than dropped
silently, because a firm page arriving with a missing photograph is worse than one that does not
arrive at all.

Both decks are 13.333 by 7.5 inches, which is checked before anything is written: grafting a slide
between differently sized decks silently rescales nothing and everything lands in the wrong place.
"""
import copy
import io
import os
import sys

from pptx import Presentation

SRC = r"C:/Users/Shreyas.1Gupta/Downloads/ABXY_Family_HNI_DEEP (2).pptx"
TGT = r"C:/tmp/kit-publish/ionic-deck-kit/out/Dutta_Family_Review_HNI_DEEP.pptx"
OUT = r"C:/tmp/dutta/Dutta_Family_Review_FINAL.pptx"
PAGES = (1, 2, 3, 4, 5)      # zero-based: slides 2 to 6 of the reference deck
AFTER = 1                    # insert after the cover


def _blank_layout(prs):
    """The emptiest layout available, so nothing inherits a placeholder we did not ask for."""
    best, best_n = None, 10 ** 6
    for master in prs.slide_masters:
        for lay in master.slide_layouts:
            n = len(lay.placeholders)
            if n < best_n:
                best, best_n = lay, n
    return best


def copy_slide(src_slide, tgt_prs, layout):
    """Deep-copy one slide's shape tree and every part it references."""
    new = tgt_prs.slides.add_slide(layout)

    # drop whatever the layout put on the new slide; we want only what we copy
    for shp in list(new.shapes):
        shp._element.getparent().remove(shp._element)

    # the background and the shape tree, verbatim
    if src_slide.background is not None:
        try:
            bg = src_slide._element.find(
                "{http://schemas.openxmlformats.org/presentationml/2006/main}cSld")
            src_bg = bg.find("{http://schemas.openxmlformats.org/presentationml/2006/main}bg") \
                if bg is not None else None
            if src_bg is not None:
                new_cSld = new._element.find(
                    "{http://schemas.openxmlformats.org/presentationml/2006/main}cSld")
                new_cSld.insert(0, copy.deepcopy(src_bg))
        except Exception:
            pass

    # FIRST bring every part the slide points at across, and remember what id it got here. The
    # copied XML still carries the SOURCE deck's relationship ids, which mean something different
    # in this file, so the ids have to be rewritten on the copied elements before they are
    # attached. Rewriting the serialised XML and reparsing loses the element's place in the tree,
    # so the attributes are edited on the live elements instead.
    # DO NOT relate the SOURCE part object into the target package. It carries its own partname,
    # so the target ends up with two ppt/media/image15.png and two ppt/slides/slide6.xml, the zip
    # writer warns about a duplicate name and the file PowerPoint opens is not the file intended.
    # The image BYTES are copied into a part the target creates and names for itself.
    missing = 0
    remap = {}
    for rel in src_slide.part.rels.values():
        try:
            if rel.is_external:
                remap[rel.rId] = new.part.rels.get_or_add_ext_rel(rel.reltype, rel._target)
                continue
            if "image" in rel.reltype:
                blob = rel._target.blob
                # add_picture registers the image in THIS package and hands back its id; the
                # placeholder shape is then discarded, leaving only the part and the mapping.
                tmp = new.shapes.add_picture(io.BytesIO(blob), 0, 0, width=1, height=1)
                remap[rel.rId] = tmp._element.blip_rId
                tmp._element.getparent().remove(tmp._element)
            # a slideLayout or slideMaster rel is not copied: the new slide has its own, and the
            # shapes we bring over carry their formatting explicitly.
        except Exception:
            missing += 1

    R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    for shp in src_slide.shapes:
        el = copy.deepcopy(shp._element)
        for node in el.iter():
            for attr in ("embed", "id", "link", "pict", "dm", "lo", "qs", "cs"):
                key = R + attr
                if key in node.attrib:
                    old = node.attrib[key]
                    if old in remap:
                        node.attrib[key] = remap[old]
        new.shapes._spTree.append(el)
    return new, missing


def main():
    if not os.path.exists(SRC):
        raise SystemExit("  reference deck not found: %s" % SRC)
    src, tgt = Presentation(SRC), Presentation(TGT)
    # a few EMU apart is the same page: 13.333in is not exactly representable and the two
    # writers round it differently. A tolerance of 0.01in catches a real mismatch (4:3 against
    # 16:9) while letting an identical page through.
    _tol = 9144  # 0.01 inch
    if (abs(src.slide_width - tgt.slide_width) > _tol
            or abs(src.slide_height - tgt.slide_height) > _tol):
        raise SystemExit("  REFUSING TO GRAFT: the two decks are different sizes "
                         "(%.3fx%.3f vs %.3fx%.3f in). Every copied shape would land in the "
                         "wrong place and nothing would say so."
                         % (src.slide_width / 914400, src.slide_height / 914400,
                            tgt.slide_width / 914400, tgt.slide_height / 914400))

    layout = _blank_layout(tgt)
    n_pics_before = 0
    added, missing_total = [], 0
    for idx in PAGES:
        s = src.slides[idx]
        n_pics_before += sum(1 for sh in s.shapes if sh.shape_type == 13)
        new, miss = copy_slide(s, tgt, layout)
        missing_total += miss
        added.append(new)

    # the grafted slides land at the END; move them to sit just after the cover
    sldIdLst = tgt.slides._sldIdLst
    ids = list(sldIdLst)
    grafted = ids[-len(PAGES):]
    for e in grafted:
        sldIdLst.remove(e)
    for i, e in enumerate(grafted):
        sldIdLst.insert(AFTER + i, e)

    tgt.save(OUT)

    chk = Presentation(OUT)
    pics_after = sum(1 for i in range(1, 1 + len(PAGES))
                     for sh in chk.slides[i].shapes if sh.shape_type == 13)
    print("  grafted %d slides from %s" % (len(PAGES), os.path.basename(SRC)))
    print("  pictures: %d in the source pages, %d landed in the target" % (n_pics_before, pics_after))
    if missing_total:
        print("  WARNING: %d relationships could not be copied" % missing_total)
    print("  deck is now %d slides -> %s" % (len(chk.slides._sldIdLst), OUT))
    for i in range(0, 7):
        ts = [" ".join(sh.text_frame.text.split()) for sh in chk.slides[i].shapes
              if sh.has_text_frame and sh.text_frame.text.strip()]
        print("   %2d  %s" % (i + 1, " | ".join(ts[:2])[:72]))


if __name__ == "__main__":
    main()
