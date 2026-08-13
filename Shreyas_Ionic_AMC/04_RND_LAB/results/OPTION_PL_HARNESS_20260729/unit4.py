r"""UNIT-4 (corrected) — degenerate-exit control.

The first version of this test was MIS-SPECIFIED BY ME, not failed by the harness:
it set stop_pct=0.99 and asserted no 'stop' could fire. But a long option CAN lose
99% of its premium (a 2-strike-OTM CE decaying from Rs.108 to Rs.0.60), so 'stop'
firing was correct behaviour. Recorded here rather than quietly rewritten.

Corrected test: with NO stop, NO target, NO trail, NO time stop, the ONLY exits
possible are the mandatory ones -- squareoff / expiry_settle / data_end.
"""
from __future__ import annotations

import datetime as dt
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import opt_pl as H          # noqa: E402
import chain                # noqa: E402
import engine_swing as ES   # noqa: E402

spot_raw = chain.load_index()
scfg = replace(ES.SwingCfg(), trigger="ema_cross", strike_offset=-2)
edays = [d for d in ES.entry_days(spot_raw, scfg) if d <= dt.date(2025, 12, 31)]
sigs = [(pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=19), 1, "u4") for d in edays]

base = H.OptCfg(min_dte=3, max_dte=9, strike_offset=+2, max_hold_days=4,
                squareoff_hhmm="15:15", lots=None, allow_opposite_signal_exit=False)

print("=" * 78)
print("UNIT-4a  no stop / no target / no trail / no time-stop => mandatory exits only")
cfg = replace(base, stop_pct=None, target_pct=None, trail_pct=None, time_stop_min=None)
tr = H.run_signals(sigs, cfg)
f = tr[tr.status == "filled"]
vc = f.exit_reason.value_counts().to_dict()
ok = set(vc) <= {"squareoff", "expiry_settle", "data_end"}
print(f"exit reasons: {vc}")
print(f"UNIT-4a: {'PASS' if ok else 'FAIL'}")

print("\n" + "=" * 78)
print("UNIT-4b  evidence that the earlier 'stop @ 99%' firings were REAL, not a bug")
cfg2 = replace(base, stop_pct=0.99, target_pct=99.0, trail_pct=None, time_stop_min=None)
tr2 = H.run_signals(sigs, cfg2)
f2 = tr2[tr2.status == "filled"]
print(f"exit reasons: {f2.exit_reason.value_counts().to_dict()}")
st = f2[f2.exit_reason == "stop"]
for _, r in st.iterrows():
    lvl = r["entry_fill"] * (1 - 0.99)
    print(f"  {r['signal_t'].date()} K{r['strike']}{r['otype']} entry_fill={r['entry_fill']:.2f} "
          f"stop_level={lvl:.4f} exit_px_raw={r['exit_px_raw']:.2f} "
          f"-> premium fell to {r['exit_px_raw']/r['entry_fill']:.3%} of entry "
          f"({'legit' if r['exit_px_raw'] <= lvl else 'BUG'})")
bugs = int((st["exit_px_raw"] > st["entry_fill"] * 0.01).sum())
print(f"UNIT-4b: {'PASS (every 99%-stop was a genuine >99% premium collapse)' if bugs == 0 else f'FAIL ({bugs})'}")

print("\n" + "=" * 78)
print("UNIT-4c  exit-precedence check: no exit price violates its own trigger level")
cfg3 = replace(base, stop_pct=0.35, target_pct=1.00, trail_pct=None)
tr3 = H.run_signals(sigs, cfg3)
f3 = tr3[tr3.status == "filled"]
bad = 0
for _, r in f3.iterrows():
    b = r["entry_fill"]
    if r["exit_reason"] == "stop" and r["exit_px_raw"] > b * 0.65 + 1e-9:
        bad += 1; print("  BAD stop", r["signal_t"], r["exit_px_raw"], b * 0.65)
    if r["exit_reason"] == "target" and r["exit_px_raw"] < b * 2.00 - 1e-9:
        bad += 1; print("  BAD target", r["signal_t"], r["exit_px_raw"], b * 2.00)
print(f"reasons {f3.exit_reason.value_counts().to_dict()}")
print(f"UNIT-4c: {'PASS' if bad == 0 else f'FAIL ({bad})'}")
