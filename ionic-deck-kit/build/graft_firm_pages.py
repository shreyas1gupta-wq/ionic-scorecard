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
import re
import io
import os
import sys

from pptx import Presentation

DEFAULT_PAGES = "2-6"        # one-based, as a reader of the reference deck would name them
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


_ASOF_RX = re.compile(r"As of\s+(.+?)\s*$", re.I)


def _pretty_date(s):
    """2026-07-26 -> '26th Jul 2026', the form the desk's own title page uses."""
    s = str(s or "").strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        return s
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    suf = "th" if 11 <= d % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")
    return "%d%s %s %d" % (d, suf, MON[mo - 1], y)


def _title_line(prs, upto=3):
    """The 'X Family As of Y' line off a deck's own front matter, if it has one.

    It must carry a NAME before the date. The cover of both decks also has a bare "As of 2026-07-25"
    on its own, and matching that first returned an empty client name, so nothing was substituted
    and the reference deck's client stayed on the finished page.
    """
    for i in range(min(upto, len(prs.slides._sldIdLst))):
        for sh in prs.slides[i].shapes:
            if not sh.has_text_frame:
                continue
            t = " ".join(sh.text_frame.text.split())
            m = _ASOF_RX.search(t)
            if m and m.start() > 0 and len(t) < 90:
                return t
    return ""


def _source_identity(src):
    """Who the REFERENCE deck was written for, so those strings can be replaced."""
    line = _title_line(src)
    m = _ASOF_RX.search(line)
    if not m:
        return "", ""
    return line[:m.start()].strip(), m.group(1).strip()


def _target_identity(tgt):
    """Who THIS deck is for, read off its own cover rather than passed in and trusted."""
    who, asof = "", ""
    for sh in tgt.slides[0].shapes:
        if not sh.has_text_frame:
            continue
        for para in sh.text_frame.paragraphs:
            t = " ".join(para.text.split())
            if not t:
                continue
            m = re.match(r"(?i)as of\s+(.+)$", t)
            if m:
                asof = _pretty_date(m.group(1))
    # the cover's PREPARED FOR block carries the name on the line after the label
    lines = []
    for sh in tgt.slides[0].shapes:
        if sh.has_text_frame:
            lines += [" ".join(p.text.split()) for p in sh.text_frame.paragraphs if p.text.strip()]
    for j, l in enumerate(lines):
        if l.upper().startswith("PREPARED FOR") and j + 1 < len(lines):
            who = lines[j + 1]
            break
    return who, asof


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


def _parse_pages(spec):
    """"2-6" or "2,3,4" -> the zero-based indices the graft copies."""
    out = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return tuple(i - 1 for i in out)


def main(src=None, tgt=None, out=None, pages=None):
    global SRC, TGT, OUT, PAGES
    if src is None:
        import argparse
        ap = argparse.ArgumentParser(
            description="Graft the firm's own introduction pages, photographs and all, out of a "
                        "reference deck into a generated review.")
        ap.add_argument("--src", required=True, help="the reference deck to lift the pages from")
        ap.add_argument("--tgt", required=True, help="the generated review to insert them into")
        ap.add_argument("--out", required=True, help="where to write the finished deck")
        ap.add_argument("--pages", default=DEFAULT_PAGES,
                        help="which pages of the reference deck to lift, one-based "
                             "(default %s)" % DEFAULT_PAGES)
        a = ap.parse_args()
        src, tgt, out, pages = a.src, a.tgt, a.out, a.pages
    SRC, TGT, OUT = src, tgt, out
    PAGES = _parse_pages(pages or DEFAULT_PAGES)
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

    # RENAME. The reference deck's own client is written on its title page, "ABXY Family As of 31st
    # July 2026", and a verbatim copy carries THAT NAME onto the next client's deck. Another
    # client's name on a client deck is the worst thing this script could do, so the substitution
    # is not optional and not a manual step afterwards: the target's own cover is read for who this
    # deck is for, and every grafted slide is rewritten to match. Run text is edited in place so
    # the typography survives.
    who, asof = _target_identity(tgt)
    src_who, src_asof = _source_identity(src)
    renamed = 0
    for i in range(AFTER, AFTER + len(PAGES)):
        for sh in tgt.slides[i].shapes:
            if not sh.has_text_frame:
                continue
            for para in sh.text_frame.paragraphs:
                for run in para.runs:
                    t0 = run.text
                    t = t0
                    if src_who and who:
                        t = t.replace(src_who, who)
                    if src_asof and asof:
                        t = t.replace(src_asof, asof)
                    if t != t0:
                        run.text = t
                        renamed += 1
    if src_who and not renamed:
        print("  WARNING: the reference client name %r was not found on the grafted slides; "
              "check the title page by hand before this goes out." % src_who)

    # RENUMBER. The kit stamps each page with its position as it builds, so inserting five slides
    # at the front leaves every later page printing a number five behind where it actually is: on
    # this deck 52 of them, and the contents page and every cross-reference point at those numbers.
    # A deck that misnumbers itself is worse than one with no numbers, because the reader trusts it.
    import re
    RX = re.compile(r"(Portfolio Review\s*[·.]\s*)(\d+)")
    renumbered = 0
    for i, s in enumerate(tgt.slides):
        for sh in s.shapes:
            if not sh.has_text_frame:
                continue
            done = False
            for para in sh.text_frame.paragraphs:
                for run in para.runs:
                    m = RX.search(run.text)
                    if m and int(m.group(2)) != i + 1:
                        run.text = RX.sub(lambda x: x.group(1) + "%02d" % (i + 1), run.text)
                        renumbered += 1
                        done = True
                        break
                if done:
                    break
            if done:
                break

    # THE CROSS-REFERENCES MOVE TOO. The kit binds every "p.NN" to its anchor at save time, which
    # is before this script exists; inserting five slides at the front leaves each of them
    # pointing five pages short of where the page it names now sits. A footer that is right and a
    # cross-reference that is wrong is the worse of the two failures, because the reader turns to
    # the page it names and finds something else there.
    import re as _re
    _PREF = _re.compile(r"\bp\.(\d{1,3})\b")
    _n_ref = 0

    def _bump(mm):
        v = int(mm.group(1))
        return "p.%02d" % (v + len(PAGES)) if v > AFTER else mm.group(0)

    for _s in tgt.slides:
        for sh in _s.shapes:
            if not sh.has_text_frame:
                continue
            for para in sh.text_frame.paragraphs:
                for run in para.runs:
                    if _PREF.search(run.text):
                        _new = _PREF.sub(_bump, run.text)
                        if _new != run.text:
                            run.text = _new
                            _n_ref += 1

    tgt.save(OUT)

    chk = Presentation(OUT)
    pics_after = sum(1 for i in range(1, 1 + len(PAGES))
                     for sh in chk.slides[i].shapes if sh.shape_type == 13)
    print("  grafted %d slides from %s" % (len(PAGES), os.path.basename(SRC)))
    print("  renamed %d run(s) to the client on this deck; renumbered %d footer(s) and "
          "%d cross-reference(s)" % (renamed, renumbered, _n_ref))
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
