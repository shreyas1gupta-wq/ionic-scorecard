# The tax on the exits this review recommends

`build/tax_engine.py`. Nothing here is a tax opinion, and nothing is invented: a slice with no data
produces no number and says so on the page.

## The tax on an exit is not one rate applied to one gain

It is a different rate on each **slice** of the same holding, and which slice a unit falls into
depends on when that unit was bought - which a holdings statement does not say and a lot statement
does.

| slice | what it is | rate |
|---|---|---|
| **LTCG units** | past the long-term line for their asset class | equity 12.5% above ₹1.25 L per holder; gold, international and pre-Apr-2023 debt 12.5%, no indexation |
| **STCG units** | inside it | equity-oriented **20%**; everything else at the holder's slab |
| **Other-income units** | debt bought **on or after 1 April 2023** | slab, whatever the holding period - capital-gains treatment was lost entirely |

The platform's tax statement carries this split already, under a column named for "other income"
units. That column **is** the post-April-2023 bucket.

## Instruments that produce no capital gain at all

Charging one a capital-gains rate states a treatment that does not exist for it.

| holding | character | what exiting early actually costs |
|---|---|---|
| bank fixed deposit, savings, bank balance | `No gain; interest at slab` | the deposit's own penalty |
| PPF, provident funds | `Tax-free on exit` | nothing, and it cannot be exited on request |
| SCSS | `No gain; interest at slab` | 1% to 1.5% of the deposit, and the rate cannot be bought back |
| ULIP | `Per the policy terms` | depends on the premium against the sum assured and when written; a deduction already claimed can be reversed |

## The lot file

```bash
--lots "C:/tmp/<client>/tax_lots_raw.csv"
```

Columns are matched case- and space-insensitively on a prefix, so a re-export with a renamed header
does not silently produce a book with no short-term gain in it.

**Summed over every folio and every family member.** A scheme held in three folios whose cost was
read from two of them prices the exit against two-thirds of what was actually paid, and the whole
error lands on the gain. On one book that was SBI Small Cap: `₹6.11 L` of cost against `₹29.5 L`
of value, where the lot file carries `₹17.06 L`.

### Matching

Exact on the normalised scheme name, then a containment test in one direction, and only where
**exactly one** lot row can claim the name. **No similarity scoring.** A fund matched by edit
distance produces a tax number that is confidently wrong and cannot be spotted on the page. Where
two rows could both claim it, none is returned and the holding falls back to the statement's own
cost - which the page then labels `no purchase date`.

### Apportionment

The lot file gives cost for the whole scheme and value per slice. The gain is apportioned across
the slices **by value**; assigning the whole gain to one slice would price the exit at whichever
rate that slice happens to carry.

```
gain_rate = 1 - invested / current          # gain as a share of value
scale     = deck_value / lot_current        # the deck's value against the lot file's
L, S, O   = ltcg_val * scale, stcg_val * scale, other_val * scale
```

## The Section 112A exemption

`₹1.25 lakh per holder per year`, applied **once across the programme**, not per holding - which
would give the same exemption to a scheme twenty times over. The holder count comes from the lot
file's member column. The page says it was applied and for how many holders.

## What is never estimated

- **slab money.** Bank interest, non-equity short-term gains, and every post-April-2023 debt unit.
  Each member's slab differs. It is disclosed in **rupees** on the page and given no number.
- **a holding with no cost on file.** No gain is computed and none is shown. The count is disclosed.
- **a debt holding with no acquisition date.** The lower of the two possible rates (12.5%) is shown,
  and the page states in rupees how much is struck that way and that the figure understates the bill
  if those units postdate April 2023. That is the only direction this estimate can be wrong in, so
  it is the direction the page has to name.

**A printed `0.0` is a positive claim.** `less STCG 0.0L` was shipped on a book whose supplied lot
file carried `₹89.5 L` of short-term units, two of them in schemes on that very sell list. Never
print a zero for something you did not compute.

## The page

Both panels - the per-move table and the waterfall - cover **the same set**, and both captions say
which set that is. They used to read "Mutual-fund actions" and "Direct-equity sells & trims" over
one list that held a bank deposit, fourteen listed shares and nineteen client-directed scheme exits.
Two captions, one set, neither caption true.

`ctx["tax"]` carries `table_scope_label`, `chart_scope_label`, `table_total_label`,
`gap_note_title`, `de_gap_note`, `gap_note_2_title`, `gap_note_2` and `foot`. The page prints what
it is given; the data layer states its own scope.

### The callouts hold about two lines each

Text that overruns a PowerPoint box is **invisible in PowerPoint's own view**. A caveat written into
the overflow is a caveat the reader never sees while the deck looks finished. Four caveats stacked
into a 0.55-inch box ran to 1.89 inches. Each note is written to fit; whatever does not fit is not
written smaller, it goes to the source line.

## Tax inertia

Units held over five years (over ten more so) carry gains that offset switching alpha, so the bar
for switching them rises to structural-only. Shares get no such pass. Where a book has real tax
caveats, those replace this standing line - it is true of every portfolio and therefore tells this
reader nothing.

## Whose units are sold is a lever

Each family member's slab differs, so *whose* units are sold matters as much as which. Where the
statement carries a holder column, the review can say so; it never assumes a slab.
