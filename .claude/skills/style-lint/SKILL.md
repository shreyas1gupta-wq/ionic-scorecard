---
name: style-lint
description: Mechanical AI-tell + house-style checker for any Principal-facing draft (docx/md/txt) — banned-tells taxonomy, citation-presence, structural tells (em-dash, bullet-itis, rule-of-three, cadence). Use for /style-lint <file>, before any Investor Letter, IC memo, or Principal deliverable ships, or whenever a draft "reads AI-generated."
---
# /style-lint — owner: Tanvi Desai (Product) + Lakshmi Narayanan (Librarian), WS-2

**Model: Haiku-class.** This is a mechanical check. The script does the detection deterministically — nothing here requires judgment to RUN. Only the "what to do about it" triage (which findings actually matter for this document) benefits from a sonnet-level read, and that's optional.

**Binding status:** advisory until `00_GOVERNANCE/STYLE_GUIDE.md` is CEO+CIO jointly approved (D-025). Run it anyway — a violations report costs nothing and the Principal has already stated the goal.

## What it checks
Sourced from `avoid-ai-writing` (https://github.com/conorbronsdon/avoid-ai-writing), WebFetch-verified 2026-07-12 — see `STYLE_GUIDE.md` §Source verification for exactly what was confirmed vs. inferred. The full taxonomy lives in `data/taxonomy.json` **inside this skill folder** so it runs fully offline:
1. **Tier-1 banned words/phrases** (always replace — "delve," "landscape," "leverage," "utilize," "robust," 40+ more) with a suggested plain-English replacement.
2. **Tier-2 words** (flag when 2+ appear in the same paragraph — "harness," "foster," "streamline," etc.).
3. **Tier-3 density** (document-level: "significant," "innovative," "compelling"... flagged if >=3% of running words).
4. **20 phrase families** — chatbot artifacts, vague attributions, cutoff disclaimers, filler phrases, generic conclusions, promotional language, infomercial hooks, novelty inflation, and more (each carries the source's own P0/P1/P2 severity).
5. **Structural tells** — em-dash rate (target zero, hard cap 1/1,000 words), "it's not X — it's Y" negation pivots, compulsive rule-of-three, bullet lists of 5+ bare noun phrases.
6. **[house] positive-rule advisories** — claim-bearing lines (contain a digit) with no nearby file-path/date/"source:" citation; uniform sentence-length cadence (a paragraph that never varies rhythm reads machine-written even with zero banned words).

## How to run it
```
python "<skill-dir>/scripts/lint.py" <path-to-draft.md-or-.docx> [--out report.md]
```
- `.md` / `.txt`: scanned line-by-line.
- `.docx`: scanned paragraph-by-paragraph (+ table cells), via python-docx (already installed firm-wide — no new dependency).
- No network calls, no JS engine installed (we did NOT port `avoid-ai-writing`'s runtime — hand-built our own regex/substring checker over the same verified word lists, per the ruflo no-runtime-dependency precedent).

## Output
A markdown table: line/paragraph number, category, severity (P0/P1/P2 from source, or `house-P2` for our own additions), the matched text, and a suggested rewrite where the taxonomy provides one. Ends with a **[house] AI-tell weighted score** (P0×3 + P1×2 + P2×1, per 1,000 words) — our own metric, not a claim of reproducing the source repo's JS "0-100 AI-ness score" (that scorer lives in code we did not fetch/verify line-by-line).

## Gate use
- Run on any draft before it goes to `09_PRODUCT/reports/` or ships as an Investor Letter / IC memo section.
- Zero P0 findings is a hard bar (chatbot artifacts, vague attributions, cutoff disclaimers, novelty-inflation — these read as an obvious AI credibility killer to any reader, not a style nuance).
- P1/P2 and house findings are triage, not an auto-fail — a strategy pack quoting "significant" once because a source document used that word is not the same failure as a paragraph of six banned words.
- This checks PROSE only. Chart/table visual rules (palette, direct labeling, no default-matplotlib look, three-line tables) are in `STYLE_GUIDE.md` §(c)/(d) and are checked by eye against `09_PRODUCT/scripts/docx_style_kit.py` output, not by this script.

## Files in this skill
- `SKILL.md` — this file.
- `data/taxonomy.json` — the full banned-tells taxonomy + structural/house rule parameters (offline, edit here to tune thresholds).
- `scripts/lint.py` — the checker. Pure stdlib + python-docx for `.docx` input.
