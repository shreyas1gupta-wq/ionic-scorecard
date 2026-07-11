"""FnO Replay Game server (P1+P2 core). Single-player, server-authoritative clock.
Run: uvicorn app:app --port 8787 (see run_game.ps1). ASCII-only logs (cp1252)."""
import asyncio, csv, io, json, math, random, sqlite3, time
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import data_loader as dl
import greeks as gk

HERE = Path(__file__).parent.parent
DB = HERE / "data" / "fno_game.db"
ELIG = json.loads((HERE / "data" / "eligible_days.json").read_text(encoding="utf-8"))["days"]
LOT = 65
TICK = 0.05
START_CAP = 1_000_000
OPEN_HM, CUTOFF_HM, SQOFF_HM, CLOSE_HM = 555, 920, 925, 929  # 09:15 15:20 15:25 15:29
FAKE_EPOCH = 946857600  # 2000-01-03 00:00 UTC (fake anchor, Monday)
RISK_FREE = 0.065
TAG_VOCAB = {
    "setup": ["ORB", "PDH-PDL", "PWH-PWL", "VWAP-reject", "VWAP-reclaim", "CPR", "trend-follow",
              "reversal", "straddle-vol", "strangle-vol", "expiry-pin", "news-guess", "other"],
    "mistake": ["none", "fomo", "revenge", "oversize", "no-stop", "moved-stop", "early-exit",
                "late-exit", "chased", "averaged-loser", "boredom-trade"],
    "emotion": ["calm", "confident", "anxious", "fomo", "frustrated", "tilted", "bored"],
}


def wilson(w, n, z=1.96):
    """Wilson 95% CI for a binomial proportion. Returns (lo, hi)."""
    if n == 0:
        return 0.0, 0.0
    p = w / n
    d = 1.0 + z * z / n
    ctr = (p + z * z / (2 * n)) / d
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, ctr - hw), min(1.0, ctr + hw)


def costs(side, px, lots):
    v = px * LOT * lots
    brok, txn, ipft, sebi = 20.0, 0.0003503 * v, 0.000005 * v, 0.000001 * v
    stt = 0.001 * v if side == "S" else 0.0
    stamp = 0.00003 * v if side == "B" else 0.0
    gst = 0.18 * (brok + txn + ipft + sebi)
    return round(brok + txn + ipft + sebi + stt + stamp + gst, 2)


def half_spread(px, expiry_day, hm):
    hs = max(TICK, 0.001 * px)
    if expiry_day and hm >= 900:
        hs *= 2
    return hs


def rt(px):  # round to tick
    return max(TICK, round(round(px / TICK) * TICK, 2))


def db():
    c = sqlite3.connect(DB)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def db_init():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS bankroll(id INTEGER PRIMARY KEY, cash REAL, season INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS played(d TEXT PRIMARY KEY);
    CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, real_date TEXT, season INTEGER,
      start_cash REAL, end_cash REAL, net_pnl REAL, n_trades INTEGER, recognized INTEGER, guess TEXT, ended_at TEXT);
    CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, expiry TEXT,
      strike INTEGER, cp TEXT, dir TEXT, lots INTEGER, entry_px REAL, exit_px REAL, entry_hm INTEGER,
      exit_hm INTEGER, gross REAL, chg REAL, net REAL, reason TEXT);
    CREATE TABLE IF NOT EXISTS journal(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER,
      trade_id INTEGER, tag_type TEXT, tag TEXT, note TEXT, created_at TEXT);
    """)
    for col, typ in (("mae", "REAL"), ("mfe", "REAL"), ("hold_min", "INTEGER"),
                     ("risk_rs", "REAL"), ("r_mult", "REAL"), ("dte", "INTEGER")):
        try:
            c.execute(f"ALTER TABLE trades ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass  # column already exists
    if not c.execute("SELECT 1 FROM bankroll").fetchone():
        c.execute("INSERT INTO bankroll(id,cash,season) VALUES(1,?,1)", (START_CAP,))
    c.commit()
    c.close()


class Game:
    def __init__(self):
        self.state = "IDLE"
        self.ws = None
        self.reset_runtime()

    def reset_runtime(self):
        self.day = None; self.spot = []; self.d1 = []; self.levels = {}
        self.chains = []; self.marks = {}; self.mark_hm = {}
        self.i = -1; self.speed = 2.0; self.paused = False; self.pause_reason = ""
        self.positions = {}; self.pending = []; self.fills = []; self.trades = []
        self.next_oid = 1
        self.cash = 0.0; self.start_cash = 0.0; self.vix = None; self.dte = []
        self.warn = ""; self.task = None
        self.eq_hist = []; self.oi = {}; self.iv_cache = {}; self.fwd_cache = {}
        self.trade_ids = []; self.session_id = None

    # ---------- session ----------
    def start(self):
        if self.state == "RUNNING":
            return {"error": "session already running"}
        c = db()
        played = {r[0] for r in c.execute("SELECT d FROM played")}
        cash = c.execute("SELECT cash FROM bankroll WHERE id=1").fetchone()[0]
        c.close()
        pool = [e for e in ELIG if e["date"] not in played]
        if not pool:
            return {"error": "eligible pool exhausted - reset played registry"}
        e = random.choice(pool)
        self.reset_runtime()
        d = date.fromisoformat(e["date"])
        self.day = d
        sp = dl.load_spot_day(d)
        sp = sp[sp["hm"] <= CLOSE_HM]
        self.spot = [dict(hm=int(r.hm), o=r.open, h=r.high, l=r.low, c=r.close) for r in sp.itertuples()]
        lv = dl.day_levels(d)
        d1 = lv["prev_day_bars"]
        self.d1 = [dict(hm=int(r.hm), o=r.open, h=r.high, l=r.low, c=r.close) for r in d1.itertuples()]
        self.levels = {k: lv[k] for k in ("pdh", "pdl", "pwh", "pwl")}
        exps = dl.front_expiries(d, 2)
        self.chains, self.dte = [], []
        for ex in exps:
            try:
                self.chains.append(dl.load_option_day(ex, d))
                self.dte.append((ex - d).days)
            except ValueError:
                pass
        try:
            vx = dl.load_vix_day(d)
            self.vix = {int(r.hm): float(r.vix) for r in vx.itertuples()} if len(vx) else None
        except Exception:
            self.vix = None
        self.cash = self.start_cash = cash
        self.i = -1
        self.state = "RUNNING"
        self.task = asyncio.get_event_loop().create_task(self.loop())
        return self.snapshot()

    def spot_mark(self):
        if not self.spot:
            return 0.0
        return self.spot[self.i]["c"] if self.i >= 0 else self.spot[0]["o"]

    def released(self):
        return self.spot[: self.i + 1]

    # ---------- marks / margin ----------
    def update_marks(self, hm):
        for ci, ch in enumerate(self.chains):
            for key, b in ch["minute_index"].get(hm, {}).items():
                self.marks[(ci,) + key] = b["c"]
                self.mark_hm[(ci,) + key] = hm
                if b.get("oi") is not None:
                    self.oi[(ci,) + key] = b["oi"]

    def track_excursions(self):
        """Per-tick MAE/MFE (rupees, position-level) on every open position."""
        for k, p in self.positions.items():
            m = self.marks.get(k, p["entry_px"])
            sign = 1 if p["dir"] == "L" else -1
            pnl = sign * (m - p["entry_px"]) * LOT * p["lots"]
            p["mae"] = round(min(p.get("mae", 0.0), pnl), 2)
            p["mfe"] = round(max(p.get("mfe", 0.0), pnl), 2)

    def pos_value(self):
        v = 0.0
        for k, p in self.positions.items():
            m = self.marks.get(k, p["entry_px"])
            v += (1 if p["dir"] == "L" else -1) * m * LOT * p["lots"]
        return v

    def equity(self):
        return self.cash + self.pos_value()

    def margin_req(self, positions=None):
        positions = self.positions if positions is None else positions
        if not positions:
            return 0.0
        S = self.spot_mark()
        shorts, longs = [], {}
        for k, p in positions.items():
            if p["dir"] == "S":
                shorts.append((k, p["lots"]))
            else:
                longs[k] = longs.get(k, 0) + p["lots"]
        def naked(k, lots):
            ci, strike, cp = k
            P = self.marks.get(k, 1.0)
            otm = max(0.0, strike - S) if cp == "CE" else max(0.0, S - strike)
            return LOT * lots * (P + max(0.045 * S - otm, 0.025 * S))
        total, un = 0.0, []
        for k, lots in shorts:  # vertical pairing: any long, same expiry+type
            ci, strike, cp = k
            paired = 0
            for lk in list(longs):
                if lk[0] == ci and lk[2] == cp and longs[lk] > 0:
                    n = min(lots - paired, longs[lk])
                    total += LOT * n * max(abs(lk[1] - strike), 0.005 * S)
                    longs[lk] -= n; paired += n
                    if paired == lots: break
            if paired < lots:
                un.append((k, lots - paired))
        ce = sorted([x for x in un if x[0][2] == "CE"], key=lambda x: -naked(*x))
        pe = sorted([x for x in un if x[0][2] == "PE"], key=lambda x: -naked(*x))
        while ce and pe:  # straddle/strangle pairing
            (kc, lc), (kp, lp) = ce.pop(0), pe.pop(0)
            n = min(lc, lp)
            other = min(self.marks.get(kc, 1.0), self.marks.get(kp, 1.0))
            total += max(naked(kc, n), naked(kp, n)) + LOT * n * other
            if lc > n: ce.insert(0, (kc, lc - n))
            if lp > n: pe.insert(0, (kp, lp - n))
        for k, lots in ce + pe:
            total += naked(k, lots)
        if self.dte and self.dte[0] == 0:
            total *= 1.3
        return round(total, 0)

    # ---------- orders ----------
    def place(self, ci, strike, cp, side, lots, tp=None, sl=None, typ="MKT", price=None, trigger=None):
        if self.state != "RUNNING":
            return {"error": "no running session"}
        typ = (typ or "MKT").upper()
        if typ not in ("MKT", "LMT", "SLM"):
            return {"error": "type must be MKT|LMT|SLM"}
        if typ == "LMT":
            if price is None or float(price) <= 0:
                return {"error": "LMT order needs price > 0"}
            price = rt(float(price))
        else:
            price = None
        if typ == "SLM":
            if trigger is None or float(trigger) <= 0:
                return {"error": "SLM order needs trigger > 0"}
            trigger = rt(float(trigger))
        else:
            trigger = None
        hm = self.spot[self.i]["hm"] if self.i >= 0 else OPEN_HM
        if hm >= CUTOFF_HM:
            return {"error": "entries blocked after 15:20"}
        if lots < 1 or lots > 27:
            return {"error": "lots must be 1..27 (freeze qty)"}
        if ci >= len(self.chains):
            return {"error": "expiry not available"}
        key = (ci, int(strike), cp)
        mk = self.marks.get(key)
        if typ == "MKT" and (mk is None or self.mark_hm.get(key, -99) < hm - 10):
            ex = self.positions.get(key)
            closing = ex and ((side == "S") == (ex["dir"] == "L"))
            if not closing:
                return {"error": "strike stale/illiquid - entry blocked"}
        # margin pre-check for new shorts (all order types; re-checked at fill for LMT/SLM)
        if side == "S" and not (key in self.positions and self.positions[key]["dir"] == "L"):
            est_px = price if typ == "LMT" else (trigger if typ == "SLM" else (mk or 1))
            est = LOT * lots * ((est_px or 1) + 0.05 * self.spot_mark())
            if self.margin_req() + est > self.equity():
                return {"error": "insufficient margin"}
        oid = self.next_oid; self.next_oid += 1
        self.pending.append(dict(id=oid, key=key, side=side, lots=lots, tp=tp, sl=sl, type=typ,
                                 price=price, trigger=trigger, placed_hm=hm, wait=0, note=""))
        return {"ok": True, "id": oid}

    def try_fills(self, hm):
        expd = self.dte and self.dte[0] == 0
        done = []
        for o in self.pending:
            ci, strike, cp = o["key"]
            typ = o.get("type", "MKT")
            b = self.chains[ci]["minute_index"].get(hm, {}).get((strike, cp))
            if b is None or b["v"] <= 0:
                if typ == "MKT":  # LMT/SLM rest until filled or cancelled (no 3-min reject)
                    o["wait"] += 1
                    pos = self.positions.get(o["key"])
                    is_exit = pos and ((o["side"] == "S") == (pos["dir"] == "L"))
                    if o["wait"] > 3 and not is_exit:
                        o["reject"] = "no liquidity"
                        done.append(o)
                continue
            prev = self.marks.get(o["key"])
            if prev and abs(b["o"] - prev) / prev > 0.30:
                continue  # freak print skip
            if typ == "LMT":
                L = o["price"]
                if o["side"] == "B":  # open <= L -> open; strict trade-through low < L -> L; touch = no fill
                    if b["o"] <= L:
                        px = rt(b["o"])
                    elif b["l"] < L:
                        px = rt(L)
                    else:
                        continue
                else:                 # sell mirror
                    if b["o"] >= L:
                        px = rt(b["o"])
                    elif b["h"] > L:
                        px = rt(L)
                    else:
                        continue
            elif typ == "SLM":
                trg = o["trigger"]
                hs = half_spread(b["o"], expd, hm)
                if o["side"] == "B":  # triggers on high >= trigger; gap fills at worse of trigger/open
                    if b["h"] < trg:
                        continue
                    px = rt(max(trg, b["o"]) + hs)
                else:                 # triggers on low <= trigger
                    if b["l"] > trg:
                        continue
                    px = rt(max(TICK, min(trg, b["o"]) - hs))
            else:  # MKT
                hs = half_spread(b["o"], expd, hm) + TICK * min(o["wait"], 3)
                px = rt(b["o"] + hs) if o["side"] == "B" else rt(max(TICK, b["o"] - hs))
            # margin re-check at fill time for LMT/SLM shorts that would OPEN
            if typ in ("LMT", "SLM") and o["side"] == "S":
                pos = self.positions.get(o["key"])
                if not (pos and pos["dir"] == "L"):
                    est = LOT * o["lots"] * (px + 0.05 * self.spot_mark())
                    if self.margin_req() + est > self.equity():
                        o["reject"] = "margin failed at trigger"
                        done.append(o)
                        continue
            self.execute(o, px, hm, reason=typ if typ != "MKT" else "MANUAL")
            done.append(o)
        for o in done:
            self.pending.remove(o)
            if "reject" in o:
                verb = "CANCELLED" if o["reject"] == "margin failed at trigger" else "REJECTED"
                self.fills.append(dict(hm=hm, msg=f"{verb} {o['key'][1]}{o['key'][2]}: {o['reject']}"))

    def execute(self, o, px, hm, reason="MANUAL"):
        key, side, lots = o["key"], o["side"], o["lots"]
        chg = costs(side, px, lots)
        v = px * LOT * lots
        self.cash += (v - chg) if side == "S" else -(v + chg)
        pos = self.positions.get(key)
        if pos and ((side == "S") == (pos["dir"] == "L")):  # closing
            n = min(lots, pos["lots"])
            sign = 1 if pos["dir"] == "L" else -1
            gross = round(sign * (px - pos["entry_px"]) * LOT * n, 2)
            chg_tot = round(chg + pos["entry_chg"] * n / pos["lots"], 2)
            risk = pos.get("risk_rs")
            self.trades.append(dict(expiry=str(self.chains[key[0]]["expiry"]), strike=key[1], cp=key[2],
                                    dir=pos["dir"], lots=n, entry_px=pos["entry_px"], exit_px=px,
                                    entry_hm=pos["entry_hm"], exit_hm=hm, gross=gross,
                                    chg=chg_tot, reason=reason,
                                    mae=pos.get("mae", 0.0), mfe=pos.get("mfe", 0.0),
                                    hold_min=hm - pos["entry_hm"], risk_rs=risk,
                                    r_mult=round((gross - chg_tot) / risk, 3) if risk else None,
                                    dte=self.dte[key[0]] if key[0] < len(self.dte) else None))
            pos["lots"] -= n
            if pos["lots"] == 0:
                del self.positions[key]
        else:
            if pos:  # same-direction add: average
                tot = pos["lots"] + lots
                pos["entry_px"] = round((pos["entry_px"] * pos["lots"] + px * lots) / tot, 2)
                pos["entry_chg"] += chg; pos["lots"] = tot
                if o.get("tp") is not None: pos["tp"] = o["tp"]
                if o.get("sl") is not None:
                    pos["sl"] = o["sl"]
                    pos["risk_rs"] = round(abs(pos["entry_px"] - o["sl"]) * LOT * tot, 2)
            else:
                risk = round(abs(px - o["sl"]) * LOT * lots, 2) if o.get("sl") is not None else None
                self.positions[key] = dict(dir="L" if side == "B" else "S", lots=lots, entry_px=px,
                                           entry_hm=hm, entry_chg=chg, tp=o.get("tp"), sl=o.get("sl"),
                                           mae=0.0, mfe=0.0, risk_rs=risk)
        self.fills.append(dict(hm=hm, msg=f"{side} {lots}x {key[1]}{key[2]} @ {px} ({reason})"))

    def check_brackets(self, hm):
        expd = self.dte and self.dte[0] == 0
        for key, p in list(self.positions.items()):
            ci, strike, cp = key
            b = self.chains[ci]["minute_index"].get(hm, {}).get((strike, cp))
            if b is None or b["v"] <= 0:
                continue
            side = "S" if p["dir"] == "L" else "B"
            hs = half_spread(b["o"], expd, hm)
            hit = None
            if p["tp"] is not None:
                if (p["dir"] == "L" and b["h"] > p["tp"]) or (p["dir"] == "S" and b["l"] < p["tp"]):
                    px = max(b["o"], p["tp"]) if p["dir"] == "L" else min(b["o"], p["tp"])
                    hit = (rt(px), "TP")
            if hit is None and p["sl"] is not None:
                if (p["dir"] == "L" and b["l"] <= p["sl"]) or (p["dir"] == "S" and b["h"] >= p["sl"]):
                    px = min(b["o"], p["sl"]) - hs if p["dir"] == "L" else max(b["o"], p["sl"]) + hs
                    hit = (rt(max(TICK, px)), "SL")
            if hit:
                self.execute(dict(key=key, side=side, lots=p["lots"]), hit[0], hm, reason=hit[1])

    def flatten(self, hm, reason):
        for key, p in list(self.positions.items()):
            side = "S" if p["dir"] == "L" else "B"
            self.pending = [o for o in self.pending if o["key"] != key]
            b = None
            for back in range(0, 4):
                b = self.chains[key[0]]["minute_index"].get(hm - back, {}).get((key[1], key[2]))
                if b and b["v"] > 0:
                    break
            px = rt(max(TICK, (b["c"] if b else self.marks.get(key, TICK)) - 2 * TICK * (1 if side == "S" else -1)))
            self.execute(dict(key=key, side=side, lots=p["lots"]), px, hm, reason=reason)

    def settle_expiry(self, hm):
        tail = [b["c"] for b in self.spot if 900 <= b["hm"] <= 929]
        sset = sum(tail) / len(tail)
        for key, p in list(self.positions.items()):
            if key[0] != 0:
                continue
            ci, strike, cp = key
            intr = max(0.0, sset - strike) if cp == "CE" else max(0.0, strike - sset)
            v = intr * LOT * p["lots"]
            if p["dir"] == "L":
                stt = round(0.00125 * v, 2)
                self.cash += v - stt
                exit_px, chg = intr, stt
            else:
                self.cash -= v
                exit_px, chg = intr, 0.0
            sign = 1 if p["dir"] == "L" else -1
            gross = round(sign * (exit_px - p["entry_px"]) * LOT * p["lots"], 2)
            chg_tot = round(chg + p["entry_chg"], 2)
            risk = p.get("risk_rs")
            self.trades.append(dict(expiry=str(self.chains[0]["expiry"]), strike=strike, cp=cp, dir=p["dir"],
                                    lots=p["lots"], entry_px=p["entry_px"], exit_px=round(exit_px, 2),
                                    entry_hm=p["entry_hm"], exit_hm=hm, chg=chg_tot,
                                    gross=gross, reason="EXPIRY_SETTLE",
                                    mae=p.get("mae", 0.0), mfe=p.get("mfe", 0.0),
                                    hold_min=hm - p["entry_hm"], risk_rs=risk,
                                    r_mult=round((gross - chg_tot) / risk, 3) if risk else None,
                                    dte=self.dte[0] if self.dte else None))
            del self.positions[key]

    # ---------- tick loop ----------
    @staticmethod
    def _log_exc(where, e):
        """ASCII-safe one-line engine log (cp1252 console must never kill the loop)."""
        try:
            msg = str(e).encode("ascii", "replace").decode()
            print(f"[engine] {where}: {type(e).__name__}: {msg}")
        except Exception:
            pass

    async def loop(self):
        while self.state == "RUNNING":
            try:
                if self.paused:
                    await asyncio.sleep(0.2); continue
                await asyncio.sleep(self.speed)
                if self.paused or self.state != "RUNNING":
                    continue
                self.step()
            except asyncio.CancelledError:
                return
            except Exception as e:  # never let one bad bar kill the session (loop continues)
                self._log_exc("loop error - bar skipped", e)
                self.warn = f"engine error - bar skipped: {type(e).__name__}"

    def cancel_pending(self, hm, opening_only, note):
        """Cancel resting orders. opening_only=True keeps orders that reduce/exit a position."""
        keep = []
        for o in self.pending:
            pos = self.positions.get(o["key"])
            reducing = bool(pos and ((o["side"] == "S") == (pos["dir"] == "L")))
            if opening_only and reducing:
                keep.append(o)
            else:
                self.fills.append(dict(hm=hm, msg=f"CANCELLED {o['key'][1]}{o['key'][2]}: {note}"))
        self.pending = keep

    def step(self):
        # --- always-safe advance: the clock can NEVER get stuck on a failing bar ---
        if self.i + 1 >= len(self.spot):
            self.end_day(); return
        self.i += 1
        hm = self.spot[self.i]["hm"]
        try:
            # --- guarded engine work: an exception skips this bar's mechanics only ---
            self.update_marks(hm)
            self.track_excursions()
            self.try_fills(hm)
            self.check_brackets(hm)
            if hm >= CUTOFF_HM:   # auto-cancel resting orders that would OPEN/increase; keep exits
                self.cancel_pending(hm, opening_only=True, note="cancelled at cutoff")
            if hm == SQOFF_HM:
                self.cancel_pending(hm, opening_only=False, note="cancelled at squareoff")
                self.flatten(hm, "SQUAREOFF")
            if hm >= CLOSE_HM:
                if self.positions:
                    self.settle_expiry(hm) if (self.dte and self.dte[0] == 0) else self.flatten(hm, "FORCED")
                self.eq_hist.append(dict(hm=hm, eq=round(self.equity(), 2)))
                self.end_day(); return
            self.eq_hist.append(dict(hm=hm, eq=round(self.equity(), 2)))
            mr = self.margin_req()
            eq = self.equity()
            self.warn = "MARGIN >100% - new orders blocked" if mr > eq else ""
        except Exception as e:
            self._log_exc(f"engine error - bar skipped (i={self.i})", e)
            self.warn = f"engine error - bar skipped: {type(e).__name__}"
        if self.ws:
            try:
                asyncio.get_event_loop().create_task(self.push())
            except Exception as e:
                self._log_exc("push scheduling error", e)

    def end_day(self):
        self.state = "ENDED"
        net = round(self.cash - self.start_cash, 2)
        c = db()
        c.execute("INSERT INTO played(d) VALUES(?)", (self.day.isoformat(),))
        season = c.execute("SELECT season FROM bankroll WHERE id=1").fetchone()[0]
        c.execute("UPDATE bankroll SET cash=? WHERE id=1", (self.cash,))
        c.execute("INSERT INTO sessions(real_date,season,start_cash,end_cash,net_pnl,n_trades,ended_at) VALUES(?,?,?,?,?,?,datetime('now'))",
                  (self.day.isoformat(), season, self.start_cash, self.cash, net, len(self.trades)))
        sid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.trade_ids = []
        for t in self.trades:
            c.execute("INSERT INTO trades(session_id,expiry,strike,cp,dir,lots,entry_px,exit_px,entry_hm,exit_hm,gross,chg,net,reason,mae,mfe,hold_min,risk_rs,r_mult,dte) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (sid, t["expiry"], t["strike"], t["cp"], t["dir"], t["lots"], t["entry_px"], t["exit_px"],
                       t["entry_hm"], t["exit_hm"], t["gross"], t["chg"], round(t["gross"] - t["chg"], 2), t["reason"],
                       t.get("mae"), t.get("mfe"), t.get("hold_min"), t.get("risk_rs"), t.get("r_mult"), t.get("dte")))
            self.trade_ids.append(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.commit(); c.close()
        self.session_id = sid
        if self.ws:
            asyncio.get_event_loop().create_task(self.push())

    # ---------- payloads (BLINDED: no dates; HH:MM only) ----------
    @staticmethod
    def hm_str(hm):
        return f"{hm // 60:02d}:{hm % 60:02d}"

    def bar_out(self, b, day_offset=0):
        t = FAKE_EPOCH + day_offset * 86400 + (b["hm"] - 555) * 60 + 33300
        return dict(time=t, open=b["o"], high=b["h"], low=b["l"], close=b["c"])

    def vix_band(self):
        """Banded + intraday %chg only (blinding: exact VIX + spot pins the day)."""
        if not self.vix or self.i < 0:
            return "n/a"
        hm = self.spot[self.i]["hm"]
        v = None
        for back in range(0, 15):
            v = self.vix.get(hm - back)
            if v is not None:
                break
        if v is None:
            return "n/a"
        band = "<13" if v < 13 else "13-17" if v < 17 else "17-25" if v < 25 else ">25"
        opn = self.vix.get(min(self.vix))
        return f"{band} {(v / opn - 1) * 100:+.1f}%" if opn else band

    def positions_out(self):
        out = []
        for k, p in self.positions.items():
            m = self.marks.get(k, p["entry_px"])
            sign = 1 if p["dir"] == "L" else -1
            out.append(dict(ci=k[0], strike=k[1], cp=k[2], dir=p["dir"], lots=p["lots"],
                            entry=p["entry_px"], mark=m, tp=p["tp"], sl=p["sl"],
                            pnl=round(sign * (m - p["entry_px"]) * LOT * p["lots"], 2),
                            stale=(self.spot[self.i]["hm"] - self.mark_hm.get(k, 0)) if self.i >= 0 else 0))
        return out

    def open_pnl(self):
        """MTM P&L of open positions vs entry (rupees)."""
        tot = 0.0
        for k, p in self.positions.items():
            m = self.marks.get(k, p["entry_px"])
            tot += (1 if p["dir"] == "L" else -1) * (m - p["entry_px"]) * LOT * p["lots"]
        return round(tot, 2)

    def day_realized(self):
        """Net realized P&L of this session's closed trades (gross - charges)."""
        return round(sum(t["gross"] - t["chg"] for t in self.trades), 2)

    def pending_out(self):
        return [dict(id=o.get("id"), strike=o["key"][1], cp=o["key"][2], side=o["side"],
                     lots=o["lots"], type=o.get("type", "MKT"), price=o.get("price"),
                     trigger=o.get("trigger"), placed_hm=o["placed_hm"], note=o.get("note", ""))
                for o in self.pending]

    def trades_out(self):
        """This session's closed trades, date-free (NO expiry field pre-reveal)."""
        return [dict(strike=t["strike"], cp=t["cp"], dir=t["dir"], lots=t["lots"],
                     entry_px=t["entry_px"], exit_px=t["exit_px"],
                     entry_hm=t["entry_hm"], exit_hm=t["exit_hm"],
                     net=round(t["gross"] - t["chg"], 2), chg=t["chg"], reason=t["reason"])
                for t in self.trades]

    def snapshot(self):
        mr = self.margin_req()
        eq = self.equity()
        return dict(state=self.state, i=self.i, lot=LOT,
                    bars=[self.bar_out(b) for b in self.released()],
                    d1=[self.bar_out(b, -1) for b in self.d1],
                    levels=self.levels, dte=self.dte, speed=self.speed, paused=self.paused,
                    pause_reason=self.pause_reason,
                    clock=self.hm_str(self.spot[self.i]["hm"]) if self.i >= 0 else "09:14",
                    vix=self.vix_band(), cash=round(self.cash, 2), equity=round(eq, 2),
                    margin=mr, free_margin=round(eq - mr, 2),  # raw: negative = margin breach
                    day_realized=self.day_realized(), open_pnl=self.open_pnl(),
                    positions=self.positions_out(), pending=self.pending_out(),
                    trades_today=self.trades_out(),
                    fills=self.fills[-12:], warn=self.warn, n_trades=len(self.trades))

    async def push(self):
        if self.ws:
            try:
                await self.ws.send_text(json.dumps(dict(type="tick", **self.snapshot())))
            except Exception:
                self.ws = None
                self.paused = True  # auto-pause on disconnect
                self.pause_reason = "disconnect"

    # ---------- greeks / IV (cached per (ci, hm) — repeated /api/chain calls are free) ----------
    def opt_T(self, ci, hm):
        """Year fraction to 15:30 on expiry day, floored at 1 minute."""
        mins = (self.chains[ci]["expiry"] - self.day).days * 1440 + (930 - hm)
        return max(mins, 1) / 525600.0

    def forward(self, ci, hm):
        """Parity forward F = K_atm + (C_atm - P_atm) when both ATM marks fresh (<=5 min), else spot."""
        ck = (ci, hm)
        if ck in self.fwd_cache:
            return self.fwd_cache[ck]
        S = self.spot_mark()
        F = S
        strikes = self.chains[ci]["strikes"]
        if strikes:
            atm = min(strikes, key=lambda k: abs(k - S))
            kc, kp = (ci, atm, "CE"), (ci, atm, "PE")
            cm, pm = self.marks.get(kc), self.marks.get(kp)
            if (cm is not None and pm is not None
                    and self.mark_hm.get(kc, -999) >= hm - 5 and self.mark_hm.get(kp, -999) >= hm - 5):
                F = atm + (cm - pm)
        self.fwd_cache[ck] = F
        return F

    def greeks_for(self, ci, strike, cp, hm):
        """Solved IV + greeks for one contract at its current mark; cached per (ci,strike,cp,hm)."""
        key = (ci, strike, cp, hm)
        if key in self.iv_cache:
            return self.iv_cache[key]
        mk = self.marks.get((ci, strike, cp))
        g = gk.solve(mk, self.forward(ci, hm), strike, self.opt_T(ci, hm), RISK_FREE, cp)
        self.iv_cache[key] = g
        return g

    def chain_out(self):
        if self.state not in ("RUNNING",) or self.i < 0:
            return {"rows": []}
        S = self.spot_mark(); hm = self.spot[self.i]["hm"]
        out = []
        for ci, ch in enumerate(self.chains):
            win = [k for k in ch["strikes"] if abs(k - S) <= 200]
            oi_vals = {}
            for cp in ("CE", "PE"):
                oi_vals[cp] = sorted(v for v in (self.oi.get((ci, k, cp)) for k in win) if v is not None)
            rows = []
            for k in win:
                r = dict(strike=k)
                for cp in ("CE", "PE"):
                    key = (ci, k, cp)
                    mk = self.marks.get(key); mh = self.mark_hm.get(key)
                    d = dict(ltp=mk, stale=(hm - mh) if mh else None,
                             iv=None, delta=None, theta=None, vega=None, oi_pct=None)
                    if mk is not None:
                        g = self.greeks_for(ci, k, cp, hm)
                        d["iv"] = round(g["iv"] * 100, 1) if g["iv"] is not None else None
                        d["delta"], d["theta"], d["vega"] = g["delta"], g["theta"], g["vega"]
                    v, vals = self.oi.get(key), oi_vals[cp]
                    if v is not None and vals:  # BLINDED: percentile only, never raw OI
                        if len(vals) == 1:
                            d["oi_pct"] = 50
                        else:
                            d["oi_pct"] = max(0, min(100, int(round(
                                100 * sum(1 for x in vals if x < v) / (len(vals) - 1)))))
                    r[cp.lower()] = d
                rows.append(r)
            out.append(dict(dte=self.dte[ci], rows=rows))
        return dict(spot=S, chains=out)

    # ---------- previews / baskets / payoff ----------
    @staticmethod
    def _sim_apply(sim, key, side, lots, px):
        """Apply a hypothetical fill to a COPY of the position book (mirrors execute())."""
        p = sim.get(key)
        if p and ((side == "S") == (p["dir"] == "L")):  # closing
            n = min(lots, p["lots"])
            p["lots"] -= n
            if p["lots"] == 0:
                sim.pop(key)
        elif p:  # same-direction add
            p["lots"] += lots
        else:
            sim[key] = dict(dir="L" if side == "B" else "S", lots=lots, entry_px=px)
        return sim

    def margin_preview(self, ci, strike, cp, side, lots):
        if self.state != "RUNNING" or self.i < 0:
            return {"error": "no running session"}
        if ci >= len(self.chains):
            return {"error": "expiry not available"}
        hm = self.spot[self.i]["hm"]
        key = (ci, int(strike), cp)
        mk = self.marks.get(key)
        ex = self.positions.get(key)
        closing = bool(ex and ((side == "S") == (ex["dir"] == "L")))
        if (mk is None or self.mark_hm.get(key, -999) < hm - 10) and not closing:
            return {"ok": False, "error": "stale strike"}
        px = mk if mk is not None else (ex["entry_px"] if ex else TICK)
        sim = {k: dict(p) for k, p in self.positions.items()}
        self._sim_apply(sim, key, side, lots, px)
        premium = round(px * LOT * lots, 2)
        margin_after = self.margin_req(sim)
        free_cash = round(self.equity() - margin_after - (premium if side == "B" else 0.0), 2)
        return dict(ok=True, margin_now=self.margin_req(), margin_after=margin_after,
                    free_cash=free_cash, premium=premium)

    def basket(self, ci, kind, side, lots, width):
        if self.state != "RUNNING" or self.i < 0:
            return {"error": "no running session"}
        if kind not in ("straddle", "strangle"):
            return {"error": "kind must be straddle|strangle"}
        if side not in ("B", "S"):
            return {"error": "side must be B|S"}
        if lots < 1 or lots > 27:
            return {"error": "lots must be 1..27 (freeze qty)"}
        if ci >= len(self.chains):
            return {"error": "expiry not available"}
        hm = self.spot[self.i]["hm"]
        if hm >= CUTOFF_HM:
            return {"error": "entries blocked after 15:20"}
        S = self.spot_mark()
        strikes = self.chains[ci]["strikes"]
        if not strikes:
            return {"error": "no strikes available"}
        if kind == "straddle":
            atm = min(strikes, key=lambda k: abs(k - S))
            legs = [(atm, "CE"), (atm, "PE")]
        else:
            w = float(width or 0)
            if w <= 0:
                return {"error": "strangle needs width > 0"}
            legs = [(min(strikes, key=lambda k: abs(k - (S + w))), "CE"),
                    (min(strikes, key=lambda k: abs(k - (S - w))), "PE")]
        # pre-check COMBINED margin on a copy of the book (atomic intent)
        sim = {k: dict(p) for k, p in self.positions.items()}
        prem = 0.0
        for st, cp in legs:
            key = (ci, st, cp)
            mk = self.marks.get(key)
            ex = self.positions.get(key)
            closing = bool(ex and ((side == "S") == (ex["dir"] == "L")))
            if (mk is None or self.mark_hm.get(key, -999) < hm - 10) and not closing:
                return {"error": f"stale strike {st}{cp} - basket blocked"}
            px = mk if mk is not None else (ex["entry_px"] if ex else TICK)
            prem += px * LOT * lots
            self._sim_apply(sim, key, side, lots, px)
        m_after = self.margin_req(sim)
        if side == "S" and m_after > self.equity():
            return {"error": "insufficient margin for combined legs"}
        if side == "B" and m_after + prem > self.equity():
            return {"error": "insufficient funds for combined premium"}
        for st, cp in legs:  # both pending same tick; fill via normal engine
            oid = self.next_oid; self.next_oid += 1
            self.pending.append(dict(id=oid, key=(ci, st, cp), side=side, lots=lots, tp=None, sl=None,
                                     type="MKT", price=None, trigger=None, placed_hm=hm, wait=0, note=""))
        return dict(ok=True, legs=[dict(strike=st, cp=cp) for st, cp in legs])

    def payoff(self, ci=None, strike=None, cp=None, side=None, lots=None):
        legs = []
        if self.state == "RUNNING" and self.i >= 0:
            hm = self.spot[self.i]["hm"]
            for k, p in self.positions.items():
                g = self.greeks_for(k[0], k[1], k[2], hm)
                legs.append(dict(K=k[1], cp=k[2], sign=1 if p["dir"] == "L" else -1, lots=p["lots"],
                                 entry=p["entry_px"], T=self.opt_T(k[0], hm),
                                 iv=g["iv"] if g["iv"] else 0.20))
            if (ci is not None and strike is not None and cp in ("CE", "PE")
                    and side in ("B", "S") and lots):
                key = (int(ci), int(strike), cp)
                if key[0] >= len(self.chains):
                    return {"error": "expiry not available"}
                mk = self.marks.get(key)
                if mk is None:
                    return {"error": "no mark for hypothetical leg"}
                g = self.greeks_for(key[0], key[1], cp, hm)
                legs.append(dict(K=key[1], cp=cp, sign=1 if side == "B" else -1, lots=int(lots),
                                 entry=mk, T=self.opt_T(key[0], hm), iv=g["iv"] if g["iv"] else 0.20))
        if not legs:
            return dict(xs=[], expiry=[], t0=[], be=[], max_profit=None, max_loss=None)
        S = self.spot_mark()
        xs = [round(S * (0.97 + 0.06 * i / 60), 2) for i in range(61)]

        def pay_exp(x):
            return sum(l["sign"] * (gk.intrinsic(x, l["K"], l["cp"]) - l["entry"]) * LOT * l["lots"]
                       for l in legs)

        def pay_t0(x):
            return sum(l["sign"] * (gk.b76_price(x, l["K"], l["T"], RISK_FREE, l["iv"], l["cp"]) - l["entry"])
                       * LOT * l["lots"] for l in legs)

        expiry = [round(pay_exp(x), 2) for x in xs]
        t0 = [round(pay_t0(x), 2) for x in xs]
        be = []
        for a in range(60):
            y0, y1 = expiry[a], expiry[a + 1]
            if y0 == 0.0:
                be.append(xs[a])
            elif y0 * y1 < 0:
                be.append(round(xs[a] - y0 * (xs[a + 1] - xs[a]) / (y1 - y0), 2))
        if expiry[-1] == 0.0:
            be.append(xs[-1])
        mp, ml = max(expiry), min(expiry)
        far_hi, far_lo = pay_exp(S * 2), pay_exp(S * 0.5)  # unbounded beyond grid -> null
        max_profit = None if max(far_hi, far_lo) > mp + 1 else round(mp, 2)
        max_loss = None if min(far_hi, far_lo) < ml - 1 else round(ml, 2)
        return dict(xs=xs, expiry=expiry, t0=t0, be=be, max_profit=max_profit, max_loss=max_loss)

    def reveal(self, guess=""):
        if self.state != "ENDED":
            return {"error": "session not ended"}
        recog = 0
        try:
            recog = 1 if abs((date.fromisoformat(guess) - self.day).days) <= 3 else 0
        except Exception:
            pass
        c = db()
        c.execute("UPDATE sessions SET recognized=?, guess=? WHERE id=?", (recog, guess, self.session_id))
        c.commit(); c.close()
        self.state = "REVEALED"
        return dict(real_date=self.day.isoformat(), weekday=self.day.strftime("%A"),
                    expiries=[str(c_["expiry"]) for c_ in self.chains], recognized=recog,
                    full_day=[self.bar_out(b) for b in self.spot],
                    trades=self.trades, net=round(self.cash - self.start_cash, 2),
                    cash=round(self.cash, 2),
                    equity=list(self.eq_hist), session_id=self.session_id)


GAME = Game()
app = FastAPI()
db_init()


@app.post("/api/session/start")
async def s_start():
    return JSONResponse(GAME.start())


@app.post("/api/order")
async def s_order(o: dict):
    return JSONResponse(GAME.place(int(o["ci"]), int(o["strike"]), o["cp"], o["side"], int(o["lots"]),
                                   o.get("tp"), o.get("sl"), o.get("type", "MKT"),
                                   o.get("price"), o.get("trigger")))


@app.post("/api/cancel")
async def s_cancel(o: dict):
    try:
        oid = int(o.get("id"))
    except (TypeError, ValueError):
        return JSONResponse({"error": "not found"})
    for p in list(GAME.pending):
        if p.get("id") == oid:
            GAME.pending.remove(p)
            return JSONResponse({"ok": True})
    return JSONResponse({"error": "not found"})


@app.post("/api/bracket")
async def s_bracket(o: dict):
    key = (int(o["ci"]), int(o["strike"]), o["cp"])
    p = GAME.positions.get(key)
    if not p:
        return JSONResponse({"error": "no such position"})
    p["tp"], p["sl"] = o.get("tp"), o.get("sl")
    return JSONResponse({"ok": True})


@app.post("/api/flatten")
async def s_flatten():
    if GAME.state == "RUNNING" and GAME.i >= 0:
        GAME.flatten(GAME.spot[GAME.i]["hm"], "MANUAL_FLAT")
    return JSONResponse({"ok": True})


@app.post("/api/ctl")
async def s_ctl(o: dict):
    if "speed" in o:
        GAME.speed = min(60.0, max(1.0, float(o["speed"])))
    if "paused" in o:
        GAME.paused = bool(o["paused"])
        GAME.pause_reason = "user" if GAME.paused else ""
    return JSONResponse({"speed": GAME.speed, "paused": GAME.paused,
                         "pause_reason": GAME.pause_reason})


@app.get("/api/chain")
async def s_chain():
    return JSONResponse(GAME.chain_out())


@app.post("/api/reveal")
async def s_reveal(o: dict):
    return JSONResponse(GAME.reveal(o.get("guess", "")))


@app.get("/api/career")
async def s_career():
    c = db()
    cash, season = c.execute("SELECT cash,season FROM bankroll WHERE id=1").fetchone()
    n = c.execute("SELECT COUNT(*), COALESCE(SUM(net_pnl),0) FROM sessions").fetchone()
    c.close()
    return JSONResponse(dict(cash=cash, season=season, sessions=n[0], total_pnl=n[1]))


@app.post("/api/reset")
async def s_reset():
    c = db()
    c.execute("UPDATE bankroll SET cash=?, season=season+1 WHERE id=1", (START_CAP,))
    c.commit(); c.close()
    return JSONResponse({"ok": True, "cash": START_CAP})


@app.post("/api/margin_preview")
async def s_margin_preview(o: dict):
    return JSONResponse(GAME.margin_preview(int(o["ci"]), int(o["strike"]), o["cp"],
                                            o["side"], int(o["lots"])))


@app.post("/api/basket")
async def s_basket(o: dict):
    return JSONResponse(GAME.basket(int(o["ci"]), o.get("kind"), o.get("side"),
                                    int(o.get("lots", 1)), o.get("width")))


@app.post("/api/step")
async def s_step():
    if GAME.state == "RUNNING" and GAME.paused:
        GAME.step()
        i = min(GAME.i, len(GAME.spot) - 1)
        clock = GAME.hm_str(GAME.spot[i]["hm"]) if GAME.spot and i >= 0 else "09:14"
        return JSONResponse({"ok": True, "clock": clock})
    return JSONResponse({"error": "not paused"})


@app.get("/api/payoff")
async def s_payoff(ci: int | None = None, strike: int | None = None, cp: str | None = None,
                   side: str | None = None, lots: int | None = None):
    return JSONResponse(GAME.payoff(ci, strike, cp, side, lots))


@app.get("/api/tags")
async def s_tags():
    return JSONResponse(TAG_VOCAB)


@app.post("/api/journal")
async def s_journal(o: dict):
    if GAME.state != "REVEALED":
        return JSONResponse({"error": "journal only available after reveal"})
    tag_type = o.get("tag_type")
    if tag_type not in TAG_VOCAB:
        return JSONResponse({"error": "unknown tag_type"})
    tag = str(o.get("tag", "")).strip()[:40]
    note = str(o.get("note") or "").strip()[:500]
    trade_id = None
    ti = o.get("trade_idx")
    if ti is not None:
        ti = int(ti)
        if not (0 <= ti < len(GAME.trade_ids)):
            return JSONResponse({"error": "bad trade_idx"})
        trade_id = GAME.trade_ids[ti]
    c = db()
    c.execute("INSERT INTO journal(session_id,trade_id,tag_type,tag,note,created_at) VALUES(?,?,?,?,?,datetime('now'))",
              (GAME.session_id, trade_id, tag_type, tag, note))
    c.commit(); c.close()
    return JSONResponse({"ok": True})


@app.get("/api/analytics")
async def s_analytics(include_recognized: int = 0):
    c = db()
    cond = "" if include_recognized else " AND COALESCE(s.recognized,0)=0"
    sess = c.execute("SELECT s.id,s.season,s.end_cash,s.net_pnl FROM sessions s WHERE 1=1"
                     + cond + " ORDER BY s.id").fetchall()
    tr = c.execute("SELECT t.net,t.chg,t.entry_hm,t.dte,t.reason,t.risk_rs FROM trades t "
                   "JOIN sessions s ON t.session_id=s.id WHERE 1=1" + cond).fetchall()
    tags = c.execute("SELECT j.tag_type||':'||j.tag, COUNT(*), COALESCE(SUM(t.net),0) FROM journal j "
                     "JOIN trades t ON j.trade_id=t.id JOIN sessions s ON t.session_id=s.id "
                     "WHERE j.tag_type IN ('setup','mistake')" + cond + " GROUP BY 1").fetchall()
    c.close()
    nets = [r[0] if r[0] is not None else 0.0 for r in tr]
    n = len(nets)
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x <= 0]
    w = len(wins)
    lo, hi = wilson(w, n)
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    career = dict(sessions=len(sess), trades=n, wins=w,
                  win_rate=round(w / n, 4) if n else 0.0, wr_lo=round(lo, 4), wr_hi=round(hi, 4),
                  avg_win=round(avg_win, 2), avg_loss=round(avg_loss, 2),
                  rr=round(avg_win / abs(avg_loss), 2) if avg_loss else None,
                  expectancy=round(sum(nets) / n, 2) if n else 0.0,
                  total_net=round(sum(nets), 2),
                  total_charges=round(sum(r[1] or 0.0 for r in tr), 2),
                  undefined_r=sum(1 for r in tr if r[5] is None))
    equity_curve = [dict(n=i + 1, cash=r[2]) for i, r in enumerate(sess)]

    def slice_by(keyfn):
        agg = {}
        for r in tr:
            k = keyfn(r)
            a = agg.setdefault(k, [0, 0.0])
            a[0] += 1
            a[1] += r[0] if r[0] is not None else 0.0
        return [dict(k=k, n=a[0], net=round(a[1], 2), low_n=a[0] < 30) for k, a in sorted(agg.items())]

    by_hour = slice_by(lambda r: f"{(r[2] or 0) // 60:02d}")
    by_dte = slice_by(lambda r: "na" if r[3] is None else str(r[3]))
    by_reason = slice_by(lambda r: r[4] or "na")
    by_tag = [dict(k=t[0], n=t[1], net=round(t[2], 2), low_n=t[1] < 30) for t in tags]
    seas = {}
    for r in sess:
        a = seas.setdefault(r[1], [0, 0.0])
        a[0] += 1
        a[1] += r[3] or 0.0
    seasons = [dict(season=k, sessions=a[0], net=round(a[1], 2)) for k, a in sorted(seas.items())]
    return JSONResponse(dict(min_n=30, career=career, equity_curve=equity_curve, by_hour=by_hour,
                             by_dte=by_dte, by_reason=by_reason, by_tag=by_tag, seasons=seasons))


@app.get("/api/export")
async def s_export():
    """CSV of all saved trades. Post-reveal artifact: sessions in DB are completed, real dates allowed.
    BLINDING: the current session's rows are written at ENDED (before reveal) - exclude them until
    the recognition prompt is answered, or the export would leak the hidden date pre-reveal."""
    hide = GAME.session_id if GAME.state == "ENDED" and GAME.session_id is not None else -1
    c = db()
    rows = c.execute(
        "SELECT t.id,t.session_id,s.real_date,s.season,t.expiry,t.strike,t.cp,t.dir,t.lots,"
        "t.entry_px,t.exit_px,t.entry_hm,t.exit_hm,t.gross,t.chg,t.net,t.reason,t.mae,t.mfe,"
        "t.hold_min,t.risk_rs,t.r_mult,t.dte,"
        "(SELECT GROUP_CONCAT(j.tag_type||':'||j.tag,'|') FROM journal j WHERE j.trade_id=t.id) "
        "FROM trades t JOIN sessions s ON t.session_id=s.id WHERE t.session_id != ? ORDER BY t.id",
        (hide,)).fetchall()
    c.close()
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(["trade_id", "session_id", "real_date", "season", "expiry", "strike", "cp", "dir",
                 "lots", "entry_px", "exit_px", "entry_hm", "exit_hm", "gross", "charges", "net",
                 "reason", "mae", "mfe", "hold_min", "risk_rs", "r_mult", "dte", "tags"])
    wr.writerows(rows)
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=fno_trades.csv"})


@app.websocket("/ws")
async def ws_ep(ws: WebSocket):
    await ws.accept()
    old = GAME.ws
    GAME.ws = ws  # replace-not-pause: a new tab/refresh takes over the live feed
    if old is not None and old is not ws:
        try:
            await old.close()
        except Exception:
            pass
    try:
        await ws.send_text(json.dumps(dict(type="sync", **GAME.snapshot())))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        # only pause if THIS socket is still the live one (i.e. no replacement arrived)
        if GAME.ws is ws:
            GAME.ws = None
            if GAME.state == "RUNNING":
                GAME.paused = True
                GAME.pause_reason = "disconnect"


app.mount("/", StaticFiles(directory=str(HERE / "static"), html=True), name="static")
