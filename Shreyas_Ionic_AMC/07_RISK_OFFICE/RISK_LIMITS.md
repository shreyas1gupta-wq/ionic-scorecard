# RISK LIMITS — CIO office (Rajan Mehta)
> **STATUS: APPROVED** (D-021, 2026-07-03). Written for the future small retail account (D-018); the paper book obeys them NOW to build the habit. CIO enforces; amendments need Principal sign-off.

## Position level
- Max risk per position: 1.0% of book equity (defined-risk structures: max loss; undefined: worst-case MTM model, NOT premium).
- Short-vol per-name notional ≤ 5% of book; inverse-IV sizing mandatory (size ∝ 1/entry-IV, ref 25% IV) — **CAPPED at 1.0× reference size until a regime gate exists (CIO ruling, QUARTERLY_PLAN_2026Q3 §2a: no upsizing into calm regimes)**.
- No naked short-vol through a name's known binary event (earnings/FDA/policy). Event calendar = sector analysts'.
- Illiquid instruments (far-OTM single-stock, far-month mid-cap options) = prohibited (COST_STANDARDS untradeable tier).

## Book level
- Aggregate short-vol margin ≤ 40% of book equity; free cash ≥ 30% at all times (gap-day survival).
- Max 20% of book in one sector; Adani-group counts as ONE name for concentration.
- Correlated-sleeve rule: S-01..S-04 (all short-vol) share ONE combined VaR budget; the equity sleeve does not offset it in stress.
- Staggered entries: max 25% of a sleeve's monthly deployment on any single entry date (April-2026 cluster lesson).

## Stress tests (monthly, CIO reviews)
- COVID-open scenario: −13% index gap → mark every option position at modeled panic IV (+25 vol pts) — book survives if drawdown <20%.
- Single-name −20% overnight gap on the largest short-vol position.
- Vol-spike correlation: all four short-vol sleeves at their historical worst month SIMULTANEOUSLY.

## Process risk (D-028 — Principal order 2026-07-04)
- **Lookahead-bias controls are a risk limit:** no strategy result enters the register, an IC memo, sizing math, or the investor letter without a LOOKAHEAD AUDIT PASS per `07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md` (T1–T10 taxonomy + `lib/lookahead_audit.py` + one-day-lag test). Dr. Bhat signs; Ritika monitors live/paper signal-reproducibility parity weekly (a divergence = T10 event). This is a TIGHTENING and needs no further sign-off; loosening it = Principal only.

## Escalation
- Any single-day book loss > 3% → trading halted, CIO review before next entry.
- 2 consecutive monthly sleeve losses → sleeve auto-demoted to paper (edge-decay rule).
- Any realized trade > 2× modeled worst-case → immediate post-mortem (RP-08) + COST/RISK amendment proposal.

## RESOLVED (D-026, Principal, 2026-07-04): paper BOOK_EQUITY = ₹1 crore → 1% rule = ₹1L/position; single lots tradeable. Original question below for the record.
## ~~OPEN CIO QUESTION~~ (2026-07-04, from risk-ceiling dry-run — Manoj)
At BOOK_EQUITY=₹10L, the 1%-per-position rule (worst-case 2× premium proxy) caps max_lots at 0-1 for ~87% of NSE F&O single lots (₹5-7L notional each). Options for CIO ruling at the Jul-31 board: (a) set paper BOOK_EQUITY to the intended future capital (₹25-50L?), (b) restrict the paper book to defined-risk structures whose max-loss fits ₹10k/position, (c) accept 1-lot minimum as a known rule breach with explicit waiver. NO change made — policy call, not ops.
