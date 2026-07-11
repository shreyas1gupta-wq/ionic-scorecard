"""Phase-0 #9: consolidated trials ledger + S1-F DSR baseline (Bailey & Lopez de Prado 2014).
Auto-rows from RUN_CARD.json files + curated historical campaign block (sources cited).
DSR computed under a declared grid of (N trials, V[SR]) assumptions — honest range, not one number.
"""
import json
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path
from scipy import stats

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
LAB = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB"
OUT = LAB / "INDEX_PROGRAM_2026"

# ---- 1. auto rows from RUN_CARDs ----
rows = []
for rc in LAB.glob("results/**/RUN_CARD.json"):
    c = json.loads(rc.read_text())
    rows.append(dict(date=c.get("run_ts", "")[:10], family=c["card"], n_trials=c.get("trials_increment", 1),
                     verdict=c.get("verdict", ""), source=str(rc.relative_to(ROOT)), kind="run_card"))

# ---- 2. curated historical block (campaign-level counts, sources = journal/MASTER_PLAN/results dirs) ----
hist = [
    ("2026-07-07", "OPT-SWEEP-50 phase 1", 26, "closed early, nothing cleared bar", "results/OPT_SWEEP50_PHASE1_20260707/PHASE1_SYNTHESIS.md"),
    ("2026-07-07", "misc campaigns 07-07 (meanrev/ORB/PEAD/scalping/sweeps)", 30, "all killed", "results/*_20260707 dirs"),
    ("2026-07-10", "cheap-test battery T1-T10 + FVG + scalp-V7", 12, "all killed/blocked->killed", "results/CHEAPTEST_SPEC_20260710/VERDICTS.md"),
    ("2026-07-10", "sell-side battery (S1/S2 grids, condor, defense, filters)", 45, "S1 family pass; rest killed", "results/SELLSIDE_20260710/"),
    ("2026-07-10", "S1 sensitivity surface", 84, "plateau check (72/84 positive)", "results/SELLSIDE_20260710/s1_sensitivity/"),
    ("2026-07-10", "buy-side last-3h battery + indicator screen", 18, "all killed (K-001 extension)", "results/BUYSIDE_LAST3H_20260710/"),
    ("2026-07-11", "cards C2/A1/C1 (pre-run-card standard)", 6, "refuted/closed/pass-park", "results/{C2_DAYNIGHT,A1_DTE_RICHNESS,C1_OVERNIGHT_TRANSFER}_20260711/"),
]
for d, fam, n, v, s in hist:
    rows.append(dict(date=d, family=fam, n_trials=n, verdict=v, source=s, kind="curated"))

led = pd.DataFrame(rows).sort_values(["date", "family"])
led.to_csv(OUT / "TRIALS_LEDGER.csv", index=False)
N_total = int(led.n_trials.sum())
print(f"ledger rows: {len(led)} | TOTAL TRIALS: {N_total}")

# ---- 3. S1-F DSR baseline ----
tr = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/final_three/final_three_trades.csv")
s1 = tr[tr.strat == "S1"].net
sr_hat = s1.mean() / s1.std(ddof=1)          # per-expiry-day Sharpe
T = len(s1)
sk = stats.skew(s1); ku = stats.kurtosis(s1, fisher=False)
gamma = 0.5772156649

def dsr(N, v_sr):
    """Deflated Sharpe: prob that SR_hat beats the expected max of N null trials."""
    e_max = np.sqrt(v_sr) * ((1 - gamma) * stats.norm.ppf(1 - 1 / N) + gamma * stats.norm.ppf(1 - 1 / (N * np.e)))
    z = ((sr_hat - e_max) * np.sqrt(T - 1)) / np.sqrt(1 - sk * sr_hat + ((ku - 1) / 4) * sr_hat ** 2)
    return stats.norm.cdf(z)

lines = [f"S1-F daily series: T={T}, SR_hat(per expiry)={sr_hat:.3f} (~{sr_hat*np.sqrt(52):.2f} annualized at 52 exp/yr), skew={sk:.2f}, kurt={ku:.1f}",
         f"Total trials on ledger: {N_total} (upper bound for N); sell-side family only: ~157",
         "", "DSR grid (prob. the edge is real after deflating for the search):",
         f"{'N trials':>10} {'V[SR] assumption':>22} {'DSR':>8}"]
for N in [50, 157, N_total]:
    for v_sr, lab in [(sr_hat**2 / 4, "tight (SR^2/4)"), (sr_hat**2, "wide (SR^2)")]:
        lines.append(f"{N:>10} {lab:>22} {dsr(N, v_sr):>8.4f}")
lines += ["", "Reading: DSR > 0.95 = edge survives deflation at that assumption. V[SR] (cross-trial SR variance)",
          "is UNKNOWN for historical cells (not individually recorded) - hence the declared grid, not one number.",
          "From now on RUN_CARDs record per-trial stats so V[SR] becomes measurable. Sameer to refine at Gate-4."]
txt = "\n".join(lines)
print(txt)
(OUT / "DSR_BASELINE.md").write_text("# S1-F DSR baseline + trials ledger (Phase-0 #9, 2026-07-11)\n\n```\n" + txt + "\n```\n", encoding="utf-8")
print("\nsaved:", OUT / "TRIALS_LEDGER.csv", "and DSR_BASELINE.md")
