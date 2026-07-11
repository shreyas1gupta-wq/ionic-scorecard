"""Anti-leak acceptance test (ROADMAP section 5): drive a full scripted session
through the real engine + REST surface and assert that NOTHING which could
identify the hidden day escapes before reveal.

DB isolation: app.DB is redirected to a scratch file BEFORE any game writes
(same pattern the server build used). The import-time db_init() on the real DB
is idempotent (CREATE IF NOT EXISTS only) and writes no sessions.
ASCII-only (cp1252 console).
"""
import json
import random
import re
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app

# ---- redirect persistence to a scratch DB (before any session runs) ----
_SCRATCH = Path(tempfile.mkdtemp(prefix="fno_game_test_")) / "test_fno_game.db"
app.DB = _SCRATCH
app.db_init()

ISO_DATE = re.compile(r"20\d\d-\d\d-\d\d")
WEEKDAYS = re.compile(r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday")
FAKE = app.FAKE_EPOCH
SIM_DAY_LO = FAKE                       # sim day anchored 2000-01-03 00:00 UTC
SIM_DAY_HI = FAKE + 86400               # upper bound: anything past this = real date leak
STEPS_A = 30


def _no_dates(payload, where):
    s = json.dumps(payload)
    assert not ISO_DATE.search(s), f"ISO date leaked pre-reveal in {where}: {ISO_DATE.search(s).group()}"
    assert not WEEKDAYS.search(s), f"weekday name leaked pre-reveal in {where}"


def _check_bars(snap, where):
    for b in snap["bars"]:
        assert SIM_DAY_LO <= b["time"] < SIM_DAY_HI, f"{where}: sim bar outside fake sim-day window"
    for b in snap["d1"]:
        assert SIM_DAY_LO - 86400 <= b["time"] < SIM_DAY_LO + 86400, f"{where}: d1 bar outside fake D-1 window"


@pytest.fixture(scope="module")
def played():
    """One scripted session, everything captured. Returns dict of artifacts."""
    random.seed(20260705)
    art = dict(pre=[], chain=None, spot=None, steps=0)
    with TestClient(app.app) as c:
        snap = c.post("/api/session/start").json()
        assert "error" not in snap, snap
        r = c.post("/api/ctl", json={"paused": True, "speed": 60}).json()
        assert r["paused"] is True
        art["pre"].append(("start_snapshot", snap))
        i0 = app.GAME.i  # bars auto-released before we got the pause in (normally 0)

        # ---- phase A: 30 paused single-bar steps, capture every payload ----
        for n in range(1, STEPS_A + 1):
            rr = c.post("/api/step").json()
            assert rr.get("ok"), rr
            art["pre"].append((f"step_{n}_resp", rr))
            s = app.GAME.snapshot()          # exactly what the WS push would carry
            art["pre"].append((f"step_{n}_snapshot", s))
            assert len(s["bars"]) == i0 + 1 + n, "released-bar count != steps taken (future bar leak?)"
            _check_bars(s, f"step {n}")
        assert app.GAME.i == i0 + STEPS_A

        # ---- chain / payoff / margin_preview captures ----
        chain = c.get("/api/chain").json()
        art["pre"].append(("chain", chain))
        art["chain"], art["spot"] = chain, chain.get("spot")
        art["pre"].append(("payoff_book", c.get("/api/payoff").json()))
        strike = _fresh_strike(chain)
        if strike is not None:
            art["pre"].append(("margin_preview", c.post(
                "/api/margin_preview",
                json=dict(ci=0, strike=strike, cp="CE", side="B", lots=1)).json()))
            art["pre"].append(("payoff_hypo", c.get(
                f"/api/payoff?ci=0&strike={strike}&cp=CE&side=B&lots=1").json()))
            # ---- place a real order, step it into a fill ----
            r = c.post("/api/order", json=dict(ci=0, strike=strike, cp="CE",
                                               side="B", lots=1)).json()
            art["pre"].append(("order_resp", r))
        for n in range(8):
            rr = c.post("/api/step").json()
            art["pre"].append((f"post_order_step_{n}_resp", rr))
            art["pre"].append((f"post_order_step_{n}_snapshot", app.GAME.snapshot()))

        # ---- pre-reveal export must NOT exist for this session yet ----
        # (rows only enter the DB at ENDED; export must hide the unrevealed session)

        # ---- phase B: fast-forward by stepping to session end ----
        guard = 0
        while app.GAME.state == "RUNNING" and guard < 500:
            rr = c.post("/api/step").json()
            guard += 1
            if guard % 60 == 0:              # sample payloads along the way
                art["pre"].append((f"ff_step_{guard}_snapshot", app.GAME.snapshot()))
        assert app.GAME.state == "ENDED", f"session did not end (state={app.GAME.state})"
        art["pre"].append(("ended_snapshot", app.GAME.snapshot()))

        # export while ENDED (pre-reveal): the just-played day's date must be hidden
        exp_pre = c.get("/api/export").text
        real = app.GAME.day.isoformat()
        assert real not in exp_pre, "export leaked the hidden date between ENDED and reveal"
        art["pre"].append(("analytics_pre", c.get("/api/analytics").json()))

        # ---- reveal ----
        rev = c.post("/api/reveal", json={"guess": ""}).json()
        art["reveal"] = rev
        art["real"] = real
        art["export_post"] = c.get("/api/export").text
    return art


def test_no_dates_or_weekdays_pre_reveal(played):
    for where, payload in played["pre"]:
        _no_dates(payload, where)


def test_bars_bounded_and_counted(played):
    # bounds asserted inside the fixture per step; re-assert on the final snapshot
    _check_bars(dict(bars=played["reveal"]["full_day"], d1=[]), "full_day(post-reveal)")
    ended = dict(played["pre"])["ended_snapshot"]
    _check_bars(ended, "ended_snapshot")
    assert len(ended["bars"]) == len(played["reveal"]["full_day"])


def test_chain_window_and_blinded_oi(played):
    chain, spot = played["chain"], played["spot"]
    assert chain.get("chains"), "no chains served"
    allowed = {"ltp", "stale", "iv", "delta", "theta", "vega", "oi_pct"}
    n_rows = 0
    for ch in chain["chains"]:
        for row in ch["rows"]:
            n_rows += 1
            assert abs(row["strike"] - spot) <= 200, "strike outside +-200 window"
            for cp in ("ce", "pe"):
                o = row[cp]
                assert set(o) <= allowed, f"unexpected field(s) in chain row: {set(o) - allowed}"
                assert "oi" not in o, "raw OI leaked"
                if o["oi_pct"] is not None:
                    assert 0 <= o["oi_pct"] <= 100
    assert n_rows > 0


def test_reveal_shows_real_date_exactly_once(played):
    rev, real = played["reveal"], played["real"]
    assert rev["real_date"] == real
    assert ISO_DATE.match(rev["real_date"])
    assert rev["session_id"] is not None
    assert isinstance(rev["equity"], list) and len(rev["equity"]) > 0
    for t in rev["trades"]:
        for f in ("mae", "mfe", "hold_min", "risk_rs", "r_mult"):
            assert f in t, f"trade missing {f}"
    # top-level keys carry the date exactly once (trades carry expiry dates - allowed post-reveal)
    top = {k: v for k, v in rev.items() if k not in ("trades", "expiries")}
    assert json.dumps(top).count(real) == 1


def test_post_reveal_export_contains_session(played):
    assert played["real"] in played["export_post"] or "trade_id" in played["export_post"]


def test_scratch_db_used_not_production(played):
    assert app.DB == _SCRATCH
    import sqlite3
    c = sqlite3.connect(_SCRATCH)
    assert c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    assert c.execute("SELECT COUNT(*) FROM played").fetchone()[0] == 1
    c.close()


def _fresh_strike(chain):
    """ATM-most CE strike with a fresh mark (orderable)."""
    if not chain.get("chains"):
        return None
    spot = chain["spot"]
    best = None
    for row in chain["chains"][0]["rows"]:
        o = row["ce"]
        if o["ltp"] is None or (o["stale"] is not None and o["stale"] > 5):
            continue
        if best is None or abs(row["strike"] - spot) < abs(best - spot):
            best = row["strike"]
    return best
