# From raw statements to one consolidated sheet

The build takes ONE workbook. Getting from what an advisor actually hands over to that workbook is
the part that varies client by client, and it is where the money goes wrong.

## What arrives

| source | shape | what it carries |
|---|---|---|
| NSDL / CDSL CAS (PDF, password-protected) | bilingual, interleaved | demat holdings as tables, MF folios as plain text lines |
| CAMS / Kfintech statement | xlsx or PDF | folio-level MF holdings, sometimes with cost |
| platform tax statement (Scripbox, Zerodha, INDmoney) | xlsx | **the lot file**: LTCG / STCG / other-income units per folio |
| an advisor's own brief | anything | deposits, PPF, SCSS, ULIPs, PMS, AIF, direct bonds |

**The CAS password is usually the PAN**, which is usually the filename the advisor sent.

**A CAS PDF is bilingual and interleaved.** Separate the English from the Hindi by *font name*, not
by position or by heuristics on the characters. The lock-in table and the transaction table share
the ISIN column with the holdings table, so a naive scrape double-counts.

## The consolidated sheet

One row per holding. The build finds its columns by **vocabulary**, not by position, so the table
can start anywhere on the sheet and the columns can be in any order.

| column | required | notes |
|---|---|---|
| `Asset Name` | yes | as the statement writes it |
| `ISIN` | where it exists | `INF` = fund unit, `INE` = company security. Exact, no lookup |
| `Asset Class` | yes | Equity / Fixed Income / Alternates / Cash |
| `Category` | yes | the SEBI category, or the instrument (`PPF`, `SCSS`, `Fixed deposit`, `PMS`, `ULIP`) |
| `Holder` | useful | drives the per-member tax exemption |
| `Value` | yes | the market value |
| `Cost` | where it exists | the invested amount |

### Do NOT include a units column

CAS units are folio-derived and can be wildly out of scale with the holding: a `₹5.97 L` position
carrying `30,201,020` units. The value-column detector picks the largest plausible number on the
row, and a units column poisoned a whole book into `₹1.2 quintillion`. **Omit the column.** The
review never needs it.

### The largest number on the row is not the value

The fallback detector explicitly excludes identified cost and unit columns. A fund worth `₹7.14 L`
against `₹8.05 L` invested was read at `8.05` - and that error lands *only on losing positions*,
which is the direction nobody checks.

## Reconcile before you build

`read_statement.py` compares the parsed total against the total the statement prints for itself.

**If it says MISMATCH, stop and tell the advisor.** A deck built on a partial read carries wrong
numbers on every page and looks completely finished.

Reconcile per family member too, not just in aggregate. A member-level offset that nets to zero
across the family is still two wrong pages.

## Rows without an ISIN are still the client's money

They go in the exceptions file because the desk cannot put a *call* on them. That is the only thing
the exceptions file means. They stay **in** the portfolio: in the total, in every weight, in the
concentration tests, on the risk-and-liquidity grid and in the holdings annexure, carrying No View.

On the reference book that was 41 of 75 holdings and 39% of the money - REITs, AIFs, direct bonds.
A review that quietly reported the other 61% would be wrong on every page.

Never drop one. Never guess which scheme it was.

## Zero-value guard

A book worth `₹0` raises `SystemExit` with a diagnostic rather than dying on a `ZeroDivisionError`
sixteen divisions later. If you see it, the value column was not read: check the sheet has a column
headed Value / Market Value / Current Value / Amount, that its numbers are stored as numbers rather
than text, and that the holdings are not all closed.

## Per-client scripts

Each client gets a small folder under `C:/tmp/<client>/` with, typically:

- `extract.py` - reads the CAS PDFs and the platform workbooks, reconciles, writes `holdings_raw.csv`
- `enrich.py` - joins the ISIN master, the score files and the risk framework
- `make_statement.py` - writes the consolidated `<Client>_Statement.xlsx` the build consumes
- `client_directives.json` - the client's own instructions, if any
- `tax_lots_raw.csv` - the lot file, if one was supplied

These are per-client because the sources are per-client. The *rules* they enforce are not: they are
in this skill, and a new client's scripts should be a copy of the last one's with the source
readers changed.
