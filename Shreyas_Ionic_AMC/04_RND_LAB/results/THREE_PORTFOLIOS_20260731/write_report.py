"""Write PORTFOLIOS.md from _state.pkl produced by build_portfolios.py"""
import pickle, json
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
           r"\Shreyas_Ionic_AMC\04_RND_LAB\results\THREE_PORTFOLIOS_20260731")
st = pickle.load(open(OUT / "_state.pkl", "rb"))
sfm = st["sleeve_full_metrics"]
crash_df = st["crash_df"]
results = st["results"]
final_rows = st["final_rows"]
corr_df = st["corr_df"]
feas_rows = st["feas_rows"]
cap_table = st["cap_table"]
static_m, cppi_m = st["static_m"], st["cppi_m"]
cppi_results = st["cppi_results"]

def pct(x, d=2):
    return "n/a" if x is None else f"{x:.{d}f}%"

md = []
md.append("# THREE PORTFOLIOS -- LOW RISK / HIGH CAGR / BALANCED")
md.append("**Built 2026-07-31, Vikram Shah (FM). Script: `build_portfolios.py` in this folder. "
           "Source: `FINAL_RANKING_20260730/all_sleeves_daily.json` (no sleeve rebuilt).**\n")

md.append("## 0. WHAT WAS EXCLUDED / CORRECTED")
md.append("- **S1_GAPFADE EXCLUDED** (mandate hard rule): t=1.44, excess kurtosis 10.11, 38.6% of "
           "profit in 3 trades, only 8.8% of trades replay from stated rules. Never earned a weight.")
md.append("- **The prior 'PORTFOLIO' file (Calmar 2.597, ~73% CAGR) is NOT reused as a starting point** "
           "-- its own metadata says it is built from 'all six' sleeves, i.e. it INCLUDES GAPFADE, so "
           "it is contaminated under the exclusion rule above. Rebuilt clean from the 5 permitted "
           "sleeves: SWEEP, CALENDAR, OVERSHOOT, LD_SELL, BOOK.")
md.append("- **[OPINION, capacity guardrail]** naive inverse-vol weighting run unconstrained wants "
           "60-80%+ of the book in CALENDAR+OVERSHOOT because both look 'quiet' against a full Rs10L "
           "allocation (capital-idleness effect) -- but neither has ever had a capacity check "
           "(STRATEGY_DOSSIER OPEN/OWED item). This may be exactly how the prior ~73% CAGR figure was "
           "reached. As FM I capped each sleeve's scale-up per mandate below rather than let the "
           "optimiser lever up an unverified-capacity sleeve; see the cap table in section 2. Note the "
           "concentration risk did not disappear, it MOVED: HIGH_CAGR's fitted solution instead "
           "concentrates in SWEEP (11.9x its documented backtest size) and BOOK (7.9x) -- a different, "
           "and arguably more executable, capacity ask (NIFTY futures and a diversified equity+S1F book "
           "scale more credibly than a thin monthly calendar spread) but still UNVERIFIED and flagged "
           "for a real capacity-check before any live sizing (see section 5).")
md.append("- **[CORRECTED mid-build, coordinator catch]** Only OVERSHOOT has genuinely NO crash-window "
           "history. CALENDAR and LD_SELL trade on the 16-year daily bhavcopy archive (back to 2011), "
           "so they DO have 2015-16/2018/COVID/2022 data -- but THINLY sampled (1-13 cycles per window), "
           "and LD_SELL shows a **measured negative COVID result** (short premium bleeding in a crash), "
           "corroborated independently by the selling desk (-Rs42,545/27 COVID cycles, worst trade "
           "-50.6% of margin even with a stop). LD_SELL therefore carries the tightest cap of the four "
           "non-BOOK sleeves in the LOW_RISK mandate specifically. A same-expiry-hedged LD_SELL variant "
           "was tested by the desk and makes risk-adjusted return WORSE (Sharpe 0.02 vs 0.92) -- LD_SELL "
           "is sized here on naked/10%-margin economics throughout, no hedged-margin credit taken.")

md.append("\n## 1. PER-SLEEVE STANDALONE METRICS (natural 1x = Rs10L allocation, full available history)")
md.append("| Sleeve | Span | Yrs | CAGR% | MaxDD% | Calmar | Sharpe | PF | Month win% | Active days |")
md.append("|---|---|---|---|---|---|---|---|---|---|")
for nm, m in sfm.items():
    md.append(f"| {nm} | {m['span']} | {m['years']} | {m['CAGR_pct']} | {m['maxDD_pct']} | {m['Calmar']} | "
               f"{m['Sharpe']} | {m['PF']} | {m['month_win_pct']} | {m['active_days']} |")

md.append("\n## 2. CAPACITY / CRASH-RISK CAP TABLE (max weight share of Rs1cr book, by mandate)")
md.append("[OPINION, judgment call -- not derived from data, stated loudly] Reflects (a) unverified "
           "scale-up capacity for CALENDAR/OVERSHOOT, (b) OVERSHOOT's total absence of crash history, "
           "(c) LD_SELL's measured negative crash behaviour.")
md.append("| Sleeve | LOW_RISK | HIGH_CAGR | BALANCED |")
md.append("|---|---|---|---|")
for nm in ["SWEEP", "CALENDAR", "OVERSHOOT", "LD_SELL", "BOOK"]:
    md.append(f"| {nm} | {cap_table['LOW_RISK'][nm]:.0%} | {cap_table['HIGH_CAGR'][nm]:.0%} | {cap_table['BALANCED'][nm]:.0%} |")

md.append("\n## 3. CRASH-WINDOW BEHAVIOUR (raw Rs P&L at natural 1x; n = trading days/cycles inside window)")
md.append("| Window | SWEEP | CALENDAR | OVERSHOOT | LD_SELL | BOOK |")
md.append("|---|---|---|---|---|---|")
for _, r in crash_df.iterrows():
    def cell(nm):
        v, n = r.get(nm), r.get(nm + "_n", 0)
        return "NO DATA" if pd.isna(v) else f"Rs{v:+,.0f} (n={int(n)})"
    md.append(f"| {r['window']} | {cell('SWEEP')} | {cell('CALENDAR')} | {cell('OVERSHOOT')} | {cell('LD_SELL')} | {cell('BOOK')} |")
md.append("\nSWEEP is the only sleeve positive in all four windows (crash hedge). OVERSHOOT has no "
           "observations before 2022. CALENDAR/LD_SELL are thinly sampled (single digits per window) -- "
           "treat their sign as indicative, not established; LD_SELL's negative COVID reading recurs "
           "under two different window definitions (stable), CALENDAR's does not (unstable).")

md.append("\n## 4. WALK-FORWARD WEIGHT FIT (FIT 2022-2023 -> EVAL 2024-2025, no lookahead)")
for pname in ["LOW_RISK", "HIGH_CAGR", "BALANCED"]:
    r = results[pname]
    md.append(f"\n### {pname}")
    md.append(f"- NAIVE (capacity-capped inverse-vol) weights: {r['weights_naive']}")
    md.append(f"  - FIT:  CAGR {r['fit_naive']['CAGR_pct']}%, MDD {r['fit_naive']['maxDD_pct']}%, Calmar {r['fit_naive']['Calmar']}")
    md.append(f"  - EVAL: CAGR {r['eval_naive']['CAGR_pct']}%, MDD {r['eval_naive']['maxDD_pct']}%, Calmar {r['eval_naive']['Calmar']}  "
               f"**OOS/IS(Calmar) = {r['oos_is_naive']}**")
    md.append(f"- FITTED (40k-sample constrained search on FIT only) weights: {r['weights_fitted']}")
    md.append(f"  - FIT:  CAGR {r['fit_fitted']['CAGR_pct']}%, MDD {r['fit_fitted']['maxDD_pct']}%, Calmar {r['fit_fitted']['Calmar']}")
    md.append(f"  - EVAL: CAGR {r['eval_fitted']['CAGR_pct']}%, MDD {r['eval_fitted']['maxDD_pct']}%, Calmar {r['eval_fitted']['Calmar']}  "
               f"**OOS/IS(Calmar) = {r['oos_is_fitted']}**")
    obj_key = "CAGR_pct" if pname != "BALANCED" else "Calmar"
    obj_label = "CAGR" if obj_key == "CAGR_pct" else "Calmar"
    fv, nv = r['eval_fitted'][obj_key], r['eval_naive'][obj_key]
    beat = f"fitted clearly beats naive OOS on the mandate's own objective ({obj_label} {fv} vs {nv})" \
        if (fv or -9) > 1.10 * (nv or -9) else \
        f"fitted does NOT clearly beat naive OOS on the mandate's own objective ({obj_label} {fv} vs {nv})"
    md.append(f"- **CHOSEN: {r['chosen_label']}** -- {beat}; per lesson (weight-fitting overfits: prior "
               f"15,625-combo search gave OOS/IS=0.36), naive is used unless fitted clearly and robustly wins OOS "
               f"on the CORRECT objective for that mandate (not always Calmar -- see section 9).")

md.append("\n## 5. FINAL PORTFOLIO METRICS (chosen weights, FULL_EXT 2022-01 to latest per sleeve)")
md.append("| Metric | LOW_RISK | HIGH_CAGR | BALANCED |")
md.append("|---|---|---|---|")
keys = [("span","Span"),("years","Years"),("CAGR_pct","CAGR %"),("maxDD_pct","MaxDD %"),
        ("Calmar","Calmar"),("Sharpe","Sharpe"),("PF","Profit factor"),("month_win_pct","Monthly win %"),
        ("worst_month_pct","Worst month %"),("worst_3mo_stretch_pct","Worst 3-mo stretch %"),
        ("worst_day_pct","Worst day %"),("capital_deployed_pct","Capital deployed % (of book)"),
        ("capital_utilisation_pct","Capital utilisation % (active x weight)")]
for k, label in keys:
    row = [str(final_rows[p].get(k, "n/a")) for p in ["LOW_RISK","HIGH_CAGR","BALANCED"]]
    md.append(f"| {label} | {row[0]} | {row[1]} | {row[2]} |")

md.append("\n### Chosen weights (fraction of Rs1cr book capital)")
md.append("| Sleeve | LOW_RISK | HIGH_CAGR | BALANCED |")
md.append("|---|---|---|---|")
for nm in ["SWEEP","CALENDAR","OVERSHOOT","LD_SELL","BOOK"]:
    row = [f"{results[p]['chosen_weights'][nm]:.1%}" for p in ["LOW_RISK","HIGH_CAGR","BALANCED"]]
    md.append(f"| {nm} | {row[0]} | {row[1]} | {row[2]} |")

md.append("\n**[OPINION, flagged loudly] HIGH_CAGR's 30.4% CAGR depends on running SWEEP at ~11.9x "
           "and BOOK at ~7.9x their documented/tested size (see section 8 AU table) -- this is a real "
           "capacity assumption, not a free scale-up. SWEEP is delta-1 NIFTY futures (generally the "
           "most scalable instrument here); BOOK's S1F sub-component is registered at ~3-4 lots/Rs10L "
           "in `06_TRADING_DESK/STRATEGY_REGISTER.md` -- running it at 7.9x that is well beyond what "
           "has been risk-approved. A `/capacity-check` on both before any live sizing is a hard "
           "precondition, not a nice-to-have, for the HIGH_CAGR mandate specifically.**")

md.append("\n### Per-sleeve active-day fraction (how often that sleeve is actually in a position)")
afrac = final_rows["LOW_RISK"]["per_sleeve_active_frac_pct"]
md.append("| Sleeve | Active-day % (of FULL_EXT calendar days) |")
md.append("|---|---|")
for nm, v in afrac.items():
    md.append(f"| {nm} | {v}% |")

md.append("\n## 6. PORTFOLIO-vs-SLEEVE correlation (monthly / quarterly, FULL_EXT window)")
for pname in ["LOW_RISK","HIGH_CAGR","BALANCED"]:
    sub = corr_df[corr_df.portfolio == pname]
    md.append(f"\n### {pname}")
    md.append("| Sleeve | corr (monthly) | corr (quarterly) |")
    md.append("|---|---|---|")
    for _, r in sub.iterrows():
        md.append(f"| {r['sleeve']} | {r['corr_monthly']} | {r['corr_quarterly']} |")

md.append("\n## 7. DYNAMIC WEIGHTING TEST -- CPPI drawdown-floor overlay vs STATIC")
md.append("[NOTE] Regime-conditioning on monthly sleeve P&L already tested elsewhere in this lab and "
           "FAILED (28 cells, 0 candidates, 22 dead, n only 111-172 months) -- not re-run; per the "
           "mandate's own steer, only the more-promising CPPI/drawdown-floor variant is tested here. "
           "Overlay: cut exposure to 35% once running drawdown from high-water-mark breaches -6%, "
           "restore to 100% once drawdown recovers above -2% (causal, uses only past equity).")
md.append("| Portfolio | | CAGR% | MaxDD% | Calmar | Sharpe |")
md.append("|---|---|---|---|---|---|")
for pname in ["LOW_RISK", "HIGH_CAGR", "BALANCED"]:
    s_, c_ = cppi_results[pname]["static"], cppi_results[pname]["cppi"]
    md.append(f"| {pname} | STATIC | {s_['CAGR_pct']} | {s_['maxDD_pct']} | {s_['Calmar']} | {s_['Sharpe']} |")
    md.append(f"| {pname} | CPPI | {c_['CAGR_pct']} | {c_['maxDD_pct']} | {c_['Calmar']} | {c_['Sharpe']} |")
md.append("\n**Result: mixed, and informative.** On LOW_RISK and BALANCED (MaxDD only -5..-6%), the "
           "6% floor barely engages -- CPPI is a wash-to-slightly-worse there (fewer active days once "
           "it does trip, no real drawdown to cut). **On HIGH_CAGR, where real drawdown depth exists "
           "(-24.7% static), the floor DOES help**: MaxDD cut from -24.7% to -14.4%, Calmar improved "
           "1.23 -> 1.70, at a real cost (CAGR 30.4% -> 24.4%). This is a genuine, usable risk lever "
           "for HIGH_CAGR specifically -- not the free lunch dynamic weighting is often sold as, but a "
           "legitimate drawdown-vs-return trade a CIO could choose to arm, especially since it pulls "
           "HIGH_CAGR's MaxDD comfortably clear of the firm's 25% hard ceiling instead of sitting right "
           "at it. This mirrors the Principal's own steer that dynamic weighting mostly loses to static, "
           "with one genuine exception where the book actually draws down enough for a floor to matter.")

md.append("\n## 8. LOT / CAPITAL FEASIBILITY -- Rs10L vs Rs1cr book")
md.append("1 AU (allocation unit) = Rs10L capital-equivalent = each sleeve's already-embedded natural "
           "sizing (1 NIFTY futures lot for SWEEP; however many option contracts a Rs10L margin slot "
           "buys at the strikes/expiries already embedded in the other sleeves' trades).")
for row in feas_rows:
    md.append(f"\n### {row['portfolio']}")
    md.append(f"- **Rs1cr book**: AU per sleeve {row['AU_at_1cr']}, total {row['total_AU_1cr']} AU -- {row['Rs1cr_verdict']}.")
    md.append(f"- **Rs10L book**: AU per sleeve {row['AU_at_10L']}, total {row['total_AU_10L']} AU -- {row['Rs10L_verdict']}.")
md.append("\n**This is exactly the 'Rs10L capital base on a Rs1cr book produced an impossible -146% "
           "MDD' trap the mandate warned about** -- forcing Rs1cr-scale weight fractions onto a Rs10L "
           "account implies 10x leverage on the natural per-sleeve margin unit. The Rs10L-feasible rows "
           "above are EXCLUDED as multi-sleeve recipes; the honest substitute is 1 AU (~Rs10L) in the "
           "single highest-weighted sleeve alone, sacrificing diversification entirely. Genuine "
           "cross-sleeve diversification, at any of these three mandates, requires roughly Rs50L-1cr+ "
           "of capital.")

md.append("\n## 9. METHOD NOTES")
md.append("- No-compounding convention throughout (`eq = capital + cumsum(daily P&L)`), matching "
           "`book_level.py`'s established firm convention so these numbers are comparable to prior lab "
           "output.")
md.append("- Weight search: 40,000-sample Dirichlet random search + 3 rounds of local polish (20,000 "
           "samples each) on the FIT window only, maximizing the mandate objective subject to the MDD "
           "constraint and the per-sleeve capacity cap in section 2. This is a much lower-dimensional, "
           "lower-DOF search than the prior 15,625-cell grid that produced OOS/IS=0.36 -- but the OOS/IS "
           "ratios in section 4 show it STILL overfits versus naive on 2 of 3 mandates, which is why "
           "NAIVE was chosen in all three.")
md.append("- FIT/EVAL windows are 2022-2023 / 2024-2025 (2yr/2yr) because BOOK (the equity+S1F "
           "diversifier) only has data from 2022-01-04 -- this is the common window across all five "
           "permitted sleeves. SWEEP/CALENDAR/LD_SELL's pre-2022 history (back to 2011/2015, including "
           "2015-16/2018/COVID) is used ONLY for the standalone per-sleeve stats and crash-window table "
           "in sections 1 and 3, never for weight-fitting -- using it there would need a lookahead-free "
           "proxy for BOOK's pre-2022 behaviour that does not exist.")
md.append("- Costs are already embedded in each sleeve's daily P&L (per `STRATEGY_DOSSIER.md`); no "
           "additional cost model applied here.")
md.append("- **Bug caught and fixed mid-build**: naive inverse-vol weighting, run at full deployment, "
           "systematically OVERWEIGHTS the low-return/low-vol sleeves (CALENDAR/OVERSHOOT/LD_SELL) "
           "regardless of mandate -- the first HIGH_CAGR cut compared fitted-vs-naive on Calmar (as all "
           "three mandates initially did) and picked a naive vector whose EVAL CAGR was only 8.8%, LOWER "
           "than LOW_RISK's 13%, an absurd result for a mandate whose entire point is maximizing CAGR. "
           "Fix: the naive-vs-fitted comparison now uses the MANDATE'S OWN objective (CAGR for LOW_RISK/"
           "HIGH_CAGR, Calmar for BALANCED), which is why HIGH_CAGR alone ends up on the FITTED weights "
           "(a genuine, OOS-improving reallocation toward SWEEP/BOOK) while LOW_RISK and BALANCED stay "
           "on NAIVE. A second bug (`cap_and_renorm` water-filling) let a sleeve pinned to its own cap in "
           "one redistribution round get pushed back over that cap in a later round -- fixed with a "
           "monotonic capped-mask; caught because SWEEP printed at 29.76% against a stated 25% cap.")
md.append("- A CAGR floor (6-8%, roughly half of naive's own EVAL CAGR) is enforced on every candidate in "
           "the search so 'maximize Calmar' cannot degenerate into a near-empty, economically irrelevant "
           "book (a real failure caught on the first BALANCED run: 22.8% deployed, 0.58% CAGR, 'winning' "
           "on Calmar alone).")

open(OUT / "PORTFOLIOS.md", "w", encoding="utf-8").write("\n".join(md))
print("wrote", OUT / "PORTFOLIOS.md")
print(len(md), "lines")
