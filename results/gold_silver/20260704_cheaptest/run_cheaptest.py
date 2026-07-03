"""Gold/Silver diversifier CHEAP-TEST (gate 3) — pre-registered kill criteria from
ideas/20260703_gold_silver_sleeve.md: KILL if gold mean return on worst equity-decile days < 0
OR tail correlation to equity > +0.3. Runs on D-009-passed ETF series + equal-weight equity proxy.
Equity proxy limitation (stated): HF daily panel ends 2026-01-22, extended with Angel 2026 bulk
(477 syms Feb→Jul 2026); proxy = equal-weight mean daily return of symbols with >90% coverage.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "results/gold_silver/20260704_cheaptest"
sys.path.insert(0, str(ROOT / "intraday_options_strategy/buying"))
import shortlist_shortvol as sv  # reuse combined_close (HF ∪ Angel-2026)

# --- data ---
gold = pd.read_parquet(ROOT / "datasets/etf_gold_silver/goldbees_daily.parquet")
silv = pd.read_parquet(ROOT / "datasets/etf_gold_silver/silverbees_daily.parquet")
for d in (gold, silv):
    d["date"] = pd.to_datetime(d["timestamp"]).dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
g = gold.set_index("date")["close"].pct_change().dropna()
s = silv.set_index("date")["close"].pct_change().dropna()

C = sv.combined_close()
cov = C.notna().mean()
panel = C[cov[cov > 0.90].index]
eq = panel.pct_change().mean(axis=1).dropna()          # equal-weight market proxy
eq = eq[(eq.index >= g.index.min())]

# align
df = pd.concat({"eq": eq, "gold": g, "silver": s}, axis=1).dropna(subset=["eq", "gold"])
print(f"aligned days: {len(df)}  ({df.index.min().date()} -> {df.index.max().date()})  silver overlap: {df['silver'].notna().sum()}")

res = {"aligned_days": len(df), "range": [str(df.index.min().date()), str(df.index.max().date())]}

def kill_test(sub, tag):
    q10 = sub["eq"].quantile(0.10)
    worst = sub[sub["eq"] <= q10]
    out = {}
    for etf in ("gold", "silver"):
        w = worst[etf].dropna()
        if len(w) < 10:
            out[etf] = {"n": len(w), "note": "too few"}
            continue
        out[etf] = {
            "n": int(len(w)),
            "mean_on_worst_days": float(w.mean()),
            "hit_positive": float((w > 0).mean()),
            "tail_corr": float(worst["eq"].corr(worst[etf])),
            "full_corr": float(sub["eq"].corr(sub[etf])),
        }
    res[tag] = out
    print(f"\n=== {tag} (worst-decile eq days, n={len(worst)}, eq mean {worst['eq'].mean():+.2%}) ===")
    for etf, v in out.items():
        if "note" in v:
            print(f"  {etf}: n={v['n']} {v['note']}"); continue
        print(f"  {etf:6s}: mean {v['mean_on_worst_days']:+.3%} | hit+ {v['hit_positive']:.0%} | tail corr {v['tail_corr']:+.2f} | full corr {v['full_corr']:+.2f}")

kill_test(df, "FULL")
kill_test(df[df.index < "2024-01-01"], "2021-23")
kill_test(df[df.index >= "2024-01-01"], "2024-26")

# worst 5 equity weeks
wk = df.resample("W").agg({"eq": lambda x: (1 + x).prod() - 1, "gold": lambda x: (1 + x).prod() - 1})
w5 = wk.nsmallest(5, "eq")
print("\n=== worst 5 equity WEEKS -> gold same week ===")
print(w5.to_string(formatters={"eq": "{:+.2%}".format, "gold": "{:+.2%}".format}))
res["worst5_weeks"] = [[str(i.date()), float(r["eq"]), float(r["gold"])] for i, r in w5.iterrows()]

# overlay illustration: 85/15 eq/gold monthly worst
mo = df.resample("ME").agg({"eq": lambda x: (1 + x).prod() - 1, "gold": lambda x: (1 + x).prod() - 1}).dropna()
blend = 0.85 * mo["eq"] + 0.15 * mo["gold"]
print(f"\n=== overlay: worst MONTH pure-eq {mo['eq'].min():+.2%} vs 85/15 blend {blend.min():+.2%} | ann ret eq {mo['eq'].mean()*12:+.1%} vs blend {blend.mean()*12:+.1%} ===")
res["overlay"] = {"worst_month_eq": float(mo["eq"].min()), "worst_month_blend": float(blend.min()),
                  "ann_eq": float(mo["eq"].mean() * 12), "ann_blend": float(blend.mean() * 12)}

# verdict per pre-registered criteria (GOLD is the hypothesis; silver informational)
gm = res["FULL"]["gold"]["mean_on_worst_days"]; gc = res["FULL"]["gold"]["tail_corr"]
verdict = "KILL" if (gm < 0 or gc > 0.3) else "PASS"
res["verdict"] = {"gold_mean_worst_days": gm, "gold_tail_corr": gc, "criteria": "KILL if mean<0 OR tail_corr>+0.3", "verdict": verdict}
print(f"\n>>> VERDICT: {verdict}  (gold mean on worst days {gm:+.3%}, tail corr {gc:+.2f}; kill if <0 or >+0.3)")
(OUT / "metrics.json").write_text(json.dumps(res, indent=1))
(OUT / "config.json").write_text(json.dumps({
    "date": "2026-07-04", "test": "gold_silver_cheaptest_gate3",
    "kill_criteria": "gold mean return on worst equity-decile days < 0 OR tail corr > +0.3 (pre-registered in one-pager)",
    "data": {"gold": "datasets/etf_gold_silver/goldbees_daily.parquet (D-009 PASS)",
             "silver": "datasets/etf_gold_silver/silverbees_daily.parquet",
             "equity_proxy": "equal-weight mean of combined HF+Angel2026 panel, >90% coverage syms",
             "limitation": "proxy not NIFTY TR index; HF panel ends 2026-01-22, Angel extends to 2026-07-03"}}, indent=1))
print("saved metrics.json + config.json")
