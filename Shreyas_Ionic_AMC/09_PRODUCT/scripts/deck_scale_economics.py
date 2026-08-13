# -*- coding: utf-8 -*-
"""SCALING THE DECK PIPELINE — parallelism, model mixing, subscription vs API, and self-hosting.
Principal, 2026-08-13: "how can we further optimize and faster this process multiple agents on
different works and mix of agents... also recheck the 20$ decks u gave since 20$ plan has very less
cost compared to the api cost... and if we plan to run using open source 2T para model or deepseek
latest open source how much one time setup cost... and if we do 100 deck per day when it will be a
breakeven (assume we also use the left idle time for rnd instead of idle wasting)".

THE PRINCIPAL IS RIGHT ABOUT THE SUBSCRIPTION AND I WAS WRONG. Earlier I framed the plan as winning
only past ~54 decks/month. That figure came from dividing the $100 Max price by the API cost of a
deck, which answers "when does the plan cost less than the API" -- but I then failed to compare it
against what the plan can ACTUALLY produce. Pro's throughput is roughly 8-14 warm 1x decks a week,
i.e. ~35-60 a month, which is 3-5x past its own break-even. The subscription is the cheaper way to
make decks by a wide margin; the API's value is not price, it is the absence of a rate ceiling.
Corrected in section 1 with the comparison stated both ways.

[DATA]      Deterministic wall-clock, measured here 2026-08-13: 103-slide build 6.7s, RM_SIMPLE 2.8s,
            five gates 23.5s -> ~33s for the whole non-model pipeline.
[DATA]      Prices: Claude from the claude-api skill (2026-06-24); DeepSeek/OpenAI and GPU rental
            fetched 2026-08-13 (URLs in the report).
[DATA]      8xH100 node ~$16-30/hr (~$12-22k/mo 24/7). DeepSeek-671B-class fits 8xH100 80GB at FP8;
            decode ~1,400-1,800 tok/s aggregate, batch=8, vLLM. Published self-host break-even for
            that class lands around 3-4 BILLION tokens/day.
[INFERENCE] Token volumes, throughput, and the serial fraction in the parallelism model.
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
OUT = os.path.join(ROOT, "Shreyas_Ionic_AMC", "09_PRODUCT", "reports", "DECK_SCALE_ECONOMICS.md")

PRICES = {"Opus 5": (5.00, 25.00), "Sonnet 5": (2.00, 10.00), "Haiku 4.5": (1.00, 5.00),
          "DeepSeek V4-Pro": (0.435, 0.87), "DeepSeek V4-Flash": (0.14, 0.28)}

# warm-case volumes from model_fitness_warm.py
VOL_1X = (0.6e6, 63_000)          # (input, output) tokens
VOL_3X = (1.7e6, 174_000)
DET_SECONDS = 33.0
WALL_1X_MIN, WALL_3X_MIN = 43.0, 117.0        # Sonnet 5, serial, from the prior model
PRO_DECKS_WK = (8, 14)                        # warm 1x decks/week on $20 Pro


def usd(vol, model):
    pin, pout = PRICES[model]
    return vol[0] / 1e6 * pin + vol[1] / 1e6 * pout


L = []
A = L.append
A("# Scaling the deck pipeline — parallelism, model mixing, subscription, self-hosting")
A("")

# ---- 1. THE CORRECTION -----------------------------------------------------------------------------
A("## 1. Correction: the subscription is the cheap option, not the API")
A("")
A("The Principal challenged my earlier framing and he is right. I said the plan \"only wins past ~54 "
  "decks/month\" — that divides the plan price by the API cost of one deck, which answers *when does "
  "the plan cost less than the API*. What I failed to do is check it against **what the plan can "
  "actually produce.**")
A("")
api_1x = usd(VOL_1X, "Sonnet 5")
api_3x = usd(VOL_3X, "Sonnet 5")
lo, hi = PRO_DECKS_WK[0] * 4.3, PRO_DECKS_WK[1] * 4.3
A("| | $20 Pro | API (Sonnet 5) |")
A("|---|---|---|")
A(f"| Cost per warm 1× deck | **${20/hi:,.2f} – ${20/lo:,.2f}** | ${api_1x:,.2f} |")
A(f"| Monthly capacity | ~{lo:.0f}–{hi:.0f} decks | unlimited |")
A(f"| Break-even vs API | {20/api_1x:.0f} decks/month | — |")
A(f"| Actual capacity vs break-even | **{lo/(20/api_1x):.1f}–{hi/(20/api_1x):.1f}×past it** | — |")
A("")
A(f"**At full utilisation Pro is {api_1x/(20/((lo+hi)/2)):.1f}× cheaper per deck than the API.** The "
  f"plan's break-even is only ~{20/api_1x:.0f} decks a month and it can do {lo:.0f}–{hi:.0f}. So the "
  f"honest ranking is: **subscription for cost, API for control.** The API buys three things a plan "
  f"cannot — no rate ceiling, real parallelism, and programmatic invocation — and you pay roughly "
  f"{api_1x/(20/((lo+hi)/2)):.1f}× per deck for them.")
A("")

# ---- 2. PARALLELISM --------------------------------------------------------------------------------
A("## 2. Making it faster — where the wall-clock actually is")
A("")
A(f"The deterministic pipeline is **{DET_SECONDS:.0f} seconds** (measured). A 3× deck takes "
  f"~{WALL_3X_MIN:.0f} minutes. So essentially **all** the wall-clock is model authoring, and the "
  f"authoring is *embarrassingly parallel by name* — 90 stocks' prose blocks are independent.")
A("")
A("Amdahl's law on this shape. Serial fraction ≈ 28% (reading the book, planning, the final "
  "cross-panel read, and fixing gate findings); parallel ≈ 72% (per-name prose).")
A("")
A("| parallel agents | 3× deck wall-clock | speed-up | note |")
A("|---:|---:|---:|---|")
S, P = 0.28, 0.72
for n in (1, 2, 3, 6, 12, 24):
    t = WALL_3X_MIN * (S + P / n)
    note = ""
    if n == 3:
        note = "**the firm's D-023 cap**"
    elif n == 6:
        note = "knee of the curve"
    elif n == 24:
        note = "diminishing — serial floor dominates"
    A(f"| {n} | {t:.0f} min | {WALL_3X_MIN/t:.1f}× | {note} |")
A(f"| ∞ | {WALL_3X_MIN*S:.0f} min | {1/S:.1f}× | hard serial floor |")
A("")
A("**Three things follow:**")
A("")
A("1. **Going from 1 to 6 agents is the whole win** — 117 → 47 min. Past 6, the serial 28% dominates "
  "and you are buying minutes for money. D-023's cap of 3 already gets you to ~61 min; raising it to "
  "6 is worth more than raising it to 24.")
A("2. **Shard by name, merge in code.** Each agent writes a *fragment* (one JSON or .py file per "
  "block of names); a deterministic script assembles `data/<client>.py`. If agents instead edit one "
  "shared file, the merge becomes serial token work and you lose the speed-up you just bought — and "
  "on a real merge it also risks the conflict class we hit on the 14 `pf_qual` files.")
A("3. **Cut the serial 28%, not the parallel 72%.** The serial part is dominated by gate-finding "
  "fixes. Every new deterministic gate (like `check_dots`) converts a slow human-ish diagnosis loop "
  "into a 2-second script — that is the highest-leverage speed work left.")
A("")

# ---- 3. MODEL MIXING ------------------------------------------------------------------------------
A("## 3. The mixed-model routing table")
A("")
A("Route each sub-task to the cheapest model that clears *its own* quality bar — not the deck's.")
A("")
ROUTE = [
    ("Field transcription, plumbing, running scripts", 0.15, "DeepSeek V4-Flash", "Haiku 4.5",
     "Pure mechanical mapping. Gates catch errors; no house voice needed."),
    ("Prose for Sell/Trim cards", 0.50, "Sonnet 5", "Sonnet 5",
     "The client-facing deliverable. tellscan catches AI tells but not off-register prose. "
     "Do NOT cheap out here — it is 50% of the tokens and ~100% of what the client reads."),
    ("Trim targets, concentration, which rationale leads", 0.10, "Opus 5", "Opus 5",
     "Explicitly FM judgment, not a formula. Few calls, high stakes, capital-facing — the one place "
     "the Opus premium is genuinely earned."),
    ("Gate-finding diagnosis + fixes", 0.15, "Sonnet 5", "Opus 5 on repeat failure",
     "Sonnet handles most; escalate only when the same gate fails twice."),
    ("Red-team / cross-check of the authored deck", 0.10, "DeepSeek V4-Pro", "Sonnet 5",
     "**Different family on purpose.** D-036 measured a same-family judge inflating its own family's "
     "score by +0.5 to +1.0/10. A non-Claude reviewer of Claude prose is methodologically better, "
     "not just cheaper."),
]
A("| sub-task | token share | primary | escalate to | why |")
A("|---|---:|---|---|---|")
for t, sh, pri, esc, why in ROUTE:
    A(f"| {t} | {sh:.0%} | **{pri}** | {esc} | {why} |")
A("")
blend_1x = sum(usd((VOL_1X[0] * sh, VOL_1X[1] * sh), pri) for _, sh, pri, _, _ in ROUTE)
blend_3x = sum(usd((VOL_3X[0] * sh, VOL_3X[1] * sh), pri) for _, sh, pri, _, _ in ROUTE)
A("| build | 1× deck | 3× deck |")
A("|---|---:|---:|")
A(f"| All Opus 5 | ${usd(VOL_1X,'Opus 5'):,.2f} | ${usd(VOL_3X,'Opus 5'):,.2f} |")
A(f"| All Sonnet 5 | ${api_1x:,.2f} | ${api_3x:,.2f} |")
A(f"| **Mixed (table above)** | **${blend_1x:,.2f}** | **${blend_3x:,.2f}** |")
A(f"| All DeepSeek V4-Flash | ${usd(VOL_1X,'DeepSeek V4-Flash'):,.2f} | "
  f"${usd(VOL_3X,'DeepSeek V4-Flash'):,.2f} |")
A("")
A(f"Mixing saves **{(1-blend_3x/api_3x)*100:.0f}%** against all-Sonnet while *raising* quality on the "
  f"judgment calls (Opus where it matters) and improving review independence (non-Claude red team). "
  f"That is the rare case where cheaper and better point the same way.")
A("")
A("**Add prompt caching before any of this.** Claude cache reads are ~0.1× input, and 90 near-"
  "identical authoring agents sharing a system prompt + score-file prefix is exactly the shape "
  "caching is built for. Input is ~90% of the token volume here, so caching is a bigger lever than "
  "the entire model-mix decision.")
A("")

# ---- 4. SELF-HOSTING ------------------------------------------------------------------------------
A("## 4. Self-hosting at 100 decks/day — the arithmetic says no")
A("")
d100_in, d100_out = VOL_1X[0] * 100, VOL_1X[1] * 100
d100_tot = d100_in + d100_out
A(f"**100 warm 1× decks/day = {d100_in/1e6:.0f}M input + {d100_out/1e6:.1f}M output ≈ "
  f"{d100_tot/1e6:.0f}M tokens/day.**")
A("")
A(f"That sounds like a lot. It is not. The published self-host break-even for a 671B-class open-weight "
  f"model lands around **3–4 billion tokens/day** — you would be at "
  f"**{d100_tot/3.5e9*100:.1f}% of it**, roughly **{3.5e9/d100_tot:.0f}× below** the crossover.")
A("")
tps = 1600                     # aggregate decode tok/s, 8xH100 batch=8 vLLM [DATA]
gpu_sec = d100_out / tps
A("| | figure |")
A("|---|---|")
A(f"| GPU-time 100 decks/day actually needs | {gpu_sec/60:.0f} min/day |")
A(f"| Utilisation of one 8×H100 node | **{gpu_sec/86400*100:.1f}%** |")
A(f"| Node cost (rented, 24/7) | $12,000–22,000/month |")
A(f"| Same work on the API (mixed routing) | **${blend_1x*100*30:,.0f}/month** |")
A(f"| Same work, all-Sonnet API | ${api_1x*100*30:,.0f}/month |")
A("")
A(f"**Renting is {12000/(blend_1x*100*30):.0f}–{22000/(blend_1x*100*30):.0f}× more expensive than the "
  f"API for this workload**, and the node sits ~{100-gpu_sec/86400*100:.0f}% idle. Buying is worse: "
  f"an 8×H100/H200 node is roughly $250–350k of capital before power, cooling, and the engineer who "
  f"keeps vLLM running.")
A("")
A("### On a 2T-parameter model")
A("")
A("A 2T model at FP8 is ~2TB of weights before KV cache — call it 2.5–3TB of VRAM, so ~20+ H200s or "
  "several B200 nodes: **$1.5–2.5M of capital**, and that is for a class of model with no strong "
  "open-weight release you could actually serve. This is not a cost-optimisation question at your "
  "volume; it is a different business.")
A("")
A("### Does R&D backfill rescue it?")
A("")
A(f"This is the right question and the answer is still no, but for an instructive reason. The node is "
  f"~{100-gpu_sec/86400*100:.0f}% idle, so to justify $12–22k/month you must fill it with work that "
  f"would *otherwise be paid for*. Filling it completely means finding "
  f"**~{3.5e9/1e6:,.0f}M tokens/day** of genuine R&D demand — about "
  f"**{3.5e9/d100_tot:.0f}× your entire 100-deck/day production load.**")
A("")
A("Two things make that harder than it looks:")
A("")
A("1. **Idle capacity is not free R&D.** Backtests and scoring runs in this firm are *pandas*, not "
  "inference — the measured 33-second deck build is the proof. Your heavy compute is CPU-bound; a "
  "GPU cluster does not absorb it.")
A("2. **You would be betting against the price curve.** API prices have fallen persistently, and "
  "Sonnet 5 is *currently* running an introductory rate. Capital committed to owned hardware is "
  "priced at today's alternative; the alternative keeps getting cheaper.")
A("")
A("**Where self-hosting would start to make sense:** sustained billions of tokens/day, a hard data-"
  "residency requirement that forbids external APIs, or a genuinely fine-tuned model you cannot get "
  "commercially. None of those is the deck pipeline.")
A("")

# ---- 5. THE ACTUAL PLAN ---------------------------------------------------------------------------
A("## 5. What to do, in order of payback")
A("")
A("| # | action | effect | effort |")
A("|---|---|---|---|")
A("| 1 | **Meter it.** Run `ws4_spend_extract.py` against one live transcript | replaces every "
  "estimate here with fact | hours |")
A("| 2 | **Prompt caching** on the shared authoring prefix | ~biggest cost lever; input is ~90% of "
  "volume | small |")
A("| 3 | **Shard authoring by name, merge in code** | 117 → ~61 min at D-023's cap of 3 | medium |")
A("| 4 | **Raise the parallel cap 3 → 6** for authoring only | 61 → 47 min | policy change |")
A("| 5 | **Mixed routing** per §3 | −%d%% cost, better judgment + review independence | medium |"
  % round((1 - blend_3x / api_3x) * 100))
A("| 6 | **Keep Pro for 1× decks, API for 3× and time-boxed work** | cheapest per deck + no ceiling "
  "when needed | none |")
A("| 7 | **Write more deterministic gates** | cuts the serial 28% that caps all parallelism | ongoing |")
A("| — | ~~Self-host~~ | 50–60× below break-even | don't |")
A("")
A("## Caveats")
A("")
A("- Pro's throughput (8–14 decks/week) is itself an estimate built on ~45 messages/5-hour window; "
  "Anthropic publishes no fixed count, and the current weekly-limit promotion runs only to "
  "**2026-08-19**. Check Settings → Usage before planning against it.")
A("- Token volumes, throughput and the 28% serial fraction are **estimates**. Item 1 above fixes that.")
A("- Sonnet 5's $2/$10 intro rate ends **2026-08-31**; every Sonnet figure here rises ~50% after.")
A("- DeepSeek remains unvalidated on this pipeline and is not an approved source under D-033. Its "
  "role in §3 is red-team *cross-check*, where family independence is the point — not authoring "
  "client prose.")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("\n".join(L))
print(f"\nwrote {OUT}")
