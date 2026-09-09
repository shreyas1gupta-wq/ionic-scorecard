# Where a call comes from

Two desks score two populations, and they are joined by the ISIN prefix. India issues fund units
under `INF` and company securities under `INE`. That is the whole test - exact, no lookup, no
name matching.

| population | file | built by |
|---|---|---|
| mutual-fund schemes | `scores/ionic_scores_*.csv` | the MF desk (QFRA-1 / QFRA-2) |
| direct equity | `scores/ionic_stock_scores_*.csv` | `export_stock_score_file.py`, 750 names |

Both are gitignored. Both are refreshed on the desk's own cadence. Neither is an advisor's to edit.

---

## The stock call: order of precedence

```
1. house view        STOCK REVIEW FINAL.xlsx      wins wherever it speaks, including "No View"
2. analyst           your_recommendation          where the house view is silent
3. quant             recommendation_v3            where both are silent
4.                   No View                      where all three are silent
```

**This matters more than it sounds.** On the current pair of files the house view disagrees with
the scorecard on **97 of 384 names, in both directions**. Shipping the scorecard's answer put a
Sell on Hindustan Aeronautics, Reliance, Bharat Dynamics, Thermax, Bajaj Auto and Vedanta in a
client deck while the house view held every one of them.

**Where the house view overrides the analyst, drop the analyst's rationale.** It was written to
argue the other case, so printing it under a house-view call contradicts the call it sits beneath.
`export_stock_score_file.py` clears `rationale` and `negative_para` when `_overridden` fires. Do
not undo that.

### The scoring itself (consume, do not re-derive)

Dual-horizon, seven pillars, never blended into one number at the analyst level. 3Y is
fundamental-tilted, 1Y technical-tilted. Overlay gates (balance-sheet safety, liquidity) are
multiplicative and cap at 40. Financial sectors are exempt from the debt-to-equity trigger, because
leverage is their business model.

Client-facing, one number: `ionic_score = clamp(0.60 * final_3y + 0.40 * final_1y + adj, 0, 100)`,
where `adj` is a forward-growth leg plus a conviction leg, clamped ±20, and can never be net
positive where expected growth is under 10% or where the analyst says Sell.

Two gates decide the client call:
- **Gate A, quality:** analyst Sell → Sell. Else `ionic_score < 40` → Sell.
- **Gate B, concentration:** `ionic_score` 40-50 **and** weight > 2.5% → Trim.

Asymmetric override bars: a Sell on a >40 scorer needs a 90%-conviction exceptional case (it wears
an amber EXCEPTIONAL tag); a Hold on a <40 scorer needs a documented 60% case. The 750 universe runs
about **33% quant Sells** - a client book far below that is override leakage, not a better book.

The full method is in `Ionic_Portfolio_Review` and `09_PRODUCT/HOW_WE_SCORE_STOCKS.md`.

---

## The fund call

The published call in `ionic_scores_*.csv`, full stop. The vocabulary is Sell, Trim, Hold (watch),
Hold, No View.

**Hold (watch)** is a held position the desk has flagged. It is not a clean Hold and it is not an
invitation to soften or harden it.

The **fund score** is the share of the scheme's own SEBI-category peer group it beat. The desk cuts
that into thirds, and the GRADE column restates that rule in words: Bottom / Middle / Top. The
score is the input; the Portfolio Review team sets the verdict.

**Steadiness** (`consistency`) is *how steadily* a fund got there, as against how far ahead it
finished. It is context for the reader, never a verdict. A Sell sitting high on steadiness is a
fund that is reliably behind.

### Capture: how much of the category's rise, and how much of its fall

`up_capture` and `down_capture`, published beside the score and computed the same way, from the same
monthly NAV panel, keyed on the same ISIN.

**The reference is the peer cohort, not an index.** The panel is AMFI NAV and carries no benchmark
TRI, so the reference is the equal-weighted average of the scheme's own SEBI category. `capture_ref`
travels with the numbers and says exactly that, and **every page that prints them prints the
reference**. Read against peers, 100% means *took as much of the category's move as the average fund
in it* — not *matched the index*. Those are different statistics and one must never be labelled as
the other.

Both legs need at least eight up-months and eight down-months or the scheme publishes nothing. A
down-capture struck on one bad quarter is the kind of number a client acts on and should not.

**These were read by four modules and published by nothing.** `funds_equity`, `funds_hybrid`,
`scheme_scorecards` and `appendix` have asked for `up_capture` / `down_capture` since the kit was
written and got `None` on every build, so the equity fund page skipped its capture panel entirely
and the per-scheme scorecards printed a dash. That is the whole failure mode of an optional column:
the page self-gates, renders nothing, and on a finished deck looks exactly like a page the desk chose
not to include. `qa/check_sync.py` now warns when the published file carries no capture columns.

### The full published schema

| column | required | what starves without it |
|---|---|---|
| `isin`, `scheme`, `category`, `score`, `call`, `rationale` | yes | the build refuses |
| `consistency`, `hit_rate`, `months` | no | the steadiness column on the fund book |
| `up_capture`, `down_capture`, `capture_months`, `capture_ref` | no | the capture panel and the per-scheme scorecards |
| `as_of` | yes | the date on the cover |

Anything optional and absent makes the deck **smaller**, never wrong. Run `qa/check_sync.py` and
read the warnings: each one names a page that is silently rendering nothing.

### Two plans, one scheme

Direct and Regular are share classes of the same portfolio. They carry the same score and the same
call, always. If they ever differ, something is wrong upstream.

The plan is read off the scheme's own name, which is where SEBI requires it to be stated. Nothing
is matched by similarity. The rupee drag of a Regular plan needs a per-scheme TER in each plan,
which a holdings statement does not carry, so the deck reports the count and the value of Regular
holdings and says the saving is not estimable rather than printing one.

---

## Discretionary mandates: PMS and AIF

**Hold, and Equity.** Not No View.

A PMS or an AIF has a manager the client has already appointed and a book the desk has not been
given. That withholds a *score*; it does not withhold a *position*. "No View" against a crore-scale
mandate reads to a client as *we have nothing to say about the largest line in your portfolio*.

- `rec = "Hold"`, with a `structural_reason` that says why there is no score
- counts as **Equity** in every asset-class band, concentration test and look-through
- appears in the fund book, the annexure and the totals like anything else

---

## What the deck may never do

- infer a call from returns visible in the statement
- fill a gap in the score file with judgement
- override a published call because it looks wrong for this client
- issue a Buy
- match a scheme by string similarity, ever, for any reason
- describe a score as a prediction

If an advisor asks why a fund is a Sell, the rationale column is the answer. If they want more than
that, it is a conversation with the desk.

---

## The census: one count, read by every page

`ctx["totals"]["census"]` holds `{scope: {call: (n, value)}}` for `book`, `funds`, `shares` and
`other`. Every page that counts a call reads it.

This exists because each page used to count for itself, off whichever field it happened to use -
`action` here, `verdict` there, the pre-overlay scored frame somewhere else - and the answers
disagreed inside one deck. A page told a client that 5 of 60 schemes carried an action while its
own table three pages earlier showed 19 client-directed exits and the annexure said 34 Holds.

If you add a page that counts anything, read the census. Do not count the book again.
