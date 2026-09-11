# -*- coding: utf-8 -*-
"""Does this deck have the pages the desk's standard review has?

    python qa/check_structure.py out/<Client>_Review_FINAL.pptx

WHY THIS EXISTS. "Make it look like the sample" is an opinion until it is a test. The reference
review is 34 pages in a settled order; this kit grew its own order module by module, and the two
had drifted without anyone being able to say by how much. STANDARD_STRUCTURE.json is that order,
read off the reference deck rather than invented, and this gate reports three things:

    PRESENT   the page is in the built deck, matched on the words its title actually uses
    MISSING   the standard has it and the deck does not, with what is needed to produce it
    ORDER     it is present but out of sequence against the standard

A MISSING page is not automatically a defect. Several standard pages need an input this pipeline is
not given - the client's own circumstances, the month's AssetX, the firm's product content, the
approved product list - and for those the honest state is absent, not invented. So this gate
REPORTS and does not fail: it exists to make the gap visible and countable, and to stop it drifting
further. What it must never do is let a page go missing silently, which is what happened until it
was written.
"""
import json
import os
import re
import sys

from pptx import Presentation

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "STANDARD_STRUCTURE.json")


# The header band. Every content page in this template puts its eyebrow and title above this
# line and nothing else there, so reading only this band identifies the page.
HEADER_BOTTOM_EMU = int(1.75 * 914400)


def _titles(path):
    """One lowercase HEADER blob per slide, in order.

    THE HEADER, NOT THE WHOLE SLIDE. Reading all of a slide's text found every page on the
    contents page, which lists every section title by design - so the first run of this gate
    reported the market-cap page as present on slide 3 and nine pages as "out of order" when
    nothing was. A page is identified by its own heading.
    """
    prs = Presentation(path)
    out = []
    for s in prs.slides:
        parts = []
        for sh in s.shapes:
            if not sh.has_text_frame or not sh.text_frame.text.strip():
                continue
            if sh.top is None or sh.top <= HEADER_BOTTOM_EMU:
                parts.append(" ".join(sh.text_frame.text.split()))
        out.append(" | ".join(parts).lower())
    return out


def main():
    if len(sys.argv) < 2:
        print("usage: check_structure.py <deck.pptx>")
        return 2
    deck = sys.argv[1]
    if not os.path.exists(deck):
        print("  no such deck: %s" % deck)
        return 2
    spec = json.load(open(SPEC, encoding="utf-8"))
    slides = _titles(deck)

    print("\n  %s" % os.path.basename(deck))
    print("  against %s (%d standard pages, %d slides built)\n"
          % (spec["reference"], len(spec["pages"]), len(slides)))

    found, missing, order = [], [], []
    for pg in spec["pages"]:
        # THE COVER IS SLIDE 1 BY DEFINITION. Matched on words it found the LAST slide whose
        # header happens to say "portfolio review" - slide 65 - and every other page then read as
        # coming before the cover, which produced 27 bogus inversions and no useful signal.
        if pg.get("first_slide"):
            if slides:
                found.append((pg, 0))
            continue
        pats = [p.lower() for p in (pg.get("match") or [])]
        at = None
        for i, blob in enumerate(slides):
            # A DIVIDER IS NOT THE PAGE IT LISTS. Section dividers print the titles of every page
            # in their section, so matching on words alone finds the divider first and reports a
            # page as present when only its name is. A divider says SECTION and is skipped.
            # A divider lists every page in its section; the contents page lists every section.
            # Neither IS the page whose name it carries.
            if re.search(r"\bsection\s*0?\d", blob) or "how to read this review" in blob:
                continue
            if any(p in blob for p in pats):
                at = i
                break
        if at is None:
            if not pg.get("optional"):
                missing.append(pg)
            continue
        found.append((pg, at))

    for pg, at in found:
        print("    ok       slide %-3d %s" % (at + 1, pg["title"]))
    # ORDER IS A PAIRWISE QUESTION, NOT A RUNNING MAXIMUM. Comparing each page against the
    # highest slide seen so far flagged twelve pages as out of order on a deck whose sequence was
    # correct: one page legitimately earlier than the reference puts it makes every later page
    # look displaced. An inversion is a PAIR the deck has in the opposite order to the standard.
    for i in range(len(found)):
        for j in range(i + 1, len(found)):
            if found[j][1] < found[i][1]:
                order.append((found[i][0], found[j][0]))
    if order:
        print()
        for a_pg, b_pg in order[:8]:
            print("    order    \"%s\" comes after \"%s\" here; the standard has it before"
                  % (b_pg["title"], a_pg["title"]))
        if len(order) > 8:
            print("             ... and %d more inverted pair(s)" % (len(order) - 8))
    if missing:
        print()
        for pg in missing:
            print("    MISSING  %s" % pg["title"])
            print("             module: %s" % pg.get("module", "-"))
            if pg.get("needs"):
                print("             needs : %s" % pg["needs"])

    print("\n  %d of %d standard pages present; %d missing, %d inverted pair(s)."
          % (len(found), len([p for p in spec["pages"] if not p.get("optional")]),
             len(missing), len(order)))
    if not order:
        print("  The pages it does carry are in the standard's order.")
    if missing:
        _blocked = [p for p in missing if not p.get("needs")]
        if _blocked:
            print("  %d of the missing pages need NO new input and are simply not written yet: %s"
                  % (len(_blocked), ", ".join(p["title"] for p in _blocked)))
    # REPORTS, NEVER FAILS. See the module docstring: absent-for-want-of-an-input is an honest
    # state and a build must not be blocked for it.
    return 0


if __name__ == "__main__":
    sys.exit(main())
