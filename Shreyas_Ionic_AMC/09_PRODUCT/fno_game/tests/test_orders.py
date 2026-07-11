"""Order-type engine tests (LMT / SLM per ROADMAP 4.1), tick-loop resilience,
WS replace/pause-reason semantics, /api/cancel, and new snapshot keys.

Synthetic Game state only (no DB writes: no test reaches end_day()).
ASCII-only (cp1252 console).
"""
import asyncio
import datetime as dt
import time

from fastapi.testclient import TestClient

import app

LOT = app.LOT
TICK = app.TICK


def _game(hms=(600, 601, 602, 603, 604), spot=25000.0, dte=(2, 9), cash=1_000_000.0):
    g = app.Game.__new__(app.Game)   # no __init__: pure runtime state, no DB
    g.reset_runtime()
    g.ws = None                      # normally set in __init__
    g.state = "RUNNING"
    g.spot = [dict(hm=h, o=spot, h=spot + 10, l=spot - 10, c=spot) for h in hms]
    g.i = 0
    g.dte = list(dte)
    g.chains = [dict(expiry=dt.date(2000, 1, 5), minute_index={},
                     strikes=[24900, 25000, 25100])]
    g.cash = g.start_cash = cash
    return g


def _bar(o, h, l, c, v=100):
    return dict(o=o, h=h, l=l, c=c, v=v, oi=None)


# ------------------------------------------------------------- LMT fills (4.1)
def test_lmt_buy_touch_no_fill_then_trade_through():
    g = _game()
    r = g.place(0, 25000, "CE", "B", 1, typ="LMT", price=100.0)
    assert r.get("ok") and r["id"] == 1
    mi = g.chains[0]["minute_index"]
    mi[601] = {(25000, "CE"): _bar(105.0, 106.0, 100.0, 104.0)}   # low == limit: TOUCH, no fill
    g.try_fills(601)
    assert g.pending and not g.positions
    mi[602] = {(25000, "CE"): _bar(105.0, 106.0, 99.95, 104.0)}   # low < limit: fill AT limit
    g.try_fills(602)
    assert not g.pending
    p = g.positions[(0, 25000, "CE")]
    assert p["entry_px"] == 100.0        # no slippage on limit fills
    assert p["entry_hm"] == 602


def test_lmt_buy_open_cross_fills_at_open():
    g = _game()
    g.place(0, 25000, "CE", "B", 1, typ="LMT", price=100.0)
    g.chains[0]["minute_index"][601] = {(25000, "CE"): _bar(98.0, 99.0, 97.0, 98.5)}
    g.try_fills(601)                     # open 98 <= 100 -> price improvement, fill at open
    assert g.positions[(0, 25000, "CE")]["entry_px"] == 98.0


def test_lmt_sell_mirror():
    g = _game()
    g.place(0, 25000, "CE", "S", 1, typ="LMT", price=100.0)
    mi = g.chains[0]["minute_index"]
    mi[601] = {(25000, "CE"): _bar(95.0, 100.0, 94.0, 96.0)}      # high == limit: touch, no fill
    g.try_fills(601)
    assert g.pending and not g.positions
    mi[602] = {(25000, "CE"): _bar(95.0, 100.05, 94.0, 96.0)}     # high > limit: fill AT limit
    g.try_fills(602)
    p = g.positions[(0, 25000, "CE")]
    assert p["dir"] == "S" and p["entry_px"] == 100.0
    # open-cross variant fills at open
    g2 = _game()
    g2.place(0, 25000, "CE", "S", 1, typ="LMT", price=100.0)
    g2.chains[0]["minute_index"][601] = {(25000, "CE"): _bar(101.0, 102.0, 100.5, 101.5)}
    g2.try_fills(601)
    assert g2.positions[(0, 25000, "CE")]["entry_px"] == 101.0


def test_lmt_no_fill_on_zero_volume_and_rests_past_3min():
    g = _game()
    g.place(0, 25000, "CE", "B", 1, typ="LMT", price=100.0)
    mi = g.chains[0]["minute_index"]
    mi[601] = {(25000, "CE"): _bar(99.0, 99.5, 98.0, 99.0, v=0)}  # penetrates but ZERO volume
    for hm in (601, 602, 603, 604, 605):                          # no 3-min MKT-style reject
        g.try_fills(hm)
    assert g.pending and not g.positions
    assert not any("REJECTED" in f["msg"] for f in g.fills)


# ------------------------------------------------------------- SLM fills (4.1)
def test_slm_buy_trigger_same_bar():
    g = _game()
    g.place(0, 25000, "CE", "B", 1, typ="SLM", trigger=100.0)
    mi = g.chains[0]["minute_index"]
    mi[601] = {(25000, "CE"): _bar(98.0, 99.9, 97.0, 99.0)}       # high < trigger: no trigger
    g.try_fills(601)
    assert g.pending and not g.positions
    mi[602] = {(25000, "CE"): _bar(98.0, 100.2, 97.0, 100.0)}     # triggered: max(100,98)+hs
    g.try_fills(602)
    hs = app.half_spread(98.0, False, 602)                        # 0.098
    assert g.positions[(0, 25000, "CE")]["entry_px"] == app.rt(100.0 + hs)  # 100.10


def test_slm_buy_gap_fills_at_worse_open():
    g = _game()
    g.place(0, 25000, "CE", "B", 1, typ="SLM", trigger=100.0)
    g.chains[0]["minute_index"][601] = {(25000, "CE"): _bar(104.0, 105.0, 103.0, 104.5)}
    g.try_fills(601)                                              # gap: max(100,104)+hs
    hs = app.half_spread(104.0, False, 601)                       # 0.104
    assert g.positions[(0, 25000, "CE")]["entry_px"] == app.rt(104.0 + hs)  # 104.10


def test_slm_sell_trigger_and_gap():
    g = _game()
    g.place(0, 25000, "CE", "S", 1, typ="SLM", trigger=100.0)
    g.chains[0]["minute_index"][601] = {(25000, "CE"): _bar(96.0, 97.0, 95.0, 96.5)}
    g.try_fills(601)                                              # low<=100: min(100,96)-hs
    hs = app.half_spread(96.0, False, 601)                        # 0.096
    p = g.positions[(0, 25000, "CE")]
    assert p["dir"] == "S" and p["entry_px"] == app.rt(96.0 - hs)  # 95.90


def test_slm_short_margin_recheck_cancels_at_trigger():
    g = _game()
    r = g.place(0, 25000, "CE", "S", 1, typ="SLM", trigger=100.0)  # placement pre-check passes
    assert r.get("ok")
    g.cash = 1000.0                                                # equity collapses before trigger
    g.chains[0]["minute_index"][601] = {(25000, "CE"): _bar(96.0, 97.0, 95.0, 96.5)}
    g.try_fills(601)
    assert not g.pending and not g.positions
    assert any("margin failed at trigger" in f["msg"] for f in g.fills)


# ---------------------------------------------------- cutoff / sqoff handling
def test_cutoff_cancels_opening_keeps_reducing():
    g = _game(hms=(918, 919, 920, 921, 925))
    g.place(0, 25000, "CE", "B", 1, typ="LMT", price=100.0)       # opening -> cancel at cutoff
    g.positions[(0, 25100, "CE")] = dict(dir="L", lots=1, entry_px=50.0, entry_hm=600,
                                         entry_chg=25.0, tp=None, sl=None,
                                         mae=0.0, mfe=0.0, risk_rs=None)
    g.place(0, 25100, "CE", "S", 1, typ="LMT", price=200.0)       # reducing -> kept
    g.step()   # 919
    g.step()   # 920 = CUTOFF
    assert len(g.pending) == 1 and g.pending[0]["key"] == (0, 25100, "CE")
    assert any("cancelled at cutoff" in f["msg"] for f in g.fills)


def test_sqoff_cancels_all_pending_then_flattens():
    g = _game(hms=(921, 922, 925))
    g.positions[(0, 25100, "CE")] = dict(dir="L", lots=1, entry_px=50.0, entry_hm=600,
                                         entry_chg=25.0, tp=None, sl=None,
                                         mae=0.0, mfe=0.0, risk_rs=None)
    g.pending = [dict(id=9, key=(0, 25100, "CE"), side="S", lots=1, tp=None, sl=None,
                      type="LMT", price=999.0, trigger=None, placed_hm=919, wait=0, note="")]
    g.step()   # 922
    g.step()   # 925 = SQOFF: cancel ALL pending (even reducing), then flatten
    assert not g.pending
    assert not g.positions
    assert any("cancelled at squareoff" in f["msg"] for f in g.fills)
    assert any(t["reason"] == "SQUAREOFF" for t in g.trades)


# ------------------------------------------------------- order-type validation
def test_order_type_and_param_validation():
    g = _game()
    assert "error" in g.place(0, 25000, "CE", "B", 1, typ="XXX")
    assert "error" in g.place(0, 25000, "CE", "B", 1, typ="LMT")             # missing price
    assert "error" in g.place(0, 25000, "CE", "B", 1, typ="LMT", price=0)
    assert "error" in g.place(0, 25000, "CE", "B", 1, typ="SLM")             # missing trigger
    assert "error" in g.place(0, 25000, "CE", "B", 1)                        # MKT stale block kept
    r1 = g.place(0, 25000, "CE", "B", 1, typ="LMT", price=100.0)
    r2 = g.place(0, 25000, "CE", "B", 1, typ="SLM", trigger=110.0)
    assert r1["id"] == 1 and r2["id"] == 2                                   # incrementing ids


# --------------------------------------------------------- tick-loop resilience
def test_step_survives_engine_error_and_clock_advances(monkeypatch):
    g = _game()
    calls = {"n": 0}

    def boom(hm):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("synthetic chain corruption")

    monkeypatch.setattr(g, "try_fills", boom)
    i0 = g.i
    g.step()                                  # bar's engine work raises -> caught, bar skipped
    assert g.i == i0 + 1                      # clock ADVANCED past the failing bar
    assert g.state == "RUNNING"
    assert "engine error - bar skipped: RuntimeError" in g.warn
    g.step()                                  # next bar processes normally
    assert g.i == i0 + 2
    assert g.state == "RUNNING"
    assert g.warn == ""                       # healthy tick clears the warning


def test_async_loop_continues_after_step_exception():
    g = _game(hms=tuple(range(600, 640)))
    g.speed = 0.01
    calls = {"n": 0}
    seen = {}

    def step_boom():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("kaboom")
        seen["warn"] = g.warn                 # captured on the ITERATION AFTER the raise
        g.state = "ENDED"                     # stop the loop without touching the DB

    g.step = step_boom
    asyncio.run(g.loop())
    assert calls["n"] == 2                    # loop survived the exception and ticked again
    assert "RuntimeError" in seen["warn"]


# ---------------------------------------------------------- snapshot additions
def test_snapshot_new_keys_arithmetic():
    g = _game()
    k = (0, 25000, "CE")
    g.positions = {k: dict(dir="L", lots=2, entry_px=100.0, entry_hm=600, entry_chg=50.0,
                           tp=None, sl=None, mae=0.0, mfe=0.0, risk_rs=None)}
    g.marks = {k: 110.0}
    g.mark_hm = {k: 600}
    g.trades = [
        dict(expiry="2000-01-05", strike=25000, cp="CE", dir="L", lots=1, entry_px=90.0,
             exit_px=100.0, entry_hm=560, exit_hm=580, gross=650.0, chg=53.0, reason="TP"),
        dict(expiry="2000-01-05", strike=24900, cp="PE", dir="S", lots=1, entry_px=80.0,
             exit_px=85.0, entry_hm=560, exit_hm=590, gross=-325.0, chg=60.0, reason="SL"),
    ]
    g.pending = [dict(id=5, key=(0, 25100, "CE"), side="B", lots=1, tp=None, sl=None,
                      type="LMT", price=42.0, trigger=None, placed_hm=605, wait=0, note="")]
    s = g.snapshot()
    assert s["day_realized"] == round((650.0 - 53.0) + (-325.0 - 60.0), 2)   # 212.0
    assert s["open_pnl"] == round((110.0 - 100.0) * LOT * 2, 2)              # 1300.0
    assert s["margin"] == 0.0                                                # long-only book
    assert s["free_margin"] == round(s["equity"] - s["margin"], 2)
    assert s["pause_reason"] == ""
    assert s["pending"] == [dict(id=5, strike=25100, cp="CE", side="B", lots=1, type="LMT",
                                 price=42.0, trigger=None, placed_hm=605, note="")]
    t0 = s["trades_today"][0]
    assert t0["net"] == 597.0 and t0["chg"] == 53.0 and t0["reason"] == "TP"
    assert "expiry" not in t0                # date-free pre-reveal
    assert len(s["trades_today"]) == 2


def test_free_margin_raw_can_be_negative():
    g = _game(cash=1000.0)
    k = (0, 25000, "CE")
    g.positions = {k: dict(dir="S", lots=1, entry_px=160.0, entry_hm=600, entry_chg=30.0,
                           tp=None, sl=None, mae=0.0, mfe=0.0, risk_rs=None)}
    g.marks = {k: 160.0}
    g.mark_hm = {k: 600}
    s = g.snapshot()
    assert s["margin"] == 83525.0            # ROADMAP 4.3 worked example
    assert s["free_margin"] == round(s["equity"] - 83525.0, 2)
    assert s["free_margin"] < 0              # raw value, NOT floored at zero


# ------------------------------------------------------------------ /api layer
def test_api_cancel_endpoint():
    saved = app.GAME.pending
    app.GAME.pending = [dict(id=77, key=(0, 25000, "CE"), side="B", lots=1, tp=None, sl=None,
                             type="LMT", price=100.0, trigger=None, placed_hm=600, wait=0, note="")]
    try:
        with TestClient(app.app) as c:
            assert c.post("/api/cancel", json={"id": 77}).json() == {"ok": True}
            assert app.GAME.pending == []
            assert c.post("/api/cancel", json={"id": 77}).json() == {"error": "not found"}
            assert c.post("/api/cancel", json={}).json() == {"error": "not found"}
    finally:
        app.GAME.pending = saved


def test_ctl_sets_pause_reason():
    saved = (app.GAME.paused, app.GAME.pause_reason)
    try:
        with TestClient(app.app) as c:
            r = c.post("/api/ctl", json={"paused": True}).json()
            assert r["paused"] is True and r["pause_reason"] == "user"
            r = c.post("/api/ctl", json={"paused": False}).json()
            assert r["paused"] is False and r["pause_reason"] == ""
    finally:
        app.GAME.paused, app.GAME.pause_reason = saved


def test_ws_replace_does_not_pause_but_disconnect_does():
    saved = (app.GAME.state, app.GAME.paused, app.GAME.pause_reason, app.GAME.ws)
    app.GAME.paused = False
    app.GAME.pause_reason = ""
    try:
        with TestClient(app.app) as c:
            with c.websocket_connect("/ws") as w1:
                assert w1.receive_json()["type"] == "sync"
                app.GAME.state = "RUNNING"    # simulate a live session (no tick task needed)
                with c.websocket_connect("/ws") as w2:
                    assert w2.receive_json()["type"] == "sync"
                    # old socket replaced by new tab: game must NOT pause
                    for _ in range(20):
                        if app.GAME.paused:
                            break
                        time.sleep(0.02)
                    assert app.GAME.paused is False
                    assert app.GAME.pause_reason != "disconnect"
                # w2 (the CURRENT socket) closed with no replacement -> pause w/ reason
                for _ in range(100):
                    if app.GAME.pause_reason == "disconnect":
                        break
                    time.sleep(0.02)
                assert app.GAME.paused is True
                assert app.GAME.pause_reason == "disconnect"
    finally:
        app.GAME.state, app.GAME.paused, app.GAME.pause_reason, app.GAME.ws = saved
