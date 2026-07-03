"""Defined-risk BULL-PUT CREDIT SPREAD engine (1 sell + 1 buy) — short-vol harvest.

Sell an OTM put (K_sell), buy a further-OTM put (K_buy = K_sell - width). Net CREDIT.
Profits if NIFTY stays above K_sell by expiry. Two aligned edges: volatility risk
premium (sell rich vol) + NIFTY upward drift. Max loss = width - credit (capped),
so margin is small -> fits low capital. Real 1-min option fills + retail costs.

Richness filter (from validated Track 1): only enter when ATM straddle >= strad_min%
of spot (vol is rich enough to be worth selling).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

import chain
from engine import BROKERAGE_PER_ORDER, STT_SELL_PCT, EXCH_TXN_PCT, GST_PCT, \
    SEBI_PER_CRORE, STAMP_BUY_PCT, STEP


@dataclass
class CreditCfg:
    target_dte: int = 3            # enter ~this many days before expiry
    min_dte: int = 2
    max_dte: int = 5
    otm_pct: float = 0.010         # sell put ~1% OTM (below spot)
    width_strikes: int = 4         # long put this many strikes below short
    strad_min: float = 0.0045      # richness filter: ATM straddle >= 0.45% of spot
    target_frac: float = 0.55      # take profit at 55% of max credit captured
    stop_mult: float = 2.0         # stop if cost-to-close >= stop_mult * credit
    entry_hhmm: str = "09:20"
    exit_hhmm: str = "15:15"
    slippage_pct: float = 0.01     # per leg (spreads: wider quotes)
    capital: float = 3_00_000.0
    risk_per_trade: float = 0.05   # fraction of capital risked (max loss) per trade
    lot_size: int = 75


def _atm(x):
    return int(round(x / STEP) * STEP)


def _pe(df, strike):
    s = df[(df["strike"] == strike) & (df["option_type"] == "PE")]
    return s.set_index("t")[["open", "high", "low", "close"]].sort_index()


def _ce(df, strike):
    s = df[(df["strike"] == strike) & (df["option_type"] == "CE")]
    return s.set_index("t")[["open", "high", "low", "close"]].sort_index()


def _costs(credit, close_val, lots, lot_size):
    """Round-trip costs: sell+buy at entry, buy+sell at exit (4 orders)."""
    qty = lots * lot_size
    brok = BROKERAGE_PER_ORDER * 4
    turnover = (credit + close_val) * qty * 2  # both legs each side, approx
    exch = EXCH_TXN_PCT * turnover
    stt = STT_SELL_PCT * (credit * qty)        # STT on sell-side premium
    gst = GST_PCT * (brok + exch)
    sebi = SEBI_PER_CRORE * turnover / 1e7
    stamp = STAMP_BUY_PCT * (credit * qty)
    return brok + exch + stt + gst + sebi + stamp


def simulate(spot, exp, cfg: CreditCfg):
    df = chain.load_expiry(exp)
    tdays = sorted(df["trading_day"].unique())
    # entry day ~target_dte sessions before expiry, within [min,max] dte
    entry_day = None
    for td in tdays:
        d = dt.date.fromisoformat(td)
        dte = (exp - d).days
        if cfg.min_dte <= dte <= cfg.max_dte:
            entry_day = d
            if dte <= cfg.target_dte:
                break
    if entry_day is None:
        return None
    et = pd.Timestamp(entry_day) + pd.Timedelta(
        hours=int(cfg.entry_hhmm[:2]), minutes=int(cfg.entry_hhmm[3:]))
    sp = spot[(spot.index.date == entry_day) & (spot.index <= et)]
    if sp.empty:
        return None
    s0 = sp["close"].iloc[-1]
    avail = sorted(df["strike"].unique())
    if not avail:
        return None
    atmk = _atm(s0)

    # richness filter: ATM straddle at entry
    ce_atm = _ce(df, min(avail, key=lambda x: abs(x - atmk)))
    pe_atm = _pe(df, min(avail, key=lambda x: abs(x - atmk)))
    ce_e = ce_atm[ce_atm.index >= et]
    pe_e = pe_atm[pe_atm.index >= et]
    if ce_e.empty or pe_e.empty:
        return None
    straddle = ce_e.iloc[0]["close"] + pe_e.iloc[0]["close"]
    if straddle / s0 < cfg.strad_min:
        return {"skip": True, "exp": exp}

    k_sell = min(avail, key=lambda x: abs(x - s0 * (1 - cfg.otm_pct)))
    k_buy = min(avail, key=lambda x: abs(x - (k_sell - cfg.width_strikes * STEP)))
    if k_buy >= k_sell:
        return None
    width = k_sell - k_buy
    sell_leg = _pe(df, k_sell)
    buy_leg = _pe(df, k_buy)
    sell_leg = sell_leg[sell_leg.index >= et]
    buy_leg = buy_leg[buy_leg.index >= et]
    if sell_leg.empty or buy_leg.empty:
        return None
    sell_e = sell_leg.iloc[0]["open"]
    buy_e = buy_leg.iloc[0]["open"]
    credit = sell_e - buy_e
    if credit <= 0:
        return None
    # entry fill: sell -slip, buy +slip -> received credit reduced
    fill_credit = sell_e * (1 - cfg.slippage_pct) - buy_e * (1 + cfg.slippage_pct)
    if fill_credit <= 0:
        return None

    # spread cost-to-close path = sell_close - buy_close
    idx = sell_leg.index
    net = sell_leg["close"] - buy_leg["close"].reindex(idx).ffill()
    net = net[net.index >= sell_leg.index[0]]
    entry_bar = net.index[0]

    tgt_close = fill_credit * (1 - cfg.target_frac)   # buy back cheap
    stop_close = fill_credit * cfg.stop_mult
    exit_t = exit_val = reason = None
    for t, val in net.items():
        if t <= entry_bar:
            continue
        d_ = t.date()
        eod = pd.Timestamp(d_) + pd.Timedelta(hours=int(cfg.exit_hhmm[:2]),
                                              minutes=int(cfg.exit_hhmm[3:]))
        if d_ >= exp and t >= eod:
            # settle at intrinsic
            exp_spot = spot[spot.index.date == exp]
            s1 = exp_spot["close"].iloc[-1] if not exp_spot.empty else s0
            val = max(0.0, min(width, k_sell - s1))
            exit_t, exit_val, reason = t, val, "expiry"; break
        if val <= tgt_close:
            exit_t, exit_val, reason = t, val, "target"; break
        if val >= stop_close or val >= width:
            exit_t, exit_val, reason = t, min(val, width), "stop"; break
    if exit_t is None:
        exit_t, exit_val, reason = net.index[-1], float(net.iloc[-1]), "eod"

    # exit fill: buy back short +slip, sell long -slip
    fill_exit = exit_val * (1 + cfg.slippage_pct)
    max_loss_per_lot = (width - fill_credit) * cfg.lot_size
    lots = max(1, int((cfg.risk_per_trade * cfg.capital) // max(max_loss_per_lot, 1)))
    qty = lots * cfg.lot_size
    gross = (fill_credit - fill_exit) * qty
    costs = _costs(fill_credit, exit_val, lots, cfg.lot_size)
    net_pnl = gross - costs
    return {
        "enter_day": entry_day, "exp": exp, "dte0": (exp - entry_day).days,
        "k_sell": k_sell, "k_buy": k_buy, "width": width, "credit": fill_credit,
        "exit_val": exit_val, "reason": reason, "entry_t": entry_bar, "exit_t": exit_t,
        "lots": lots, "qty": qty, "gross": gross, "costs": costs, "net_pnl": net_pnl,
        "max_loss_lot": max_loss_per_lot,
        "hold_days": (exit_t.date() - entry_bar.date()).days,
        "ret_on_risk": net_pnl / max(max_loss_per_lot * lots, 1),
    }


def run_range(cfg: CreditCfg, start: dt.date, end: dt.date) -> pd.DataFrame:
    spot = chain.load_index()
    _, exps = chain.build_expiry_index()
    rows = []
    skipped = 0
    for exp in exps:
        if not (start <= exp <= end):
            continue
        try:
            tr = simulate(spot, exp, cfg)
            if tr is None:
                continue
            if tr.get("skip"):
                skipped += 1
                continue
            rows.append(tr)
        except Exception as e:
            print(f"  {exp}: ERR {type(e).__name__}: {e}")
    print(f"  [{start}..{end}] {len(rows)} trades, {skipped} skipped (vol not rich)")
    return pd.DataFrame(rows)


def summarize(df, cfg, label):
    print(f"\n--- {label}: {len(df)} trades ---")
    if df.empty:
        return
    wr = (df["net_pnl"] > 0).mean()
    tot = df["net_pnl"].sum()
    wins = df[df["net_pnl"] > 0]["net_pnl"]
    losses = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else np.inf
    print(f"WR {wr:.1%} | net Rs.{tot:,.0f} | PF {pf:.2f} | "
          f"avg/trade Rs.{df['net_pnl'].mean():,.0f} | on Rs.{cfg.capital:,.0f}: {tot/cfg.capital:+.1%}")
    print(f"avg credit {df['credit'].mean():.1f} | avg maxloss/lot Rs.{df['max_loss_lot'].mean():,.0f} "
          f"| avg hold {df['hold_days'].mean():.1f}d | reasons {df['reason'].value_counts().to_dict()}")


if __name__ == "__main__":
    cfg = CreditCfg()
    b = run_range(cfg, dt.date(2021, 1, 1), dt.date(2025, 12, 31))
    summarize(b, cfg, "BUILD 2021-2025")
    f = run_range(cfg, dt.date(2026, 1, 1), dt.date(2026, 6, 2))
    summarize(f, cfg, "FORWARD 2026 H1")
