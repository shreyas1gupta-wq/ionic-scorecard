"""S1 Z-SCORE OPEN FADE WITH *REAL* STOPS — replacing my own optimistic loss-cap.

WHY THIS EXISTS — a defect in my own analysis, disclosed:
I estimated S1's stop-loss benefit by CLIPPING endpoint P&L at -40/-60/-80 pts. That produced
Calmar 9.88 and "226% CAGR". **It is an upper bound, not a result.** A loss cap credits the benefit
(trades that END below the cap are truncated) while ignoring the cost (trades that DIP below the cap
intraday and then RECOVER are stopped out and become losses). With mean +4.28 and std 119.5, many
winners certainly dip first. The trade file holds only date/dir/entry/exit — NO PATH — so the clip
was unmeasurable by construction.
This is the same error class as the +3.03 trailing result discredited earlier today.

WHAT THIS DOES: replays every S1 entry against real 1-min bars and applies genuine stops, with
ADVERSE-FIRST resolution inside each bar (if a bar's range contains both the stop and a new favourable
extreme, the STOP is taken). So the result is pessimistic, not optimistic.

Entry convention preserved from the source run: enter at the day's open (first bar >= 09:15 — the
09:00-09:07 PRE-OPEN AUCTION prints must be excluded or every gap/open calc is corrupted), hold to
15:25 unless stopped. dir from the source file.
Cost: era-correct futures round trip, 4.47 pts before 2024-10-01 / 5.97 after, + 0.5 slippage.
Reported: Calmar and the lots permitted by a 25% maxDD budget, so CAGR is always paired with its risk.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).parent
IDX = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
       r"\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet")
LOT, CAP = 65, 1_000_000.0
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}

px = pd.read_parquet(IDX, columns=["open", "high", "low", "close"])
px = px[(px.index.time >= pd.Timestamp("09:15").time()) &
        (px.index.time <= pd.Timestamp("15:30").time())]
print(f"[spot] {len(px):,} bars {px.index.min()} .. {px.index.max()}", flush=True)

tr = pd.read_csv(HERE / "futures_trades_S1_futures_primary_z1.0.csv")
tr["date"] = pd.to_datetime(tr["date"])
print(f"[S1 trades] {len(tr):,}", flush=True)

by_day = {d: g for d, g in px.groupby(px.index.date)}


def replay(stop_pts, trail_pts=0, flat_hhmm="15:25"):
    out = []
    fh, fm = int(flat_hhmm[:2]), int(flat_hhmm[3:])
    for _, r in tr.iterrows():
        d = r["date"].date()
        g = by_day.get(d)
        if g is None or len(g) < 10:
            continue
        sgn = int(r["dir"])
        e = float(g["open"].iloc[0])
        cut = pd.Timestamp(d) + pd.Timedelta(hours=fh, minutes=fm)
        g2 = g[g.index <= cut]
        if len(g2) < 5:
            continue
        hi = g2["high"].to_numpy(); lo = g2["low"].to_numpy(); cl = g2["close"].to_numpy()
        peak = 0.0
        exit_px, why = float(cl[-1]), "flat"
        for k in range(1, len(cl)):
            fav = (hi[k] - e) if sgn > 0 else (e - lo[k])
            adv = (lo[k] - e) if sgn > 0 else (e - hi[k])
            # ADVERSE FIRST: a bar containing both outcomes resolves as the stop
            if stop_pts and adv <= -stop_pts:
                exit_px, why = e - sgn * stop_pts, "stop"
                break
            peak = max(peak, fav)
            if trail_pts and peak > trail_pts and (peak - fav) >= trail_pts:
                exit_px, why = e + sgn * (peak - trail_pts), "trail"
                break
        gross = sgn * (exit_px - e)
        cost = (4.47 if d < pd.Timestamp("2024-10-01").date() else 5.97) + 0.5
        out.append({"date": r["date"], "ds": r["date"].strftime("%Y-%m-%d"),
                    "why": why, "gross": gross, "net": gross - cost})
    return pd.DataFrame(out)


def report(x, lbl):
    if len(x) < 50:
        print(f"{lbl:<34} n={len(x)} too thin"); return
    dd = x.groupby("ds")["net"].sum()
    eq = dd.cumsum()
    mdd = float((eq - eq.cummax()).min())
    yrs = max((x.date.max() - x.date.min()).days / 365.25, .01)
    ppy = x.net.sum() / yrs
    cal = ppy / max(abs(mdd), 1e-9)
    lots = max(int(0.25 * CAP / max(abs(mdd) * LOT, 1)), 0)
    cagr = 100 * ppy * LOT * max(lots, 1) / CAP if lots >= 1 else 0.0
    w, l = x[x.net > 0].net, x[x.net <= 0].net
    pf = float(w.sum() / abs(l.sum())) if l.sum() else np.nan
    mix = x["why"].value_counts().to_dict()
    print(f"{lbl:<34}{len(x):>6}{x.net.mean():>8.2f}{x.net.median():>8.2f}{100*(x.net>0).mean():>6.1f}%"
          f"{ppy:>9.0f}{mdd:>10.0f}{cal:>8.3f}{pf:>7.2f}{lots:>6}{cagr:>8.1f}%  {mix}")


print()
print("=" * 132)
print("S1 WITH REAL STOPS (adverse-first inside each bar). Compare to my clip-based UPPER BOUND.")
print("  clip -40 claimed Calmar 9.88 / 226% CAGR. A real stop must beat its own collateral damage.")
print("=" * 132)
print(f"{'variant':<34}{'n':>6}{'mean':>8}{'median':>8}{'win%':>7}{'pts/yr':>9}{'maxDD':>10}"
      f"{'Calmar':>8}{'PF':>7}{'lots':>6}{'CAGR':>8}  exit mix")
print("-" * 132)
base = replay(0)
report(base, "no stop (EOD flat) BASELINE")
for sl in (40, 60, 80, 120, 200):
    report(replay(sl), f"real stop -{sl}")
report(replay(80, trail_pts=60), "stop -80 + trail 60")
report(replay(120, trail_pts=80), "stop -120 + trail 80")
b2 = replay(80)
if len(b2):
    b2 = b2[b2.date >= pd.Timestamp("2019-03-01")]
    report(b2, "real stop -80, 2019-03 onward")
    report(b2[~b2.ds.isin(SCH)], "stop -80, 2019+, ex-events")
print()
print("  >100% CAGR at a 25% maxDD budget requires Calmar > 4.0.")
print("  firm certified S1-F = 2.83 | sweep flagship = 0.85 | S1 no-stop baseline = 0.213")
print("  If a real stop lands far below the clip's 9.88, the clip was the artifact — as expected.")
