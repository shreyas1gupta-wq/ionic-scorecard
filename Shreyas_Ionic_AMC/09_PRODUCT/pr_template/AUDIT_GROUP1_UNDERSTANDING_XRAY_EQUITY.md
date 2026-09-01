# Audit — Understanding / Portfolio X-ray / Equity Book modules

Scope: `cover.py, contents_legend.py, disclaimer.py, exec_summary.py, since_last_review.py,
mandate_method.py, snapshot.py, allocation_house_view.py, concentration_risk.py,
sector_exposure.py, mcap_positioning.py, score_method.py, book_scored.py, equity_book.py,
sell_list.py, hold_rationale.py` + `group_concentration.py` (parked, audited on request).

**Headline: neither of the two known bug classes (hardcoded-numbers-as-real-data,
sell-only-always-wins structural bias) was found live in any of the 16 shipping modules.**
One close relative of the sell-only-bias pattern was found, but only in
`group_concentration.py`, which is currently permanently cut and never renders — see Finding 1.

## Classification table

| Module | Classification | Model-tier | Top issue (1 line) |
|---|---|---|---|
| cover.py | SAFE_AS_IS | Haiku | None — mechanical, demo-tag/placeholder-collapse logic already handles the first-review case |
| contents_legend.py | SAFE_AS_IS | Haiku | None — static section/vocab legend, annexure tag list is mechanical |
| disclaimer.py | SAFE_AS_IS | Haiku | None — static text, real-vs-demo suffix is a one-line branch |
| exec_summary.py | DATA_ONLY | Haiku | Good: no-IPS / all-Direct / no-Switch fallback rows are baked into shared code, not client data |
| since_last_review.py | DATA_ONLY | Haiku (module) / Sonnet (meeting-note authoring, not module's job) | Self-gates cleanly (`return 0`) when no meeting_history — correct |
| mandate_method.py | DATA_ONLY | Haiku | Good: horizon/construction "not yet on file" phrasing is in shared code |
| snapshot.py | DATA_ONLY | Haiku | Mild KPI overlap with exec_summary (see Finding 4) |
| allocation_house_view.py | DATA_ONLY | Haiku | Good: `has_real_gap` guard drops chart cleanly when no IPS/targets exist |
| concentration_risk.py | DATA_ONLY | Haiku | Clean; on_file-aware source line |
| sector_exposure.py | NEEDS_CODE_CHANGES | Haiku | Single-sector book duplicates the sector name in prose (Finding 3) |
| mcap_positioning.py | DATA_ONLY | Haiku | Good: drops 0%-buckets, guards missing mid/small gap |
| score_method.py | SAFE_AS_IS | Haiku | Static methodology page, no client data at all |
| book_scored.py | DATA_ONLY | Haiku (module) / Sonnet (analyst_read authoring) | Overlaps equity_book.py (Finding 4) |
| equity_book.py | REDUNDANT_CANDIDATE | Haiku | Same weight-vs-score-vs-rec data as book_scored, chart form (Finding 4) |
| sell_list.py | DATA_ONLY | Haiku (module) / Sonnet (client_case authoring) | Case-fallback order (overlay→negative→trigger) correctly enforces "leans with the call" |
| hold_rationale.py | DATA_ONLY | Haiku (module) / Sonnet (analyst_read authoring) | Clean; correctly cut the "what would flip a Hold" meta-text per ruling |
| group_concentration.py (parked) | NEEDS_CODE_CHANGES | Sonnet (before any resurrection) | Post-sale % uses pre-sale denominator — flatters the improvement (Finding 1); GROUP map coverage gap (Finding 2) |

## TOP FINDINGS (severity order)

**1. `group_concentration.py` line 72 — post-sale denominator bug, same bias family as the
stress_scenarios cut (NEEDS_CODE_CHANGES, currently dormant since the module is parked).**
```python
after = 100.0 * sum(e["weight_pct"] for e in members if e["rec"] != "Sell") / eq_total
```
`eq_total` (line 38) is the **pre-sale** direct-equity sleeve total. The numerator correctly
drops sold names, but the denominator doesn't shrink to match — so the "after" percentage is
computed against a larger base than will actually exist once those names are sold and the
sleeve contracts. That mechanically prints a lower (better-looking) post-sale group share than
the true post-sale sleeve would show. It is a smaller-scale instance of exactly the
pattern that got `annex_stress_scenarios.py` cut: an "after" figure that looks better partly
because of an accounting artifact of selling, not purely because of a genuine risk reduction.
Fix: recompute the post-sale denominator as `eq_total - sum(all sold weight_pct in the whole
book)`, not just this group's sold names, since cash raised from ANY equity sell shrinks the
sleeve total that the remaining group members are a share of.

**2. `group_concentration.py` lines 11–26 — GROUP promoter-map coverage gap.** Only ~40
tickers across 10 groups (Tata, Reliance, Adani, Bajaj, Aditya Birla, Mahindra, JSW, Vedanta,
L&T) are mapped. A real client's book will routinely hold group-affiliated names this dict
doesn't know about (HDFC group, Kotak, Wipro/Azim Premji, Godrej, Piramal, Bharti, ITC, Hero,
Vardhman, etc.) — those names silently fall through `GROUP.get(e["symbol"])` returning `None`
and are never counted toward any group's exposure. Because the module's own docstring already
says "extend as the universe grows," this is a known-incomplete lookup, not a secret one — but
as currently written it is not fail-safe: a real client concentrated in a group outside the map
gets a false "nothing trips" (`return 0`) instead of the correct alert. Before any resurrection,
either expand coverage meaningfully or add an explicit "coverage: N of M holdings mapped" note
so a false negative is at least visible instead of silent.

**Recommendation on group_concentration.py: fix Findings 1–2, then resurrect — don't delete.**
It is a distinct risk lens (single-owner/event-risk pooling) not covered by `concentration_risk.py`
(single-name) or `sector_exposure.py` (sector), the code is otherwise well-guarded (self-gates
at 0 slides when nothing trips, correct same-basis % as the CEO sweep required), and promoter-
group concentration is a real, client-relevant risk for Indian portfolios. Deleting it would lose
a working, mostly-sound module for a fixable denominator bug and a documented, extensible
coverage gap.

**3. `sector_exposure.py` line 42 — duplicate-sector text bug on a thin real-client book.**
```python
top1, v1 = ranked[0]; top2, v2 = ranked[1] if len(ranked) > 1 else (ranked[0])
```
If a real client's direct-equity holdings span only one distinct sector (plausible for a small
first-review book, or one dominated by a single-sector cluster after `sector` field gaps
collapse everything into "Diversified"), `top2` becomes the same tuple as `top1`, and the
generated prose reads "the book leans toward IT (46%) and IT (46%)" — a visibly broken sentence
in a client deck. Low probability but a real crash-adjacent risk on real data, not just a demo
edge case; the module has no test for `len(ranked) == 1`. Fix: guard with an explicit
single-sector branch ("Your entire direct-equity book sits in one sector: X").

**4. Redundancy — `book_scored.py` vs `equity_book.py` show the same underlying relationship.**
Both plot/tabulate the same three fields for the same population (direct equity: weight_pct,
ionic_score, rec) — `book_scored` as a table capped at 11 rows with per-name analyst prose and
row-level hotspots; `equity_book` as a bubble scatter of the FULL population with no per-name
detail. They are not byte-identical duplicates (table gives depth on the largest names + links
into the annexure; the bubble gives shape/outliers across the whole book, including names below
the table's row cap), so this is flagged as a **candidate**, not a confirmed cut — worth a
Principal/Product-head call on whether both need to ship in every tier, or whether `equity_book`
should be annexure-only / RM_SIMPLE-dropped given `book_scored` already carries the headline
read. Milder, same-family overlap: `exec_summary.py`'s KPI strip (AUM, n_stocks/n_funds,
top10%, sell count, fund actions) repeats three of the same four numbers `snapshot.py`'s KPI
strip shows one section later (AUM, n_stocks, n_funds, top10%) — standard deck practice
(headline recap → section-opener detail) rather than a defect, but worth naming since the user
asked to flag any overlap for a second look, including across modules outside this group (e.g.
whether `concentration_risk.py`'s top-10 treemap duplicates anything in a Portfolio-X-ray-
adjacent Annexure module such as `spotlight_holdings` — outside this audit group's scope, flagged
for the X-ray/Annexure group to check).

## Positive finding worth recording

The prior Client B session's crash-guard fixes for missing IPS / no meeting history / all-
Direct funds / no SWITCH actions are **in the shared module code** (`exec_summary.py`,
`mandate_method.py`, `allocation_house_view.py`, `mcap_positioning.py`,
`concentration_risk.py`, `since_last_review.py`), not patched into that one client's data file —
confirmed by reading each fallback branch above. These protect every future first-review client,
not just Client B's book.
