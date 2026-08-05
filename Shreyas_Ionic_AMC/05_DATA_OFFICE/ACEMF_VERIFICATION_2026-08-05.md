# ACE MF "Advisory V2" feed — D-009 verification + what it unblocks
**File received:** `Downloads/10. V2 Data_31th July_2026.xlsx` (7.5 MB, 1 sheet, 19,428 x 116)
**Verified:** 2026-08-05, DESK-20. Cached digest: `%TEMP%/acemf_clean.parquet`.
**Cadence agreed (Principal, 2026-08-05):** ACE MF becomes the single consolidated MF source, refreshed
MONTHLY and sent to us. Supersedes the ad-hoc mix of `MF Dashboard.xlsx` + repo NAV files for the
fields it covers.

Layout note for whoever parses it next: real header is **Excel row 9** (`header=8`); group headers are
on row 5; row 3 carries the template tag `>>CustomTemplate:Advisory V2`. Column names REPEAT across
blocks (six separate `Month End`, four `Others`), so de-duplicate on read or you will silently join the
wrong block.

---

## D-009 GATE: two findings that must be handled before this feed is used

### 1. [DATA] The filename says July. The data is JUNE. Do not label a deck from the filename.
Every dated block resolves to **202606 (30-Jun-2026)** as its modal as-of, and the sheet tab agrees
("V2 of unique Funds-30th Jun, 26"). The filename "31th July_2026" does not.

| Block | Modal as-of |
|---|---|
| Expense Ratio | 202606 |
| Asset Allocation | 202606 |
| Asset Type Allocation | 202606 |
| Sector Wise Allocation | 202606 |
| Average Maturity / YTM | 202606 |
| Rating Allocation | 202606 |
| Maturity Profile | 202606 |

**But the RETURN block is a different vintage:** the rolling-return group headers read
"31-July-2025 To 31-July-2026", i.e. returns appear to run to 31-Jul while every holdings-derived
block is 30-Jun. **This is a mixed-as-of dataset.** Each block must be stamped with its OWN as-of on
any page that uses it. Never print one deck-level "data as of" date over the whole thing.

### 2. [DATA] 39.5% of rows are NOT at the current month-end. Some are years stale.
On the Asset Allocation block: 60.5% of rows are at 202606, 7.0% at 202605, and the tail includes
**202203, 202104 and 201804**. So staleness here is a **per-fund, per-block** property, not a
property of the file.

This makes the FM's comment #4 both correct and understated: a file-level freshness check would pass
this file while a client's own fund silently carries 2018 allocation data. **The staleness gate must
run at row level and refuse to print an allocation whose block as-of is older than the threshold.**

Other coverage limits, stated so nobody assumes full coverage:
- 19,418 rows are ALL plan variants. `Plan` = Standard 9,616 / **Direct 8,907** / Suspended 569 /
  Regular 82 / Institutional 63+. Filter to Direct and **exclude Suspended**.
- Debt Direct-plan rows: 4,486, of which only **2,529 carry YTM (56%)** and 3,010 carry an expense
  ratio (67%). YTM coverage is partial, which limits FM comment #22.
- `Sub Category` is populated on only 6,523 of 19,418 rows.

---

## WHAT THIS FEED UNBLOCKS (verified against the data, not assumed)

### #2 look-through equity — FULLY UNBLOCKED, and our current error is large
`Asset Allocation` gives real Equity / Debt / Others percentages per fund. Measured medians on
Direct-plan hybrids (911 rows):

| Category | median equity % |
|---|---|
| Aggressive Hybrid | **73.0** |
| Balanced Advantage | 70.1 |
| Dynamic Asset Allocation | 68.6 |
| Equity Savings | 68.1 |
| Multi Asset Allocation | 66.5 |
| Conservative Hybrid | 18.9 |
| Balanced Hybrid | 16.7 |

Our code today counts **every one of these as 0% equity**. For a client holding an aggressive hybrid at
10% of portfolio, we are understating true equity by about 7.3 percentage points from that single line.

**[OPINION] One trap to handle before wiring this in.** Arbitrage funds show a median 70.5% equity and
Equity Savings 68.1%, but both are substantially HEDGED — that is gross equity exposure, not equity
risk. Feeding raw ACE equity percentages into an IPS equity-band check would classify an arbitrage
fund as equity-heavy when its risk profile is debt-like. The look-through needs a
hedged-exposure adjustment for Arbitrage, Equity Savings and Balanced Advantage, or an explicit
"gross vs net equity" distinction on the page. This is a judgment call for the FM.

### #9 and #10 sector and concentration for funds — UNBLOCKED at SECTOR level only
`Sector Wise Allocation` carries **44 named sectors per fund** (Bank, Finance, IT, Healthcare, Power,
G-Sec, and so on). That is enough to build true combined sector exposure across direct equity and the
fund sleeve, which is exactly what the FM asked for.
**Not unblocked: stock-level look-through.** The feed has no holdings list, so we cannot compute
overlap or concentration down to individual securities. Sector-level yes; stock-level no.

### #22 debt sell rule — UNBLOCKED (with the 56% YTM caveat)
`YTM (%)`, `Average Maturity Years`, `Modified Duration`, `Macaulay Duration`, plus `Ratio` and
`Direct Plan Ratio` for expense. Also `Rating Allocation` (AAA / AA / A / BBB / D / SOV / Unrated) and
`Maturity Profile` buckets, which additionally complete the fixed-income section of the IPS page.

### #14 returns and capture — PARTLY UNBLOCKED
Present: fund returns at 1M / 3M / 6M / 9M / 1Y / 3Y / 5Y / since-inception, three rolling-return
windows, and **Up Capture / Down Capture / Up-Down Capture against both the fund's own benchmark and
Nifty 500**. That covers the capture half of comment #14 directly.
**Missing: period benchmark returns.** Only `SI Benchmark` is provided, so "1Y/3Y/5Y return vs
benchmark" still needs an external benchmark **TRI** series (Principal confirmed TRI, 2026-08-05).
`Benchmark Indices` names the right index per fund, so the join key exists.

### #15 risk-adjusted returns — PARTLY UNBLOCKED
Present: `SD` and `SD Annualised`. **Absent: Sharpe, Sortino and Information Ratio — the feed has no
such columns.** We must compute those ourselves from NAV history, which needs a risk-free convention
(FM decision B4).

### #4 staleness gate — UNBLOCKED and better than asked
Six independent `Month End` stamps make a per-block, per-fund freshness check possible.

### #20 hybrid scoring — DATA unblocked, METHOD still open
Actual equity/debt split, category, benchmark, capture ratios and expense are now all available for
2,488 hybrid rows. The scoring method remains the FM's call.

---

## STILL BLOCKED, and on what

| FM # | Blocked on | Note |
|---|---|---|
| #19, #21 | **Purchase dates and cost per lot** (asked as C2) | STCG/LTCG split and the 1-Apr-2023 debt cut-off are date-driven. ACE MF cannot supply these; they are client-transaction data |
| #24 | Stock-level holdings | Scheme **NAV correlation** is computable today from NAV history and needs nothing new. Holdings-level **overlap** needs a security-level feed ACE V2 does not carry |
| #1 | FM decision | Core/satellite mapping and target split |
| #16 | FM decision | Which tail measure |
| #17 | FM decision | Weights and cut-offs for the five scoring inputs |
| #20 | FM decision | Hybrid method |
| #14 | Benchmark TRI series | Not in this feed; index name is, so the join is ready |
| #15 | FM decision | Risk-free convention |

---

## Recommended build order now that the feed exists
1. **Row-level staleness gate** (#4). Nothing depends on a decision, and 39.5% stale rows means every
   downstream number needs it first.
2. **ACE MF loader + Direct-plan/Suspended filter + per-block as-of stamping**, into
   `pr_template/lib/`. Everything else consumes this.
3. **Look-through equity** (#2), with the hedged-exposure question put to the FM before it goes on a
   client page.
4. **Combined sector exposure** (#10) and scheme/AMC concentration including funds (#9, sector level).
5. **Debt sell inputs** (#22) and the fixed-income IPS section.
6. Deck restructure into three parts (#11), calculation-base convention (#8), MF methodology page
   (#12), asset allocation on the snapshot (#6), retire allocation-vs-house-view (#7).
7. Scheme NAV correlation (#24) to replace the overlap page.
8. Everything behind an FM decision, last.
