# STYLE_GUIDE.md — Shreyas_Ionic_AMC De-AI-ification Style System

**Owner:** Tanvi Desai (Head of Product, E-026). **Program:** WS-2, `04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/MASTER_PLAN.md`.
**Status: DRAFT — pending CEO + CIO joint approval (D-025).** This is a firm STANDARD (same class as COST_STANDARDS); it does not bind any deliverable until jointly approved. Until approved, `/style-lint` runs in advisory mode only.
**Goal (Principal order):** Word/PPT/PDF/HTML/chat outputs read and look like a high-IQ human original, not an LLM-generated document. This guide is the binding checklist; `.claude/skills/style-lint/` is the mechanical gate; `09_PRODUCT/scripts/docx_style_kit.py` is the implementation.

**Tagging in this document:** **[DATA]** = verified against the cited source. **[house]** = our own rule, not sourced externally, added to meet the Principal's brief or existing firm protocol.

---

## Source verification

The banned-tells taxonomy below is extracted from **avoid-ai-writing** (Conor Bronsdon), a 53-category AI-writing detector — `https://github.com/conorbronsdon/avoid-ai-writing`. Verified 2026-07-12 by direct WebFetch of the repo's `SKILL.md` and `detector/CATEGORIES.md` (not from training-data memory of the taxonomy). Confirmed facts **[DATA]**:
- 53 human-facing pattern categories, mapped internally to 44-45 detector `type` labels in `detector/CATEGORIES.md` (a stricter regex-detectable subset of the 53).
- Three operating modes: **Detect** (flag only, no rewrite), **Rewrite** (default — flag + fix + one corrective pass, cap 2 passes), **Edit** (in-place minimal edits).
- Severity is **qualitative P0/P1/P2**, not a single numeric "AI-ness" score — `SKILL.md` prose defines P0/P1/P2 tiers with no scoring formula. (A separate WebFetch of the repo's landing README described a "0-100 AI-ness score computed by the detection engine"; that claim lives in the JS scoring engine `detector/patterns.js`, which we did not port or verify line-by-line — we did **not** install the JS engine, per the ruflo no-runtime-dependency precedent in WS-1d. Our own skill below therefore implements its **own [house]** point score, described in §Scoring, rather than claim we replicated theirs.)

---

## (a) PROSE RULES

### A.1 — Banned tells, Tier 1: always replace **[DATA]**
Flag on ANY occurrence. Suggested replacement in parens.

delve/delve into (explore, dig into, look at) · landscape-as-metaphor (field, space, industry) · tapestry (describe the actual complexity) · realm (area, field, domain) · paradigm (model, approach, framework) · embark (start, begin) · beacon (rewrite entirely) · testament to (shows, proves, demonstrates) · robust (strong, reliable, solid) · comprehensive (thorough, complete, full) · cutting-edge (latest, newest, advanced) · leverage-as-verb (use) · pivotal (important, key, critical) · underscores (highlights, shows) · meticulous/meticulously (careful, detailed, precise) · seamless/seamlessly (smooth, easy, without friction) · game-changer/game-changing (name the specific change) · utilize (use) · watershed moment (turning point, shift) · nestled (is located, sits, is in) · vibrant (describe what makes it active, or cut) · thriving (growing, active — or cite a number) · deep dive/dive into (look at, examine) · unpack/unpacking (explain, break down) · bustling (busy, active — or cite what makes it busy) · intricate/intricacies (complex, detailed) · ever-evolving (changing, growing) · daunting (hard, difficult) · holistic/holistically (complete, full, whole) · actionable (practical, useful, concrete) · impactful (effective, significant) · learnings (lessons, findings, takeaways) · thought leader/thought leadership (expert, authority) · best practices (what works, proven methods) · synergy/synergies (describe the actual combined effect) · interplay (relationship, connection) · in order to (to) · due to the fact that (because) · serves as (is) · features-as-verb (has, includes) · boasts (has) · presents-inflated (is, shows, gives) · commence (start, begin) · ascertain (find out, determine) · endeavor (effort, attempt, try) · embrace-as-metaphor (adopt, accept, switch to).

### A.2 — Banned tells, Tier 2: flag when 2+ appear in the same paragraph **[DATA]**
harness · navigate/navigating · foster · elevate · unleash · streamline · empower · bolster · spearhead · resonate/resonates with · revolutionize · facilitate/facilitates · underpin · nuanced · crucial · multifaceted · ecosystem-as-metaphor · myriad · plethora · encompass · catalyze · reimagine · galvanize · augment · cultivate · illuminate · elucidate · juxtapose · cornerstone · paramount · poised (to) · burgeoning · nascent · quintessential · overarching.

### A.3 — Banned tells, Tier 3: flag at high density (~3%+ of running words) **[DATA]**
significant/significantly · innovative/innovation · effective/effectively · dynamic/dynamics · scalable/scalability · compelling · unprecedented · exceptional/exceptionally · remarkable/remarkably · sophisticated · instrumental · world-class/state-of-the-art/best-in-class.

### A.4 — Banned phrase families (flag at 2+ uses or in clusters) **[DATA]**
- **Tier-3 phrases:** "emerging sector/space/category" · "the integration of X with Y" · "the intersection of X and Y" · "community-driven" · "long-term sustainability" · "user engagement" · "designed for long-term X."
- **Transitions to remove/rewrite:** Moreover · Furthermore · Additionally · "In today's X" / "In an era where" · "It's worth noting that" / Notably · "Here's what's interesting" · "In conclusion" / "In summary" · "When it comes to" · "At the end of the day" · "That said" / "That being said."
- **Template phrases:** "a [adj] step towards [adj] X" · "a [adj] step forward for X" · "Whether you're X or Y" · "I recently had the pleasure of [verb]-ing."
- **Chatbot artifacts — P0, credibility killers:** "I hope this helps!" · "Certainly!" · "Absolutely!" · "Great question!" · "Feel free to reach out" · "Let me know if you need anything else" · "In this article, we will explore…" · "Let's dive in!" · any "Let's explore/take a look/break this down/examine" construction.
- **Cutoff disclaimers — P0:** "As of my last update" or equivalent.
- **Vague attributions — P0 (no named source):** "Experts believe" · "Studies show" · "Research suggests" · "Industry leaders agree."
- **Filler phrases:** "It is important to note that" · "In terms of" · "The reality is that."
- **Generic conclusions — P2:** "The future looks bright" · "Only time will tell" · "One thing is certain" · "As we move forward."
- **Promotional/travel-brochure language:** "nestled within the breathtaking foothills" · "a vibrant hub of innovation" · "a thriving ecosystem."
- **Formulaic challenges:** "Despite challenges, X continues to thrive" · "While facing headwinds, the organization remains resilient."
- **Speculative openers:** "Imagine a world where…" · "Picture a future in which…" · "Envision a world where…"
- **Infomercial hooks:** "The catch?" · "The kicker?" · "Here's the thing." · "But here's the kicker:" · "The best part?" · "Plot twist:" · "The result?"
- **Social-endorsement closers:** "This one is worth your time" · "must-read" · "you won't want to miss this" · "Save this for later" · "Bookmark this" · "Don't sleep on this one" · "Thank me later."
- **Emotional-flatline patterns:** "What surprised me most" · "I was fascinated to discover" · "What struck me was" · "I was excited to learn" · "The most interesting part" · "hit differently/hits different."
- **Rhetorical-question openers:** "But what does this mean for X?" · "So why should you care?" · "What's next?"
- **Parenthetical hedging:** "(and, increasingly, Z)" · "(or, more precisely, Y)" · "(and perhaps more importantly, W)."
- **Hollow intensifiers:** genuine/genuinely · real-as-intensifier · truly · quite frankly · to be honest · let's be clear.
- **Vague endorsement:** worth reading/a look/exploring/checking out/your time.
- **Hedging words:** perhaps · could potentially · it's important to note that · to be clear.
- **Confidence-calibration filler:** Interestingly · Surprisingly · Importantly · Significantly · Notably · Certainly · Undoubtedly · Without a doubt.
- **Persuasive-authority tropes:** "the real question is" · "at its core" · fundamentally · "make no mistake" · "the truth is."
- **Novelty inflation:** "He introduced a term" · "She coined the phrase" · "a concept nobody's naming" · "a failure mode nobody talks about" · "the insight everyone's missing" · "what nobody tells you about."

### A.5 — Structural tells **[DATA]**
- **Em dashes:** target zero; hard cap **1 per 1,000 words**. Replace with commas, periods, parentheses, or split into two sentences.
- **"It's not X — it's Y" negation pivot** (incl. multi-negation countdown: "It's not the price. It's not the features. It's the trust.") — rewrite as a direct positive statement.
- **Copula avoidance** — "serves as / features / boasts / presents" standing in for a plain "is/has": default back to "is" or "has."
- **Synonym cycling** — e.g. "developers … engineers … practitioners … builders" naming the same referent four ways in one paragraph: repeat the clearest word instead.
- **"Real/actual" adjective inflation** without an explicit contrast (bare "real on-chain tokenomics" vs. the acceptable "real on-chain settlement, not bridged IOUs" — keep only the version with a named contrast).
- **Compulsive rule of three** — habitual three-item groupings used as a rhythm crutch rather than because the list is actually three items.
- **Uniform sentence/paragraph rhythm** — sentence-length variance too low, paragraphs of near-identical length; over-polished, too-clean grammar with no natural friction.
- **Bullet-point-itis** — bullet lists of 5+ bare noun phrases with no verb, no number, no source.
- **Bold overuse, title-case headings, hashtag stuffing, inline-header lists, numbered-list inflation, false concession, list-label periods** — all flagged as P1/P2 per source.

### A.6 — POSITIVE rules **[house]** (what to write INSTEAD)
1. **Varied cadence.** Alternate short (5-12 word) and long (25+ word) sentences inside the same paragraph. A paragraph where every sentence is 15-20 words reads as machine output even with no banned word in it.
2. **Concrete numbers carry units and dates**, always — "+11.4pts (2×-cost, 2016-2025)" not "significant outperformance." This is already firm law (`CLAUDE.md` "never headline a CAGR without kills/artifacts") — this guide extends it to every number, not just headline CAGRs.
3. **Every claim carries a file-path citation** — `path/to/file.ext:row_or_line` or `(source: X, N rows, as of YYYY-MM-DD)`. Matches the firm protocol "verify claims with file path + row count before publishing."
4. **First-person ownership of judgment.** Write "I assess this as decaying" or "Tanvi's read: this misses the Principal's bar," not "it could be argued that" or "some might say." Hedged-third-person voice is an AI tell in our own house style, not just the source taxonomy's.
5. **One strong claim per paragraph.** If a paragraph makes three claims, it reads as a summary of someone else's thinking. Split it. One claim, its number, its source, its caveat — then a paragraph break.
6. **Lead with what's honestly bad.** Per the Investor Letter lesson (2026-07): kills and decay before the best number of the month. A guide that bans AI-tells but still leads with the shiniest metric has fixed the prose and missed the point.

---

## (b) DOCUMENT DESIGN **[house — informed by existing 09_PRODUCT builders + confirmed local fonts]**

- **Typography.** Body: **Georgia**, 10.5-11pt, ink color (see palette). Headings: **Bahnschrift** (SemiBold for H1/H2, Light for eyebrows/kickers) — a geometric, humanist sans, NOT Calibri. Both fonts are confirmed present in `C:\Windows\Fonts` on the build machine (`georgia.ttf/-b/-i/-z`, `bahnschrift.ttf`) so no install dependency. This replaces the current house default (`build_principal_report.py` sets `Normal` font to Calibri, Word's own default) — every builder script should call `docx_style_kit.apply_firm_styles(doc)` going forward instead of hand-setting Calibri.
- **Margins / grid.** 1-inch margins (Word default is acceptable — do not fight the print grid). Single-column body. A narrow left rule (2pt, Firm Navy) beside exhibit captions distinguishes them from body text at a glance.
- **Title-page furniture.** Title (Bahnschrift SemiBold, 24-28pt) · one-line thesis/subtitle (Georgia italic, 12pt, Stone gray) · date · classification line "Internal — Shreyas_Ionic_AMC" · author/desk line. No default Word "Title" style (it inherits the theme's blue accent) — direct-format every title-page run.
- **Numbered exhibits.** Every chart and table is "Exhibit N." with a one-line caption, referenced in prose by number ("see Exhibit 3"), never "the chart above/below" (breaks on reflow, also a filler-phrase tell).
- **Footnoted sources.** Every data claim gets an inline parenthetical or footnote: file path + row count/date. This is the typographic form of the firm's existing verification law — the point is to make source-checking effortless for the Principal, not just true in the agent's head.
- **No default-blue Office theme.** Ban Word's default Accent-1 blue (`4472C4`) and the default Calibri body/heading pairing outright. Every color, every font in a Principal-facing document must trace to this guide's palette — never "whatever python-docx's `doc.add_heading()` gives you by default."

---

## (c) CHARTS

### Firm palette — 6 hex colors **[house, continuity: Stone matches the `5F5E57` gray already in use in `build_principal_report.py:133`]**

| Role | Name | Hex |
|---|---|---|
| Primary text / axis / ink | Firm Ink | `1C1C1A` |
| Primary brand / primary series / headings | Firm Navy | `1F3A5D` |
| Accent / highlight / conviction-weighted | Firm Gold | `B08D57` |
| Secondary series / positive-signed numbers | Firm Teal | `2E6E62` |
| Negative-signed / kills / losses / warnings | Firm Rust | `A34A28` |
| Neutral / gridlines / captions / baseline | Firm Stone | `5F5E57` |

- **Direct labeling over legends.** Label each line/bar with its name and terminal value at the line's own end; drop the legend box unless there are 5+ series. A legend forces the reader's eye off the data — direct labels don't.
- **No default-matplotlib look.** Top and right spines OFF always; left/bottom spines present but at 40% opacity (Firm Stone). Gridlines: y-axis only, dotted, faint (15-20% opacity), never both axes, never solid. Annotation-first: the 2-4 numbers that matter get a callout with the actual value; nothing is left for the reader to "read off the axis."
- **Never the default matplotlib color cycle** (`tab10` blue/orange/green…) — always draw from the 6-color palette above.
- **Every chart carries its data source + as-of date** as a small caption beneath the plot (Georgia italic, 8pt, Firm Stone) — e.g. "Source: `06_TRADING_DESK/STRATEGY_REGISTER.md`, 258 trades, as of 2026-07-10."

## (d) TABLES

- **Alignment.** Text columns left-aligned; numeric columns right-aligned with a consistent decimal count within the column (don't mix "12.4" and "12.40" in the same column).
- **Units in the header**, never repeated per cell — "CAGR (%)" and "8.2", not "8.2%" in every row.
- **No vertical rules, ever.** Use the "three-line table" convention: one rule above the header, one rule below the header, one rule at the table's bottom — no grid, no vertical lines. Header row bold.
- **Row banding:** none by default (banding is a spreadsheet tell); use it only for tables over ~15 rows where the eye needs a tracking aid, and then a 4-6% Firm Stone tint, not a saturated color.

---

## Blind A/B protocol (WS-2 scientific check)

Per `MASTER_PLAN.md` §WS-2: *"blind A/B — show the Principal (and optionally colleagues) paired documents (old vs new style), guess-which-is-AI test; bar = new style beats old on 'human-made' ratings in >=70% of pairs."*

**Design**
1. **Pairing.** For each test round, take one real firm deliverable (an Investor Letter section, a strategy pack, an IC memo excerpt) and produce two renders of the *same content*: (i) the prior house style (Calibri, default Word theme, unfiltered prose) and (ii) the new style (this guide, `/style-lint`-passed, `docx_style_kit` applied). Content and claims must be IDENTICAL between the pair — only style differs. This isolates style from substance.
2. **Blinding.** Each pair is labeled **A / B** only, order randomized per pair (coin flip, logged), never "old / new." The rater is not told which letter is which style.
3. **Raters.** The Principal is the mandatory rater. Optional colleague raters (per Principal unlock, `MASTER_PLAN.md` §Sequencing) may be added once available — more raters tighten the estimate but the Principal's verdict alone is sufficient to pass/fail a round.
4. **Question asked per pair.** "Which of A/B reads like it was written by a knowledgeable person, and which reads AI-generated? (forced choice, no 'both'/'neither')." Recorded per pair: rater, pair ID, choice, optional one-line reason.
5. **Sample size.** Minimum 5 pairs per round to start (matches "colleague raters... pending" — do not wait for a large N to run the first round; a 5-pair round with the Principal alone is a valid first data point, just noted as low-N).
6. **Bar.** PASS if the new style is rated "human-made" in **>=70% of pairs** in a round. Below 70%: the round's dissenting pairs get logged with the rater's stated reason and routed back into this guide as a revision, not argued with.
7. **Cadence.** Re-run after any material revision to this guide, and at minimum once per quarter as part of the WS-2 program even absent revisions (drift check — a style guide gates 5-6 months and then quietly stops being followed if unaudited).
8. **Recording.** Log every round in a plain table appended below this section (round date, N pairs, rater(s), pass rate, verdict, revision items). No round is "the final word" — each is a checkpoint.

### A/B round log
| Round | Date | N pairs | Raters | Pass rate | Verdict | Revisions filed |
|---|---|---|---|---|---|---|
| — | — | — | — | — | **Not yet run** — this guide is DRAFT pending CEO+CIO approval; first round scheduled once approved and a real deliverable pair exists. | — |
