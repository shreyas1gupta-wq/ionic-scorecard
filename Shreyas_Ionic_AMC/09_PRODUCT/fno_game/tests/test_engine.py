"""Engine unit tests: costs / margin / wilson / greeks / tick rounding.

Every expected value is HAND-COMPUTED from the ROADMAP section 4 formulas and
cross-checked against the implementation in server/app.py + server/greeks.py.
No server binding, no DB writes (Game state built synthetically; margin_req,
costs, rt, wilson are pure w.r.t. the DB).
ASCII-only (cp1252 console).
"""
import math

import app
import greeks as gk

LOT = app.LOT          # 65 (L7)
TICK = app.TICK        # 0.05


# ---------------------------------------------------------------- costs (4.2)
def _hand_costs(side, px, lots):
    v = px * LOT * lots
    brok = 20.0
    txn = 0.0003503 * v          # NSE 0.03503%
    ipft = 0.000005 * v          # 0.0005%
    sebi = 0.000001 * v          # 0.0001%
    stt = 0.001 * v if side == "S" else 0.0      # 0.1% sell only
    stamp = 0.00003 * v if side == "B" else 0.0  # 0.003% buy only
    gst = 0.18 * (brok + txn + ipft + sebi)
    return brok, txn, ipft, sebi, stt, stamp, gst


def test_costs_buy_components_sum():
    # BUY 1 lot @ 100: v=6500 -> 20 + 2.27695 + 0.0325 + 0.0065 + 0 + 0.195
    #                            + 0.18*22.31595(=4.016871) = 26.527821 -> 26.53
    comps = _hand_costs("B", 100.0, 1)
    assert round(sum(comps), 2) == 26.53
    assert app.costs("B", 100.0, 1) == 26.53


def test_costs_sell_components_sum():
    # SELL 1 lot @ 100: buy stack minus stamp, plus STT 6.50 -> 32.832821 -> 32.83
    comps = _hand_costs("S", 100.0, 1)
    assert round(sum(comps), 2) == 32.83
    assert app.costs("S", 100.0, 1) == 32.83


def test_costs_multi_lot_scaling():
    # 5 lots @ 80 SELL: v = 80*65*5 = 26000
    v = 26000.0
    hand = 20.0 + 0.0003503 * v + 0.000005 * v + 0.000001 * v + 0.001 * v \
        + 0.18 * (20.0 + 0.0003503 * v + 0.000005 * v + 0.000001 * v)
    assert app.costs("S", 80.0, 5) == round(hand, 2)


# ------------------------------------------------------------- margin (4.3)
def _game(spot=25000.0, dte=(2, 9)):
    g = app.Game.__new__(app.Game)      # no __init__: pure runtime state
    g.reset_runtime()
    g.spot = [dict(hm=600, o=spot, h=spot + 10, l=spot - 10, c=spot)]
    g.i = 0
    g.dte = list(dte)
    return g


def test_margin_naked_short_atm():
    # ROADMAP 4.3 worked example: S=25000, ATM short P=160
    # 65 * (160 + max(0.045*25000 - 0, 0.025*25000)) = 65 * (160+1125) = 83525
    g = _game()
    k = (0, 25000, "CE")
    g.positions = {k: dict(dir="S", lots=1)}
    g.marks = {k: 160.0}
    assert g.margin_req() == 83525.0


def test_margin_naked_short_otm():
    # S=25000, short 25200 CE @ 80, OTM=200:
    # 65 * (80 + max(1125-200, 625)) = 65 * (80+925) = 65325
    g = _game()
    k = (0, 25200, "CE")
    g.positions = {k: dict(dir="S", lots=1)}
    g.marks = {k: 80.0}
    assert g.margin_req() == 65325.0


def test_margin_vertical_pairing():
    # short 25000 CE + long 25100 CE (same expiry/type):
    # implemented formula = 65 * max(width, 0.005*S) = 65*max(100,125) = 8125
    g = _game()
    ks, kl = (0, 25000, "CE"), (0, 25100, "CE")
    g.positions = {ks: dict(dir="S", lots=1), kl: dict(dir="L", lots=1)}
    g.marks = {ks: 160.0, kl: 110.0}
    assert g.margin_req() == 8125.0
    # wider spread: long 25300 -> 65*max(300,125) = 19500
    kl2 = (0, 25300, "CE")
    g.positions = {ks: dict(dir="S", lots=1), kl2: dict(dir="L", lots=1)}
    g.marks = {ks: 160.0, kl2: 40.0}
    assert g.margin_req() == 19500.0


def test_margin_straddle_pairing():
    # short 25000 CE @160 + short 25000 PE @150, S=25000:
    # naked CE = 65*(160+1125) = 83525; naked PE = 65*(150+1125) = 82875
    # pair = max(83525, 82875) + 65*min(160,150) = 83525 + 9750 = 93275
    g = _game()
    kc, kp = (0, 25000, "CE"), (0, 25000, "PE")
    g.positions = {kc: dict(dir="S", lots=1), kp: dict(dir="S", lots=1)}
    g.marks = {kc: 160.0, kp: 150.0}
    assert g.margin_req() == 93275.0


def test_margin_expiry_day_multiplier():
    # same straddle with front DTE=0 -> x1.3: round(93275*1.3) = 121258
    g = _game(dte=(0,))
    kc, kp = (0, 25000, "CE"), (0, 25000, "PE")
    g.positions = {kc: dict(dir="S", lots=1), kp: dict(dir="S", lots=1)}
    g.marks = {kc: 160.0, kp: 150.0}
    assert g.margin_req() == round(93275.0 * 1.3, 0)


def test_margin_long_only_is_zero():
    g = _game()
    k = (0, 25000, "CE")
    g.positions = {k: dict(dir="L", lots=3)}
    g.marks = {k: 160.0}
    assert g.margin_req() == 0.0


# ------------------------------------------------------------------- wilson
def test_wilson_5_of_10():
    # known Wilson 95% CI for 5/10: (0.2366, 0.7634)
    lo, hi = app.wilson(5, 10)
    assert abs(lo - 0.2366) < 0.002
    assert abs(hi - 0.7634) < 0.002


def test_wilson_edges():
    assert app.wilson(0, 0) == (0.0, 0.0)
    lo, hi = app.wilson(0, 20)
    assert lo == 0.0 and 0.0 < hi < 0.25
    lo, hi = app.wilson(20, 20)
    assert 0.75 < lo < 1.0 and hi == 1.0


# ------------------------------------------------------------- greeks (4.6)
def test_b76_put_call_parity():
    F, K, T, r, sig = 25000.0, 25100.0, 7 / 365.0, 0.065, 0.20
    c = gk.b76_price(F, K, T, r, sig, "CE")
    p = gk.b76_price(F, K, T, r, sig, "PE")
    assert abs((c - p) - math.exp(-r * T) * (F - K)) < 1e-6


def test_solve_iv_round_trip():
    # price a 20%-IV option, solve back: within 0.5 vol pt
    F, K, T, r = 25000.0, 25200.0, 5 / 365.0, 0.065
    for cp in ("CE", "PE"):
        mark = gk.b76_price(F, K, T, r, 0.20, cp)
        iv = gk.solve_iv(mark, F, K, T, r, cp)
        assert iv is not None
        assert abs(iv - 0.20) < 0.005


def test_atm_call_delta_near_half_discounted():
    F = K = 25000.0
    T, r, sig = 7 / 365.0, 0.065, 0.20
    g = gk.greeks(F, K, T, r, sig, "CE")
    assert abs(g["delta"] - 0.5 * math.exp(-r * T)) < 0.02


def test_solve_below_intrinsic_flags():
    # deep-ITM mark below intrinsic-0.05 -> iv None, |delta| = 1
    F, K, T = 25000.0, 24000.0, 2 / 365.0
    g = gk.solve(900.0, F, K, T, cp="CE")   # intrinsic 1000, mark 900
    assert g["iv"] is None and g["delta"] == 1.0
    g = gk.solve(900.0, F, 26000.0, T, cp="PE")
    assert g["iv"] is None and g["delta"] == -1.0


def test_greeks_signs_sane():
    F, K, T, r, sig = 25000.0, 25000.0, 7 / 365.0, 0.065, 0.20
    for cp, dsign in (("CE", 1), ("PE", -1)):
        g = gk.greeks(F, K, T, r, sig, cp)
        assert g["delta"] * dsign > 0
        assert g["gamma"] > 0
        assert g["vega"] > 0
        assert g["theta"] < 0     # long option decays


# ----------------------------------------------------------- tick rounding
def test_rt_tick_rounding():
    assert app.rt(100.02) == 100.0
    assert app.rt(100.03) == 100.05
    assert app.rt(100.10) == 100.10
    assert app.rt(0.01) == TICK      # floor at one tick
    assert app.rt(0.0) == TICK
    assert app.rt(87.62) == 87.60
    assert app.rt(87.63) == 87.65


def test_half_spread():
    # base: max(1 tick, 0.1% of premium); x2 on expiry day after 15:00
    assert app.half_spread(10.0, False, 600) == 0.05
    assert app.half_spread(200.0, False, 600) == 0.20
    assert app.half_spread(200.0, True, 910) == 0.40
    assert app.half_spread(200.0, True, 890) == 0.20  # expiry but before 15:00
