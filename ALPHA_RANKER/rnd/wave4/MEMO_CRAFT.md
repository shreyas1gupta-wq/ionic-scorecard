# MEMO CRAFT — how top PMS/AIF managers express thesis + conviction, distilled for ALPHA_RANKER's per-stock output
Author: Ananya Iyer (Head of Equity Research, E-003). 2026-07-17.
Source: `Shreyas_Ionic_AMC/04_RND_LAB/PMS_STUDY_20260712/notes_*.md` (10 managers, all extract claims
independently verified per SYNTHESIS.md L2). Every craft element below is quoted or closely paraphrased
from a named source file+line; nothing is invented. Tags: [DATA]=verbatim/near-verbatim, [INFERENCE]=my
construction from a named pattern, [OPINION]=my editorial judgment on what to adopt.

---

## 1. THE BIGGEST TAKEAWAY (read this first)

**[OPINION]** The best managers do NOT lead with the score or the multiple — they lead with a single
falsifiable claim about what changes, followed immediately by the one fact that would prove them wrong.
SageOne's own admitted mistake pattern (see SYNTHESIS.md SS1 row 7, SS3) is instructive precisely because
he STATES his exit hierarchy in rank order — deterioration-of-the-thesis beats valuation-discomfort as a
sell trigger, every time, and he says so in writing. Marcellus's letters, by contrast, subordinate
valuation to quality without ever stating what would flip that stance — and that is the documented
proximate cause of a negative-alpha-since-inception outcome (SYNTHESIS.md SS2). **The craft lesson for
ALPHA_RANKER: a conviction score without an explicit "what would change my mind" clause is exactly the
failure mode we have independent evidence for.** Every per-stock thesis paragraph the ranker emits MUST
end with a falsification condition, not a valuation comfort statement.

---

## 2. THE THESIS SKELETON (what / why-now / what-would-break-it / margin-of-safety)

Distilled from convergent patterns across the 10 managers (not any single manager's literal template —
none of them publish a fill-in-the-blank memo format; this is the skeleton that recurs across their
letters and disclosure documents):

| Slot | What it does | Source language that inspired it |
|---|---|---|
| **WHAT** (1 sentence) | The specific, checkable claim — not "good company," but the mechanism | ValueQuest's "variant perception" — a position where their view differs meaningfully from consensus, stated as a specific belief, not a vibe [DATA: notes_valuequest.md L54] |
| **WHY NOW** (1 sentence) | The trigger that makes this a NOW decision, not a standing truism | Carnelian's "Magic" basket catalyst identification — management/CEO change, industry-structure change, new growth catalyst, capex-phase completion [DATA: notes_carnelian.md L122]; Solidarity's phase language — "first big break by a marquee customer," "moat emerging," "leadership depth visible" [DATA: notes_solidarity.md L372] |
| **WHAT WOULD BREAK IT** (1 sentence, MANDATORY) | The single fact that, if observed, ends the thesis — not a price level | SageOne's ranked exit hierarchy: (1) business-environment deterioration impairing the growth hurdle = fastest-acting; (2) capital-allocation red flags; (3) valuation "beyond comfort" = most flexible, and the trigger he admits he gets wrong [DATA: SYNTHESIS.md SS3, row SageOne]; Solidarity's governance exit — "management stopped communicating for a long period" [DATA: notes_solidarity.md L391-392] |
| **MARGIN OF SAFETY** (1 sentence) | Why the downside is bounded even if WHY-NOW doesn't play out on schedule | Carnelian's "value cannot grow faster than earnings" discipline [DATA: SYNTHESIS.md SS1 row 5]; Bandhan/Gunwani's DCF-margin-of-safety-on-long-run-cashflows framing for loss-making names [DATA: notes_bandhan_smallcap.md L43] |

**[INFERENCE] Template sentence structure** (adopt verbatim as the per-stock paragraph skeleton):
> "[WHAT]: {company} is priced for {consensus assumption}, but {specific mechanism} implies {differentiated view}.
> [WHY NOW]: this is timely because {catalyst/inflection with an approximate date or trigger}.
> [MARGIN OF SAFETY]: even if the catalyst slips, {downside-bounding fact} limits the loss.
> [WHAT WOULD BREAK IT]: this thesis is wrong if {single falsifiable observation} — that is the one thing to watch, not the price."

---

## 3. CONVICTION LANGUAGE → THE -100..+100 SCORE

**[OPINION, informed by DATA below]** The managers studied do NOT use a numeric conviction score in
their investor-facing language — they use POSITION SIZE and HOLDING-PERIOD LANGUAGE as the conviction
proxy, and several are explicit that conviction is a LADDER, not a single decision:

- **Solidarity's position ladder**: initial 3% → 5% → 8% → 10-15%, stepped up only as subsequent
  quarters CONFIRM the thesis [DATA: SYNTHESIS.md SS4 candidate #5; notes_solidarity.md L357]. This
  maps directly onto a score band: a fresh idea should never open at ±80-100; it should open modest and
  the score should RISE with confirming PIT data, not on day one.
- **Marcellus's relative-conviction rotation**: a full exit fires when "a new candidate has HIGHER
  relative conviction and displaces an existing holding" — conviction is comparative across the book, not
  absolute [DATA: notes_marcellus.md L50, item 10b].
- **ValueQuest's asymmetry language**: "variant perception" (view differs from consensus) is explicitly
  paired with "operating leverage" (margin expansion amplifying EPS beyond revenue growth) as the
  SPECIFIC reason a position earns a higher weight [DATA: notes_valuequest.md L54, L73].
- **SageOne's Competitive-Advantage-Period framing**: conviction is a DURATION judgment (how long does
  20%+ growth persist), not a point-in-time snapshot [DATA: SYNTHESIS.md SS5, "Competitive-Advantage-Period
  duration judgment"].

**[INFERENCE] Adoption for ALPHA_RANKER's -100..+100 score:**
1. **Score magnitude should read like a position-sizing instruction, not a probability.** ±80-100 = "this
   is a top-3-position-sized idea if you had a book," not "100% certain." State this explicitly in the
   score's accompanying text so a reader doesn't over-read precision the model doesn't have (matches
   FRAMEWORK_CATALOG's own "Explainability is mandatory" rule, SS17).
2. **A score should carry an implicit ladder-stage, not just a number.** Borrow Solidarity's language:
   describe a fresh/thin-history signal as "initial-stage conviction" (would map to a damped score, e.g.
   cap at ±40-50 regardless of raw factor strength) vs a signal confirmed over multiple PIT quarters as
   "confirmed-stage conviction" (full score range available). This is a genuine craft adoption: it stops
   the ranker from emitting a ±95 on a single fresh data point the way a raw z-score composite would.
3. **Every score ships with its OWN falsification clause** (SS1 above), in the manager's register — not
   "sell if price drops 15%," but "wrong if {fundamental fact} shows up," per SageOne's own admission that
   valuation-only exits are where he is least reliable.

---

## 4. EXIT-TRIGGER ARTICULATION (how the best managers write down "why we'd sell")

**[DATA]** The clearest pattern in the whole study (SYNTHESIS.md SS1 row 8, SS3): managers who RANK their
exit triggers explicitly (deterioration > capital-allocation red flags > valuation, SageOne) show
materially better realized outcomes than the one manager with **no disclosed mechanical exit rule at all**
(Marcellus CCP — negative alpha since inception, SYNTHESIS.md SS2). The craft lesson is specific: **write
the exit trigger in the SAME paragraph as the thesis, ranked, not as a separate risk-disclosure boilerplate
section.**

**[INFERENCE] Adoption**: the per-stock output's "what would change my mind" clause should itself be
ranked when more than one applies — lead with the fastest-acting/most-diagnostic one (fundamental
deterioration), not the slowest one (valuation richness), mirroring SageOne's stated hierarchy and
avoiding Marcellus's disclosed gap.

---

## 5. TWO WORKED EXAMPLES (in this voice — [ILLUSTRATIVE] numbers, NOT a live call)

**[ILLUSTRATIVE] Example A — mid-cap industrial, confirmed-stage conviction, score +62**

> **{TICKER}, Score: +62 (confirmed-stage)** — [ILLUSTRATIVE figures throughout, not a real position]
> priced at [ILLUSTRATIVE] 22x trailing earnings for [ILLUSTRATIVE] 14% revenue CAGR, the market is
> underwriting a linear extrapolation of the last three years. The differentiated view: margin expansion
> from a capacity ramp completed [ILLUSTRATIVE] two quarters ago should push EPS growth to ~1.6x revenue
> growth over the next four quarters (operating-leverage read, ValueQuest-style), which the current
> multiple does not reflect. This is timely because the capacity utilization inflection is now visible
> in the last two PIT quarters, not a forward promise. Margin of safety: even flat top-line growth from
> here, the balance-sheet is net-cash and ROCE has held above 18% for eight consecutive quarters — the
> quality floor (Marcellus/SageOne convergent screen) limits the downside case to a re-rating pause, not
> a capital-impairment event. What would change my mind, ranked: (1) trailing-4Q revenue growth
> decelerating below 8% for two consecutive quarters — the Anti-Marcellus-Trap deceleration trigger — is
> the fastest-acting kill switch; (2) a CFO/PAT divergence appearing for the first time in this name's
> PIT history; (3) valuation richening further is explicitly NOT a sell signal on its own (SageOne's own
> admitted mistake pattern) — watch (1) and (2), not the multiple.

**[ILLUSTRATIVE] Example B — smallcap consumer name, initial-stage conviction, score +28 (capped)**

> **{TICKER}, Score: +28 (initial-stage, capped)** — [ILLUSTRATIVE figures throughout, not a real position]
> this name screens well on the quality funnel (ROE [ILLUSTRATIVE] 19%, low D/E, growth 17%) but has only
> two quarters of PIT history at this ROE level, so the score is deliberately capped below what the raw
> composite would emit (Solidarity's position-ladder logic: initial conviction earns an initial weight,
> not a full one). The claim: distribution reach is scaling faster than the P&L shows because of a lag
> between store additions and same-store maturity — a variant-perception-style bet that current revenue
> understates run-rate capacity. Margin of safety is thin at this stage — this is explicitly why the score
> is capped, not why the name is excluded. What would change my mind: (1) if the next two PIT quarters do
> NOT confirm ROE holding above 15%, the score should fall, not just fail to rise — no averaging down on a
> quality name that hasn't proven duration yet (this is the specific discipline that separates SageOne's
> track record from Marcellus's); (2) any receivables-growth-vs-revenue-growth divergence appearing in the
> forensic gate ends this immediately regardless of the growth story.

---

## 6. WHAT NOT TO ADOPT (honest exclusions)

**[OPINION]** Two craft patterns from the study are explicitly NOT recommended for ALPHA_RANKER's output:
- **Marcellus's valuation-subordinated-to-quality register** — the language that reads most "confident"
  in the study ("double-digit growth AND ROCE above cost of capital, ten years running" — a clean,
  declarative, quality-forever voice) is attached to the worst realized outcome in the sample
  (SYNTHESIS.md SS2). Confidence of prose is not evidence of edge; do not let the ranker's language get
  MORE assertive than its falsification clause supports.
- **Aequitas's discretionary top-down cash-timing framing** — compelling in retrospect ("bubble of epic
  proportions" ahead of the 2025 smallcap correction) but explicitly flagged in our own prior study as a
  personal, non-mechanical judgment call that would be lookahead to backtest [DATA: SYNTHESIS.md SS5].
  Per-stock output should never borrow this register to imply market-timing conviction the model does not
  have.
