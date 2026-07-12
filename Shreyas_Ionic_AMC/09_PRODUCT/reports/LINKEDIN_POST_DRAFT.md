# LinkedIn post — draft v1 (Fable, 2026-07-13). [RESULT] slots fill after grading. ~600 words.
# Rules honored: neutral alias, no employer/broker names, no strategy content, hook never exceeds the PDF.

---

I ran an experiment on myself. Or rather, on the AI research firm I built on my laptop.

For the past two weeks, outside of work hours, I have been running a personal experiment: a "research firm" of 28 AI agents — a CIO, fund managers, sector analysts, a red team, a data office — that does quantitative finance research the way a real firm would. Not a chatbot with a fancy prompt. A system with rules: every experiment pre-registered in a git commit before it runs, every claim attacked by an adversarial red-team agent before it counts, every backtest checked against placebo controls, every kill recorded with the conditions under which it may be reopened.

Then I asked the obvious question. Does any of that machinery actually matter, or would one strong model with a good prompt do just as well?

So I measured it.

I built a 20-task exam from the real data traps my system had stepped on during two weeks of research: lookahead bugs that inflate returns, timezone stamps that shift signals a day early, settlement-price quirks that fabricate profits, statistical tricks that make randomness look like skill. Sixteen tasks contain one verified defect each — verified meaning a script demonstrates the defect changes the answer. Four tasks are clean: they contain no defect, and saying "no defect" is the right answer. Those four exist to catch a failure mode nobody talks about: reviewers who look smart by inventing problems.

Three contestants took the same exam with the same instructions:
- a single model call, no tools;
- a single model call with a code sandbox;
- the full firm pipeline — reviewer, red-team, synthesis — capped at 1.5x the token budget of the second contestant, so orchestration overhead counts against it.

The exam was frozen in a git commit before any contestant saw it. So was the grading rubric. So was the paper's results section — empty tables, committed before the first run. Grading was blind: answers stripped of identifying furniture, shuffled, scored against the key by graders who did not know which answer came from which contestant. I pre-registered the pass bar: the multi-agent system had to find at least 20% more verified defects than the best single-model arm, or I would publish that the overhead does not pay.

Here is what I found:

[RESULT: headline — defects found per arm, X/16 vs Y/16 vs Z/16]
[RESULT: false-positive rate on the four clean tasks — did anyone invent defects?]
[RESULT: cost — tokens and dollars per arm; what one extra caught defect costs]
[RESULT: one-line verdict against the pre-registered bar]

[RESULT: 2-3 sentence honest interpretation — including, if the system failed the bar, what that means and what I am changing before the v2 battery]

A few things I learned that did not need a benchmark:

The value of pre-registration is not statistical. It is psychological. When the empty results table is already committed, you stop negotiating with yourself about what the numbers mean.

Clean controls change reviewer behavior more than hard tasks do. Knowing that "no defect" might be the right answer forces precision; without it, everyone hedges by listing possibilities.

And the most expensive failure mode in AI-assisted research is not hallucination. It is a plausible answer to a question whose premise contains the bug.

The full write-up — methodology, the grading rubric, example tasks, cost accounting, and everything I am not claiming — is in the attached PDF. The method is deliberately copyable: freeze commits, adversarial review, placebo controls, blind grading. If you build with LLMs, you can run this exam on your own system next week.

This is a personal project, done on personal time, on paper only — no live capital, no investment advice, and the findings are about research process, not markets.

[Attachment: SYSTEM_VS_LLM paper PDF]

---
# Post-fill checklist (next session): insert 5 [RESULT] slots from RESULTS.md; /style-lint this file;
# verify no employer/broker/internal-firm-name strings; Principal review; only then publish.
