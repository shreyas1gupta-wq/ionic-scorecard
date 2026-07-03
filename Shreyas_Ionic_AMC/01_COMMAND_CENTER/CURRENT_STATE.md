# CURRENT STATE — read me first (updated every session end)
**As of: 2026-07-03 (late), by DESK-20**

## Right now
- **Firm foundation only** on disk: root CLAUDE.md + `00_GOVERNANCE/` + `01_COMMAND_CENTER/`. The earlier "firm structure just built" claim was overstated (session died mid-build). True inventory + completion spec: `01_COMMAND_CENTER/WORK_ORDER_DESK100_BUILD.md`.
- Principal's factor mandate + standards seed filed: `02_PROMPT_LIBRARY/drafts/BUILD_ADDENDUM_v1.md` (factor library mapped to on-disk data, 12 prompt clauses, cost skeleton, reference library, Red-Team checklist — ALL DRAFT per D-020).
- 23 Angel OHLCV stragglers pending rate-limit cooldown (list in RESUME_TOMORROW.md §Angel Daily Bulk).
- `AngelDailyOptionCapture` Windows task runs daily 15:45/20:00/23:00 IST (DESK-100 owns; check `angel_capture/capture.log` if in doubt).

## Awaiting PRINCIPAL approval (nothing is binding yet)
1. `BUILD_ADDENDUM_v1.md §2` — the 12 standard prompt clauses (approve one by one, D-020)
2. `BUILD_ADDENDUM_v1.md §3` — cost/slippage/brokerage skeleton (becomes COST_STANDARDS.md after DESK-100 formalizes + Principal signs)
3. `BUILD_ADDENDUM_v1.md §6` — governance extras (CIO/FM recommend, Principal decides)

## Next actions
- **DESK-100:** execute `WORK_ORDER_DESK100_BUILD.md` top-to-bottom (git, 15 agents, folders 03–07/99, skills, seeds), then journal + update this file.
- **DESK-100:** retry 23 Angel stragglers after cooldown; HF refill of 17-month option gap when bandwidth allows.
- **Either desk:** after build — seed STRATEGY_REGISTER reviews (4 forward strategies need owners + kill criteria in IC memos).
- **Home-network day:** NSE-blocked items (FII/DII flows, Total-Market/MicroCap constituents, 217 missing quarterly symbols).

## Blockers
- NSE API blocked on corporate proxy (403) — needs home network/VPN.
- Angel API rate limit: use ≥1.2s/req; 23 symbols pending cooldown.
