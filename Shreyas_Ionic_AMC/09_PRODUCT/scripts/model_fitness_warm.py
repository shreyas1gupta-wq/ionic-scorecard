# -*- coding: utf-8 -*-
"""WHICH MODEL TO RUN, given scores + templates + skills are already in place.
Principal, 2026-08-13: "assume i already have all scores and other templates and skills in place...
rate the agents basis quality of final output... score basis 100 for each model and then cost and then
for a 3x size portfolio and also with normal 20$ acc subscription sonnet 5 how many and expected time
for 1 deck in api and 20$ sub."

His hypothesis: with the template and scores frozen, low-effort models do the same work cheaper at
similar quality. This tests it rather than assuming it, and the answer is mostly YES -- for a
structural reason worth stating plainly:

    THE DETERMINISTIC GATES SET THE QUALITY FLOOR, NOT THE MODEL.
    check_method catches Sell calls above the frozen bar. tellscan catches AI tells and internal
    jargon. check_dots catches an empty universe join. check_geometry x2 catches layout. All are
    plain Python and run identically regardless of which model authored the input. A cheaper model
    that makes a mechanical mistake gets caught; the gate does not care who wrote the file.

So the residual model-sensitive work is narrow: client-facing PROSE, JUDGMENT calls the gates cannot
express (trim targets, which rationale leads), and DIAGNOSING a gate finding correctly instead of
suppressing it. The rubric below weights exactly those.

[DATA]      Deterministic wall-clock, measured on this machine 2026-08-13 against the real 59-name
            Talaulikar book: HNI_DEEP 103 slides in 6.7s, RM_SIMPLE 30 slides in 2.8s, five gates
            23.5s total. The whole non-model pipeline is ~30 seconds.
[DATA]      Provider prices (claude-api skill 2026-06-24; DeepSeek/OpenAI fetched 2026-08-13).
[DATA]      Pro $20 limits: ~45 messages / 5-hour rolling window, ~40-80 active Sonnet hours/week,
            shared between chat and Claude Code. Anthropic publishes no fixed message count.
[OPINION]   The quality scores. These are reasoned judgments against a stated basis per model, NOT a
            benchmark run on this pipeline. The one measured anchor the firm owns is D-036: Sonnet
            ties or beats Opus on review-type work at ~1/10-1/15th the cost.
[INFERENCE] Token volumes and generation throughput. Not metered here (ws4_spend_extract.py has
            never been run), so bands, not points.
"""
import os

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
OUT = os.path.join(ROOT, "Shreyas_Ionic_AMC", "09_PRODUCT", "reports", "MODEL_FITNESS_WARM.md")

PRICES = {                                    # USD / MTok (in, out)
    "Claude Opus 5":           (5.00, 25.00),
    "Claude Sonnet 5":         (2.00, 10.00),   # intro rate, ends 2026-08-31
    "Claude Haiku 4.5":        (1.00,  5.00),
    "DeepSeek V4-Pro":         (0.435, 0.87),
    "DeepSeek V4-Flash":       (0.14,  0.28),
    "OpenAI GPT-5.5":          (5.00, 30.00),
    "OpenAI GPT-5.6 Terra":    (2.50, 15.00),
}

# ---- the rubric: what actually varies by model once template + scores are frozen -------------------
# Weight = how much of the REMAINING risk each dimension carries. Anything a deterministic gate fully
# covers is deliberately down-weighted, because the gate neutralises model differences there.
DIMS = [
    ("Client-facing prose", 0.28,
     "Tone, SEBI-safe phrasing, sounds like the desk not an LLM. tellscan catches AI TELLS "
     "mechanically but cannot catch dull, wrong, or off-register prose."),
    ("Judgment the gates can't express", 0.24,
     "Trim targets (FM judgment, explicitly not a formula), which rationale leads a Sell card, "
     "concentration reads. No gate encodes these."),
    ("Gate-failure diagnosis", 0.20,
     "A geometry overlap or a check_method finding must be FIXED, not suppressed. This session's "
     "real examples: legend colliding with source(), 3 stale MAXROWS refs, Circle-as-ellipse."),
    ("Long-spec instruction following", 0.14,
     "SKILL.md is ~1,440 lines of frozen rules. Holding the ladder, the Sell/Hold-only vocabulary "
     "and the no-restated-threshold rule across a long session."),
    ("Rule adherence (gate-backed)", 0.08,
     "Down-weighted ON PURPOSE: check_method already catches ladder violations regardless of model."),
    ("Silent-failure resistance", 0.06,
     "Noticing a deck that built cleanly with no data. Now largely covered by check_dots, so "
     "down-weighted -- it was 20%+ before that gate existed."),
]

# per-model scores per dimension (0-100), with the basis recorded
SCORES = {
    "Claude Opus 5":        (92, 95, 96, 93, 95, 94,
                             "Top tier on judgment and on diagnosing its own output; docs cite high "
                             "precision AND recall on code review, and self-verification without "
                             "prompting. Its headroom is largely WASTED here: the hard parts "
                             "(scoring, layout) are already frozen in code. Needs the conciseness "
                             "and scope-discipline instructions or it pads deliverables."),
    "Claude Sonnet 5":      (88, 86, 89, 92, 95, 90,
                             "The best FIT, not merely the value pick. Near-Opus on coding/agentic; "
                             "follows instructions literally, which is what a frozen spec wants; "
                             "effort ladder to xhigh for the rare hard diagnosis. D-036 measured it "
                             "tying or beating Opus on review-type work."),
    "Claude Haiku 4.5":     (70, 62, 64, 72, 90, 78,
                             "Fine for transcription and running scripts. Weakest on novel diagnosis "
                             "and on prose that must carry a desk's voice. 200K context (vs 1M) is a "
                             "real constraint against a 1,440-line skill plus score data."),
    "DeepSeek V4-Pro":      (72, 80, 82, 80, 88, 78,
                             "Strong reasoning and 1M context. UNVALIDATED on this pipeline, and the "
                             "specific gap is Indian-market client prose under SEBI constraints in a "
                             "house voice -- nobody has tested that. Not an approved source (D-033)."),
    "DeepSeek V4-Flash":    (58, 60, 62, 68, 85, 66,
                             "Cheap and adequate for mechanical passes. Same unvalidated-prose and "
                             "governance concerns, with less reasoning headroom for diagnosis."),
    "OpenAI GPT-5.5":       (86, 88, 88, 86, 92, 86,
                             "Capable, and the quality gap to Claude on this task is small. The cost "
                             "is NOT tokens: skills, subagents, hooks and SKILL.md are Claude Code "
                             "constructs, so the harness would need rebuilding."),
    "OpenAI GPT-5.6 Terra": (80, 78, 80, 80, 90, 80,
                             "Mid-tier OpenAI. Same harness-rebuild cost, less capability than 5.5."),
}

# ---- warm-case token volumes (INFERENCE, bands) ----------------------------------------------------
# Stages that remain when scores/templates/skills exist. Data-module authoring scales with NAMES;
# orchestration and QA are part fixed, part scaling (more rows -> more pages -> more findings).
def volumes(n_stocks, n_funds, band="mid"):
    names = n_stocks + n_funds
    base = 45                                  # the 30+15 reference book
    lin = names / base
    idx = {"low": 0, "mid": 1, "high": 2}[band]
    # (in_low, in_mid, in_high, out) -- authoring scales linearly, QA at 0.5x linear + fixed
    author_in = (150_000, 300_000, 600_000)[idx] * lin
    author_out = 40_000 * lin
    qa_in = (100_000, 200_000, 400_000)[idx] * (0.5 + 0.5 * lin)
    qa_out = 15_000 * (0.5 + 0.5 * lin)
    rev_in = (60_000, 120_000, 250_000)[idx] * lin
    rev_out = 8_000 * lin
    return author_in + qa_in + rev_in, author_out + qa_out + rev_out


def usd(tin, tout, model):
    pin, pout = PRICES[model]
    return tin / 1e6 * pin + tout / 1e6 * pout


# ---- measured deterministic wall-clock -------------------------------------------------------------
DET_BUILD_HNI, DET_BUILD_RM, DET_GATES = 6.7, 2.8, 23.5     # seconds, measured 2026-08-13
DET_TOTAL = DET_BUILD_HNI + DET_BUILD_RM + DET_GATES

# generation throughput, output tokens/sec [INFERENCE]
TPS = {"Claude Opus 5": 55, "Claude Sonnet 5": 80, "Claude Haiku 4.5": 150,
       "DeepSeek V4-Pro": 45, "DeepSeek V4-Flash": 90,
       "OpenAI GPT-5.5": 60, "OpenAI GPT-5.6 Terra": 80}
# wall-clock is not just generation: tool round-trips, file reads, thinking, gate re-runs.
WALL_MULT = 3.2

L = []
A = L.append
A("# Which model to run, once scores + templates + skills are frozen")
A("")
A("Assumes the 751-stock scores, 181-fund grades, `pr_template`, and the skill are all in place. "
  "So **no per-name research** — the warm case only.")
A("")
A("## 0. Why the Principal's hypothesis is right")
A("")
A("**The deterministic gates set the quality floor, not the model.** `check_method` catches Sell "
  "calls above the frozen bar; `tellscan` catches AI tells and internal jargon; `check_dots` catches "
  "an empty universe join; `check_geometry` ×2 catches layout. All plain Python, all indifferent to "
  "which model wrote the input.")
A("")
A(f"**And the deck is nearly free in time as well as money.** Measured on this machine today against "
  f"the real 59-name book: HNI_DEEP {DET_BUILD_HNI}s for 103 slides, RM_SIMPLE {DET_BUILD_RM}s, all "
  f"five gates {DET_GATES}s. **The entire non-model pipeline is ~{DET_TOTAL:.0f} seconds.**")
A("")
A("So the residual model-sensitive work is narrow — prose, judgment the gates can't express, and "
  "diagnosing a finding correctly instead of papering over it. The rubric weights those.")
A("")

A("## 1. Rubric — weighted to the residual risk")
A("")
A("| dimension | weight | why |")
A("|---|---:|---|")
for nm, w, why in DIMS:
    A(f"| {nm} | {w:.0%} | {why} |")
A("")
A("Two dimensions are **deliberately down-weighted** because a gate now covers them. "
  "Silent-failure resistance would have carried 20%+ before `check_dots` existed — building that "
  "gate is what made a cheaper model safe here.")
A("")

A("## 2. Quality score out of 100")
A("")
A("| model | score | prose | judgment | diagnosis | long-spec | rules | silent-fail |")
A("|---|---:|---:|---:|---:|---:|---:|---:|")
ranked = []
for m, vals in SCORES.items():
    s = sum(v * w for v, (_, w, _) in zip(vals[:6], DIMS))
    ranked.append((s, m))
    A(f"| {m} | **{s:.1f}** | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} | {vals[4]} | {vals[5]} |")
A("")
A("**Basis for each score:**")
A("")
for m, vals in SCORES.items():
    A(f"- **{m}** — {vals[6]}")
A("")

A("## 3. Cost and value — 1× (30+15) and 3× (90+45), warm")
A("")
A("| model | score | 1× deck | 3× deck | score per $ (3×) |")
A("|---|---:|---:|---:|---:|")
ranked.sort(reverse=True)
rows = []
for s, m in ranked:
    i1, o1 = volumes(30, 15)
    i3, o3 = volumes(90, 45)
    c1, c3 = usd(i1, o1, m), usd(i3, o3, m)
    rows.append((m, s, c1, c3))
    A(f"| {m} | {s:.1f} | ${c1:,.2f} | ${c3:,.2f} | {s / c3:,.0f} |")
A("")
i1, o1 = volumes(30, 15)
i3, o3 = volumes(90, 45)
A(f"Volumes (mid band): 1× ≈ **{i1/1e6:.1f}M in / {o1/1e3:.0f}K out**; "
  f"3× ≈ **{i3/1e6:.1f}M in / {o3/1e3:.0f}K out**. Note 3× is **~2.6×** the cost, not 3× — "
  f"orchestration and QA don't scale fully with name count.")
A("")

A("## 4. The verdict on the hypothesis")
A("")
top = rows[0]
son = next(r for r in rows if r[0] == "Claude Sonnet 5")
hai = next(r for r in rows if r[0] == "Claude Haiku 4.5")
opu = next(r for r in rows if r[0] == "Claude Opus 5")
A(f"- **Sonnet 5 is the pick.** {son[1]:.1f}/100 at **${son[3]:,.2f}** for a 3× deck, against Opus 5's "
  f"{opu[1]:.1f} at **${opu[3]:,.2f}**. You give up {opu[1] - son[1]:.1f} points and pay "
  f"**{opu[3] / son[3]:.1f}× less**. On a frozen template that trade is clearly right.")
A(f"- **Haiku is the honest floor, not a free lunch.** {hai[1]:.1f}/100 at ${hai[3]:,.2f} — "
  f"{son[1] - hai[1]:.1f} points below Sonnet. Fine for transcription passes and script running; the "
  f"gap is concentrated in prose and diagnosis, which is exactly what a *client-facing* deliverable "
  f"is made of. Use it for the mechanical sub-steps, not for authoring the data module.")
A("- **Where the hypothesis breaks:** the residual work is the judgment part *specifically because* "
  "everything mechanical was automated. Freezing the template removed the cheap-model risk on layout "
  "and rules — it did not remove it on prose and trim targets, which are now a larger share of "
  "what's left.")
A("- **DeepSeek and OpenAI are priced, not recommended.** For OpenAI the blocker isn't quality "
  "(GPT-5.5 scores well) — it's that skills, subagents and hooks are Claude Code constructs, so the "
  "harness needs rebuilding. That switching cost dwarfs the token saving.")
A("")

A("## 5. Time for one deck — API vs $20 subscription")
A("")
A("| model | output tokens (3×) | generation | + tool/read/fix | **wall-clock** |")
A("|---|---:|---:|---:|---:|")
for s, m in ranked:
    if m not in TPS:
        continue
    _, o3 = volumes(90, 45)
    gen = o3 / TPS[m] / 60
    wall = gen * WALL_MULT + DET_TOTAL / 60
    A(f"| {m} | {o3/1e3:.0f}K | {gen:.0f} min | ×{WALL_MULT} | **{wall:.0f} min** |")
A("")
_, o1 = volumes(30, 15)
gen1 = o1 / TPS["Claude Sonnet 5"] / 60
wall1 = gen1 * WALL_MULT + DET_TOTAL / 60
A(f"For a **1× deck on Sonnet 5**: ~{gen1:.0f} min of generation → **~{wall1:.0f} min wall-clock** "
  f"on the API. The ~{DET_TOTAL:.0f}s of building and gating is a rounding error.")
A("")
A("### On the $20 Pro plan")
A("")
A("Pro is **~45 messages per rolling 5-hour window**, ~40–80 active Sonnet hours/week, shared "
  "between the chat app and Claude Code. Anthropic publishes no fixed count, so treat these as "
  "planning figures and check Settings → Usage.")
A("")
A("| | 1× deck (30+15) | 3× deck (90+45) |")
A("|---|---|---|")
A("| API wall-clock | ~%.0f min | ~%.0f min |" % (wall1, next(
    volumes(90, 45)[1] / TPS["Claude Sonnet 5"] / 60 * WALL_MULT + DET_TOTAL / 60 for _ in [0])))
A("| Turns consumed (est.) | ~40–70 | ~100–180 |")
A("| Fits one 5-hour window? | Yes, comfortably | **No — 2–4 windows** |")
A("| Decks per week, Pro | ~8–14 | ~3–5 |")
A("")
A("**So on the $20 plan: roughly 8–14 warm 1× decks a week, or 3–5 at 3× size** — and that assumes "
  "the account does nothing else, which is not how you actually use it. A 3× deck **will not finish "
  "in one sitting on Pro**: it spans 2–4 rate-limit windows, so the wall-clock stretches from ~1 hour "
  "of work to most of a day of waiting.")
A("")
A("**The practical split:** Pro for 1× decks and iteration — the marginal cost is zero and one fits "
  "in a window. API for 3× books and anything time-boxed, where **$%.2f buys you no rate ceiling** "
  "and the deck lands in about an hour instead of spanning windows." % son[3])
A("")
A("## Caveats")
A("")
A("- **The quality scores are reasoned judgment, not a benchmark on this pipeline.** The only "
  "measured anchor the firm owns is D-036 (Sonnet ties/beats Opus on review work). To make these "
  "numbers real, run the same client book through two models and grade the decks blind.")
A("- **Token volumes and throughput are estimates.** `ws4_spend_extract.py` was written to meter "
  "exactly this and has never been run.")
A("- Deterministic wall-clock IS measured, on this machine, against the real 59-name book.")
A("- Sonnet 5's $2/$10 intro rate ends **2026-08-31**; after that every Sonnet figure here rises 50%.")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("\n".join(L))
print(f"\nwrote {OUT}")
