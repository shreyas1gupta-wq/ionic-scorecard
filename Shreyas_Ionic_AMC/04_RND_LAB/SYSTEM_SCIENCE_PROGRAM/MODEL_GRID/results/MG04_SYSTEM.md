# PRE-MORTEM RISK MEMO — Short Index-Option Book into a Double-Event Week (CB decision + Union Budget)

**From:** Rajan Mehta, CIO (E-001) — consolidated verdict integrating Arjun Rao draft (E-004) + Nikhil Bose red-team (E-014)
**Date:** 2026-07-14 | **Horizon:** assume it is ~2027; the book just printed its worst WEEK ever
**Tags:** [DATA] historical fact · [INFERENCE] modeled estimate · [OPINION] judgment. Paper book; ₹ figures illustrative on the assumed book.
**Book assumed (paper):** ₹1.00 cr. NIFTY ~25,000, lot 75, ₹18.75L notional/lot. Defined-risk sleeve (iron condors, 500-pt width, 150 credit, ₹26,250 capped/lot) = 30 lots. Naked strangle sleeve = 15 lots, ~5% OTM wings, ~250 credit/lot, UNCAPPED.

---

## VERDICT: REJECT as constructed → conditionally APPROVE only on full naked flatten by T-1 close.

The book carrying ANY naked short gamma through both prints is FRAGILE-by-construction and I veto it on tail-risk grounds. It becomes acceptably robust — and only then — when the naked sleeve is **fully flattened (not converted)** before the first print, collapsing the tail to the defined sleeve's bounded ₹7.875L.

**3-line rationale.** (1) The naked sleeve is mis-labelled at 40% — on tail terms it is **~70% of the loss** (₹20-22L of a ₹28-30L worst case); it is the entire story. (2) The draft's tail is quoted on IV-doubled *fair value* but the same memo says the exit is a *forced liquidation* at 3-5x mid — transaction price exceeds MTM, so the honest worst-week is **~-34% to -43%**, not -25% to -35%. (3) Five of the six proposed triggers assume a functioning market at the moment of stress; on a circuit-halt/gap they are unexecutable. **Only the calendar flatten is load-bearing. Everything else is theatre.**

## TAIL-RISK ASSESSMENT (numeric)

- **Worst single-day anchors [DATA]:** Budget days swing ±2-4% intraday; election-result 4-Jun-2024 ~-8.5% intraday / -5.9% close, VIX 15→27; Mar-2020 ~-12% single days. Entry VIX of 13 into a *known* CB+Budget week is unrealistic [OPINION] — event risk pre-prices to ~18-24, so "IV doubling" runs off an already-elevated base (larger vega loss than modelled).
- **Worst month / worst WEEK [INFERENCE]:** the task is worst-*week*, not worst-day. A naked put held across two prints with IV pinned high gets NO theta relief and can compound (−6% CB day THEN −6% budget day). COVID week Mar-2020 was ~-12% in a week with intraday −13% [DATA]. True worst-week index push = **-15% to -20%** — the draft's -11% is a floor, not a ceiling.
- **Correlated-blowup scenario (the killer):** three factors fire together on the naked sleeve — (a) both prints push the *same* direction through the naked strike; (b) IV expands INTO and THROUGH the event, so we lose delta AND vega at once (the crush we waited for never arrives); (c) liquidity vaporizes — buyback at 3-5x mid, SPAN 2-4x's while MTM losses drain the *same* collateral, forcing liquidation at the worst tick.
  - Naked sleeve, -11% gap, forced-liquidation realized (1.3-1.7x MTM): **≈ ₹26-35L** (not the draft's ₹20-22L MTM).
  - Defined sleeve: a -8% to -11% move blows through essentially all put spreads → realizes its **FULL ₹7.875L** (draft's ₹5-6L understates by ~30-50%).
  - **BOOK worst-week ≈ -34% to -43%** of capital. Realized ≈ 2x any single-event model that ignored two same-direction prints, vega, forced-liquidation slippage, and SPAN drain.
- **The MISSING tail — whipsaw [INFERENCE, likely MORE probable]:** the two events firing OPPOSITE ways (hawkish CB down, populist budget up) test BOTH wings — you lose on put AND call; realized vol, not net direction, kills you even if the week closes flat. This is arguably the more likely double-event tail and must be sized for.
- **Probability tag [OPINION, coarse]:** a -35%+ correlated-shock week ≈ 3-6% per double-event window carried naked; near-0% if flat by T-1. Size against the expected tail, not just its magnitude.

## SIZING RULING

- **Naked short gamma through a double print: sized to ZERO.** This is a hard cap, not a preference — the gap is uninsurable while held, and re-labelling by *premium/margin* hid a ~70%-naked-risk book behind a 40% label. Re-label the book by **tail**, not premium, in the register.
- Defined-risk sleeve permitted at current 30 lots; its bounded **₹7.875L (~-8%)** becomes the ACTUAL worst case with zero execution assumption baked in.
- **Margin ≤ 25-30% pre-event** (not 50%). "50% × 2x SPAN = 100%" sits AT the wall with zero buffer while SPAN 2-4x's — the draft's ceiling gives false comfort; forced liquidation is near-certain under it.

## KILL CRITERIA (pre-committed, mechanical — honestly demoted)

1. **LOAD-BEARING — T-1 CALENDAR FLATTEN.** By the close before the first print, the naked sleeve is FLAT. Not converted (converting = defined ₹7.875L + converted-naked ~₹7-8L ≈ **-15 to -16%**, ~2x the "flatten" residual — §draft-4 and §draft-5 contradict; only full flatten reaches ~-8%). This is the only trigger that does not require a live market at the moment of stress.
2. **SECONDARY, NON-LOAD-BEARING (state explicitly to any reader):** VIX>20 → half size at entry; delta band ±N NIFTY-pts neutralized in futures; 1.5x-credit MTM buy-to-close. **These are pre-print hygiene only.** On a -8/-11% gap they FAIL: India's 10/15/20% circuit breakers halt cash AND index futures/derivatives together, so "neutralize in futures immediately" is unavailable; a price stop set the day before is gapped THROUGH overnight (you open at 3-5x, never trade at 1.5x). A reader who banks on triggers 2-6 carries the book believing he has stops he does not have — the exact way capital dies.
3. **Review date:** re-run this pre-mortem at every CB+Budget cluster via `/macro-calendar` + `/stress-replay` (Jun-2024, Mar-2020 paths) on the live book before entry. Post-mortem mandatory if any week > 2x modelled worst case.

## WHAT CANNOT BE HEDGED AT ACCEPTABLE COST (honest)

- **The naked gap is uninsurable while held.** The only real hedge is buying the wings, which consumes most/all the credit — "hedging the strangle" = not having a strangle. You cannot keep the premium AND remove the tail.
- **Vega + liquidity are jointly worst exactly at the event** — tail protection is priciest in the very week you need it; buying vol into the print pays the market's own worst-case price.
- **Correlation → 1 in a macro shock** — put spreads and naked puts lose together; intra-index "diversification" is illusory on a print day.
- **No guaranteed fill on a circuit-locked/gapped bar** (D-031: no-fill = drop, never assume fills in dead markets) — you are stuck with the position, not the modelled exit.

## SINGLE WEAKEST ASSUMPTION

That we can exit the naked strangle near a modelled price after the event. **We cannot** — gap + IV-spike + liquidity evaporation make the realized exit 3-5x credit under a forced liquidation, and that alone is the tail. Pre-commit to the calendar flatten and the tail collapses to the bounded, designed ₹7.875L / ~-8%.

## DISSENTS RECORDED

- **Arjun Rao (E-004), draft author:** direction correct; numbers accepted as revised upward. No standing dissent — adopts red-team corrections (tail on forced-liquidation, full defined-sleeve loss, flatten≠convert).
- **Nikhil Bose (E-014), Red Team:** concurs; his corrections are adopted verbatim into this verdict (tail re-quantified to -34/-43%, triggers demoted to "calendar-flatten or bust", whipsaw added, margin ≤25-30%, book re-labelled by tail). No residual dissent.
