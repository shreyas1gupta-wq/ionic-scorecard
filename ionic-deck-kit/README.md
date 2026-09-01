# Ionic Portfolio Review Kit

Give it a client's holding statement. It gives you the review deck and the holdings workbook, in the
house format, with Ionic's calls already applied.

## Use it

```
python build/build_review.py <statement.xlsx> --client "Family Name"
```

Output lands in `out/`:

| File | What it is |
|---|---|
| `<Client>_Review_HNI_DEEP.pptx` | The deck |
| `<Client>_Holdings.xlsx` | Every holding, the call, the rationale |
| `<Client>_EXCEPTIONS.csv` | Anything the parser could not resolve. Only written if there is something to report. |

Tiers: `--tier HNI_DEEP` (full), `STANDARD`, `RM_SIMPLE`.

## What it will tell you, and you should read it

Three lines in the output matter more than the rest.

**Reconciliation.** The parser adds up what it read and compares it against the total the statement
prints for itself. If those disagree, the deck is built on a partial read and the number is wrong.
Do not send a deck where this says MISMATCH.

**Schemes absent from the score file.** They render as No View. That is correct behaviour, not a
failure, but if a large holding comes back No View it is worth asking central whether the scheme
should be covered.

**Exceptions.** Rows carrying money that the parser could not tie to a scheme. Never zero these out
by ignoring them. Send them back.

## Where the calls come from

`scores/` holds a file published centrally, keyed on ISIN. It carries the score, the call and the
one-line rationale, and nothing else. It is distributed to you privately and it is not in this
repository.

You cannot change a call by editing anything in this kit, and you should not try. If a call looks
wrong for a client, that is a conversation with the desk, not a spreadsheet edit. The kit deliberately
holds no scoring logic: no NAV history, no peer construction, no percentile maths. It renders what
central publishes.

A scheme missing from the file gets No View rather than a guess.

## Check the date

`scores/VERSION.json` carries the as-of date, and the deck prints it. The calls are refreshed on the
desk's own cadence. If the file is months old, get a newer one before sending anything to a client.

## Test it without a client

```
python fixtures/make_demo_statement.py     # a synthetic statement, no real holder
python scores/make_demo_scores.py          # invented scores, clearly labelled
python build/build_review.py fixtures/demo_statement.xlsx --client "Demo Family"
```

The demo statement is deliberately awkward: a title block above the header, a TOTAL row at the
bottom, a second sheet with no holdings, and one ISIN the score file has never heard of. If the kit
handles that, it will handle a real statement.

## What it needs

Python with `pandas`, `openpyxl`, `python-pptx`, `matplotlib`.

## Before you send anything

Run the QA gates in `qa/`. Geometry findings mean something is off the page or overlapping. A deck
that fails geometry has content the reader cannot see.
