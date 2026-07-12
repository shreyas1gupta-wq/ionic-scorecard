# CARD: Kiru package — NIFTYBEES↔GOLDBEES ratio-Donchian rotation + 0DTE short straddle (SL-30%)
Filed 2026-07-13 by DESK-20 (Principal order: "backtest all"). Source: external podcast spec (guest Kirubakaran) supplied verbatim by Principal.
**Status: FROZEN PRE-RUN** — bars pre-registered below; commit precedes any run (loop-day law). Scripts-only (org spend limit; no subagents).

## Claims under test (his, as supplied)
- C1: Rotation NIFTYBEES↔GOLDBEES via 20-day Donchian on the ratio "significantly reduces vol and drawdown vs buy-and-hold" and contributes ~18%/yr.
- C2: 0DTE ATM short straddle at ~09:16 with combined-premium SL +30% contributes ~12%/yr via theta.
- C3: Pledging the rotation corpus funds the option margin → combined ~30%/yr.

## Prior-art fences (must be cited in verdict; do NOT re-litigate)
- **K-011** (2026-07-04): gold as SAME-DAY crash hedge = KILLED. Explicitly unclaimed: "strategic low-corr return sleeve". This card tests a RELATIVE-STRENGTH SWITCH — different hypothesis, allowed.
- **GOLD-TREND NOT ADOPTED** (2026-07-13, 1/4 bars; GT-2 DENIED by Nikhil): gold-only trend sleeve is fenced. This card is always-invested rotation (equity OR gold), not gold-trend. Signed-corr template law applies to any corr claim.
- **S1-F / 0DTE family**: firm already certified S1-F (paper, Tue 09:12 engine) and killed/fenced several expiry-day short-vol variants (S-02, S-04 artifacts; KB lessons). C2 is the SAME trade family — verdict must state overlap/incremental vs S1-F, not claim novelty. IC-1 law: headline CAGR inadmissible; regime-beta decomposition required.
- Roadmap 2026-07-13: new sleeves must be DIFFERENT-FACTOR (vol/gold/macro/flow). Rotation qualifies as gold/macro-flavored — on-roadmap if bars pass.

## Pre-registered spec — Component A (rotation)
- Ratio R_t = NIFTYBEES_close / GOLDBEES_close. Donchian N=20 on R using PRIOR 20 sessions (shift(1) — no same-bar peek).
- R_close > 20d-HH → hold NIFTYBEES; R_close < 20d-LL → hold GOLDBEES; else hold prior state. Always invested; start = NIFTYBEES at first valid signal.
- Execution primary: signal close t → trade at t+1 OPEN. Variants: t+1 close; t close (idealized upper bound, labeled).
- Costs per approved COST_STANDARDS (ETF delivery): per SWITCH (sell one + buy other) = STT 0.1%×2 + slippage 0.10%×2 + stamp 0.015% + exch/GST ~0.007% + ₹20×2 ≈ **0.44% of corpus per switch** (computed exactly in script).
- Window primary: common real-ETF history (GOLDBEES starts 2021-01-10) → ~2021-02→2026-07. NO 2020 crash in window — stated openly; long-history proxy run only if a verified INR-gold + NIFTY series ≥2008 exists on disk (else that question stays OPEN per K-011 resurrection note).
- Benchmarks: NIFTYBEES B&H, GOLDBEES B&H, 50/50 monthly-rebalanced.

**Bars (rotation):**
- KR-R1 existence: net CAGR ≥ NIFTYBEES B&H − 1pp AND MaxDD ≤ 0.6× B&H MaxDD (both net, t+1-open exec).
- KR-R2 robustness: N∈{15,25,30} neighbors keep the DD-improvement sign; no neighbor's net CAGR < B&H − 3pp.
- KR-R3 cost honesty: switching drag ≤ 2pp/yr at approved costs (report switches/yr).
- KR-R4 (report-only, D-034 lens): monthly-horizon corr of rotation returns vs S1-F & B1b sleeves + % time in gold; signed-corr template. No pass/fail today.
- Verdict: R1+R2+R3 all pass → ADOPT-CANDIDATE (proceeds to Sameer /sensitivity + Nikhil red-team before any register row); exactly 2 → COMPONENT-BANK; ≤1 → NOT ADOPTED.

## Pre-registered spec — Component B (0DTE straddle)
- Universe: every valid NIFTY weekly expiry in `hf_index_options_1m/options/NIFTY/` (~261, 2021→2026), on the EXPIRY DAY itself.
- Entry: 09:16 bar (explicitly ≥09:15 — auction landmine); ATM = strike nearest spot (index/NIFTY.parquet) at 09:16, 50-pt grid; SELL 1 CE + 1 PE at that strike; fills at bar close − slippage max(₹0.05, 0.5% premium)/leg.
- Risk: exit BOTH legs when 1-min combined close ≥ 1.30 × entry combined; SL fill = trigger-bar combined × 1.01 + leg slippage ×2 (stress law). Else hold to expiry: settle at intrinsic vs settlement proxy = mean of index close 15:01–15:30 (official is last-30-min average; landmine #9: NEVER bhavcopy expiry settles).
- Costs: STT 0.1% sell premium; exch 0.035% premium both sides + GST 18%; stamp 0.003% buy side; ₹20/order (2 entry always; 2 exit only on SL/early exit); lot 75.
- Gate: both legs must have volume>0 at entry bar, else skip day (logged).
- Variants (labeled): SL∈{20%, 40%, none}; exit-at-15:20; overlay = firm deploy-rule filter (entry combined ≥ 0.45% of spot).

**Bars (straddle):**
- KR-S1 existence: mean net P&L per expiry > 0 (% of spot), n ≥ 200.
- KR-S2 incremental (IC-1 law): SL-30% spec beats no-SL baseline on BOTH mean and p5 tail; overlap statement vs S1-F mandatory in verdict.
- KR-S3 decay: trailing-12m era mean ≥ −0.05%/expiry.
- KR-S4 (report-only): interaction with ≥0.45% filter — does his spec add anything to our known rule?
- Verdict: S1+S2+S3 → hand to Vikram as an S1-F-family VARIANT memo (never a new register row without IC); else NOT ADOPTED with the numbers.

## Component C (combined) — report-only claim check
Rotation corpus pledged (10% haircut), margin utilization capped 60% ⇒ overlay levels 1× and 2× straddle notional shown; state what overlay C2's "12%/yr" requires and whether margin math supports it. No bar — informational vs the 30% claim.

## Trials plan (ledger 249 → planned +15)
Rotation: 2 windows? (1 real + proxy-if-data) × exec 3 + N-neighbors 3 = ≤9. Straddle: primary + SL 3 + exit-1520 + filter overlay = 6. All logged regardless of outcome.

## Landmine checklist
ETF parquet stamps are UTC 18:30 → +05:30 convert (catalog note) · options ts already +05:30 (chain.py) · first bar ≥09:15 · settle from spot, never bhavcopy · volume>0 gate · no fundamentals ⇒ no PIT exposure · corrupt expiry files skipped per chain.py CORRUPT set.

Results → `results/KIRU_PKG/20260713/`. Verdict + KB lesson + ledger update on completion.

---
## VERDICT (2026-07-13, same day — full detail in results/KIRU_PKG/20260713/SUMMARY.md)
- **A (rotation): NOT ADOPTED** — KR-R1 FAIL (net 9.79% CAGR vs 10.93 bar; MaxDD −32.96% vs −21.8 bar), KR-R3 FAIL (3.16pp/yr cost drag), KR-R2 pass-with-flag (N20 = worst neighbor). Claimed 18% ≈ same-bar execution illusion (lookahead demo 29.4% → honest t+1-open 9.8%). Kill = **K-016** w/ resurrection conditions. **COMPONENT-BANKED: 50/50 monthly-rebal NIFTY-gold dominates (12.29%/10.47%vol/−21.49%DD)** → evidence for K-011's unclaimed strategic-gold-sleeve; route to Devika.
- **B (0DTE SL-30 straddle): bars S1/S2/S3 PASS** — but honest edge +1.7%/yr of notional unlevered (claim was 12%); SL-30 is the good part (tail p5 −0.76→−0.29); our ≥0.45% filter dominates his unfiltered spec (sub-filter days NEGATIVE). → S1-F-family VARIANT note to Vikram; NO register row.
- **C (combined 30%/yr): NOT REPRODUCED** — honest stack 11.5-18.6%/yr with correlated stress.
- Trials +12 (rotation 6, straddle 6). NIFTYBEES 2013-26 + GOLDBEES-ext 2013-26 fetched & guarded (new data assets, catalog entries pending Kavya D-009 formalization of the pre-2021 extension).
