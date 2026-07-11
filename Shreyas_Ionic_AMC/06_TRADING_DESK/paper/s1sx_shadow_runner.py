"""S1-SX SHADOW runner (SX1-CARD stage 2, frozen @ 26e1684): SENSEX 0DTE ATM straddle,
ZERO SIZE for 13 Thursday expiries. Exact S1-F rules on SENSEX: 09:20 sell ATM CE+PE
(strike round-100), 30% per-leg SL, 15:25 flat, F1 RSI5 / F2 prior-day vetoes on SENSEX dailies.
Logs intent BEFORE market action to s1sx_shadow_log.csv. Run Thursdays ~09:10 IST.
"""
import csv
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture")
from angel_cfg import login  # noqa: E402

HERE = Path(__file__).resolve().parent
LOG = HERE / "s1sx_shadow_log.csv"
SENSEX_TOKEN, LOT_FALLBACK, STEP = "99919000", 20, 100
today = dt.date.today()

import truststore  # noqa: E402
truststore.inject_into_ssl()
import requests  # noqa: E402
import pandas as pd  # noqa: E402

sm_path = Path(r"C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\scrip_master.json")
sm = json.loads(sm_path.read_text(encoding="utf-8"))
exp_str = today.strftime("%d%b%Y").upper()
sx_opts = [x for x in sm if x.get("exch_seg") == "BFO" and x.get("name") == "SENSEX"
           and x.get("instrumenttype") == "OPTIDX" and x.get("expiry") == exp_str]
if not sx_opts:
    nxt = sorted({x["expiry"] for x in sm if x.get("exch_seg") == "BFO" and x.get("name") == "SENSEX"
                  and x.get("instrumenttype") == "OPTIDX"},
                 key=lambda s: dt.datetime.strptime(s, "%d%b%Y"))
    nxt = [e for e in nxt if dt.datetime.strptime(e, "%d%b%Y").date() >= today]
    print(f"SKIP — {today} is not a SENSEX expiry day (next: {nxt[0] if nxt else '?'})")
    sys.exit(0)

obj, _ = login()
frm = (today - dt.timedelta(days=400)).strftime("%Y-%m-%d 00:00")  # LANDMINE #8: 00:00 fromdate
r = obj.getCandleData({"exchange": "BSE", "symboltoken": SENSEX_TOKEN, "interval": "ONE_DAY",
                       "fromdate": frm, "todate": today.strftime("%Y-%m-%d 09:00")})
c = pd.Series({pd.to_datetime(x[0]).date(): x[4] for x in (r.get("data") or [])}).sort_index()
c = c[c.index < today]
delta = c.diff()
up = delta.clip(lower=0).ewm(alpha=1 / 5, adjust=False).mean()
dn = (-delta.clip(upper=0)).ewm(alpha=1 / 5, adjust=False).mean()
rsi5 = float((100 - 100 / (1 + up / dn)).iloc[-1])
pret = float(c.pct_change().iloc[-1] * 100)
absret = c.pct_change().abs()
halve = float(absret.rolling(3).mean().iloc[-1]) > 2 * float(absret.rolling(250).median().iloc[-1])

veto = None
if rsi5 >= 80 or rsi5 <= 20:
    veto = f"F1 RSI5={rsi5:.1f}"
if abs(pret) > 1.5:
    veto = (veto + " & " if veto else "") + f"F2 prior-day {pret:+.2f}%"

ltp = obj.ltpData("BSE", "SENSEX", SENSEX_TOKEN)["data"]["ltp"]
atm = round(ltp / STEP) * STEP
toks = {x["symbol"][-2:]: (x["token"], int(float(x.get("lotsize", LOT_FALLBACK))))
        for x in sx_opts if float(x["strike"]) / 100 == atm}
lot = next(iter(toks.values()))[1] if toks else LOT_FALLBACK

print("=" * 60)
print(f"S1-SX SHADOW TICKET  {today}  (SENSEX~{ltp:.0f}, ATM {atm}, lot {lot})")
print(f"vetoes: RSI5(D-1)={rsi5:.1f}  prior-day={pret:+.2f}%  crash-halve={halve}")
if veto:
    print(f"DECISION: SKIP — {veto}")
else:
    print(f"DECISION: SHADOW-GO (ZERO SIZE) — at 09:20 note quotes for:")
    for cp, (tok, _l) in toks.items():
        print(f"  SELL SENSEX {exp_str} {atm} {cp}  (token {tok})  SL=1.30x entry, exit 15:25")

new = not LOG.exists()
with open(LOG, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if new:
        w.writerow(["date", "decision", "veto", "atm", "lot", "rsi5", "pret", "halve",
                    "tok_ce", "tok_pe", "entry_ce", "entry_pe", "exit_ce", "exit_pe", "notes"])
    w.writerow([today, "SKIP" if veto else "SHADOW-GO", veto or "", atm, lot,
                f"{rsi5:.1f}", f"{pret:+.2f}", halve,
                toks.get("CE", ("", 0))[0], toks.get("PE", ("", 0))[0], "", "", "", "", ""])
print(f"intent logged -> {LOG.name} (fill entry/exit quotes at 09:20/15:25)")
