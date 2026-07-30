import time
import run_backspread as rb
t0=time.time()
df, skips = rb.run_cell("full_CE_w2", "CE", 2, None, hold_to_expiry=False)
print("elapsed", time.time()-t0, "n=", len(df), "skips=", skips)
