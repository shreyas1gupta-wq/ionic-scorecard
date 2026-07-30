import datetime as dt
import run_backspread as rb

rb.START = dt.date(2021,5,24)
rb.END = dt.date(2021,9,30)
rb.TCAL = rb.trading_calendar()
rb.TCAL_POS = {d:i for i,d in enumerate(rb.TCAL)}

df, skips = rb.run_cell("smoke_CE", "CE", 2, None, hold_to_expiry=False)
print(df.head(10).to_string())
print("skips:", skips)
print("n:", len(df))
if len(df):
    print(df[["gross_rs","fee_rs","net_rs","in_trap_zone"]].describe())
