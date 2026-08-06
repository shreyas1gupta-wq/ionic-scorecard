# -*- coding: utf-8 -*-
"""Export chosen slides of a PPTX to PNG, for the mandatory visual QA gate.

The geometry and tell scanners read the XML; they cannot see a chip whose label overflows its shape,
a colour that vanishes against its background, or two shapes that collide only once PowerPoint has
laid out the text. Only looking at the rendered page catches those. Until now the only route was a
full-deck PDF, which needs poppler to view -- absent on this machine -- so a "visual check" step
existed with no way to perform it. This closes that.

  python pptx_slide_png.py <deck.pptx> 25            one slide
  python pptx_slide_png.py <deck.pptx> 25,26,30       several
  python pptx_slide_png.py <deck.pptx> 25-28          a range

Writes <deck-stem>_sNN.png beside the deck. Windows + MS PowerPoint, same COM backend pptx_to_pdf.py
already relies on.
"""
import os
import sys


def _slides(spec):
    out = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part.lstrip("-"):
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def export(src, spec, width=2400):
    src = os.path.abspath(src)
    if not os.path.exists(src):
        print(f"missing: {src}")
        return 2
    want = _slides(spec)
    stem = os.path.splitext(src)[0]
    try:
        import comtypes.client as cc
    except ImportError:
        print("comtypes not installed:  pip install comtypes")
        return 3

    ppt = pres = None
    written = []
    try:
        ppt = cc.CreateObject("PowerPoint.Application")
        # NOTE: no `ppt.Visible = False`. PowerPoint's automation interface rejects that assignment
        # (it will not run fully hidden), and setting it raises rather than being ignored. Opening the
        # presentation WithWindow=False is the supported way to keep it off-screen.
        pres = ppt.Presentations.Open(src, ReadOnly=True, WithWindow=False)
        n = pres.Slides.Count
        # 16:9 at 13.333in wide -> height follows the deck's own aspect, never a hardcoded 1080
        h = int(round(width * pres.PageSetup.SlideHeight / pres.PageSetup.SlideWidth))
        for i in want:
            if not 1 <= i <= n:
                print(f"  slide {i} out of range (deck has {n})")
                continue
            dst = f"{stem}_s{i:02d}.png"
            pres.Slides(i).Export(dst, "PNG", width, h)
            written.append(dst)
            print(f"OK  {dst}  ({width}x{h})")
    except Exception as e:                                  # COM surfaces everything as generic
        print(f"COM error: {e}")
        return 1
    finally:
        try:
            if pres is not None:
                pres.Close()
        except Exception:
            pass
        try:
            if ppt is not None:
                ppt.Quit()
        except Exception:
            pass
    return 0 if written else 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(export(sys.argv[1], sys.argv[2],
                    width=int(sys.argv[3]) if len(sys.argv) > 3 else 2400))
