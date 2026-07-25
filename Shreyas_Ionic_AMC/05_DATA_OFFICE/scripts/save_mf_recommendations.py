# -*- coding: utf-8 -*-
"""save_mf_recommendations.py — persist the full MF recommendation set to the firm tree
(Principal 2026-07-26: "save all mf recomm all catg buy/sell/hold also check new launches").

Runs QFRA-1 (mf_capture_recomm) across ALL 6 categories at the latest month-end anchor
(June-end 2026 — a one-time out-of-cycle save; the standing cadence is APR-END/OCT-END),
joins QFRA-2 verdicts where the fund is in the curated 40, flags NEW/young funds
(NAV history too short for the engines — the blank-gate class), and writes:

  03_RESEARCH_DESK/MF_RECOMMENDATIONS/<anchor>/QFRA1_all_categories.csv
  03_RESEARCH_DESK/MF_RECOMMENDATIONS/<anchor>/QFRA2_verdicts.csv   (copy, with asof)
  03_RESEARCH_DESK/MF_RECOMMENDATIONS/<anchor>/MF_RECOMMENDATIONS.md (summary)

Read-only on the workbook. Usage: python save_mf_recommendations.py
"""
import os
import re
import csv
import shutil
import importlib.util

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIRM = os.path.abspath(os.path.join(HERE, "..", ".."))
DASHBOARD = os.path.abspath(os.path.join(FIRM, "..", "MF Dashboard.xlsx"))
QFRA2_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\mr_x_framework\outputs\recommendations\QFRA2_current.csv"
CATS = {"large": "large2", "largemid": "largemid2", "mid": "mid2",
        "flexi": "flexi2", "multi": "multi2", "small": "small2"}
YOUNG_MONTHS = 30    # < ~2.5y of NAV history = young/new launch for engine purposes


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _norm(s):
    return re.sub(r"[^a-z]", "", str(s).lower())


def main():
    mod = _load("mf_capture_recomm", os.path.join(HERE, "mf_capture_recomm.py"))
    import openpyxl
    wb = openpyxl.load_workbook(mod.resolve_path(DASHBOARD), read_only=True, data_only=True)

    # coverage-aware anchor: the workbook is hand-updated and can carry a NEWER anchor row
    # whose NAV data is mostly empty (large @2026-04-30 rated 1/30 funds, 2026-07-26) —
    # walk back until >=80% of funds actually produce a BUY/SELL/HOLD
    frames, notes = [], []
    for cat, cat2 in CATS.items():
        chosen = None
        for idx in range(-1, -13, -1):
            try:
                df, anchor = mod.compute_category(wb, cat, cat2, cat, target_anchor_idx=idx, verbose=False)
            except Exception:
                continue
            cov = df.recommendation.isin(["BUY", "SELL", "HOLD"]).mean()
            if cov >= 0.8:
                chosen = (df, anchor, idx, cov)
                break
            if idx == -1:
                notes.append(f"{cat}: latest anchor {getattr(anchor, 'date', lambda: anchor)()} "
                             f"rated only {cov:.0%} of funds (incomplete NAV rows) — walked back")
        if chosen is None:
            raise SystemExit(f"{cat}: no anchor with >=80% coverage in the last 12 — workbook broken")
        df, anchor, idx, cov = chosen
        df.insert(0, "category", cat)
        df["anchor"] = str(getattr(anchor, "date", lambda: anchor)())
        df["coverage"] = round(cov, 3)
        frames.append(df)
        print(f"{cat:9s} anchor={df['anchor'].iloc[0]} (idx {idx}, coverage {cov:.0%})  "
              f"BUY {int((df.recommendation == 'BUY').sum())} / "
              f"SELL {int((df.recommendation == 'SELL').sum())} / "
              f"HOLD {int((df.recommendation == 'HOLD').sum())}  (n={len(df)})")
    allrec = pd.concat(frames, ignore_index=True)
    anchor_used = allrec["anchor"].max()

    # ---- QFRA-2 join (curated 40 only; anything else is honestly framework-2-uncovered)
    q2 = pd.read_csv(QFRA2_CSV)
    q2["_k"] = q2["fund"].map(_norm)
    allrec["_k"] = allrec["fund"].map(_norm)
    j = q2[["_k", "verdict", "qfra_score", "merit_grade", "conviction", "new_fund", "asof"]].rename(
        columns={"verdict": "qfra2_verdict", "qfra_score": "qfra2_score",
                 "merit_grade": "qfra2_grade", "new_fund": "qfra2_new_fund", "asof": "qfra2_asof"})
    allrec = allrec.merge(j, on="_k", how="left").drop(columns=["_k"])

    # ---- young/new-launch flag + data currency, from the raw NAV matrices ----
    young, data_cut = {}, {}
    for cat in CATS:
        dates, fund_names, nav = mod.load_raw_sheet(wb, cat)
        data_cut[cat] = str(dates.max().date()) if len(dates) else "-"
        for j, fund in enumerate(fund_names):
            col = nav[:, j]
            idx = [i for i, v in enumerate(col) if v == v]     # non-NaN
            if idx:
                months = (dates.max() - dates[idx[0]]).days / 30.4
                if months < YOUNG_MONTHS:
                    young[_norm(fund)] = round(months, 1)
    allrec["young_fund_months"] = allrec["fund"].map(lambda f: young.get(_norm(f)))
    print("raw NAV data cut per category:", data_cut)

    # ---- write (folder named by SAVE date — anchors differ per category and none is
    # June-end: the honest label is when we saved, with per-category anchors inside) ----
    import datetime as _dt
    outdir = os.path.join(FIRM, "03_RESEARCH_DESK", "MF_RECOMMENDATIONS",
                          f"saved_{_dt.date.today().isoformat()}")
    os.makedirs(outdir, exist_ok=True)
    p1 = os.path.join(outdir, "QFRA1_all_categories.csv")
    allrec.to_csv(p1, index=False)
    p2 = os.path.join(outdir, "QFRA2_verdicts.csv")
    shutil.copy2(QFRA2_CSV, p2)

    import datetime as _dt2
    lines = [f"# MF Recommendations — saved {_dt2.date.today().isoformat()} (one-time out-of-cycle, Principal 2026-07-26)",
             "",
             "**Standing cadence: full model re-run at APR-END and OCT-END only (next: Oct-end 2026);**",
             "NAVs accrue monthly (1st). QFRA-1 = short-term capture overlay; QFRA-2 verdicts joined",
             "where the fund is in its curated set (asof per column). Client-facing fund Sell needs",
             "BOTH frameworks non-Hold (dual-framework rule).",
             "",
             "## [DATA] Anchor honesty — a June-end set is NOT computable from the current workbook",
             f"Raw NAV data cut per category: {data_cut}. The `large` sheet was extended to May-2026",
             "but its new rows rate only 1/30 funds (mostly empty NAV cells + at least one typo cell",
             "'13O'), so the engine walked back to the latest anchor where >=80% of funds are ratable.",
             "Per-category anchors are in the CSV. To produce a TRUE June-end 2026 set: backfill the",
             "dashboard's month-end NAVs Feb-2025 to Jun-2026 (AMFI history), then re-run this script.",
             ""]
    if notes:
        lines += ["**Walk-back notes:** " + " · ".join(notes), ""]
    for cat in CATS:
        sub = allrec[allrec.category == cat]
        buys = sub[sub.recommendation == "BUY"].sort_values("IR_rank")
        sells = sub[sub.recommendation == "SELL"]
        lines.append(f"## {cat}  (n={len(sub)}, anchor {sub['anchor'].iloc[0]})")
        lines.append(f"- **BUY ({len(buys)}):** " + ("; ".join(
            f"{r.fund} (rank {int(r.IR_rank)}, HC {r.HC_total_cap_6M:.2f}, FN {r.FN_downside_cap_6M:.2f})"
            for _, r in buys.iterrows()) or "none"))
        lines.append(f"- **SELL ({len(sells)}):** " + ("; ".join(
            f"{r.fund} (12M excess {r.CJ_trailing12M_excess:+.1%})" for _, r in sells.iterrows()) or "none"))
        lines.append(f"- HOLD: {int((sub.recommendation == 'HOLD').sum())}")
        yg = sub[sub.young_fund_months.notna()]
        if len(yg):
            lines.append(f"- Young/new funds (<{YOUNG_MONTHS} months of history — engine cannot rate; "
                         f"the workbook's blank-gate forces HOLD): " +
                         "; ".join(f"{r.fund} (~{r.young_fund_months:.0f}m)" for _, r in yg.iterrows()))
        lines.append("")
    nf = q2[q2.new_fund.astype(str).str.lower().isin(("true", "1", "yes"))]
    lines.append("## New-fund flags from QFRA-2 (curated set)")
    lines.append("; ".join(f"{r.fund} ({r.category})" for _, r in nf.iterrows()) or "none flagged")
    lines.append("")
    lines.append("_New NFO launches (post-data-cut) have no ratable record by construction; they are"
                 " listed for awareness in the journal, never recommended without 3y history._")
    p3 = os.path.join(outdir, "MF_RECOMMENDATIONS.md")
    open(p3, "w", encoding="utf-8").write("\n".join(lines))
    print("\nsaved:")
    for p in (p1, p2, p3):
        print(" ", p)


if __name__ == "__main__":
    main()
