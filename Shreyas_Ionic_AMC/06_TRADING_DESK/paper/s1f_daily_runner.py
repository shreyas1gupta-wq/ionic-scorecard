"""S1-F daily paper runner (run ~09:10 IST on any day; safe to run daily).
Prints GO/SKIP + order ticket; appends intent to s1f_paper_log.csv BEFORE action.
DRAFT-OPS v1 (Manoj to harden). Data: Angel SmartAPI (data-only account) + local scrip master."""
import sys, json, math, time, datetime as dt
from pathlib import Path
import pandas as pd

sys.path.insert(0, r"C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture")
from angel_cfg import login

HERE = Path(__file__).resolve().parent
LOG = HERE / "s1f_paper_log.csv"
SCRIP = Path(r"C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture\scrip_master.json")
NIFTY_TOKEN = "99926000"   # NSE NIFTY 50 index
CAPITAL = 1_000_000        # update to current paper equity before each run
MARGIN, LOT = 110_000, 75

today = dt.date.today()
scrip = json.loads(SCRIP.read_bytes())
nifty_opts = [x for x in scrip if x.get("exch_seg") == "NFO" and x.get("name") == "NIFTY"
              and x.get("instrumenttype") == "OPTIDX"]
def ed(s):
    try: return dt.datetime.strptime(s, "%d%b%Y").date()
    except Exception: return None
expiries = sorted({e for e in (ed(x["expiry"]) for x in nifty_opts) if e and e >= today})
if not expiries or expiries[0] != today:
    print(f"SKIP — {today} is not a NIFTY expiry day (next: {expiries[0] if expiries else '?'})")
    sys.exit(0)

obj, _ = login()
# daily candles for vetoes + vol (fromdate at 00:00 — landmine #8)
frm = (today - dt.timedelta(days=400)).strftime("%Y-%m-%d 00:00")
r = obj.getCandleData({"exchange": "NSE", "symboltoken": NIFTY_TOKEN, "interval": "ONE_DAY",
                       "fromdate": frm, "todate": today.strftime("%Y-%m-%d 09:05")})
d = pd.DataFrame(r.get("data") or [], columns=["ts", "o", "h", "l", "c", "v"])
d["date"] = pd.to_datetime(d.ts).dt.date
d = d[d.date < today]                      # D-1 and earlier only
c = d.set_index("date")["c"].astype(float)
# F1 RSI5
delta = c.diff(); up = delta.clip(lower=0).ewm(alpha=1/5, adjust=False).mean()
dn = (-delta.clip(upper=0)).ewm(alpha=1/5, adjust=False).mean()
rsi5 = float((100 - 100 / (1 + up / dn)).iloc[-1])
# F2 prior-day return
pret = float(c.pct_change().iloc[-1] * 100)
# crash rule: daily |ret| 3d avg vs 1y median (daily-bar proxy of the RV3 rule)
absret = c.pct_change().abs()
rv3 = float(absret.rolling(3).mean().iloc[-1]); rvmed = float(absret.rolling(250).median().iloc[-1])
halve = rv3 > 2 * rvmed

veto = None
if rsi5 >= 80 or rsi5 <= 20: veto = f"F1 RSI5={rsi5:.1f}"
if abs(pret) > 1.5: veto = (veto + " & " if veto else "") + f"F2 prior-day {pret:+.2f}%"
lots = int(0.75 * CAPITAL / MARGIN)
if halve: lots = max(lots // 2, 0)

spot_ltp = obj.ltpData("NSE", "Nifty 50", NIFTY_TOKEN)["data"]["ltp"]
atm = round(spot_ltp / 50) * 50
exp_str = today.strftime("%d%b%Y").upper()
toks = {x["symbol"][-2:]: x["token"] for x in nifty_opts
        if x["expiry"] == exp_str and float(x["strike"]) / 100 == atm}

print("=" * 60)
print(f"S1-F PAPER TICKET  {today}  (spot~{spot_ltp:.0f}, ATM {atm})")
print(f"vetoes: RSI5(D-1)={rsi5:.1f}  prior-day={pret:+.2f}%  crash-halve={halve}")
if veto:
    print(f"DECISION: SKIP — {veto}")
    row = dict(date=str(today), decision="SKIP", reason=veto, rsi5=round(rsi5, 1), pret=round(pret, 2))
else:
    print(f"DECISION: GO — at 09:20 SELL {lots}x lots (75/lot):")
    print(f"  SELL NIFTY {exp_str} {atm} CE  (token {toks.get('CE', '?')})  -> SL: exit leg at 1.30x fill")
    print(f"  SELL NIFTY {exp_str} {atm} PE  (token {toks.get('PE', '?')})  -> SL: exit leg at 1.30x fill")
    print(f"  Exit survivors 15:25. Log ACTUAL 09:20 fills into {LOG.name} (cols fill_ce/fill_pe).")
    row = dict(date=str(today), decision="GO", reason="", rsi5=round(rsi5, 1), pret=round(pret, 2),
               lots=lots, halved=halve, atm=atm, tok_ce=toks.get("CE"), tok_pe=toks.get("PE"),
               fill_ce="", fill_pe="", exit_ce="", exit_pe="", notes="intent logged pre-action")
print("=" * 60)
pd.DataFrame([row]).to_csv(LOG, mode="a", header=not LOG.exists(), index=False)
print("intent appended ->", LOG)
