# Hypothesis one-pager — Sentiment Alpha (news/transcript tone)
_Intake 2026-07-03 · R&D (Aditya Verma) · RESEARCH_SOP §template · stage 1-INTAKE_

- **Name:** `sentiment_alpha` — cross-sectional news/transcript tone tilt.
- **One-line edge:** Rank the F&O universe by aggregated financial-news tone (and call-transcript tone), long the top / short/underweight the bottom; documents are stale-priced by the crowd so tone predicts the next few days' cross-sectional return.

- **Economic WHY (who loses money to us, why do they keep doing it?):**
  Under-reaction / limited-attention. Retail and slower institutions read headlines but do not fully price the *tone* of the full body / the Q&A section of a call the same session. This is a **behavioral** loser (attention is scarce, negativity is under-reacted-to per the disposition effect) with a **structural** amplifier (news volume per name is huge; humans triage, machines don't). They keep doing it because attention does not scale and the flow of documents is relentless — the mispricing regenerates every news cycle. Our edge is systematic full-corpus tone scoring at zero marginal attention cost.

- **Factor sleeve:** Sentiment Alpha (FACTOR_LIBRARY §Proprietary — FinBERT; **lexicon baseline FIRST** per firm rule).
- **Universe:** 210 F&O names (join to the tradeable set; sentiment on the wider NIFTY-500 corpus is fine for scoring but positions only where we can trade/hedge).
- **Holding period:** 1–5 trading days (event-decay horizon of a news tone shock; to be measured, not assumed).
- **Expected decay horizon:** Fast — post-publication decay is the norm for sentiment (McLean-Pontiff); Indian retail-news under-reaction likely half-lives in days. Treat as a **short-horizon, crowding-sensitive** signal.
- **Capacity estimate:** UNKNOWN pending liquidity overlay. Ceiling is the tradeable float of the shorted tail; long-only large-cap tilt is capacious, the short/underweight leg on mid-caps is the binding constraint. Estimate at cheap-test on the top/bottom decile ADV.

- **Data needed (on disk? Y/N per DATA_CATALOG):**
  - India financial news — `datasets/india_fin_news`, **125K docs, tier-segregated** — **Y** (§4). [books] count, not re-verified on disk.
  - Earnings-call transcripts (MiMIC) — **1,042 calls, prepared vs Q&A split** — **Y** (§4). [books].
  - Prices for the return join — Stock daily (HF) **Y** but **stale tail →2026-01-22** (landmine #1: asof after Jan-26 returns stale prices); Angel daily 2026 bulk covers Feb–Jul-2026 (477/500). **PIT hazard:** must join prices on the document's **available_date only** — no publication-timestamp lookahead.
  - FinBERT model — ProsusAI/finbert (KNOWLEDGE_BASE §B HF models) — download is a separate step, not on disk.

- **Cheap-test design (the single cheapest falsification):**
  Lexicon-only (Loughran-McDonald style + a small hand-tuned India-finance word list), **no FinBERT yet**. Score each doc's tone; aggregate per name per day; on the tier-1 (highest-quality) news subset only, form a daily top-vs-bottom tone-quintile spread on the 210 names, hold 1 day, join returns strictly on `available_date+1 open`. Event-study the 5-day CAR around high-|tone| shocks. **Kill threshold pre-registered below, set BEFORE touching data.** If the *free lexicon* baseline is flat, FinBERT is not worth the GPU — the firm rule (lexicon FIRST) is exactly this triage.

- **Pre-registered KILL criteria:**
  1. Tier-1 top-minus-bottom tone-quintile 1-day spread **< +3 bps/day gross** (before any cost) over the test window → KILL (signal too weak to survive costs).
  2. 5-day CAR after high-|tone| shocks statistically indistinguishable from a **date-shuffled placebo** (tone label permuted) → KILL (it's beta/momentum, not tone).
  3. Any result that depends on prices past 2026-01-22 without the Angel-bulk overlay → **VOID the run** (stale-price landmine), not a pass.
  4. Signal survives only with a publication-timestamp that is *not* `available_date` → KILL (lookahead).

- **Trials run so far on this family:** **0** (new family; no prior sentiment variants in KILLED_IDEAS or STRATEGY_REGISTER).

- **Cheapest falsification (closing line):** On the tier-1 news subset alone, score tone with a **free lexicon**, form the 1-day top-minus-bottom tone quintile on the 210 names joined at `available_date+1 open`, and kill the family if that gross spread is under **+3 bps/day** or matches a tone-shuffled placebo — no FinBERT spend until the lexicon clears this bar.
