---
name: agentic-fund-manager
description: Run the Ionic Wealth NDPMS client-portfolio review — convert the scored stock universe + a client's holdings into Sell/Trim/Hold recommendations with trim targets, concentration/mcap/sector analysis, and the two-sheet Ionic Wealth client workbook (Before-vs-After). Use for /agentic-fund-manager <client holdings>, "review this client portfolio", "generate client recommendations", or any NDPMS portfolio-feedback ask.
---

# Agentic Fund Manager — NDPMS client portfolio review (FROZEN v1, 2026-07-18)
**Contract: `Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/FROZEN_METHODOLOGY.md` (v6) — read its CLIENT PORTFOLIO LAYER section first; it governs every number this skill produces. Client identity: Ionic Wealth. Vocabulary: Sell / Trim / Hold — NEVER Buy.**

## Inputs
1. Client holdings (NSDL CAS or equivalent): symbol, value_inr; purchase dates/costs if available (activates tax-aware notes; otherwise sheet carries the "confirm tax status" line).
2. Scored universe: quant CSV (per-stock pillar scores, final_3y_adj/final_1y_adj) + `pf_qual_<SYMBOL>.json` analyst files. Any holding NOT in the scored universe → research it first via the scorecard-analyst workflow (one Sonnet sector-persona agent per stock); never score a client holding quant-only without flagging it.
3. Client profile if provided (risk band, IPS constraints, mcap tolerance, sector exclusions); else the standard NDPMS template.

## Step 1 — Mechanical layer (script, not judgment; ~0 tokens)
Compute per holding: `ionic_score` (0.60×3Y + 0.40×1Y base, then growth leg −6…+6 from expected_next_3y_growth_pct bands and conviction leg ±6, total clamp ±10 — exact bands in FROZEN_METHODOLOGY.md); % of portfolio; sector weights; mcap band (Large/Mid/Small/Micro by mcap tercile/size); flags:
- Gate A: analyst Sell → Sell; else ionic_score <40 → Sell-candidate
- Gate B: ionic_score 40-50 AND weight >2.5% → Trim-candidate
- **Balance-sheet gate is CONTEXT-AWARE (Principal 2026-07-25): the debt/interest-cover bar is judged against industry norms (utilities, lenders, infra run structurally levered), sovereign/PSU backing, and membership of a strong promoter group with demonstrated capital support — never one fixed ratio across all names.** A gate trip in a levered-by-design industry needs the analyst to confirm it is abnormal FOR THAT industry before it caps the score.
- **Commodity-cycle lens (Principal 2026-07-25): any Metals & Mining / Oil & Gas / commodity-power name gets an explicit cycle-position read in its commentary** — where we are in the 10-15yr commodity cycle (2000s = China/internet buildout; today = electrification + AI data-centre demand), whether the bull case is structural demand or just spot-price beta, and the call must engage that thesis (a Sell must say why it stands DESPITE the upcycle: valuation already prices it, earnings not following price, or company-specific execution). Route these names through the industrials/commodities lens (Rohan Deshmukh) + macro regime read (Cyrus Daruwalla).
- Concentration: weight 5-10% + forward growth modest → note; >10% → "little bad" Trim-advice zone; >20% → extreme
- **Single-GROUP concentration (Principal 2026-07-25): map holdings to promoter groups (Tata / Reliance / Adani / Bajaj / Aditya Birla / JSW / Vedanta / Mahindra / L&T …) and compute each group's share of the equity sleeve on every run. If no group exceeds 20% → check only, nothing goes in the client deck. If a group exceeds 20% → the group-concentration slide renders with the member table and a cap-near-20% recommendation** (deck module `group_concentration.py` implements this contract).
- Sector: any sector >20-25% of book → check vs Sector&Macro pillar + current regime call; overweight + weak forward view → tighten the Trim band for that sector's weakest names
- Mcap: micro/small positions judged on a lower comfort band than large-caps at the same weight; note book-level mcap mix
- Liquidity: position value vs stock's median turnover (days-to-exit at ~20% ADV) — a Trim that takes >10 trading days to execute must say so
- Clutter: positions <0.25% → consolidation note (not a forced Sell)
- **Tax inertia (Principal 2026-07-25): FUND units held >5y (stronger >10y) get a RAISED sell/switch bar** — embedded LTCG offsets switching alpha, so Switch/Exit only on structural grounds (plan cost, mandate, closet-index), never a performance gap. **Stocks are exempt** — single-name risk dominates the tax cost, equity Sell guidance unchanged (tax shown, threshold not raised).
- **Fund Sell needs BOTH frameworks to agree (Principal 2026-07-25): the long-term framework (/qfra2-rerun) and the short-term capture framework (/qfra1-rerun · MF Dashboard) each produce calls. A fund Sell/Exit goes to the client ONLY when both are non-Hold. One says Sell, the other Hold → default HOLD (or spawn one adjudication agent if the position is large); both Hold → Hold.** Structural actions (Redeem-to-Direct, mandate switch) are exempt — they are plan/category facts, not performance calls.
- **Client vocabulary (Principal 2026-07-25): internal codenames NEVER reach a client artifact — no 'SENTINEL', 'QFRA', 'MERIT', engine version numbers or agent names. Use plain words: 'fund score /100', 'grade', 'watch-outs', 'the firm's fund-quality framework'.** The deck tell-scan enforces this.
- Debt look-through flags (via /mf-lookthrough): single issuer >10% of book, debt sleeve >10% with below-AA paper, or issuer tripping the scored-universe leverage gate → surface in the review (flag only; no FI framework per Principal).

## Step 2 — FM judgment pass (agent, Sonnet)
Summon ONE fund-manager persona (fm-fundamental-sanjay-kulkarni for long-only quality books; fm-vikram-shah for allocation-heavy questions) with the mechanical flag list + per-stock analyst summaries. The FM:
- Sets the final action per flagged name and the **Trim target ("Trim to ~X% of portfolio")** — judgment, NOT formula: company future expectations + score + conviction + buying price/IPS if known + mcap context (Principal ruling: no hard caps).
- May override a mechanical flag with stated reasoning (e.g., keep a 12% position intact on high conviction) — overrides are logged.
- Writes the one-line client-appropriate reason per action and the Sheet-2 Before-vs-After narrative.
- **Call-aligned commentary (Principal 2026-07-25): every client-facing line leans the way the call leans.** A Sell name's commentary OPENS with the concern driving the call; a strength may appear only as the rejected bull, explicitly discounted ("order book is strong, but already in the price / does not clear the leverage gate"). A Hold opens with why holding is right; risks read as monitorables, not alarms. Never ship a line that argues against its own pill (e.g. "good order book, robust execution" beside a Sell). If honest commentary cannot support the call, the mismatch goes back to the FM / escalation — it does not go into the client deck.
- Never invents facts; anything shaky goes back to the analyst layer, not into the client sheet.
Output: `pf_fm_actions.json` — per stock: {symbol, action, trim_target_pct|null, client_reason, fm_note}.

## Step 3 — Verification gate (MANDATORY before building the workbook — Principal: "double sure of all checks and correctness")
Script-verify: weights sum to 100.00 (±0.05) before AND after; after-weights = before minus actions with freed cash as its own line (never auto-redeployed — no Buy advice); every Sell/Trim has a client_reason; every Trim has a target < current weight; vocabulary ∈ {Sell, Trim, Hold}; score-vs-call divergences (score >50 with Sell, or <40 with Hold) each carry an auto-footnote; **commentary sentiment matches the call — the first clause of every client_reason/read leans with the pill (opens negative for Sell/Trim, positive for Hold); positives on a Sell only as an explicitly rejected bull**; no technical/chart language anywhere client-facing; escalated names either resolved by Principal or excluded from action (noted as "under review").

## Step 4 — Build + ship gate
Build the Ionic Wealth two-sheet workbook via `Shreyas_Ionic_AMC/09_PRODUCT/scripts/build_client_excel.py` (v3: Sheet 1 Recommendations with ONE Ionic Score + Trim-to column; Sheet 2 Portfolio Before-vs-After). Also refresh the analyst Excel (`build_analyst_excel.py`) so the internal book matches.
**No client deliverable ships without Principal sign-off.** Present: action list, biggest concentration findings, book-score before/after, and all open escalations.

## Cadence
Quarterly after each results season (per SCRAPING_SOP.md refresh) + event-driven single-name re-checks (escalation events, knife-edge earnings prints). Log every run to the client's PROGRESS file so any session can resume.