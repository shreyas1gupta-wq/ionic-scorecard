"""WHAT WOULD WE HAVE TRADED TODAY — live 0DTE run on REAL option prices.

Today = NIFTY weekly expiry (Tuesday). Pulls today's real 1-min ATM CE/PE
candles + index from Angel, then runs the LEAD strategy (delta-hedged 0DTE
short straddle) on the real intraday path with real prices, real costs, real
slippage. Prints the trade blotter and P&L breakdown. Creds via env only.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import truststore
truststore.inject_into_ssl()

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (BROKERAGE_PER_ORDER, DIVIDEND_YIELD, GST_PCT, LOT_SIZE,  # noqa: E402
                    NSE_TXN_PCT, RAW_DIR, RESULTS_DIR, RISK_FREE_RATE,
                    SEBI_PER_CRORE, STT_SELL_PCT, TOTAL_CAPITAL)
from options.bs_pricing import bs_greeks, implied_vol  # noqa: E402

MASTER = RAW_DIR / "options" / "angel_nfo_nifty.csv"
OPT_SLIP = 0.02            # 2% per option leg (conservative 0DTE)
FUT_SLIP_PTS = 0.5         # Nifty futures slippage (index pts)
HEDGE_BAND = 0.25
ENTRY_T, EXIT_T = "09:20", "14:30"
TMIN_YEAR = 252 * 375
RISK_BUDGET = 0.006        # 0.6% of capital max-loss → lot count
IV_GATE_PCT  = 0.0045      # skip if straddle < 0.45% of spot (real-fill validated: no edge below)


def login():
    import pyotp
    from SmartApi import SmartConnect
    obj = SmartConnect(api_key=os.environ["ANGEL_API_KEY"])
    s = obj.generateSession(os.environ["ANGEL_CLIENT"], os.environ["ANGEL_PIN"],
                            pyotp.TOTP(os.environ["ANGEL_TOTP_SECRET"]).now())
    if not s.get("status"):
        raise SystemExit(f"login failed: {s}")
    return obj


def candles(obj, token, frm, to, exch="NFO"):
    p = {"exchange": exch, "symboltoken": str(token), "interval": "ONE_MINUTE",
         "fromdate": f"{frm} 09:15", "todate": f"{to} 15:30"}
    d = obj.getCandleData(p).get("data", [])
    df = pd.DataFrame(d, columns=["dt", "o", "h", "l", "c", "v"])
    if len(df):
        df["dt"] = pd.to_datetime(df["dt"]).dt.tz_localize(None)
        df = df.set_index("dt")
    return df


def tte_years(t_now, expiry_close):
    rem = max((expiry_close - t_now).total_seconds() / 60, 1.0)
    return rem / TMIN_YEAR        # intraday on expiry day → pure trading mins


def main():
    obj = login()
    today = (pd.Timestamp(sys.argv[1]).normalize() if len(sys.argv) > 1
             else pd.Timestamp.now().normalize())
    frm = to = today.strftime("%Y-%m-%d")
    m = pd.read_csv(MASTER, parse_dates=["expiry_dt"])
    m = m[m["name"] == "NIFTY"]
    fut = m[m["expiry_dt"] >= today]                 # nearest expiry ON/AFTER target date
    expiry = fut["expiry_dt"].min() if len(fut) else m["expiry_dt"].min()
    print(f"today={today.date()} nearest NIFTY expiry={expiry.date()} "
          f"({'0DTE - EXPIRY DAY' if expiry.normalize()==today else 'NOT expiry today'})")

    nifty = candles(obj, "99926000", frm, to, "NSE")
    vix = candles(obj, "99926017", frm, to, "NSE")
    if not len(nifty):
        raise SystemExit("no index data today (market not open yet / holiday)")
    spot_open = float(nifty["o"].iloc[0])
    atm = round(spot_open / 50) * 50
    leg = {}
    for typ in ("CE", "PE"):
        r = m[(m["expiry_dt"] == expiry) & np.isclose(m["strike"], atm)
              & m["symbol"].str.endswith(typ)]
        if not r.empty:
            leg[typ] = str(r.iloc[0]["token"])
    print(f"spot@open~{spot_open:.0f} ATM={atm} tokens={leg}")
    ce = candles(obj, leg["CE"], frm, to)
    pe = candles(obj, leg["PE"], frm, to)
    print(f"today candles: NIFTY={len(nifty)} CE={len(ce)} PE={len(pe)} "
          f"VIX={len(vix)}")
    if not len(ce) or not len(pe):
        raise SystemExit("no option candles for today yet")

    expiry_close = expiry.normalize() + pd.Timedelta("15:30:00")
    bars = sorted(set(ce.index) & set(pe.index) & set(nifty.index))
    t_entry = today + pd.Timedelta(ENTRY_T + ":00")
    t_exit = today + pd.Timedelta(EXIT_T + ":00")
    walk = [b for b in bars if t_entry <= b <= t_exit]
    if not walk:
        raise SystemExit(f"no bars in {ENTRY_T}-{EXIT_T} yet (market still early?)")

    # ENTRY (sell straddle at real price minus slippage)
    e = walk[0]
    ce0, pe0 = float(ce.loc[e, "c"]), float(pe.loc[e, "c"])
    straddle0 = ce0 + pe0
    strd_pct   = straddle0 / atm
    if strd_pct < IV_GATE_PCT:
        print(f"\nIV GATE: straddle {straddle0:.1f} = {strd_pct:.3%} of ATM {atm} < {IV_GATE_PCT:.2%} threshold.")
        print("Real-fill data shows NO edge when IV is this low — SKIP trading today.")
        raise SystemExit(0)
    print(f"IV check: straddle {straddle0:.1f} = {strd_pct:.3%} of ATM (gate {IV_GATE_PCT:.2%}) — PASS, deploying.")
    entry_fill = straddle0 * (1 - OPT_SLIP)
    # position sizing on Rs.1Cr: max-loss/lot ~ 25% of credit; lots from risk budget
    maxloss_lot = 0.25 * straddle0 * LOT_SIZE
    lots = max(1, int(RISK_BUDGET * TOTAL_CAPITAL / max(maxloss_lot, 1)))
    units = LOT_SIZE * lots

    blotter = [f"{e:%H:%M}  SELL  {lots} lot straddle {atm}CE+{atm}PE  "
               f"CE {ce0:.1f} PE {pe0:.1f}  credit {straddle0:.1f} "
               f"(fill {entry_fill:.1f} after {OPT_SLIP:.0%} slip)"]
    hedge = 0.0; hedge_pnl = 0.0; hedge_cost = 0.0; n_reb = 0
    prev_s = float(nifty.loc[e, "c"])
    for b in walk:
        s = float(nifty.loc[b, "c"])
        hedge_pnl += hedge * (s - prev_s); prev_s = s
        t_yr = tte_years(b, expiry_close)
        iv_c = implied_vol(float(ce.loc[b, "c"]), s, atm, t_yr, RISK_FREE_RATE, DIVIDEND_YIELD, True)
        iv_p = implied_vol(float(pe.loc[b, "c"]), s, atm, t_yr, RISK_FREE_RATE, DIVIDEND_YIELD, False)
        iv = np.nanmean([iv_c, iv_p])
        if np.isnan(iv):
            continue
        dC = float(bs_greeks(s, atm, t_yr, iv, RISK_FREE_RATE, DIVIDEND_YIELD, True)["delta"])
        dP = float(bs_greeks(s, atm, t_yr, iv, RISK_FREE_RATE, DIVIDEND_YIELD, False)["delta"])
        target = dC + dP                          # futures units to hold (per straddle unit)
        if abs(target - hedge) > HEDGE_BAND:
            hedge_cost += abs(target - hedge) * FUT_SLIP_PTS
            n_reb += 1
            side = "BUY" if target > hedge else "SELL"
            blotter.append(f"{b:%H:%M}  HEDGE {side} fut d:{hedge:+.2f}->{target:+.2f} "
                           f"@spot {s:.0f}")
            hedge = target

    x = walk[-1]
    # flatten residual futures hedge at exit (cost + blotter line)
    if abs(hedge) > 1e-9:
        hedge_cost += abs(hedge) * FUT_SLIP_PTS
        n_reb += 1
        blotter.append(f"{x:%H:%M}  HEDGE FLATTEN {'SELL' if hedge > 0 else 'BUY'} fut "
                       f"{hedge:+.2f}->0.00 @spot {prev_s:.0f}  (square off, no overnight)")
        hedge = 0.0
    cex, pex = float(ce.loc[x, "c"]), float(pe.loc[x, "c"])
    straddleX = cex + pex
    exit_fill = straddleX * (1 + OPT_SLIP)
    closed_intraday = x >= t_exit
    blotter.append(f"{x:%H:%M}  BUY-BACK straddle  CE {cex:.1f} PE {pex:.1f}  "
                   f"value {straddleX:.1f} (fill {exit_fill:.1f})"
                   f"{'' if closed_intraday else '  [MTM - market still open]'}")

    # P&L (per lot then scaled)
    straddle_pnl_lot = (entry_fill - exit_fill) * LOT_SIZE
    hedge_pnl_lot = hedge_pnl * LOT_SIZE
    sell_turn = entry_fill * units; buy_turn = exit_fill * units
    opt_cost = (STT_SELL_PCT * sell_turn + NSE_TXN_PCT * (sell_turn + buy_turn) * (1 + GST_PCT)
                + SEBI_PER_CRORE * (sell_turn + buy_turn) / 1e7)
    fixed = BROKERAGE_PER_ORDER * (1 + GST_PCT) * (4 + n_reb) * lots
    hedge_cost_rs = hedge_cost * units
    gross = (straddle_pnl_lot + hedge_pnl_lot) * lots
    net = gross - opt_cost - fixed - hedge_cost_rs

    print("\n=== TODAY'S TRADE BLOTTER (delta-hedged 0DTE short straddle) ===")
    print("\n".join(blotter))
    tot_vol = int(ce["v"].sum() + pe["v"].sum())
    print(f"\nliquidity: ATM CE+PE traded volume today ~{tot_vol:,} (lot {LOT_SIZE}); "
          f"our {lots} lots = {units} qty — {'ample' if tot_vol > units*50 else 'check'}")
    print("\n=== P&L (Rs.1Cr capital, sized to ~0.6% risk budget) ===")
    print(f"lots: {lots}  ({units} qty)   credit collected: Rs.{entry_fill*units:,.0f}")
    print(f"straddle P&L : Rs.{straddle_pnl_lot*lots:>12,.0f}")
    print(f"hedge P&L    : Rs.{hedge_pnl_lot*lots:>12,.0f}  ({n_reb} rebalances)")
    print(f"option costs : Rs.{-opt_cost:>12,.0f}  (STT+NSE+GST+SEBI)")
    print(f"brokerage    : Rs.{-fixed:>12,.0f}")
    print(f"hedge slip   : Rs.{-hedge_cost_rs:>12,.0f}")
    print(f"{'-'*40}\nNET P&L      : Rs.{net:>12,.0f}   ({net/TOTAL_CAPITAL:+.3%} of capital)")
    print(f"{'closed 14:30' if closed_intraday else 'MTM (market still open)'}")

    out = pd.DataFrame({"metric": ["lots", "credit", "straddle_pnl", "hedge_pnl",
                                   "opt_costs", "brokerage", "hedge_slip", "net"],
                        "rs": [lots, entry_fill*units, straddle_pnl_lot*lots,
                               hedge_pnl_lot*lots, -opt_cost, -fixed, -hedge_cost_rs, net]})
    RESULTS_DIR.mkdir(exist_ok=True)
    out.to_csv(RESULTS_DIR / f"today_{today:%Y%m%d}_pnl.csv", index=False)
    pd.DataFrame({"blotter": blotter}).to_csv(RESULTS_DIR / f"today_{today:%Y%m%d}_blotter.csv", index=False)
    print(f"\nsaved -> results\\today_{today:%Y%m%d}_*.csv")


if __name__ == "__main__":
    main()
