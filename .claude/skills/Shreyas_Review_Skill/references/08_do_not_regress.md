# Every defect this deck has shipped once

Read this before changing any module. Each line is a real page that went out or nearly went out.
Every one of them passed all three QA gates.

## Counting

| what shipped | why | the fix |
|---|---|---|
| "5 of 60 schemes carry an action" beside a table showing 19 EXIT (CLIENT) rows and an annexure saying 34 Holds | the directive overlay set `verdict`/`rec` but not `action`, and the fund pages count `action` | the overlay writes `action` too; `ctx["totals"]["census"]` is the one count every page reads |
| "19 SELL CALLS" on a book with 20 client-directed exits worth ₹2.74 Cr, unmentioned | the executive summary lists the *desk's* gaps and a client instruction is not one | a `Your instruction` row, first, with count, value and share of the book |
| "5 FUND ACTIONS" counting only desk Sells | same field, same cause | desk actions and client instructions counted apart, in both |
| the fund-actions page opening "All 5 of these actions are performance calls" | 19 client exits would each have got a card claiming the scheme sits in the bottom third of its category | client exits are excluded from the cards and named in a line |
| the executive summary counting Sells in the fund sleeve only | `_n_call` counted `G`, not the whole book | count the whole book: a client with 20 direct-equity Sells was told the review found five |

## Money

| what shipped | why | the fix |
|---|---|---|
| "₹45.4 L GROSS FREED" headlining a ₹3.37 Cr programme, above its own sub-item of ₹63.0 L | `deployment.proceeds_inr` summed `funds` only | struck on the whole book; the headline adds the client's exits and says so |
| NET (₹3.28 Cr) larger than GROSS (₹3.19 Cr) on one page | the 14 direct-equity Sells were in one figure and not the other | both figures on the same population |
| a waterfall captioned "DIRECT-EQUITY SELLS & TRIMS" plotting the whole ₹3.37 Cr programme, of which direct equity is ₹17.6 L | two captions over one list | the data layer states its own scope; both panels print it |
| a fund worth ₹7.14 L read at ₹8.05 L | the value detector took the largest number on the row, which was the cost | bare "value" added to the vocabulary; identified cost and unit columns excluded. **The error lands only on losing positions** |
| a ₹1.2 quintillion book | CAS units are folio-derived (30,201,020 for a ₹5.97 L holding) and the detector took them as value | omit the units column entirely |
| ₹2.43 Cr double-counted in the reconciling workbook, 124 duplicate lines | the pre-split frame still holds the direct shares; it was written alongside `equity_rows` | export `_G_FUNDS`, never `G` |
| "₹0.0 L gross freed" three lines above ₹96.29 Cr of fund actions | zeros where the figure was unknown | `None` means could-not-compute and prints "Not estimated" |

## Tax

| what shipped | why | the fix |
|---|---|---|
| "less STCG 0.0L" on a book whose supplied lot file carried ₹89.5 L of short-term units, two on the sell list | `stcg` was hard-coded 0 and the lot file was never read | `tax_engine.py` reads it; equity STCG at 20% |
| a flat 12.5% on everything with a cost basis | one rate applied to one gain | three slices, each at its own rate; slab money disclosed and never estimated |
| a ₹1 Cr bank FD priced at "12.5% or slab" | a deposit produces no capital gain at all | instruments with no capital gain return a 0.0 rate and their own character |
| SBI Small Cap priced on 2 of its 3 folios' cost | folio-level cost was not summed | the lot file is summed over every folio and every member |
| the tax page pricing ₹62.8 L of desk sells and ignoring ₹2.74 Cr of client exits | the directive block ran **after** the tax block | reordered |
| "the tax on these sales cannot be estimated from it" on a deck carrying a tax page that estimates it | a stale footnote | said only where the book genuinely carries no cost |
| four caveats stacked into a 0.55in box, rendering 1.89in | overflow is invisible in PowerPoint's own view | each note written to fit; the rest goes to the source line |

## Attribution

| what shipped | why | the fix |
|---|---|---|
| six client-directed exits pilled `EXIT` in the desk's Sell red, directly above a row that *was* a desk Sell | `ACT_MAP` had no `EXIT (CLIENT)` entry and the code collapsed to `EXIT` | its own code, its own amber pill, the word "(client)" kept |
| "Exit (client)" and "Retain" on 23 holdings worth ₹3.84 Cr, appearing in no legend and no prose in 64 pages | nothing taught the reader the vocabulary | a `YOURS` row in the legend, a line on the mandate page, the instruction stated in the client's own words |
| three Retains as a bare word with the fund-coverage boilerplate as their reason | the workbook read a default string, not `structural_reason` | the reason flows to the workbook and to its own page in the deck |
| a Sell on Hindustan Aeronautics, Reliance, Bharat Dynamics, Thermax, Bajaj Auto and Vedanta | the scorecard's answer shipped where the house view held them - 97 of 384 names disagree | house view is the top of the precedence order |
| an analyst rationale arguing the opposite of the call above it | the house view overrode the call and not the rationale | `_overridden` clears rationale and negative_para |
| PMS and AIF as "No View" against crore-scale mandates | withholding a score was read as withholding a position | Hold, with a structural reason, counted as Equity |

## Mapping

| what shipped | why | the fix |
|---|---|---|
| "STATE BANK OF INDIA" as a "Thematic / Sectoral Fund" | the sector regex matched a listed bank | `sub_for_fund` refuses direct-equity categories |
| ₹70 L of PPF and SCSS in no lock-in test and no liquidity page | they arrive as their own statement category and never reached the instrument tests | `CATEGORY_TO_SUB` entries plus bands for each |
| "Silver 3.7% PENDING" on a book holding no silver | the framework's band is `Gold / Silver ETF or FoF`, so a gold ETF's own sub-category contains "silver" | one band, one row, named "Gold and silver" |
| a book at 0.4% cash against a 1% floor stamped ALIGNED | the band's floor was thrown away, publishing only the cap | bands are tuples |
| a holding inside a "15% cap" while the trim engine cut it to 10% | the whole-book cap and the equity-sleeve IPS limit were read as one number | two caps, two populations, two denominators |
| "State Bank of India NCD 2029" banded as a small-finance-bank deposit | the issuer word "bank" was tested before the instrument | instrument before issuer |
| 8 debt schemes listed under "no performance view" on the page after the plan to exit them | the coverage list was built from the pre-overlay frame | rows carrying a call are excluded |

## Pages

| what shipped | why | the fix |
|---|---|---|
| 14 Sells with wholly empty CASE cells under a column headed THE CASE | the demo context maps the paragraph to `negative`; the pipeline writes `negative_para` | `_case_text` reads every name the field has |
| an empty DETAIL column and a source line promising a rationale page that did not exist | a dead pageref is blanked at save time | the column and the promise are dropped together when `_rendered` says the cards did not render |
| a half-drawn page with a heading and no content | `engine.build` swallows module exceptions | the engine removes the slides a failed module added; read the `[skip]` lines |
| 52 footers five pages behind, and cross-references pointing five short | the kit numbers and binds before the graft inserts five slides | the graft renumbers both |
| another client's name on the finished title page | the title matcher hit the cover's bare "As of" first and substituted nothing | `m.start() > 0`; the script warns if nothing was renamed |
| two `image15.png` and two `slide6.xml` in one file | source part objects were related into the target, bringing their partnames | copy image **bytes** |
| a page printing 66% in its header and 62% in its own read line | asset class and look-through, neither named | both bases named |
| the plain-language register promising "replace N weak funds with stronger, cheaper ones" | it was never swept when the other two were | no client Buy, in any register: saying it in simpler words makes it likelier to be believed, not smaller |

## Gates and libraries that existed and were never called

| what | how long it sat unused | what it cost |
|---|---|---|
| `check_method.py` | written 2026-08-05 after an audit found five quality Sells on names the model scores as Hold | its command line takes a legacy data *module*, and this pipeline has none, so every deck through this path shipped unchecked. It runs on the live ctx now |
| `lib/mf_sell_gates.py` | the Layer-1 vetoes, sell priority and the churn arithmetic | `ctx["fund_churn"]` arrived as `{}` on every build, so the churn split - the rule that stops a client being handed thirty simultaneous actions - could not fire on any book |
| `up_capture` / `down_capture` | read by four modules since the kit was written | published by nothing, so the equity fund page skipped its capture panel and the scorecards printed a dash |
| the statement's `holder` column | present in every family statement | kept only as a *count*, so no page could say who the plan lands on |

**The pattern is one thing:** a consumer with no producer, or a producer with no consumer. Neither
errors. The page self-gates, renders nothing, and on a finished deck that is indistinguishable from
a page the desk chose not to include. `qa/check_sync.py` now warns on a starved column, and
`run_review.py` fails the run on a module that produced no page.

## Two ways a page goes missing, and the quieter one

`[skip]` is an import that failed. `[ERR ]` is a module that **raised while drawing**, so the engine
had to remove a half-drawn page. The second is the dangerous one.

On this book one fund carried `holding_years = None`, and `fund_actions.py` tested
`f.get("holding_years", 0) >= 5`. **A `.get` default only fires when the key is ABSENT**, so `None`
reached the comparison, `TypeError` was raised after `deck.content()` had already drawn the heading,
and the whole fund-actions page was removed. The only other trace was a zipfile warning about a
duplicate slide part. Use `(f.get(k) or 0)`, never `.get(k, 0)`, against anything a data layer can
write as None.

## A shadowed import is the quietest failure in Python

`lib/` and `modules/` share file names — `core_satellite.py` and `lookthrough.py` exist in both. Put
`lib/` at the front of `sys.path` and the engine imports the library version of a slide module.
Load a library by explicit path (`importlib.util.spec_from_file_location`), never by pushing its
directory onto `sys.path`.

## Process

- **`\b` written through a bash heredoc becomes a literal backspace byte.** Four occurrences. Use
  the Edit tool or `chr(92) + "b"`, and check with `grep -c $'\x08' <file>`.
- **The demo score file is dated later than production on purpose** so nobody mistakes it for real.
  If the invented-data warning fires, the deck is not sendable at any price. Say so and stop.
- **The repo is PUBLIC.** Score files, band files, `VERSION.json`, `out/`, `_charts/` and every
  client artefact are gitignored and stay that way.
- **A client's real name never enters a public repo**, in code, in a commit message, or in a
  changelog entry describing the scrub.

---

## Claims the deck made and could not support

Not one of these was a wrong number. Each was a sentence the deck printed about itself, on every
build, that nothing in the pipeline backed.

| what it said | what was true |
|---|---|
| "each call here carries a named reviewer's sign-off" and "every call passed a human review", rotated across a third of every deck's pages | no field records a reviewer or a review. Both deleted from the rotation |
| "Direct-plan NAV against **total-return** benchmarks" in the always-on disclaimer | no TRI series is obtainable from the desk's sources. Every index level here is price-return, and the fund score is struck against the scheme's own category peers |
| "Two frameworks today" over a page explaining originate-and-veto | this kit's Sells come off the percentile rule. `ctx["fund_call_method"]` now says which path produced the calls and the page prints that one |
| "35 funds under one of the two checks", counted from the SEBI category | counted from whether a **score exists** now. A fund the score file has no score for was reported as covered, under a footer reading "coverage counted from this book's own holdings, not assumed" |
| "a company is not in that population" on the coverage page | said in a deck that scored 113 single companies three pages earlier. It is outside the direct-equity universe the desk scores, which is a different and checkable statement |
| "What stays, and why" promising one read per name | `analyst_read` is read by two pages and set by nothing, so all 99 Holds rendered a blank line |
| a positive case under a red SELL pill: "operating margin strong, ROE strong, valuation reasonable, growth" | 9 of 160 Sell rows in the score file carry a case with no adverse attribute in it. The exporter emits only what leans with the call; the deck refuses an all-favourable recital under a Sell whatever the file says |

**The lesson is one thing:** a sentence about process is a claim, and a claim needs a field behind
it. If nothing in the pipeline can be pointed at, the sentence does not go on the page.

## A tier that does not change the deck is not a tier

`optional_on` was intersected with a two-name allow-list, so `HNI_DEEP`'s seventeen annexure
modules collapsed to two and `HNI_DEEP` and `STANDARD` built the **same 60-page deck**. Three tiers
that differed only in register, against a manual promising three different lengths.

Modules that need data no statement carries are named in `DROP_ANNEX` **with the field each one
needs**, verified by running them: each raises on its missing key *after* drawing its heading, which
costs the whole page. Everything else is offered to the tier and self-gates.

And page count is set by the **book**, not the tier: 64 / 62 / 34 on a 194-holding book, 37 / 37 /
26 on a 20-holding one. Do not put a page count in a manual without saying what book it was
measured on.

## The documented command has to work on the fixture shipped beside it

`build_client_workbook.py` did its own `pd.read_excel` and indexed a column literally named
`"Asset Name"`. Running the one command the skill documents, on the kit's own
`fixtures/demo_statement.xlsx`, built the deck and then died at `rc=2`. Half the delivered product,
gone on any statement whose columns are named differently — which is the normal case, and the whole
reason `parse/read_statement.py` finds its columns by vocabulary.

**Test the documented path on the shipped fixture.** It is the only test that catches this class.
