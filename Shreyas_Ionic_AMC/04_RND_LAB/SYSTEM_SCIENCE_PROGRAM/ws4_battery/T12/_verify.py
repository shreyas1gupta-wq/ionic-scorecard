# T12 verification: NSE F&O bhavcopy convention -- on the EXPIRY DAY, an option
# row's SETTLE_PR field holds the UNDERLYING's final settlement level (e.g.
# 19,253.80), NOT the option's settlement value. Reading it as the option exit
# price books a "buyback" of each leg at ~the full index level.
# (Firm incident 2026-07-11: -15,428-pt fake losses in study A4; landmine #9.)
# This script reconstructs the arithmetic with rows shaped exactly like the
# bhavcopy convention and shows the booked vs true P&L.
import pandas as pd

# expiry-day rows for an ATM 19250 straddle, index settles at 19,253.80:
rows = pd.DataFrame([
    # OPTION_TYP STRIKE  CLOSE(last trade)  SETTLE_PR(= underlying level!)  true option value
    ("CE", 19250.0, 6.10, 19253.80, max(19253.80 - 19250.0, 0.0)),
    ("PE", 19250.0, 1.95, 19253.80, max(19250.0 - 19253.80, 0.0)),
], columns=["typ", "strike", "close_pr", "settle_pr", "intrinsic"])

credit = 178.40                                   # entry credit (both legs)
debit_task = rows["settle_pr"].sum()              # task's exit: SETTLE_PR both legs
debit_true = rows["intrinsic"].sum()              # correct: cash-settle at intrinsic

pnl_task = credit - debit_task
pnl_true = credit - debit_true
print(rows.to_string(index=False))
print("\nentry credit             : %+10.2f pts" % credit)
print("task exit (SETTLE_PR)    : books %+10.2f pts" % pnl_task)
print("true exit (intrinsic)    : books %+10.2f pts" % pnl_true)
assert pnl_task < -30000 and pnl_true > 0, "demo failed"
print("\nDEFECT CONFIRMED: expiry-day SETTLE_PR is the underlying's settlement")
print("level; using it as the option exit fabricates ~38,500 pts of loss on a")
print("quiet week -- exactly the four-digit 'pin risk' losses in the summary.")
print("Fix: never read expiry-day option SETTLE_PR; cash-settle each leg at")
print("intrinsic value computed from the underlying's final settlement price.")
