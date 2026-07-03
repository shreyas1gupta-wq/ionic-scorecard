"""GAP-SELL grid on NIFTY index options: gap-up -> sell CE, gap-down -> sell PE.

Full grid: gap threshold {0.3%,0.6%,0.9%} x stop-loss {10%,25%,50%} x strike {ATM,0.25%OTM,0.5%OTM}
= 27 combos. Entry after first 5 min (09:20 use 09:15+5min bar), exit EOD (15:15) or on stop.
Fixed 1 lot, real 1-min prices, realistic short-side costs. Build 2021-2025 / forward 2026 H1.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

import chain
from engine import BROKERAGE_PER_ORDER, STT_SELL_PCT, EXCH_TXN_PCT, GST_PCT, SEBI_PER_CRORE, \
    STAMP_BUY_PCT, STEP

LOT = 75
SLIP = 0.005
SPLIT = dt.date(2025, 12, 31)
ENTRY_HHMM = "09:20"     # ~5 min after 09:15 open
EOD_HHMM = "15:15"


def short_costs(sell_prem, buy_prem):
    qty = LOT
    brok = BROKERAGE_PER_ORDER * 2
    turnover = (sell_prem + buy_prem) * qty
    exch = EXCH_TXN_PCT * turnover
    stt = STT_SELL_PCT * (sell_prem * qty)
    gst = GST_PCT * (brok + exch)
    sebi = SEBI_PER_CRORE * turnover / 1e7
    stamp = STAMP_BUY_PCT * (buy_prem * qty)
    return brok + exch + stt + gst + sebi + stamp


def daily_prevclose(spot):
    """Day open = REGULAR SESSION open (first bar at/after 09:15), not pre-open-auction
    prints (present in 2026 data from 09:00, which converge near prev close by design and
    corrupt gap detection if used as 'open')."""
    reg = spot[spot.index.time >= dt.time(9, 15)]
    g = reg.groupby(reg.index.date)
    d = pd.DataFrame({"open": g["open"].first(), "close": g["close"].last()})
    d.index = [pd.Timestamp(x) for x in d.index]
    d["prev_close"] = d["close"].shift(1)
    d["gap"] = d["open"] / d["prev_close"] - 1
    return d


def _t(day, hhmm):
    return pd.Timestamp(day) + pd.Timedelta(hours=int(hhmm[:2]), minutes=int(hhmm[3:]))


@dataclass
class Cfg:
    gap_min: float
    sl_pct: float
    otm_pct: float       # 0.0 = ATM


def run(cfg: Cfg, start, end):
    spot = chain.load_index()
    dgap = daily_prevclose(spot)
    days = sorted({d for d in spot.index.date if start <= d <= end})
    rows = []
    for day in days:
        ts = pd.Timestamp(day)
        if ts not in dgap.index or not np.isfinite(dgap.loc[ts, "gap"]):
            continue
        gap = dgap.loc[ts, "gap"]
        if abs(gap) < cfg.gap_min:
            continue
        direction = "CE" if gap > 0 else "PE"   # gap up -> sell CE; gap down -> sell PE
        sd = spot[spot.index.date == day]
        et = _t(day, ENTRY_HHMM)
        se = sd[sd.index <= et]
        if se.empty:
            continue
        s0 = se["close"].iloc[-1]
        exp = chain.nearest_expiry(day, 0, 7)
        if exp is None:
            continue
        cdf = chain.day_chain(exp, day)
        if cdf.empty:
            continue
        avail = sorted(cdf["strike"].unique())
        if not avail:
            continue
        if cfg.otm_pct == 0.0:
            target = s0
        elif direction == "CE":
            target = s0 * (1 + cfg.otm_pct)
        else:
            target = s0 * (1 - cfg.otm_pct)
        k = min(avail, key=lambda x: abs(x - round(target / STEP) * STEP))
        leg = cdf[(cdf["strike"] == k) & (cdf["option_type"] == direction)].set_index("t")[
            ["open", "high", "low", "close"]].sort_index()
        le = leg[leg.index >= et]
        if le.empty:
            continue
        entry_px = le.iloc[0]["open"]
        if not (np.isfinite(entry_px) and entry_px > 0):
            continue
        sell_fill = entry_px * (1 - SLIP)
        stop_lvl = entry_px * (1 + cfg.sl_pct)
        eod = _t(day, EOD_HHMM)
        path = le[le.index <= eod]
        hit = path[path["high"] >= stop_lvl]
        if not hit.empty:
            exit_px, reason = stop_lvl, "stop"
        else:
            exit_px, reason = path["close"].iloc[-1], "eod"
        buy_fill = exit_px * (1 + SLIP)
        gross = (sell_fill - buy_fill) * LOT
        costs = short_costs(entry_px, exit_px)
        net = gross - costs
        rows.append({"day": day, "gap": gap, "dir": direction, "strike": k,
                     "entry": entry_px, "exit": exit_px, "reason": reason,
                     "net_pnl": net, "win": net > 0})
    return pd.DataFrame(rows)


def stat(df, cap=3_00_000.0):
    if df.empty or len(df) < 5:
        return dict(n=len(df))
    wr = df["win"].mean(); net = df["net_pnl"].sum()
    w = df[df["net_pnl"] > 0]["net_pnl"]; l = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = w.sum() / abs(l.sum()) if l.sum() != 0 else 99.0
    d2 = df.sort_values("day")
    eq = cap + d2["net_pnl"].cumsum().values
    dd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min()
    r = d2["net_pnl"] / cap
    yrs = max((d2["day"].iloc[-1] - d2["day"].iloc[0]).days / 365.25, 0.1)
    tpy = len(df) / yrs
    sharpe = r.mean() / r.std() * np.sqrt(tpy) if r.std() > 0 else 0
    return dict(n=len(df), wr=wr, pf=pf, net=net, tot=net / cap, maxdd=dd, sharpe=sharpe, tpy=tpy)


if __name__ == "__main__":
    GAPS = [0.003, 0.006, 0.009]
    SLS = [0.10, 0.25, 0.50]
    OTMS = [0.0, 0.0025, 0.005]
    results = []
    for gap, sl, otm in product(GAPS, SLS, OTMS):
        cfg = Cfg(gap_min=gap, sl_pct=sl, otm_pct=otm)
        b = run(cfg, dt.date(2021, 1, 1), dt.date(2025, 12, 31))
        f = run(cfg, dt.date(2026, 1, 1), dt.date(2026, 6, 2))
        sb, sf = stat(b), stat(f)
        results.append({"gap": gap, "sl": sl, "otm": otm,
                        "b_n": sb.get("n", 0), "b_wr": sb.get("wr", np.nan), "b_pf": sb.get("pf", np.nan),
                        "b_sharpe": sb.get("sharpe", np.nan), "b_maxdd": sb.get("maxdd", np.nan),
                        "b_tot": sb.get("tot", np.nan),
                        "f_n": sf.get("n", 0), "f_pf": sf.get("pf", np.nan),
                        "f_sharpe": sf.get("sharpe", np.nan), "f_tot": sf.get("tot", np.nan)})
        print(f"gap={gap:.1%} sl={sl:.0%} otm={otm:.2%}: "
              f"B n={sb.get('n',0):3d} WR={sb.get('wr',0):.0%} PF={sb.get('pf',0):.2f} "
              f"Sharpe={sb.get('sharpe',0):.2f} DD={sb.get('maxdd',0):.0%} tot={sb.get('tot',0):+.0%} | "
              f"F n={sf.get('n',0):3d} PF={sf.get('pf',0):.2f} Sharpe={sf.get('sharpe',0):.2f} tot={sf.get('tot',0):+.0%}")
    RES = pd.DataFrame(results)
    RES.to_csv(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\buying\gap_sell_grid.csv", index=False)
    print("\nTOP 10 by BUILD Sharpe:")
    print(RES.sort_values("b_sharpe", ascending=False).head(10).to_string(index=False))
    print("\nTOP 10 by (build AND forward both positive) sharpe:")
    robust = RES[(RES["b_sharpe"] > 0) & (RES["f_sharpe"] > 0)]
    print(robust.sort_values("f_sharpe", ascending=False).head(10).to_string(index=False))
