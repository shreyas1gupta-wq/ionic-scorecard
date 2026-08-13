# -*- coding: utf-8 -*-
"""COST OF ONE NDPMS DECK — 30 direct equities + 15 mutual funds.
Principal, 2026-08-13: "estimated cost of a 30 stock 15 mutual fund portfolio review deck in claude
subs, vs claude api - opus 5 vs sonnet 5 vs deepseek vs chatgpt."

WHAT IS MEASURED AND WHAT IS NOT, stated up front because the difference is the whole answer:

  [DATA]      Provider prices. Claude from the claude-api skill (cached 2026-06-24). DeepSeek and
              OpenAI from vendor/aggregator pages fetched 2026-08-13 (URLs in the report).
  [DATA]      Which pipeline stages cost ZERO tokens. Verified by reading the code: the deck build,
              all five QA gates, client_intake, the Excel builders and the scoring chain are plain
              Python/pandas. They cost compute, not tokens. This is the single biggest cost fact
              about this pipeline and it is not an estimate.
  [DATA]      Output size of one stock-research artefact. Anchored on a real committed file,
              results/pf_qual_TMCV.json -- measured below, not guessed.
  [INFERENCE] Cumulative INPUT tokens per research agent. Not metered in this repo:
              ws4_spend_extract.py exists but was never run and no spend.csv was ever written, so
              there is no historical measurement to cite. Modelled from the agent's shape (a
              multi-turn web-search loop re-sends its growing history every turn) and reported as a
              LOW/MID/HIGH band rather than a single fake-precise number.

The cold-vs-warm split matters more than the model choice. The repo already carries scores for 751
stocks and grades for 181 funds, so for a client whose names are already covered, ALL per-name
research is zero -- that is what committing the data bought. Both cases are priced.

Writes 09_PRODUCT/reports/DECK_COST_MODEL.md and prints the tables.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _root(p):
    found = None
    while True:
        p, tail = os.path.split(p)
        if not tail:
            if found:
                return found
            raise RuntimeError("repo root not found")
        cand = os.path.join(p, tail)
        if os.path.isdir(os.path.join(cand, "Shreyas_Ionic_AMC")) or tail == "NIFTY 500":
            found = cand


ROOT = _root(HERE)
RES = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
OUT = os.path.join(ROOT, "Shreyas_Ionic_AMC", "09_PRODUCT", "reports", "DECK_COST_MODEL.md")

N_STOCKS, N_FUNDS = 30, 15

# ---- provider prices, USD per million tokens (input, output) ---------------------------------------
# Claude: claude-api skill, cached 2026-06-24. Sonnet 5 carries an introductory rate through
# 2026-08-31 -- today is inside that window, so both are shown.
PRICES = {
    "Claude Opus 5":            (5.00, 25.00),
    "Claude Sonnet 5 (intro)":  (2.00, 10.00),
    "Claude Sonnet 5 (list)":   (3.00, 15.00),
    "Claude Haiku 4.5":         (1.00,  5.00),
    "DeepSeek V4-Pro":          (0.435, 0.87),
    "DeepSeek V4-Flash":        (0.14,  0.28),
    "OpenAI GPT-5.5":           (5.00, 30.00),
    "OpenAI GPT-5.6 Terra":     (2.50, 15.00),
}
BATCH_DISCOUNT = 0.50          # Claude and OpenAI both halve batched work; not usable interactively
CACHE_READ_MULT = 0.10         # Claude cache read ~0.1x input


def measure_artifact():
    """OUTPUT tokens for one stock's research artefact, from a real committed file.
    ~4 chars/token is the standard English approximation; this is a measurement of the artefact's
    size, and only the chars->tokens step is an approximation."""
    p = os.path.join(RES, "pf_qual_TMCV.json")
    if not os.path.exists(p):
        return None, None
    with open(p, encoding="utf-8") as fh:
        blob = json.load(fh)
    prose = "".join(str(v) for k, v in blob.items() if isinstance(v, str))
    return len(prose), int(len(prose) / 4)


# ---- the workload ----------------------------------------------------------------------------------
# Per-agent (tokens_in, tokens_out). LOW / MID / HIGH bands on the input side, because cumulative
# input on a multi-turn tool-using agent is what dominates and is what we have not metered.
def workload(art_out):
    """art_out: measured output tokens for one research artefact."""
    return {
        # stage:                          (count, in_low, in_mid, in_high, out_each, tier, cold_only)
        "Stock research (deep, websearch)": (N_STOCKS, 180_000, 350_000, 600_000, art_out, "worker", True),
        "Technical agent (price parquet)":  (N_STOCKS,  40_000,  80_000, 150_000,  1_500, "worker", True),
        "Fund mapping (QFRA, websearch)":   (N_FUNDS,   30_000,  60_000, 120_000,  1_200, "worker", True),
        "Data module authoring":            (1,        150_000, 300_000, 600_000, 40_000, "judge",  False),
        "Orchestration + QA reading":       (1,        100_000, 200_000, 400_000, 15_000, "judge",  False),
        "Red-team / review pass":           (1,         60_000, 120_000, 250_000,  8_000, "judge",  False),
    }


ZERO_TOKEN_STAGES = [
    "client_intake.py (ISIN join)",
    "fix_thin_coverage_v3.py (scoring correction)",
    "earnings_quality_decomp.py (profit bridge)",
    "build_<client>.py (the whole PPTX, all tiers)",
    "check_geometry / check_geometry2 / tellscan / check_dots / check_method",
    "build_scores_excel.py, build_client_excel.py",
]


def cost(tin, tout, model, batch=False):
    pin, pout = PRICES[model]
    c = tin / 1e6 * pin + tout / 1e6 * pout
    return c * (1 - BATCH_DISCOUNT) if batch else c


def totals(band, warm):
    """Return (tokens_in, tokens_out) split by tier for one band, warm or cold."""
    wl = workload(ART_OUT)
    idx = {"low": 1, "mid": 2, "high": 3}[band]
    agg = {"worker": [0, 0], "judge": [0, 0]}
    for _, (n, lo, mid, hi, oe, tier, cold_only) in wl.items():
        if warm and cold_only:
            continue
        agg[tier][0] += n * (lo, mid, hi)[idx - 1]
        agg[tier][1] += n * oe
    return agg


ART_CHARS, ART_OUT = measure_artifact()
if ART_OUT is None:
    print("pf_qual_TMCV.json missing -- cannot anchor the artefact size. Aborting rather than guess.")
    sys.exit(2)

L = []
L.append("# What one NDPMS deck costs — 30 stocks, 15 funds")
L.append("")
L.append("Prices are per million tokens. **The cold/warm split matters more than the model choice** "
         "— see §3.")
L.append("")
L.append("## 0. Measured anchor")
L.append("")
L.append(f"One stock's research artefact (`results/pf_qual_TMCV.json`, a real committed file) holds "
         f"**{ART_CHARS:,} characters of prose ≈ {ART_OUT:,} output tokens**. That is the per-stock "
         f"output floor, measured rather than assumed.")
L.append("")
L.append("**Not metered in this repo:** cumulative *input* per research agent. `ws4_spend_extract.py` "
         "exists but was never run and no `spend.csv` was ever written, so there is no historical "
         "figure to cite. Input is therefore given as a LOW/MID/HIGH band, and it is the dominant "
         "term — a multi-turn web-search agent re-sends its whole growing history every turn.")
L.append("")

L.append("## 1. The stages that cost zero tokens")
L.append("")
L.append("Verified by reading the code, not assumed. These are plain Python/pandas:")
L.append("")
for s in ZERO_TOKEN_STAGES:
    L.append(f"- `{s}`")
L.append("")
L.append("**The deck itself is free to build.** Every token in this model is spent on *research and "
         "authoring*, never on assembling slides. That is the most useful cost fact here: throwing a "
         "more expensive model at the pipeline does not make the deck better, because the deck-making "
         "part is deterministic.")
L.append("")

# ---- 2. per-model, cold ----------------------------------------------------------------------------
for warm, title, note in [
    (False, "2. COLD — all 45 names need research from scratch",
     "The first time you score these names, or any name outside the 751-stock / 181-fund universe."),
    (True, "3. WARM — names already in the committed universe",
     "The normal case now. All per-name research drops out; only intake, authoring and QA remain."),
]:
    L.append(f"## {title}")
    L.append("")
    L.append(note)
    L.append("")
    L.append("| model | low | **mid** | high | mid, batched |")
    L.append("|---|---:|---:|---:|---:|")
    for model in PRICES:
        row = []
        for band in ("low", "mid", "high"):
            a = totals(band, warm)
            c = (cost(a["worker"][0], a["worker"][1], model)
                 + cost(a["judge"][0], a["judge"][1], model))
            row.append(c)
        a = totals("mid", warm)
        cb = (cost(a["worker"][0], a["worker"][1], model, batch=True)
              + cost(a["judge"][0], a["judge"][1], model, batch=True))
        L.append(f"| {model} | ${row[0]:,.2f} | **${row[1]:,.2f}** | ${row[2]:,.2f} | ${cb:,.2f} |")
    L.append("")
    a = totals("mid", warm)
    ti = a["worker"][0] + a["judge"][0]
    to = a["worker"][1] + a["judge"][1]
    L.append(f"Mid-band volume: **{ti / 1e6:.1f}M input, {to / 1e3:.0f}K output tokens.**")
    L.append("")

# ---- 4. the split-tier build ------------------------------------------------------------------------
L.append("## 4. The build you would actually run (split tiers)")
L.append("")
L.append("Per D-036 and the firm's model policy: mechanical/reading work on the cheap tier, judgment "
         "on the expensive one. Mid band, cold.")
L.append("")
L.append("| workers | judgment | total (cold) | total (warm) |")
L.append("|---|---|---:|---:|")
for wm, jm in [("Claude Haiku 4.5", "Claude Opus 5"),
               ("Claude Sonnet 5 (intro)", "Claude Opus 5"),
               ("DeepSeek V4-Flash", "Claude Opus 5"),
               ("DeepSeek V4-Flash", "Claude Sonnet 5 (intro)"),
               ("DeepSeek V4-Pro", "DeepSeek V4-Pro")]:
    r = []
    for warm in (False, True):
        a = totals("mid", warm)
        r.append(cost(a["worker"][0], a["worker"][1], wm)
                 + cost(a["judge"][0], a["judge"][1], jm))
    L.append(f"| {wm} | {jm} | ${r[0]:,.2f} | ${r[1]:,.2f} |")
L.append("")

# ---- 5. subscription ------------------------------------------------------------------------------
L.append("## 5. Subscription vs API — different shape of cost")
L.append("")
L.append("A subscription is a **fixed** cost with a rate/usage ceiling; the API is **variable** with "
         "no ceiling. So a deck has no marginal price on a subscription — the question is how many "
         "decks fit inside the plan before you hit limits.")
L.append("")
L.append("| decks per month | $20 plan, per deck | $100 plan, per deck |")
L.append("|---:|---:|---:|")
for n in (1, 2, 4, 8, 20):
    L.append(f"| {n} | ${20 / n:,.2f} | ${100 / n:,.2f} |")
L.append("")
a = totals("mid", True)
warm_sonnet = (cost(a["worker"][0], a["worker"][1], "Claude Sonnet 5 (intro)")
               + cost(a["judge"][0], a["judge"][1], "Claude Sonnet 5 (intro)"))
a = totals("mid", False)
cold_sonnet = (cost(a["worker"][0], a["worker"][1], "Claude Sonnet 5 (intro)")
               + cost(a["judge"][0], a["judge"][1], "Claude Sonnet 5 (intro)"))
import math                                                              # noqa: E402
warm_break = math.ceil(100 / warm_sonnet)
cold_break = math.ceil(100 / cold_sonnet)
L.append(f"**Where the $100 plan pays for itself** (mid band, Sonnet 5 intro):")
L.append("")
L.append(f"- A **warm** deck is about **${warm_sonnet:,.2f}** on the API, so the plan only wins past "
         f"roughly **{warm_break} decks/month**. Below that, pay-as-you-go is cheaper.")
L.append(f"- A **cold** deck is about **${cold_sonnet:,.2f}**, so the plan breaks even at about "
         f"**{cold_break} decks/month**.")
L.append("")
L.append("The caveat that matters more than either figure: a cold deck fans out 45 research agents, "
         "and a subscription's rate limits — not its price — are what decide whether you can finish "
         "one in a sitting. The API has no such ceiling. That is the real reason to hold both.")
L.append("")
L.append("## 6. What actually moves the number")
L.append("")
L.append("1. **Warm beats cold by roughly an order of magnitude.** Committing the score and grade "
         "files to the repo was the single largest cost decision in this pipeline.")
L.append("2. **Input dominates, so caching is the biggest API lever.** Claude cache reads are ~0.1x "
         "input. A stable system prompt + score-file prefix across 30 near-identical research agents "
         "is exactly the shape prompt caching is for.")
L.append("3. **Batch halves it** on Claude and OpenAI — fine for overnight scoring runs, useless for "
         "interactive deck work.")
L.append("4. **Model tier is the *smallest* lever of the three.** Cheapest-to-dearest across the "
         "whole table is a wide spread, but caching plus warm-vs-cold swamps it.")
L.append("")
L.append("### Caveats")
L.append("")
L.append("- The input band is an **estimate**, not a measurement. To replace it with real numbers, "
         "run `ws4_spend_extract.py` against a live transcript directory — it was written for exactly "
         "this and has never been run.")
L.append("- DeepSeek and OpenAI numbers are **price comparisons only**. Neither has been tested on "
         "this pipeline, and neither is an approved data source under D-033. Output *quality* on "
         "forensic equity research is unmeasured here — treat the cheap columns as a budget ceiling, "
         "not a recommendation.")
L.append("- Claude prices are from the `claude-api` skill (cached 2026-06-24). Sonnet 5's intro rate "
         "ends **2026-08-31**; after that its column rises to the list row.")
L.append("- Excludes the technical-agent pass if scores already exist, embeddings, and any human time.")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("\n".join(L))
print(f"\nwrote {OUT}")
