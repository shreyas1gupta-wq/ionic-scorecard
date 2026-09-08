# The gates, and what each of them cannot see

Run all three, in order, every time. Then read the pages you changed - **no gate can see a page.**

```bash
cd Shreyas_Ionic_AMC/09_PRODUCT/pr_template
for g in check_geometry.py check_geometry2.py tellscan.py; do
  PYTHONIOENCODING=utf-8 "$PY" $g "<deck>.pptx"
done
```

## check_geometry.py / check_geometry2.py

Read PowerPoint **shape geometry**: boxes off the slide, boxes overlapping, text estimated to
overflow the box it is in, text under an image.

| finding | what it means |
|---|---|
| `possible-overflow` / `clip-risk` | the text is longer than the box can show |
| `text-collision` / `text-overlap` | two boxes occupy the same space |
| `spill-bounds` | a box extends past the slide edge |
| `pic-over-text` / `under-image` | text is behind an image |

**Overflow is invisible in PowerPoint's own view.** A caveat written into the overflow is a caveat
the reader never sees while the deck looks completely finished. This is the single most common way
a page ships wrong.

**What they cannot see:**
- anything inside a **chart image**. Every chart is a rendered PNG; the gate sees a picture.
- whether a number is *right*.
- whether two pages contradict each other.
- whether a table row is empty, only whether it overlaps something.

## tellscan.py

Reads the deck's text for things that must never reach a client page.

| bucket | examples |
|---|---|
| AI writing tells | em-dash, "genuinely", "robust", "holistic" |
| internal jargon | SENTINEL, QFRA, MERIT, `pf_qual`, "Ratified Sell", "House decision" |
| data-QA vocabulary | "stale", "does not reconcile", "data feed", "data cut" |
| source and analyst citations | screener.in, INDmoney, Groww, Advisorkhoj, an analyst's name |
| raw field names | `asset_class`, `hit_rate`, `trim_to_pct` |
| mislabelled real data | "synthetic", "demo", "illustrative" on a real client book |

A small false-positive rate on ordinary English is expected.

**It only reads PowerPoint.** The holdings workbook is a client artefact and this gate cannot see
it. The workbook shipped the framework's internal name in 24 rationale cells and raw field names as
column headings before anyone noticed. Scrub the workbook by hand, or in the build.

## The cross-page consistency check, which has no script

Any two numbers a reader will assume are the same set **must reconcile or be explicitly scoped.**
This is where the real defects live, and it is a human or agent pass.

Check every time:

1. **Every count of a call.** The executive summary, the fund book's closing read, the fund-actions
   opening, the priority page and the annexure must all agree. Read `totals.census`; do not count
   the book again.
2. **Every rupee total.** The tax page's foot, the priority page's headline, the sum of its own
   numbered rows, and the annexure. A sub-item exceeding the page's own headline total is the
   classic symptom.
3. **Gross vs net.** A net figure larger than the gross above it means the two were struck on
   different populations.
4. **Every percentage of the book.** Asset class and look-through are different bases; a page
   printing both must name both.
5. **Every caption against its own contents.** A panel headed "mutual-fund actions" holding a bank
   deposit and fourteen listed shares is a caption defect, not a data defect, and it is the harder
   of the two to spot.
6. **Every cross-reference.** `p.NN` must land on the page it names, after the graft.
7. **Every promise the page makes about itself.** "Each row links to the full rationale page"
   requires those pages to exist. A dead link is blanked at save time and leaves an empty column
   under a heading.
8. **Every pill colour against the call it carries.** A client-directed exit in the desk's Sell red
   is a false attribution of a call.
9. **Names on the same entity across slides.** `short_name` width ≥ 30 for scheme tables.
10. **A driver or tag against the narrative beside it** and against the same call's rationale
    elsewhere in the deck.

## The silent-page-loss trap

`engine.build` swallows a module exception. A module that raises **before** it draws anything simply
vanishes. A module that raises **after** `deck.content()` is worse: the title, the eyebrow and the
section rail are already on a slide, so a half-drawn page **ships** - a heading promising content,
no content, and no error anywhere a gate can see, because an empty page overlaps nothing.

The engine now removes the slides a failed module added, so a raise costs the whole page and never
half of one. It still prints `[skip] <module>: <why>` - **read the build output**, every time.

## The probe pass

The deck is built twice: once discarded, to learn which modules produced pages, and once for real.
`ctx["_rendered"]` is that map. A module that needs to know whether another module rendered - the
sell list asking whether the rationale cards exist, for instance - reads it rather than guessing.

## What "0 findings" is worth

It means nothing is off the page and no banned word is in the text. It does not mean the deck is
right. Every defect in `references/08_do_not_regress.md` passed all three gates.
