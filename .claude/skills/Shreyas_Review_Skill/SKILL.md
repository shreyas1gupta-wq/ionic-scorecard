---
name: Shreyas_Review_Skill
description: The single operating manual for producing an Ionic Wealth portfolio-review deck end to end - statement in, client deck and holdings workbook out. Covers the deck kit (ionic-deck-kit), the two centrally published score files and their order of precedence, client-directive overlays, the lot-aware tax engine, risk and liquidity mapping, the grafted firm pages, and the QA gates. Use whenever an advisor hands over a CAS, CAMS, Kfintech, NSDL or platform holdings export and wants the standard review. Supersedes ionic-wealth-complete, ndpms-deck and the ionic-deck-kit SKILL; Ionic_Portfolio_Review remains the deep reference for the scoring chain itself. v1.0
---

<!-- SKILL: Shreyas_Review_Skill | VERSION: v1.0 | SEQUENCE: 1 -->

# Shreyas Review Skill

**One skill, one pipeline: a holdings statement goes in, a client-ready review deck and a
reconciling holdings workbook come out.** Everything an advisor or an agent needs to produce the
review the way this desk produces it is either in this file or in `references/`.

> Check this copy is current before you rely on it:
> ```bash
> python check_version.py
> ```
> A skill dropped into `.claude/skills/` is a *copy* and does not track the repository.

---

## 0. The five rules that override everything else

1. **You do not decide the calls.** Sell, Trim, Hold, Hold (watch) and No View are published
   centrally, keyed on ISIN, and read. Never inferred from returns you can see, never filled in by
   judgement, never softened or hardened for a client. A holding absent from the score file is
   **No View**, and that is the right answer, not a problem to solve.
2. **No client Buy is ever issued.** The vocabulary is Sell, Trim, Hold, Hold (watch), No View on
   holdings the client already owns. Proceeds go to cash pending a separate conversation.
3. **Never match a fund by string similarity.** The join is on ISIN. A scheme's name changes; its
   ISIN does not. See `references/05_mapping.md`.
4. **Never fabricate a number, and never print a zero for something you could not compute.** A
   printed `0.0` is a positive claim that the quantity is nil. Where a figure cannot be struck, the
   page says so in words and in rupees.
5. **The repository `shreyas1gupta-wq/ionic-scorecard` is PUBLIC.** The score files, the risk and
   liquidity bands, the market-cap bands, `VERSION.json` and every client artefact are
   `.gitignore`d and stay that way. Publishing the desk's calls or a client's holdings is not a
   thing you can undo.

---

## 1. What you run

```bash
PY="C:/Users/Shreyas.1Gupta/AppData/Local/Python/pythoncore-3.14-64/python.exe"
```

The `python` alias is broken on this machine. Always set `PYTHONIOENCODING=utf-8` and
`PYTHONUNBUFFERED=1`; the console is cp1252 and will otherwise die on a rupee sign.

### Two commands. That is the whole thing.

```bash
cd ionic-deck-kit

# 1. is this installation in sync? run it before any client build
PYTHONIOENCODING=utf-8 "$PY" qa/check_sync.py

# 2. build, graft and check, in one go
PYTHONIOENCODING=utf-8 "$PY" build/run_review.py \
    "C:/tmp/<client>/<Client>_Statement.xlsx" \
    --client "<Client> Family" \
    --tier HNI_DEEP \
    --directives "C:/tmp/<client>/client_directives.json" \
    --lots "C:/tmp/<client>/tax_lots_raw.csv" \
    --firm-deck "<a deck carrying the firm's introduction pages>"
```

`run_review.py` runs `build_review.py`, then `graft_firm_pages.py`, then all three QA gates. It
**exits non-zero** on any gate finding that lands on a page this kit generated, and reports
findings on the grafted firm pages without failing - those slides are another firm-page layout
lifted verbatim and are not this kit's to re-lay. It also surfaces the `[skip]` lines, which is how
a whole page goes missing without anything looking wrong.

Everything it did lands in `out/<Client>_RUN.json`: the inputs, the score-file dates, the pages that
did not render, and the gate results. A deck can be traced back to what produced it.

`--directives`, `--lots` and `--firm-deck` are all optional and independent. Each one omitted makes
the deck say **less**, never anything untrue:

| omitted | what the deck does instead |
|---|---|
| `--lots` | prices a gain only where the statement carries a cost, cannot tell short-term from long, and says so on the page |
| `--directives` | shows only the desk's own calls |
| `--firm-deck` | ships without the introduction pages rather than with invented credentials |

`--skip-gates` exists for iterating. A deck built with it prints UNCHECKED and does not go out.

### The steps underneath, if you need one on its own

| # | step | command |
|---|---|---|
| 1 | read the raw statements | `parse/read_statement.py` (called by the build) |
| 2 | build one consolidated statement sheet | a per-client `extract.py` / `make_statement.py` |
| 3 | build the deck, workbook and IPS | `build/build_review.py` |
| 4 | graft the firm's introduction pages | `build/graft_firm_pages.py` |
| 5 | QA gates | `check_geometry.py`, `check_geometry2.py`, `tellscan.py` |
| 6 | **read the pages you changed** | no gate can see a page |

Step 6 is not automatable and is not optional. Every defect in
`references/08_do_not_regress.md` passed all three gates.

---

## 2. Tiers

| tier | audience | slides | register |
|---|---|---|---|
| `HNI_DEEP` | family office / sophisticated HNI | ~60-65 | technical, full annexure |
| `STANDARD` | typical NDPMS client | ~38-40 | professional |
| `RM_SIMPLE` | RM-led or newer investor | ~19-23 | plain language, larger type |

Build the tier the advisor asked for. Do not ship `HNI_DEEP` to an RM meeting because it is more
thorough; the registers are different documents, not different lengths.

---

## 3. What is published centrally, and never written in a module

Six files in `ionic-deck-kit/scores/`, refreshed on the desk's own cadence, none of them an
advisor's to edit for a meeting. **All six are gitignored.** A fresh clone has none of them and the
build will degrade honestly rather than invent.

| file | what it fixes |
|---|---|
| `ionic_scores_*.csv` | the fund calls, scores, steadiness and rationales |
| `ionic_stock_scores_*.csv` | the direct-equity calls, built by `export_stock_score_file.py` |
| `house_view.json` | the desk's stance, targets and what Ionic does for a client |
| `firm_profile.json` | the firm's AUM, co-founders, edge and asset-class view |
| `risk_liquidity_bands.csv` | the risk and liquidity band for every instrument sub-category |
| `equity_mcap_bands.csv` | large / mid / small / micro for the top 750 by market cap |
| `VERSION.json` | the as-of date and `single_scheme_cap_pct` |

Without `firm_profile.json` the introduction pages render **nothing** rather than inventing a
credential. That is correct behaviour, not a bug.

---

## 4. The reference files

| file | read it when |
|---|---|
| `references/01_pipeline.md` | building the consolidated statement from raw CAS / platform files |
| `references/02_calls_and_scoring.md` | anything about where a call comes from, MF or stock |
| `references/03_client_directives.md` | the client has asked for something the desk did not call |
| `references/04_tax.md` | the tax page, the lot file, and what is never estimated |
| `references/05_mapping.md` | a holding landed in the wrong sleeve, band or category |
| `references/06_firm_pages.md` | the grafted introduction pages |
| `references/07_qa_gates.md` | a gate fired, or you are about to trust one that cannot see |
| `references/08_do_not_regress.md` | **read before changing any module.** Every defect this deck has shipped once |

For the scoring chain itself - how a stock score is computed, the frozen v3 layer, QFRA-1 and
QFRA-2, the analyst research pass - `Ionic_Portfolio_Review` remains the deep reference. This skill
consumes those outputs; it does not re-derive them.

---

## 5. The order of precedence for a call

**Stocks** (`references/02_calls_and_scoring.md` has the detail):

```
house view  >  analyst your_recommendation  >  quant recommendation_v3  >  No View
```

The house view wins wherever it speaks, including where it says No View. On the current pair of
files it disagrees with the scorecard on **97 of 384 names, in both directions**. Where it
overrides the analyst, the analyst's rationale is dropped - it was written to argue the other case.

**Funds:** the published call in `ionic_scores_*.csv`, full stop.

**Both, then:** the client-directive overlay, which never becomes a desk call
(`references/03_client_directives.md`).

**A discretionary mandate is Hold, not No View.** A PMS or an AIF has a manager the client already
appointed and a book the desk was not given. That withholds a *score*, not a position: "No View"
against a crore-scale mandate reads as *we have nothing to say about the largest line in your
portfolio*. It is Hold, the rationale says why, and it counts as **Equity** in every band, every
concentration test and every look-through.

**Trim is never in the score file.** It is derived from `single_scheme_cap_pct`: a holding above the
cap becomes a Trim sized back to the cap. A Sell is a judgement on a holding and is the same in
every portfolio; a Trim is a judgement on a *weight* and is portfolio-specific. Never hand-set one
and never adjust the cap for a client.

---

## 6. Two caps, and they are not the same cap

| | `single_scheme_cap_pct` (VERSION.json) | "A single listed security" (IPS) |
|---|---|---|
| population | **any** holding | directly-held listed shares only |
| denominator | the **whole book** | the **equity sleeve** |
| what it does | fires a Trim | tests IPS compliance on the IPS page |

Reading either as the other is the most expensive mistake available in this kit. It once reported a
holding as comfortably inside a 15% cap while the trim engine was already cutting it back to 10%,
and put three different single-name caps in one deck.

---

## 7. Escalate rather than guess

Stop and ask a human when:

- the parsed total does **not** reconcile to the total the statement prints for itself;
- a holding's asset class, sleeve or call is genuinely ambiguous and the answer changes a number on
  a client page;
- the demo-score warning fires (the deck is not sendable at any price - say so and stop);
- a client directive would have the deck print something as the firm's call that the firm did not
  make.

"Not found" beats a wrong guess, every time. A gap the client can see is recoverable; a confident
wrong number on Ionic letterhead is not.

---

## 8. House style

No long dashes. No filler adjectives. No three-item lists for their own sake. Rupees with a
thousands separator. State the call and the published rationale; do not add a forecast, do not
annualise anything, and never describe a score as a prediction - it describes a record.

Internal vocabulary never reaches a client page: not QFRA, not SENTINEL, not `pf_qual`, not a raw
field name, not an analyst's name or a data source. `tellscan.py` catches most lapses; it cannot
read inside a chart image.

---

## 9. Deliverables

| artefact | where |
|---|---|
| the deck | `out/<Client>_Review_<TIER>.pptx`, then the grafted `<Client>_Review_FINAL.pptx` |
| the holdings workbook | `out/<Client>_Holdings.xlsx` - **every** holding, the call, the reason |
| the IPS workbook | `out/<Client>_IPS_<Profile>.xlsx` |
| unmatched rows | `out/<Client>_Holdings_Without_Scheme_Match.csv` |

The workbook is a client artefact and obeys the same rules the slides do: no internal names, no raw
field headings, and the same call on the same holding as the deck three feet away. They are built
from the same objects for exactly that reason.
