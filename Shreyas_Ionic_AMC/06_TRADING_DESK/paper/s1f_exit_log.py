"""Log S1F-001 exit (14JUL2026 0DTE straddle). SL-or-15:25 exit from real 1-min data; mark P&L; close ledger."""
import sys, time, datetime as dt
import pandas as pd
sys.path.insert(0, r"C:\Users\Shreyas.1Gupta\AppData\Local\angel_capture")
from angel_cfg import login
obj, _ = login()
D = "2026-07-14"
LOT, LOTS = 75, 2
QTY = LOT * LOTS
legs = {"CE": {"tok": "51377", "entry": 45.00, "sl": 58.50},
        "PE": {"tok": "51378", "entry": 83.15, "sl": 108.10}}
def fetch(tok):
    for a in range(5):
        try:
            return obj.getCandleData({"exchange": "NFO", "symboltoken": tok, "interval": "ONE_MINUTE",
                                      "fromdate": f"{D} 09:15", "todate": f"{D} 15:30"})
        except Exception:
            time.sleep(4 + 3 * a)
    raise SystemExit("Angel rate-limit persisted; retry later (data account busy).")

for k, v in legs.items():
    r = fetch(v["tok"])
    df = pd.DataFrame(r.get("data") or [], columns=["ts", "o", "h", "l", "c", "v"])
    df["ts"] = pd.to_datetime(df.ts)
    df = df[df.ts.dt.strftime("%H:%M") >= "09:21"]   # monitor ONLY after the 09:20 entry (no pre-entry SL)
    hit = df[df.h >= v["sl"]]
    if len(hit):
        v["exit"], v["when"], v["how"] = v["sl"], str(hit.iloc[0].ts.time())[:5], "SL hit"
    else:
        c25 = df[df.ts.dt.strftime("%H:%M") == "15:25"]
        px = float(c25.iloc[0].c) if len(c25) else float(df.iloc[-1].c)
        v["exit"], v["when"], v["how"] = px, "15:25", "time exit"
    v["pnl"] = (v["entry"] - v["exit"]) * QTY   # short: profit if exit < entry
    print(f"{k}: entry {v['entry']} -> exit {v['exit']} ({v['how']} @ {v['when']})  P&L Rs {v['pnl']:+.0f}")
    time.sleep(1.4)
tot = sum(v["pnl"] for v in legs.values())
print(f"S1F-001 TOTAL realized P&L: Rs {tot:+.0f}  (credit 19,222.5; kept if positive)")

# update paper log
LOG = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\06_TRADING_DESK\paper\s1f_paper_log.csv"
lg = pd.read_csv(LOG, dtype=str)
i = lg.index[lg.date == D][0]
lg.loc[i, "exit_ce"] = f"{legs['CE']['exit']}({legs['CE']['how']})"
lg.loc[i, "exit_pe"] = f"{legs['PE']['exit']}({legs['PE']['how']})"
lg.loc[i, "notes"] = str(lg.loc[i, "notes"]).split(" | EXIT ")[0] + f" | EXIT {D}: CE {legs['CE']['how']}@{legs['CE']['when']} PE {legs['PE']['how']}@{legs['PE']['when']}; realized P&L Rs {tot:+.0f}"
lg.to_csv(LOG, index=False)
open(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\06_TRADING_DESK\paper\S1F001_EXIT.txt", "w").write(
    f"S1F-001 closed {D}. " + " | ".join(f"{k} {v['entry']}->{v['exit']} ({v['how']}) Rs{v['pnl']:+.0f}" for k, v in legs.items()) + f" | TOTAL Rs {tot:+.0f}")
print("logged -> s1f_paper_log.csv + S1F001_EXIT.txt")
