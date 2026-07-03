# STRATEGY REGISTER — every strategy the firm runs or is validating (FM owns)
Nothing trades (even paper) without a row here: owner, edge, gates, kill criteria, review date.

| ID | Strategy | Stage | Owner | Per-trade edge (fwd, 210-univ unless noted) | Gates/sizing | Kill criteria | Review |
|---|---|---|---|---|---|---|---|
| S-01 | IV/RV short straddle (IV/RV≥1.4, IV<100% cap) | **SEND-BACK (IC 2026-07-03)** — paper-tracking only, FIREWALLED | Paper: FM (Vikram) · Resurrection: Quant (Arjun) | **REGISTERED EDGE: +11.4pts INCREMENTAL over unconditional short-vol (~+8.8 at 2× costs)** — the +37.6% headline is 71% regime beta (Red Team, memo 20260703) | NO capital. Paper small, live-feed IV-cap fixed first, event-gated | Resurrection: 2018+2020 backfill re-run + per-trade sizing DSR + genuine 3×3 grid + positive incremental through a real vol-spike | first VIX>20 event or 8 wks |
| S-02 | Earnings short-vol (ATM straddle through print) | IC-memo pending | Quant + sector analysts | +21.6%/event, 60% hit fwd (n=1,359) | LARGE-CAP only; skip if expiry-DTE<7 at event (return-explosion artifact) + IT/pharma gap warning | fwd mean <+5% over 2 qtrs | quarterly |
| S-03 | FF calendar single-CE (FF≥0.25, tiered 0.75/1.0/1.25) | IC-memo pending | Quant | +6-9%/trade fwd, 70% hit (n=1,650 FF≥0.2) | LARGE-CAP only (liquid back month); stagger entries; NO stop (K-008), tail via size | fwd mean <+3% over 6 cycles | monthly |
| S-04 | Short strangle 14-DTE 5%-OTM, managed 50% | IC-memo pending | Quant + TCA (Tara) | +1.75%/spot fwd, 88% hit (n=5,039); ~+10-15% on margin | Full univ; ex-ante inverse-IV sizing; event-gate (re-check earnings before EVERY entry); worst −27.8% spot acknowledged | fwd mean <+0.5%/spot over 3 cycles | monthly |
| S-05 | Track-1: delta-hedged 0DTE/DTE1 NIFTY short straddle, morning-straddle ≥0.45% spot filter | Paper-ready (pre-firm validated) | FM (Vikram) | CAGR +5.9%, MaxDD 5%, 6/6 yrs positive [books] | Index-only; real-fill validated | 2 consecutive negative quarters | monthly |
| S-06 | Equity Mom-12-1 + LowVol blend | Backtest (re-run w/ PIT universe + draft costs pending) | Quant | +15%/yr ann (below bar, diversifier) | The only long-equity diversifier vs short-vol book | DSR<0.95 | quarterly |

## Book-level standing rules (CIO)
1. All S-01..S-04 are SHORT-VOL — correlated in a vol spike. Combined book sizing must assume they draw down TOGETHER.
2. No naked short-vol through a name's known binary (earnings/FDA/big policy date). Sector analysts publish the calendar; desk gates entries.
3. Compounded portfolio CAGRs are reporting artifacts — size from per-trade edge × worst-case MTM, never from headline CAGR.
4. Paper first (RESEARCH_SOP §12 DoD), Principal approves any LIVE step (D-010/D-018).
