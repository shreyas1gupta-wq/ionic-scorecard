"""B1b GATE-4: costed strategy test. Spec frozen @ aebdaca.
q4 -> long 1x notional close(D+1)->close(D+2), 4 bps RT. Bars: Sharpe>=1, expectancy>=8bps,
maxDD<=15%, era-split both positive. DSR N=7 reported.
"""
import datetime as dt
import json
import numpy as np, pandas as pd
from pathlib import Path
from scipy import stats

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/B1b_GATE4_20260711"
OUT.mkdir(parents=True, exist_ok=True)

panel = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/B1b_FII_CLIENT_SPREAD_20260711/b1b_panel.csv",
                    parse_dates=["day"])
COST = 4.0  # bps round trip
# r1 in panel = close(D+1)->close(D+2) in bps (exactly the trade)
panel["trade"] = np.where(panel.q == 4, panel.r1 - COST, 0.0)
panel = panel.sort_values("day").reset_index(drop=True)

daily = panel.set_index("day")["trade"] / 1e4  # daily return series (0 on idle days)
n_tr = int((panel.q == 4).sum())
per_trade = panel[panel.q == 4].trade  # net bps per trade
sharpe = daily.mean() / daily.std(ddof=1) * np.sqrt(252)
eq = (1 + daily).cumprod()
dd = (eq / eq.cummax() - 1).min() * 100
mid = panel.day.iloc[len(panel) // 2]
era1 = panel[panel.day < "2023-01-01"]; era2 = panel[panel.day >= "2023-01-01"]
e1 = era1[era1.q == 4].trade.mean(); e2 = era2[era2.q == 4].trade.mean()

# DSR with N=7 family cells; V[SR] measured proxy = variance of the 7 recorded per-day spreads' t/sqrt...
# per spec: report with V[SR] grid as in baseline
sr_hat = daily.mean() / daily.std(ddof=1)  # per-day
T = len(daily)
sk = stats.skew(daily); ku = stats.kurtosis(daily, fisher=False)
gamma = 0.5772156649
def dsr(N, v_sr):
    e_max = np.sqrt(v_sr) * ((1 - gamma) * stats.norm.ppf(1 - 1 / N) + gamma * stats.norm.ppf(1 - 1 / (N * np.e)))
    z = ((sr_hat - e_max) * np.sqrt(T - 1)) / np.sqrt(1 - sk * sr_hat + ((ku - 1) / 4) * sr_hat ** 2)
    return stats.norm.cdf(z)

bars = {
    "sharpe>=1.0": sharpe >= 1.0,
    "expectancy>=8bps": per_trade.mean() >= 8.0,
    "maxDD<=15%": dd >= -15.0,
    "era_both_positive": (e1 > 0) and (e2 > 0),
}
verdict = "GATE-4 PASS -> red-team + sensitivity next (no autoadvance)" if all(bars.values()) \
          else "GATE-4 FAIL -> stream DEMOTED to watch-list (sample closed)"

lines = [f"trades={n_tr} over {T} days ({panel.day.min().date()}..{panel.day.max().date()}) | trade freq {n_tr/T*100:.0f}%",
         f"net per trade: mean {per_trade.mean():+.1f} bps (median {per_trade.median():+.1f}, win% {(per_trade>0).mean()*100:.0f}%)",
         f"annualized net Sharpe (all days): {sharpe:.2f}  | maxDD {dd:.1f}%  | total return {(eq.iloc[-1]-1)*100:+.1f}%",
         f"era split (net bps/trade): 2019-22 {e1:+.1f} | 2023-26 {e2:+.1f}",
         "bars: " + ", ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in bars.items()),
         f"DSR (N=7): tight {dsr(7, sr_hat**2/4):.3f} | wide {dsr(7, sr_hat**2):.3f}",
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")
panel.to_csv(OUT / "gate4_daily.csv", index=False)

card = {"card": "B1b-GATE4", "frozen_commit": "aebdaca", "run_ts": dt.datetime.now().isoformat(timespec="seconds"),
        "script": "b1b_gate4.py", "data": ["b1b_panel (participant_oi_normalized + kaggle NIFTY)"],
        "n_obs": n_tr, "metrics": {"sharpe": round(float(sharpe), 2), "bps_per_trade": round(float(per_trade.mean()), 1),
        "maxdd_pct": round(float(dd), 1)}, "validation": {"era_split": f"{e1:+.1f}/{e2:+.1f}",
        "bootstrap_ci95": None, "lookahead_ast": "pre-flight", "one_day_lag": "T+1 by construction"},
        "verdict": verdict, "bars_hit": [k for k, v in bars.items() if v],
        "trials_increment": 1, "token_cost_agents": 0}
(OUT / "RUN_CARD.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
print("RUN_CARD.json written")
