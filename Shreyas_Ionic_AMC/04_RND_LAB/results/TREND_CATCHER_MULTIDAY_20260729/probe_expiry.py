import datetime as dt
import sys

import trend_catcher as tc  # noqa: F401 (sets up sys.path for chain)
import chain

e = dt.date.fromisoformat(sys.argv[1])
df = chain.load_expiry(e)
print("OK", e, len(df))
