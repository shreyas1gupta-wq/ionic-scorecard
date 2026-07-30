import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\buying")))
import chain
_, exps = chain.build_expiry_index()
with open(Path(__file__).parent / "expiry_list.txt", "w") as f:
    for e in exps:
        f.write(e.isoformat() + "\n")
print(len(exps))
