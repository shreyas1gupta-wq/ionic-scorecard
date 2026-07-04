"""DELTA TABLE builder: old HF-panel BT-11 vs union-panel BT-11 re-run.
Answers: how much of BT-11's early-era edge was SURVIVORSHIP?
Per year 2016-2026 (+ full period): CAGR-proxy (book return %), rupee P&L, win rate, and the
shuffle percentile old-vs-new. 2014-2015 reported as NEW (no old comparison).
Writes delta_per_year.csv + delta_summary.json. Run AFTER bt11_union.py."""
from __future__ import annotations
import json, os
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OLD = os.path.join(ROOT, r"results\T2-SIG11\20260704_bt11")
NEW = os.path.join(ROOT, r"results\T2-SIG11\20260704_bt11_union")

old_m = json.load(open(os.path.join(OLD, "metrics.json")))
new_m = json.load(open(os.path.join(NEW, "metrics.json")))
old_s = json.load(open(os.path.join(OLD, "shuffle_percentile.json")))
new_s = json.load(open(os.path.join(NEW, "shuffle_percentile.json")))

rows = []
for cfg in ["N10_cost1x", "N20_cost1x", "N10_cost2x", "N20_cost2x"]:
    o = old_m[cfg]; n = new_m[cfg]
    o_by = o["per_year_book_return_pct"]; n_by = n["per_year_book_return_pct"]
    o_tr = o["per_year_trade_pl"]; n_tr = n["per_year_trade_pl"]
    years = sorted(set(list(o_by.keys()) + list(n_by.keys())), key=lambda x: int(x))
    for y in years:
        yi = int(y)
        orow = o_by.get(y); nrow = n_by.get(y)
        opl = o_tr.get(y, {}).get("rupee_pl"); npl = n_tr.get(y, {}).get("rupee_pl")
        owr = o_tr.get(y, {}).get("win_rate_pct"); nwr = n_tr.get(y, {}).get("win_rate_pct")
        novol = n_tr.get(y, {}).get("pct_entries_no_vol")
        is_new = (orow is None)  # 2014,2015 = union-only NEW window
        rows.append({
            "config": cfg, "year": yi,
            "old_book_ret_pct": orow, "new_book_ret_pct": nrow,
            "delta_book_ret_pct": (None if is_new else round(nrow - orow, 3)),
            "old_rupee_pl": opl, "new_rupee_pl": npl,
            "delta_rupee_pl": (None if (opl is None or npl is None) else round(npl - opl, 2)),
            "old_win_rate_pct": owr, "new_win_rate_pct": nwr,
            "new_pct_entries_no_vol": novol,
            "status": ("NEW (union-only, no HF comparison)" if is_new else "compared"),
        })
df = pd.DataFrame(rows)
df.to_csv(os.path.join(NEW, "delta_per_year.csv"), index=False)

# ---- full-period + like-for-like summary ----
summary = {}
for cfg in ["N10_cost1x", "N20_cost1x", "N10_cost2x", "N20_cost2x"]:
    o = old_m[cfg]; n = new_m[cfg]
    n_from2016 = n.get("cagr_pct_from_2016")
    summary[cfg] = {
        "OLD_HF": {
            "cagr_pct_2016_2026": o["cagr_pct"], "final_equity_rupees": o["final_equity_rupees"],
            "total_pl_rupees": o["total_pl_rupees"], "max_dd_pct": o["max_drawdown_pct"],
            "monthly_sharpe": o["monthly_sharpe"], "n_trades": o["n_trades"],
        },
        "UNION_full_2014plus": {
            "cagr_pct": n["cagr_pct"], "final_equity_rupees": n["final_equity_rupees"],
            "total_pl_rupees": n["total_pl_rupees"], "max_dd_pct": n["max_drawdown_pct"],
            "monthly_sharpe": n["monthly_sharpe"], "n_trades": n["n_trades"],
            "pct_fills_no_vol_overall": n.get("pct_fills_no_vol_overall"),
        },
        "UNION_like_for_like_from2016": {
            "cagr_pct_2016_2026": n_from2016,
            "delta_cagr_vs_old_pp": (None if n_from2016 is None else round(n_from2016 - o["cagr_pct"], 3)),
        },
    }
# shuffle old vs new (cost1x N10/N20)
for N in ["N10", "N20"]:
    summary.setdefault("shuffle", {})[N] = {
        "OLD_HF": {"real_cagr_pct": old_s[N]["real_cagr_pct"],
                   "shuffle_mean_pct": old_s[N]["shuffle_cagr_mean_pct"],
                   "percentile": old_s[N]["real_percentile_vs_shuffles"],
                   "beats_mean_pp": old_s[N]["beats_shuffle_mean_by_pct_per_yr"]},
        "UNION": {"real_cagr_pct": new_s[N]["real_cagr_pct"],
                  "shuffle_mean_pct": new_s[N]["shuffle_cagr_mean_pct"],
                  "percentile": new_s[N]["real_percentile_vs_shuffles"],
                  "beats_mean_pp": new_s[N]["beats_shuffle_mean_by_pct_per_yr"]},
    }
json.dump(summary, open(os.path.join(NEW, "delta_summary.json"), "w"), indent=2, default=str)

# ---- console read for the operator ----
print("=== DELTA (book return %, per year, N20_cost1x headline) ===")
sub = df[df["config"] == "N20_cost1x"].sort_values("year")
print(sub[["year", "old_book_ret_pct", "new_book_ret_pct", "delta_book_ret_pct",
           "old_rupee_pl", "new_rupee_pl", "status"]].to_string(index=False))
print("\n=== SUMMARY ===")
print(json.dumps(summary, indent=2, default=str))
print("\n[delta] delta_per_year.csv + delta_summary.json written")
