# IC-memo Round-1 fan-out — cheap test (n=2, pre-registered before running)

**Question:** does the IC memo's current Round-1 (3 parallel independent specialist
agents, blind to each other) produce material that a single consolidated call
covering the same 3 lenses can't match — enough to justify ~3x the token cost?
Follows directly from D-036 (Red Team moved Opus->Sonnet on WS-4 evidence);
this is the fan-out pattern WS-4 did NOT test, flagged as untested in that
session's own follow-up.

**This is a cheap-test (Gate-3-style), NOT a full study**: n=2 real pipeline
ideas, single grading pass, no repeat runs. Directional evidence only — a
signal to decide whether a bigger test is warranted, not a certified verdict.

## Arms
- **Arm X (current pattern):** 3 parallel agent calls, real firm personas, each
  blind to the other two, each writing their lens's IC-memo section.
- **Arm Y (consolidated):** 1 single Sonnet call, no persona, one prompt asking
  for all 3 lenses in one pass.
Same task text into both arms. Neither arm sees the other's output.

## Samples (real IDEA_PIPELINE rows, chosen because each already has enough
real supporting material for a 3-lens memo, and neither is at a stage where a
test memo could be mistaken for the real IC verdict)
1. **Track-2 small-cap leadership momentum** (IDEA_PIPELINE row, stage
   3-CHEAP-TEST) — Arm X personas: `fm-equities-devika-menon` (book/allocation
   lens), `quant-head-arjun-rao` (stats/backtest-validity lens),
   `technical-head-dhruv-kapoor` (trend/entry lens).
2. **FF term-structure, liquidity-native vehicle** (IDEA_PIPELINE row, stage
   1-INTAKE, scoping memo `04_RND_LAB/ideas/20260707_ff_signal_near_month_vehicle.md`)
   — Arm X personas: `structurer-aakash-jain` (vehicle/strike/liquidity lens),
   `quant-head-arjun-rao` (signal-stats lens), `execution-tca-tara-singh`
   (fill-realism lens).

## Grading
One blind Sonnet grading call per sample: both memos shown as "Memo 1"/"Memo 2"
(order randomized, no persona names), asked which is more complete/actionable
across all 3 lenses, or whether they're equivalent. Grader also flags anything
one memo surfaces that the other misses entirely.

## Pre-registered kill threshold (written before any agent runs)
If, on BOTH samples, the blind grader rates arm Y (1 call) as equivalent to or
better than arm X (3 calls) — i.e. no lens-specific content is genuinely missing
from Y — that is directional evidence AGAINST keeping Round-1 fan-out as the
default, mirroring the Red Team result. If arm X wins clearly on at least one
sample (surfaces something Y misses that changes the memo's substance), that is
evidence the fan-out is earning its cost here, unlike the WS-4 verification
chain, and Round-1 should NOT be touched pending a larger test.

n=2 explicitly is NOT enough to certify either direction — this decides
whether to run something bigger, not whether to change MODEL_ASSIGNMENTS.md
or the /ic-memo skill outright.
