"""LIQUIDITY SWEEP on 11.34 YEARS of NIFTY 1-min — full stats pack.

Principal ask: monthly heatmap, 1-lot vs 0.1-Kelly sizing, CAGR / Sharpe / MDD, plus
trailing exits to capture 200-300pt runners and an overnight/multi-day variant.

WHY THIS RUN MATTERS: the whole session so far used the 5.03-yr hf file (2021-05..2026-06).
`processed/nifty_1min.parquet` is 11.34 yrs (2015-01-09..2026-05-14, 1,047,541 bars).
=> 2015-01..2021-04 was NEVER touched by any of today's search. It is a PRISTINE out-of-sample
set and it CONTAINS COVID-2020 + 2015-16 correction + 2018 IL&FS. Every drawdown quoted today
came from a sample with no real crisis in it, so those MDDs are optimistic by construction.

Windows:
  IS      2021-05-01 .. 2025-12-31  (the window today's 22-trigger search actually mined)
  OOS_PRE 2015-01-09 .. 2021-04-30  (PRISTINE - never seen; includes COVID)
  FWD     2026-01-01 .. 2026-05-14  (thin, low power)

Sweep definition is copied VERBATIM from
`EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py::sweep_signals`
so results stay directly comparable. PIT-safe: prior-DAY levels only; intraday reference
shifted 2 bars.

Costs (Principal-supplied + era-correct STT):
  futures round trip = brokerage + exch + GST + stamp + SEBI + STT(sell)
  STT 0.0125% before 2024-10-01, 0.020% from 2024-10-01  => ~4.5 / ~6.0 index pts
  + 0.25 pt slippage per side.
Margin: 10% of notional (Principal ruling 22:56), dynamic (scales with spot).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
SRC = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
           r"\NIFTY 500\intraday_options_strategy\datasets\processed\nifty_1min.parquet")

LOT = 75
MARGIN_PCT = 0.10          # Principal 22:56, unhedged delta-1
SLIP_PTS_SIDE = 0.25
CAPITAL = 10_00_000.0
ENTRY_START, ENTRY_END = dt.time(9, 20), dt.time(14, 30)
FLAT_T = dt.time(15, 25)

IS_A, IS_B = dt.date(2021, 5, 1), dt.date(2025, 12, 31)
FWD_A = dt.date(2026, 1, 1)

# ---------------------------------------------------------------- costs
BROK, EXCH, GST, STAMP, SEBI_CR = 20.0, 0.0019 / 100, 0.18, 0.002 / 100, 10.0
STT_OLD, STT_NEW, STT_SWITCH = 0.0125 / 100, 0.020 / 100, dt.date(2024, 10, 1)


def rt_cost(entry_px, exit_px, lots, d: dt.date):
    qty = lots * LOT
    stt_rate = STT_OLD if d < STT_SWITCH else STT_NEW
    turn = (entry_px + exit_px) * qty
    brok = BROK * 2
    exch = EXCH * turn
    stt = stt_rate * exit_px * qty
    gst = GST * (brok + exch)
    stamp = STAMP * entry_px * qty
    sebi = SEBI_CR * turn / 1e7
    return brok + exch + stt + gst + stamp + sebi


# ---------------------------------------------------------------- data
def load_spot() -> pd.DataFrame:
    d = pd.read_parquet(SRC)
    d = d[~d.index.duplicated()].sort_index()
    tod = d.index.time
    d = d[(tod >= dt.time(9, 15)) & (tod <= dt.time(15, 30))]   # pre-open auction landmine
    return d[["open", "high", "low", "close"]]


def to_15min(spot: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for _, day in spot.groupby(spot.index.date):
        r = day.resample("15min", origin=day.index[0], label="right", closed="right").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        parts.append(r)
    return pd.concat(parts).sort_index()


# ------------------------------------------- sweep signals (VERBATIM definition)
def sweep_signals(bars15: pd.DataFrame) -> dict[str, pd.DataFrame]:
    daily_hi = bars15.groupby(bars15.index.date)["high"].max()
    daily_lo = bars15.groupby(bars15.index.date)["low"].min()
    ds = sorted(daily_hi.index)
    prior_hi = {d: daily_hi[ds[i - 1]] for i, d in enumerate(ds) if i > 0}
    prior_lo = {d: daily_lo[ds[i - 1]] for i, d in enumerate(ds) if i > 0}
    out = {"priorday_reclaim": [], "priorday_continue": [],
           "intraday_reclaim": [], "intraday_continue": []}
    for d, day in bars15.groupby(bars15.index.date):
        if d not in prior_hi:
            continue
        ph, pl = prior_hi[d], prior_lo[d]
        hi_so_far = day["high"].cummax().shift(2)
        lo_so_far = day["low"].cummin().shift(2)
        for t, row in day.iterrows():
            hi, lo, close = row["high"], row["low"], row["close"]
            if hi > ph:
                out["priorday_reclaim" if close < ph else "priorday_continue"].append(
                    {"t": t, "dir": -1 if close < ph else 1})
            if lo < pl:
                out["priorday_reclaim" if close > pl else "priorday_continue"].append(
                    {"t": t, "dir": 1 if close > pl else -1})
            ihi, ilo = hi_so_far.loc[t], lo_so_far.loc[t]
            if pd.notna(ihi) and hi > ihi:
                out["intraday_reclaim" if close < ihi else "intraday_continue"].append(
                    {"t": t, "dir": -1 if close < ihi else 1})
            if pd.notna(ilo) and lo < ilo:
                out["intraday_reclaim" if close > ilo else "intraday_continue"].append(
                    {"t": t, "dir": 1 if close > ilo else -1})
    res = {}
    for k, v in out.items():
        df = pd.DataFrame(v)
        if len(df):
            tod = pd.to_datetime(df["t"]).dt.time
            df = df[(tod >= ENTRY_START) & (tod <= ENTRY_END)]
            df = df.drop_duplicates("t").sort_values("t").reset_index(drop=True)
        res[k] = df
    return res


# ---------------------------------------------------------------- trade sim
def simulate(spot: pd.DataFrame, sig: pd.DataFrame, *, stop_pts, trail_pts,
             target_pts, hold_days) -> pd.DataFrame:
    """Delta-1. Entry = next 1-min OPEN after the 15-min signal bar closes.
    trail_pts>0 -> trail from peak once in profit (captures runners).
    hold_days=0 -> flat by 15:25 same day; >0 -> allow overnight up to N sessions."""
    by_day = {d: g for d, g in spot.groupby(spot.index.date)}
    days = sorted(by_day)
    dpos = {d: i for i, d in enumerate(days)}
    rows = []
    for _, r in sig.iterrows():
        t0, sgn = r["t"], int(r["dir"])
        d0 = t0.date()
        if d0 not in dpos:
            continue
        # build the forward path across allowed sessions
        last_i = min(dpos[d0] + hold_days, len(days) - 1)
        path = []
        for i in range(dpos[d0], last_i + 1):
            dd = days[i]
            seg = by_day[dd]
            seg = seg[seg.index > t0] if i == dpos[d0] else seg
            if i == last_i:
                seg = seg[seg.index.time <= FLAT_T]
            path.append(seg)
        path = pd.concat(path) if path else None
        if path is None or path.empty:
            continue
        e = float(path["open"].iloc[0])
        if not np.isfinite(e) or e <= 0:
            continue
        hi = path["high"].to_numpy(); lo = path["low"].to_numpy()
        cl = path["close"].to_numpy(); ts = path.index.to_numpy()
        peak = 0.0
        x, why, xt = float(cl[-1]), "timebox", ts[-1]
        for k in range(len(cl)):
            fav = sgn * (hi[k] - e) if sgn > 0 else sgn * (lo[k] - e)
            adv = sgn * (lo[k] - e) if sgn > 0 else sgn * (hi[k] - e)
            if stop_pts and adv <= -stop_pts:
                x, why, xt = e - sgn * stop_pts, "stop", ts[k]; break
            if target_pts and fav >= target_pts:
                x, why, xt = e + sgn * target_pts, "target", ts[k]; break
            peak = max(peak, fav)
            if trail_pts and peak > trail_pts and (peak - fav) >= trail_pts:
                x, why, xt = e + sgn * (peak - trail_pts), "trail", ts[k]; break
            x, why, xt = float(cl[k]), "timebox", ts[k]
        gross_pts = sgn * (x - e) - 2 * SLIP_PTS_SIDE
        rows.append({"date": d0, "t": t0, "dir": sgn, "entry": e, "exit": x,
                     "why": why, "gross_pts": gross_pts,
                     "hold_min": (pd.Timestamp(xt) - t0).total_seconds() / 60.0,
                     "notional": e * LOT})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- sizing + metrics
def apply_sizing(tr: pd.DataFrame, mode: str, kelly_f: float, stop_pts: float) -> pd.DataFrame:
    """mode='1lot' -> always 1 lot. mode='kelly01' -> 0.1x Kelly fraction of equity,
    risking stop_pts per lot; equity compounds. Margin 10% caps lots."""
    tr = tr.sort_values("t").reset_index(drop=True).copy()
    eq = CAPITAL
    lots_l, eqs, pnl_l, cost_l = [], [], [], []
    for _, r in tr.iterrows():
        margin_per_lot = r["notional"] * MARGIN_PCT
        if mode == "1lot":
            lots = 1
        else:
            risk_rs = 0.1 * kelly_f * eq
            per_lot_risk = max(stop_pts, 1.0) * LOT
            lots = int(max(0, np.floor(risk_rs / per_lot_risk)))
            lots = min(lots, int(np.floor(eq / margin_per_lot)))  # margin cap
        if lots < 1:
            lots_l.append(0); pnl_l.append(0.0); cost_l.append(0.0); eqs.append(eq); continue
        gross = r["gross_pts"] * LOT * lots
        cost = rt_cost(r["entry"], r["exit"], lots, r["date"])
        net = gross - cost
        eq += net
        lots_l.append(lots); pnl_l.append(net); cost_l.append(cost); eqs.append(eq)
        if eq <= 0:
            break
    n = len(lots_l)
    tr = tr.iloc[:n].copy()
    tr["lots"], tr["net"], tr["cost"], tr["equity"] = lots_l, pnl_l, cost_l, eqs
    tr["gross"] = tr["gross_pts"] * LOT * tr["lots"]
    return tr


def nw_t(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 10: return np.nan
    m = x.mean(); d = x - m; n = len(x); var = (d @ d) / n
    for L in range(1, min(lags, n - 1) + 1):
        var += 2 * (1 - L / (lags + 1)) * ((d[L:] @ d[:-L]) / n)
    return m / np.sqrt(var / n) if var > 0 else np.nan


def metrics(tr: pd.DataFrame, label: str) -> dict:
    if tr.empty or len(tr) < 10:
        return {"window": label, "n": int(len(tr))}
    daily = tr.groupby("date")["net"].sum()
    eq = CAPITAL + daily.cumsum()
    peak = eq.cummax()
    mdd = float(((eq - peak) / peak).min())
    yrs = max((max(tr["date"]) - min(tr["date"])).days / 365.25, 0.01)
    endv = float(eq.iloc[-1])
    cagr = (endv / CAPITAL) ** (1 / yrs) - 1 if endv > 0 else float("nan")
    dr = daily / CAPITAL
    sharpe = float(dr.mean() / dr.std() * np.sqrt(252)) if dr.std() > 0 else float("nan")
    w, l = tr[tr.net > 0]["net"], tr[tr.net <= 0]["net"]
    pf = float(w.sum() / abs(l.sum())) if l.sum() != 0 else float("inf")
    m = tr.copy(); m["ym"] = pd.to_datetime(m["date"]).dt.to_period("M")
    mo_net = m.groupby("ym")["net"].sum(); mo_gr = m.groupby("ym")["gross"].sum()
    return {
        "window": label, "n": int(len(tr)), "years": round(yrs, 2),
        "net_rs": round(float(tr.net.sum())), "gross_rs": round(float(tr.gross.sum())),
        "cost_rs": round(float(tr.cost.sum())),
        "cost_pct_of_gross": round(100 * float(tr.cost.sum() / max(tr.gross.sum(), 1)), 1),
        "mean_gross_pts": round(float(tr.gross_pts.mean()), 2),
        "CAGR_pct": round(100 * cagr, 2), "maxDD_pct": round(100 * mdd, 2),
        "Calmar": round(float(cagr / abs(mdd)), 2) if mdd else None,
        "Sharpe": round(sharpe, 2), "PF": round(pf, 2),
        "hit": round(float((tr.net > 0).mean()), 3),
        "t_nw_daily": round(float(nw_t(daily.values)), 2),
        "months": int(len(mo_net)),
        "months_pos_net": int((mo_net > 0).sum()),
        "months_pos_gross": int((mo_gr > 0).sum()),
        "month_win_net": round(float((mo_net > 0).mean()), 3),
        "worst_month_rs": round(float(mo_net.min())), "best_month_rs": round(float(mo_net.max())),
        "max_trade_share": round(float(tr.net.abs().max() / max(abs(tr.net.sum()), 1)), 3),
        "trades_per_month": round(len(tr) / max(len(mo_net), 1), 1),
        "avg_hold_min": round(float(tr.hold_min.mean()), 1),
        "exit_mix": tr["why"].value_counts().to_dict(),
        "max_win_pts": round(float(tr.gross_pts.max()), 1),
        "min_pts": round(float(tr.gross_pts.min()), 1),
        "pts_p95": round(float(tr.gross_pts.quantile(0.95)), 1),
    }


def heatmap(tr: pd.DataFrame, name: str):
    if tr.empty: return None
    m = tr.copy(); m["dtv"] = pd.to_datetime(m["date"])
    m["Y"], m["M"] = m.dtv.dt.year, m.dtv.dt.month
    piv = m.pivot_table(index="Y", columns="M", values="net", aggfunc="sum")
    piv = piv.reindex(columns=range(1, 13))
    piv["YEAR"] = piv.sum(axis=1)
    piv.to_csv(OUT / f"heatmap_{name}.csv")
    return piv


def kelly_from(tr: pd.DataFrame) -> float:
    """Kelly f* = p - q/b on per-trade points (computed on IS only, no lookahead)."""
    x = tr["gross_pts"].to_numpy()
    w, l = x[x > 0], x[x <= 0]
    if len(w) < 10 or len(l) < 10: return 0.0
    p = len(w) / len(x); b = w.mean() / abs(l.mean())
    f = p - (1 - p) / b
    return float(max(0.0, min(f, 1.0)))


CONFIGS = [
    ("A_intraday_stop30",      dict(stop_pts=30, trail_pts=0,  target_pts=0,   hold_days=0)),
    ("B_intraday_trail25",     dict(stop_pts=40, trail_pts=25, target_pts=0,   hold_days=0)),
    ("C_intraday_trail40",     dict(stop_pts=50, trail_pts=40, target_pts=0,   hold_days=0)),
    ("D_overnight1_trail40",   dict(stop_pts=50, trail_pts=40, target_pts=0,   hold_days=1)),
    ("E_swing3_trail60",       dict(stop_pts=60, trail_pts=60, target_pts=0,   hold_days=3)),
    ("F_intraday_tgt200",      dict(stop_pts=40, trail_pts=0,  target_pts=200, hold_days=0)),
]


def main():
    spot = load_spot()
    print(f"[spot] {len(spot):,} bars {spot.index[0]} .. {spot.index[-1]}", flush=True)
    b15 = to_15min(spot)
    print(f"[15min] {len(b15):,} bars", flush=True)
    sw = sweep_signals(b15)
    sig = sw["priorday_reclaim"]
    sig["date"] = pd.to_datetime(sig["t"]).dt.date
    print(f"[signals] priorday_reclaim total={len(sig)}", flush=True)
    for k, v in sw.items():
        print(f"    {k}: {len(v)}", flush=True)

    report = {"data": {"bars": len(spot), "start": str(spot.index[0]), "end": str(spot.index[-1])},
              "margin_pct": MARGIN_PCT, "capital": CAPITAL, "configs": []}

    for name, cfg in CONFIGS:
        tr = simulate(spot, sig, **cfg)
        if tr.empty:
            print(f"  {name}: no trades"); continue
        is_tr = tr[(tr.date >= IS_A) & (tr.date <= IS_B)]
        kf = kelly_from(is_tr) if len(is_tr) > 20 else 0.0
        entry = {"config": name, "params": cfg, "kelly_f_from_IS": round(kf, 3), "sizing": {}}
        for mode in ("1lot", "kelly01"):
            sized = apply_sizing(tr, mode, kf, cfg["stop_pts"])
            wins = {
                "ALL_11yr": sized,
                "IS_2021_2025": sized[(sized.date >= IS_A) & (sized.date <= IS_B)],
                "OOS_PRE_2015_2021": sized[sized.date < IS_A],
                "FWD_2026": sized[sized.date >= FWD_A],
            }
            entry["sizing"][mode] = {k: metrics(v, k) for k, v in wins.items()}
            if mode == "1lot":
                heatmap(sized, f"{name}_1lot")
            else:
                heatmap(sized, f"{name}_kelly01")
            sized.to_csv(OUT / f"trades_{name}_{mode}.csv", index=False)
        report["configs"].append(entry)
        a = entry["sizing"]["1lot"]["ALL_11yr"]; o = entry["sizing"]["1lot"]["OOS_PRE_2015_2021"]
        print(f"  {name:24s} 1lot: n={a.get('n')} CAGR={a.get('CAGR_pct')}% "
              f"MDD={a.get('maxDD_pct')}% Sh={a.get('Sharpe')} PF={a.get('PF')} "
              f"t={a.get('t_nw_daily')} | OOS15-21 PF={o.get('PF')} pts={o.get('mean_gross_pts')}",
              flush=True)

    (OUT / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("\nwrote report.json + heatmaps + trade CSVs", flush=True)


if __name__ == "__main__":
    main()
