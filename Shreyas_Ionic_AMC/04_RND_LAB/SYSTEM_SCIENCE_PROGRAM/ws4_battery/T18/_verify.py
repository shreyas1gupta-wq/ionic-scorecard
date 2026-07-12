# T18 verification: Angel getCandleData ONE_DAY bars are stamped 00:00 IST.
# A fromdate carrying an intraday time ("<entry_date> 09:15") is AFTER the entry
# day's 00:00 stamp, so the API silently omits that day's bar -- no error, the
# response just starts at the NEXT day. The audit then finds no entry-day bar and
# flags every leg UNFILLABLE. That is exactly the observed symptom: 501/501
# UNFILLABLE including deep-liquid ATM weeklies (an impossible real-world result).
# (Firm incident 2026-07-10: same bug made the whole 6-Jul book look unfilled;
# landmine #8. Standing rule: fromdate = <date-1> 00:00 for daily candles.)
# The API itself cannot be called offline; this simulates the documented
# stamp-vs-window mechanics and shows the fix changes the verdict.
import pandas as pd

entry_date = pd.Timestamp("2026-07-06")
# what the exchange really traded (bars stamped 00:00 IST, healthy volume):
bars = pd.DataFrame({
    "ts": pd.date_range("2026-07-06 00:00", periods=5, freq="D"),
    "volume": [184250, 220110, 197004, 254880, 176035],
})

def api_window(fromdate, todate):
    """Angel semantics: return bars whose stamp falls inside [fromdate, todate]."""
    return bars[(bars["ts"] >= fromdate) & (bars["ts"] <= todate)]

# task's request window
task = api_window(pd.Timestamp("2026-07-06 09:15"), pd.Timestamp("2026-07-11 15:30"))
# fixed request window (standing rule)
fixed = api_window(pd.Timestamp("2026-07-05 00:00"), pd.Timestamp("2026-07-11 15:30"))

def has_entry_bar(resp):
    return (resp["ts"].dt.date == entry_date.date()).any()

print("fromdate '2026-07-06 09:15' -> first bar returned:", task["ts"].iloc[0].date(),
      "| entry-day bar present:", has_entry_bar(task))
print("fromdate '2026-07-05 00:00' -> first bar returned:", fixed["ts"].iloc[0].date(),
      "| entry-day bar present:", has_entry_bar(fixed))
assert not has_entry_bar(task) and has_entry_bar(fixed)
print("DEFECT CONFIRMED: the intraday fromdate silently drops the entry-day bar;")
print("the 'UNFILLABLE x501' verdict is an artifact of the request, not of")
print("liquidity. Fix: fromdate = (entry_date - 1 day) at 00:00 for ONE_DAY bars,")
print("and treat 100% UNFILLABLE on liquid ATM legs as a red flag in any audit.")
