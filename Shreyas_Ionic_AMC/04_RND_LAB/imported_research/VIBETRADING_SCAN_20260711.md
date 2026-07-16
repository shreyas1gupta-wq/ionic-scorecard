# Vibe-Trading scan (2026-07-11) — HKUDS/Vibe-Trading, 18.8k★ (extract-only per Principal 2026-07-10 note)
NL-question → analysis agent framework: Plan/Ground/Execute/Validate/Deliver pipeline, 19 data loaders with fallback chains, 6 backtest engines, 460-factor Alpha Zoo, bounded-autonomy broker layer. We do NOT install (framework overlaps our firm OS); we adopt concepts.

## ADOPT NOW (cheap, additive, no gate changes)
1. **RUN CARD standard** (theirs: JSON+MD per run with metrics/trades/benchmark/validation/token-cost/repro hash). Ours: every experiment card run emits `RUN_CARD.json` next to RESULTS.md → the consolidated trials ledger (Phase-0 #9, DSR-blocking) becomes a one-line aggregation instead of manual curation. Template at bottom.
2. **AST purity gate for lookahead** (theirs: static analysis gates on factor code). Ours: `04_RND_LAB/lib/ast_lookahead_scan.py` (BUILT TODAY, additive) — flags `.shift(-n)`, `.iloc[i+…]`, `center=True` rolls, `bfill`, whole-frame `.mean()/.std()` normalization, future-date slicing in any backtest script. Run before every experiment: catches T1-T10 instances mechanically, complements lib/lookahead_audit.py's one-day-lag test.
3. **Fallback chains in REMOTE_SOURCES.md** (theirs: loaders ordered by ban-risk). Ours already has the registry; added principle: every catalog dataset lists primary + fallback route.

## ADOPT AT NEXT MILESTONE (needs CEO+CIO sign-off, D-025 — process changes)
4. **Shadow Account / counterfactual audit** (their killer feature): extract rules from actual trade journal, backtest the extracted behavior, diff actual vs counterfactual path + behavior diagnostics (disposition effect, momentum-chasing). For us: run it on the S1-F PAPER ledger after ~13 expiries — it operationalizes kill-criterion #3 (implementation shortfall) AND audits Principal's manual behavior if/when the personal line goes live. Owner: Neel (attribution) + Tara (TCA).
5. **Bootstrap/Monte-Carlo CIs on expectancy** in every run card (theirs: standard validate stage). Cheap addition to Sameer's Gate-4 battery.
6. **Alpha Zoo replication** (Qlib158 + Kakushadze101 + GTJA191 = 460 public factor definitions with IC/IR bench): a factor library benched on OUR PIT NIFTY500 data would give Devika's momentum book literature-prior factors. Medium project → R&D intake (Arjun/Ishaan). The factor families are public papers — Lakshmi prior-art first.

## NOTED, NOT ADOPTED
- Swarm teams / IM-channel runtime / 10-broker connectors / Pine-MQL5 export: we have our own team model, Angel+Kotak only, no TradingView deployment.
- Their India rails include **Dhan + Shoonya APIs** (free broker APIs with data) — potential third data rail if Angel/Kotak ever constrains; needs account = Principal decision. Parked.
- QVeris premium marketplace: paid, park.

## RUN_CARD.json template (adopt from next experiment)
```json
{"card": "A4-CARD", "frozen_commit": "<hash of freeze-only commit>", "run_ts": "", "script": "", 
 "data": ["<catalog keys>"], "n_obs": 0, "metrics": {"mean": 0, "t": 0, "pf": 0, "maxdd": 0},
 "validation": {"era_split": "", "bootstrap_ci95": [0, 0], "lookahead_ast": "PASS|FAIL", "one_day_lag": ""},
 "verdict": "", "bars_hit": [], "trials_increment": 1, "token_cost_agents": 0}
```

## Addendum 2026-07-16 (DESK-20, Principal re-check) — status verified against disk
- Repo now 24.2k★ (was 18.8k on 07-11), MIT, updated today — still active. **Adoption status confirmed on disk, not just planned:** AST scanner live (`lib/ast_lookahead_scan.py`), RUN_CARD.json in real use across A4/B1/B1b/B1c+ result folders, fallback-chain principle in the catalog registry.
- **Still the one open gap: Alpha Zoo replication (item 6) — not started.** Recommend intake card for Arjun/Ishaan (code-only, no D-009 data gate, benches public factor families vs our PIT NIFTY500).
- Dhan/Shoonya third-rail: still parked, no Principal decision in DECISIONS_LOG — unchanged.
- **NEW find: India-specific fork `hopit-ai/india-trade-cli`** (77★, NSE/BSE/NFO) — 7 LLM analysts + VISIBLE bull-vs-bear debate → fund-manager verdict. **Deliberately NOT adopted**: our blind-R1-memo + independent-Red-Team design (SELF_IMPROVEMENT.md anti-collusion section) exists specifically because visible agent debate risks convergence, not verification. Noted for the record, not a gap.

## Scanner first-run triage (2026-07-11, same day)
Ran ast_lookahead_scan.py on today's three experiment scripts: C1 CLEAN; C2 (8) + A1 (5) advisory `?`-flags all triaged FALSE-POSITIVE — .mean()/.std() hits are in results-reporting stat() functions (outcome measurement, not signal normalization); the [i+1] is the overnight-exit mapping (execution-time). Verdicts stand. Standard: every future experiment runs the scanner pre-run; `?`-flags need a one-line triage note in the run card.
