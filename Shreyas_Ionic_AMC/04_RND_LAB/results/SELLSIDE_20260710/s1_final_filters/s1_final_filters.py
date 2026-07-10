"""S1 FINAL filter battery (12 rules) -> frozen final-model recommendation.
ADOPTION BAR (frozen): uplift >= +1.0 pts AND vetoed-days mean < 0 AND kept-t > baseline-t (2.94).
All features D-1 or pre-entry. Basis: 09:20/30 cell, old-cost-model net (+8.02 baseline).
Ledger +12."""
import numpy as np, pandas as pd, datetime as dt
from pathlib import Path
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/s1_final_filters"
OUT.mkdir(parents=True, exist_ok=True)

m = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/s1_filters_kelly/s1_primary_with_features.csv")
m["date"] = pd.to_datetime(m["date"]).dt.date
for c in ["net", "pcr"]: m[c] = pd.to_numeric(m[c], errors="coerce")
m = m.sort_values("date").reset_index(drop=True)

sp = pd.read_csv(ROOT / "intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv", parse_dates=["date"])
sp = sp.set_index("date").sort_index()
sp = sp[sp.index.time >= dt.time(9, 15)]
dd = sp.groupby(sp.index.date).agg(o=("open", "first"), c=("close", "last"))
def rsi(s, n):
    d = s.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)
r14, r5 = rsi(dd.c, 14).shift(1), rsi(dd.c, 5).shift(1)
gap = (dd.o / dd.c.shift(1) - 1) * 100                       # same-day open gap (pre-entry)
pret = dd.c.pct_change().shift(1) * 100
up = (dd.c.diff() > 0).astype(int)
streak = up.groupby((up == 0).cumsum()).cumsum().shift(1)
dist20 = (dd.c / dd.c.rolling(20).mean() - 1).shift(1) * 100
r2 = (sp["close"].pct_change() ** 2).groupby(sp.index.date).sum() ** 0.5
rv3 = r2.rolling(3).mean().shift(1)
rv3_med = rv3.rolling(250, min_periods=100).median()

for col, s in [("rsi14", r14), ("rsi5", r5), ("gap", gap), ("pret", pret),
               ("streak", streak), ("dist20", dist20), ("rv3", rv3), ("rv3med", rv3_med)]:
    m[col] = m["date"].map(s)
m["prev_loss"] = (m["net"].shift(1) < 0)

BASE_T = m.net.mean() / (m.net.std(ddof=1) / np.sqrt(len(m)))
def rule(name, keep_mask):
    keep, veto = m[keep_mask], m[~keep_mask]
    if len(keep) < 100: return f"{name}: keeps {len(keep)} - too few", False
    tk = keep.net.mean() / (keep.net.std(ddof=1) / np.sqrt(len(keep)))
    up_ = keep.net.mean() - m.net.mean()
    adopt = (up_ >= 1.0) and (len(veto) > 0 and veto.net.mean() < 0) and (tk > BASE_T)
    return (f"{name}: keep {len(keep)}/{len(m)} | kept={keep.net.mean():+.2f}(t={tk:.2f}) "
            f"vetoed={veto.net.mean():+.2f}(n={len(veto)}) | uplift={up_:+.2f} | "
            f"{'ADOPT-CANDIDATE' if adopt else 'reject'}"), adopt

rules = [
    ("RSI5 not 80/20",  ~((m.rsi5 >= 80) | (m.rsi5 <= 20))),
    ("RSI5 not 70/30",  ~((m.rsi5 >= 70) | (m.rsi5 <= 30))),
    ("RSI14 not 70/30", ~((m.rsi14 >= 70) | (m.rsi14 <= 30))),
    ("skip |gap|>0.5%", m.gap.abs() <= 0.5),
    ("skip |gap|>1.0%", m.gap.abs() <= 1.0),
    ("skip gap-UP>0.5%", m.gap <= 0.5),
    ("skip gap-DOWN<-0.5%", m.gap >= -0.5),
    ("skip prior-day |ret|>1.5%", m.pret.abs() <= 1.5),
    ("skip vol-regime RV3>2x median", m.rv3 <= 2 * m.rv3med),
    ("skip 4+ up-day streaks", m.streak.fillna(0) < 4),
    ("skip |dist from 20DMA|>3%", m.dist20.abs() <= 3),
    ("skip after prev S1 loss", ~m.prev_loss),
]
lines = [f"# S1 FINAL filter battery. Baseline +{m.net.mean():.2f} t={BASE_T:.2f}. Adoption bar: uplift>=1.0 AND vetoed<0 AND t up."]
adopted = []
for name, mask in rules:
    txt, a = rule(name, mask.fillna(True))
    lines.append(txt)
    if a: adopted.append(name)
lines.append(f"\nADOPT-CANDIDATES: {adopted if adopted else 'NONE - S1 stays unconditional'}")
out = "\n".join(lines)
print(out)
(OUT / "SUMMARY.md").write_text(out + "\n", encoding="utf-8")
