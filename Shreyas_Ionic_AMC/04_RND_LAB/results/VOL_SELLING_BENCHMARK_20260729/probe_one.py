import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\buying")))
import datetime as dt
import chain
exp = dt.date.fromisoformat(sys.argv[1].strip())
df = chain.load_expiry(exp)
print("OK", exp, len(df), df["strike"].nunique())
