"""TWO PRINCIPAL-SPECIFIED TESTS (2026-07-30).

TEST 1 — "TOP-DECILE-EXCLUDED BREAKEVEN" (Principal's robustness criterion, now firm convention):
  *"trend catchers will always be skewed, but it should be balanced such that even if we miss the top
   10% trades at least we still breakeven."*
  This is STRICTER and more useful than the single-trade >30% concentration check I had been using.
  Strip the best 10% (and 5%/20%) of trades and ask whether the strategy is still >= breakeven.
  Rationale: in live trading you WILL miss the best trades (not at the screen, limit unfilled, sized
  small, on holiday). A strategy that only works if you catch every outlier is not executable.

TEST 2 — VOL-FLOOR FILTER ON THE SWEEP, MECHANISM-MOTIVATED (not data-mined):
  The sweep's profit lives in its RIGHT TAIL (p95 = 202 pts, max win 607 pts vs mean 16). Tails require
  volatility to exist. Measured fact: the flagship's dead window (Oct-2024..2025) had the LOWEST realized
  vol and VIX of any era (RV 11.39%, VIX 13.58) and 2026 rebounded (16.69%/16.74).
  => HYPOTHESIS WITH A STATEABLE MECHANISM: the strategy needs a vol FLOOR; below it, the 200+pt runners
  that carry the P&L never materialise and the fixed trail just bleeds.
  GUARD AGAINST FITTING: report ALL buckets with n (not just the good ones), and require the filter to
  work in BOTH the pre-Oct-2024 and post-Oct-2024 halves. A filter that only rescues the recent window
  is a FITTED PATCH and must be labelled as such.
  Vol state is computed on a TRAILING window only (no lookahead, no full-sample percentile).
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
R = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
         r"\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results")
OUT = Path(__file__).parent
LOT, CARRY_M = 75, 0.005
SPLIT = pd.Timestamp("2024-10-01")

# ---------------------------------------------------------------- candidate trade series
def load_candidates() -> dict[str, pd.DataFrame]:
    S = {}
    for tag, fn in (("SWEEP_E", "trades_E_swing3_trail60_1lot.csv"),
                    ("SWEEP_D", "trades_D_overnight1_trail40_1lot.csv")):
        t = pd.read_csv(R / "SWEEP_11YR_20260729" / fn)
        t["date"] = pd.to_datetime(t["date"])
        carry = t["entry"] * (CARRY_M / 30.0) * np.maximum(t["hold_min"] / 375.0, 0.5)
        t["net"] = (t["gross_pts"] - np.sign(t["dir"]) * carry) * LOT - t["cost"]
        S[tag] = t[["date", "net"]]
    rc = pd.read_csv(R / "RATIO_CALENDAR_20260730" / "grid_a_trades_raw.csv")
    c = rc[(rc.strike_struct == "ATM_ATM") & (rc.ratio == "1x1") & (rc.exit_variant == "3d_before")]
    c = c.drop_duplicates(subset=["day0", "near_expiry"]).copy()
    c["date"] = pd.to_datetime(c["exit_day"]); c["net"] = c["net_pts"] * LOT
    S["CALENDAR_1x1"] = c[["date", "net"]]
    sw = pd.read_csv(R / "SWING_DELTA1_20260729" / "all_trades.csv")
    m = [x for x in sw["cell"].unique() if "priorweek" in x and "fixed_10" in x]
    if m:
        q = sw[sw["cell"] == m[0]].copy(); q["date"] = pd.to_datetime(q["exit_date"])
        S["SWING_pw10"] = q[["date", "net"]]
    bk = pd.read_csv(R / "STACKED_BOOK_20260711" / "book_daily_pnl.csv", index_col=0)
    bk.index = pd.to_datetime(bk.index)
    for col in ("s1f", "b1b"):
        if col in bk.columns:
            x = bk[[col]].reset_index(); x.columns = ["date", "net"]
            S[f"book_{col}"] = x[x.net != 0]
    return S


def topdecile_test(df: pd.DataFrame, label: str) -> dict:
    n = df["net"].to_numpy(float)
    tot = n.sum()
    out = {"strategy": label, "n": len(n), "net_total": round(tot)}
    for pct in (5, 10, 20):
        k = int(np.ceil(len(n) * pct / 100))
        kept = np.sort(n)[:-k] if k else n          # drop the k BEST trades
        out[f"ex_top{pct}_net"] = round(float(kept.sum()))
        out[f"ex_top{pct}_ok"] = bool(kept.sum() >= 0)
    # how much of gross profit lives in the best decile
    pos = n[n > 0]
    k10 = int(np.ceil(len(n) * 0.10))
    out["top10_share_of_gross_profit"] = round(float(np.sort(n)[-k10:].sum() / max(pos.sum(), 1)), 3)
    return out


print("=" * 116)
print('TEST 1 — "MISS THE TOP 10% AND STILL BREAKEVEN?"  (Principal robustness criterion)')
print("=" * 116)
S = load_candidates()
rows = [topdecile_test(d, k) for k, d in S.items()]
t1 = pd.DataFrame(rows)
t1.to_csv(OUT / "topdecile_robustness.csv", index=False)
print(f"{'strategy':<15}{'n':>6}{'net':>12}{'ex-top5%':>13}{'ex-top10%':>13}{'ex-top20%':>13}"
      f"{'top10 share':>13}  verdict")
print("-" * 116)
for _, r in t1.iterrows():
    v = "PASS (survives losing best 10%)" if r["ex_top10_net"] >= 0 else "FAIL (needs the outliers)"
    print(f"{r['strategy']:<15}{r['n']:>6}{r['net_total']:>12,}{r['ex_top5_net']:>13,}"
          f"{r['ex_top10_net']:>13,}{r['ex_top20_net']:>13,}{r['top10_share_of_gross_profit']:>13}  {v}")

# ---------------------------------------------------------------- TEST 2: vol floor on sweep
print()
print("=" * 116)
print("TEST 2 — VOL-FLOOR FILTER ON SWEEP_E (mechanism: the right tail needs volatility)")
print("=" * 116)
# daily close -> trailing realized vol, memory-light (close column only, resample immediately)
px = pd.read_parquet(R.parent.parent.parent / "intraday_options_strategy" / "datasets" /
                     "processed" / "nifty_1min.parquet", columns=["close"])
px = px[(px.index.time >= pd.Timestamp("09:15").time()) &
        (px.index.time <= pd.Timestamp("15:30").time())]
daily = px["close"].resample("D").last().dropna()
del px
ret = np.log(daily).diff()
rv20 = ret.rolling(20).std() * np.sqrt(252) * 100          # trailing only
rv_pct = rv20.rolling(252, min_periods=120).rank(pct=True)  # trailing percentile, no lookahead
volinfo = pd.DataFrame({"rv20": rv20, "rv_pct": rv_pct}).dropna()

t = S["SWEEP_E"].copy()
t["d"] = t["date"].dt.normalize()
# state must be known BEFORE the trade -> shift by 1 day
vi = volinfo.copy(); vi.index = vi.index.normalize()
vi = vi.shift(1)
t = t.join(vi, on="d")
t = t.dropna(subset=["rv20", "rv_pct"])
t["era"] = np.where(t["date"] >= SPLIT, "post_Oct2024", "pre_Oct2024")

print(f"{'bucket':<22}{'era':<15}{'n':>6}{'net':>13}{'mean/trade':>12}{'PF':>7}")
print("-" * 116)
buckets = [("rv_pct<0.25", lambda x: x.rv_pct < 0.25),
           ("rv_pct 0.25-0.50", lambda x: (x.rv_pct >= 0.25) & (x.rv_pct < 0.50)),
           ("rv_pct 0.50-0.75", lambda x: (x.rv_pct >= 0.50) & (x.rv_pct < 0.75)),
           ("rv_pct>=0.75", lambda x: x.rv_pct >= 0.75),
           ("FILTER rv_pct>=0.25", lambda x: x.rv_pct >= 0.25),
           ("FILTER rv_pct>=0.40", lambda x: x.rv_pct >= 0.40),
           ("ALL (no filter)", lambda x: pd.Series(True, index=x.index))]
res2 = []
for name, f in buckets:
    for era in ("pre_Oct2024", "post_Oct2024", "ALL"):
        d = t if era == "ALL" else t[t.era == era]
        d = d[f(d)]
        if len(d) < 10:
            continue
        w, l = d[d.net > 0]["net"], d[d.net <= 0]["net"]
        pf = float(w.sum() / abs(l.sum())) if l.sum() else np.nan
        res2.append({"bucket": name, "era": era, "n": len(d), "net": round(float(d.net.sum())),
                     "mean": round(float(d.net.mean())), "PF": round(pf, 2)})
        print(f"{name:<22}{era:<15}{len(d):>6}{round(float(d.net.sum())):>13,}"
              f"{round(float(d.net.mean())):>12,}{round(pf, 2):>7}")
pd.DataFrame(res2).to_csv(OUT / "volfloor_sweep.csv", index=False)
print("\nwrote topdecile_robustness.csv, volfloor_sweep.csv")
