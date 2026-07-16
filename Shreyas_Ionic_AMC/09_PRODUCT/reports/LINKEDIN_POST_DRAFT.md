# LinkedIn post — draft v2 (angle rewritten 2026-07-15 per Principal's post-angle ruling: lead with clean wins).
# Rules honored: neutral alias ("Firm S"), no employer/broker names, no strategy content, hook never exceeds the paper.
# Numbers verified against SYSTEM_VS_LLM_PAPER_DRAFT.md Tables 5-6 (committed 2026-07-15). System-vs-LLM result: one honest line only, per Principal.

---

I benchmarked four AI models on real research work. The cheapest one tied the most expensive — at a tenth of the cost.

Outside work hours, over the past few weeks, I've been running a personal experiment: a research process — call it "Firm S" — that reviews quantitative research the way a real desk should: every test pre-registered in a git commit before it runs, every claim attacked by an adversarial check before it counts, every result graded blind so nobody grades their own work.

I used that process to build an exam, then ran it across four models to see what you actually get for the money.

**The exam:** 20 review tasks built from real data traps — lookahead bugs, timestamp errors, settlement quirks, statistical tricks that make randomness look like skill. Sixteen tasks each hide one verified defect (verified: a script proves the defect changes the answer). Four are clean — the correct answer is "no defect" — because a reviewer that invents problems to look thorough is exactly as dangerous as one that misses real ones.

**What I found:**

The mid-tier model matched the flagship on defects found — 15 out of 16 either way — at roughly **one-tenth the cost**. The most expensive model in the lineup was not the most accurate. And answer length tracked false alarms: the two most verbose models also flagged the most non-existent problems on the clean tasks. Terseness bought precision here, not the other way around.

Along the way, I caught something in my own method worth sharing on its own. I had one model grade a set of answers, and it ranked itself and its closest sibling higher than a neutral second judge did — by up to a full point on a 10-point scale — while every other model's score barely moved between judges. Self-preference in AI-as-judge scoring isn't a rumor; I measured it directly, by accident, while sanity-checking a result that looked wrong. Anyone running "AI judges AI" evaluations should assume their single judge is quietly grading on a curve for its own family, and check for it the way I stumbled into checking for it.

Whether the added review machinery itself is worth its cost on this particular exam is a separate, harder question — the honest answer there is nuanced enough that it belongs in the full write-up, not a headline.

**Two things I'd tell anyone building with LLMs:**

Pre-registration isn't really about statistics. It's psychological — when the empty results table is already committed before you've seen a single number, you stop negotiating with yourself about what a bad result means.

And if you're using one model to grade another, don't trust a single judge. Cheap, avoidable bias, easy to check, easy to miss if you don't look.

The full write-up — every table, the method, what I'm not claiming, and the caveats I'd want a skeptic to press on — is in the attached PDF. The method is copyable on purpose: freeze commits, blind grading, clean controls that penalize false alarms. If you build with LLMs, you can run this exam on your own stack next week.

Personal project, personal time, paper only — no live capital, no investment advice. This is about how I evaluate AI tools for research, not a market call.

[Attachment: Firm S benchmark PDF]

---
# Post-fill checklist: /style-lint this file; verify no employer/broker/internal-firm-name strings;
# Principal confirms the "one honest line" on the system test above is acceptable (currently a soft
# non-claim, no number quoted); Principal review + spot-audit sign-off; only then publish.
