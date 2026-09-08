# The firm's introduction pages

Slides 2 to 6 are the firm talking about itself: photographs, a logo lockup, a laid-out credentials
page, the co-founders, the moat, the asset-class view.

## Why they are grafted and not generated

Rebuilding them from `firm_profile.json` reproduces the **words** but not the page. The advisor
asked for the page. So the slides are lifted whole out of a reference deck, with their images, and
inserted after the cover.

`modules/firm_intro.py` exists and renders the same content from JSON. It is **off by default** and
is the fallback for a build with no reference deck to hand. Where a reference deck exists, graft.

```bash
PYTHONIOENCODING=utf-8 "$PY" build/graft_firm_pages.py \
    --src "<reference deck>" --tgt "out/<Client>_Review_HNI_DEEP.pptx" \
    --out "<Client>_Review_FINAL.pptx" [--pages 2-6]
```

## What the graft does

**Copies the whole shape tree plus every part it references**, with relationship ids rewritten to
whatever the target assigns. python-pptx has no slide copy, so it walks the relationships itself.
Anything it cannot resolve is **reported**, not dropped silently - a firm page arriving with a
missing photograph is worse than one that does not arrive.

**Copies image BYTES, never the source part object.** A source part carries its own partname, so
relating it into the target produces two `ppt/media/image15.png` and two `ppt/slides/slide6.xml`,
the zip writer warns about a duplicate name, and the file PowerPoint opens is not the file intended.
`add_picture` registers the image in the target package and hands back its own id.

**Refuses to run if the two decks are different sizes.** Both are 13.333 x 7.5 inches. Grafting
between differently sized decks silently rescales nothing and everything lands in the wrong place.
Tolerance is 0.01 inch, because 13.333in is not exactly representable and the two writers round it
differently.

## Renaming, which is not optional

The reference deck's own client is written on its title page. A verbatim copy carries **that
client's name onto the next client's deck**, which is the worst thing this script could do.

The target's own cover is read for who this deck is for, and every grafted slide is rewritten to
match. Run text is edited in place so the typography survives.

**The title-line matcher must require a name before the date.** Both decks' covers carry a bare
`As of 2026-07-25` on its own; matching that first returned an empty client name, nothing was
substituted, and the reference client stayed on the finished page. The fix is `m.start() > 0`.

If the reference client's name is not found on any grafted slide, the script **warns**. Do not
ignore that warning.

## Renumbering, which is also not optional

The kit stamps each page with its position as it builds and binds every `p.NN` cross-reference to
its anchor at save time - both before this script exists. Inserting five slides at the front leaves:

- every later footer printing a number five behind where the page actually is (52 of them on one
  deck), and
- every cross-reference pointing five pages short of the page it names.

Both are renumbered here. A footer that is right and a cross-reference that is wrong is the worse of
the two failures, because the reader turns to the page it names and finds something else.

## The gates will fire on these pages

Slides 2 to 6 are another firm's layout, lifted verbatim. `check_geometry`, `check_geometry2` and
`tellscan` will report pic-over-text, under-image, text-overlap, spill-bounds, em-dashes and a
`QFRA` mention on them. **Those are expected and out of scope**: re-laying them would be exactly the
rebuild the advisor rejected.

Filter them when you read a gate:

```bash
PYTHONIOENCODING=utf-8 "$PY" check_geometry2.py "<deck>" | grep -v "'slide': [1-6][,}]"
```

**Any finding on slide 7 or later is a defect.**
