"""Quick smoke test: run the pipeline on the first 12 valid expiries only, to catch bugs
cheaply before the full ~260-expiry x 16-config run."""
import sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import vol_selling_backtest as V
import chain

_, exps = chain.build_expiry_index()
small_exps = exps[:12]
print("testing on", small_exps)

spot = V.chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15))]
flags = V.build_day_flags(spot)

# monkeypatch build_expiry_index to only return the small set for build_base_trades
orig = V.chain.build_expiry_index
V.chain.build_expiry_index = lambda: (orig()[0], small_exps)

base = V.build_base_trades(spot, flags)
print(base.shape)
print(base[["structure","entry_day","exp","credit","fill_credit","net_pnl","gross_pnl","cost_rs","reason","max_loss_per_lot","spot0"]].head(20).to_string())

for structure in ("short_strangle","iron_condor"):
    sub = base[base.structure==structure]
    pf_ = V.portfolio(sub, V.MARGIN_RATE[structure])
    print(structure, pf_.shape)
    print(pf_.head(12).to_string())
    m = V.metrics(pf_)
    print(m)
print("SMOKE TEST OK")
