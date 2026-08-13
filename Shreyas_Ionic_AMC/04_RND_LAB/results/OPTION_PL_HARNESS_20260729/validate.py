r"""VALIDATION of opt_pl.py against PREREG.md (written before any run).
UNIT-1..4 (correctness), REG-1 (incumbent regression), SANITY-5/6.
Run:  python validate.py            -> prints everything, writes trades to parquet
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import opt_pl as H                                    # noqa: E402
import chain                                           # noqa: E402
import engine_swing as ES                              # noqa: E402  incumbent

BUILD_S, BUILD_E = dt.date(2021, 1, 1), dt.date(2025, 12, 31)
FWD_S, FWD_E = dt.date(2026, 1, 1), dt.date(2026, 6, 30)
RESULT: dict = {}


def hdr(s):
    print("\n" + "=" * 78 + f"\n{s}\n" + "=" * 78)


# =============================================================================
hdr("REG-1  incumbent emacross_ITM2 -- signal set from engine_swing.entry_days()")
# Reuse the INCUMBENT signal generator verbatim so the only thing being compared is
# the fill/exit engine, not the signal logic.
spot_raw = chain.load_index()
scfg = replace(ES.SwingCfg(), trigger="ema_cross", strike_offset=-2, spread_width=0)
edays_all = ES.entry_days(spot_raw, scfg)
edays = [d for d in edays_all if BUILD_S <= d <= BUILD_E]
print(f"incumbent trigger days in build window: {len(edays)}  {edays[:4]} ... {edays[-3:]}")

# ---- incumbent baseline, run live (not trusted from REPORT.md alone)
inc = ES.run_range(scfg, BUILD_S, BUILD_E)
inc_pf = (inc[inc.net_pnl > 0].net_pnl.sum() / abs(inc[inc.net_pnl <= 0].net_pnl.sum())
          if (inc.net_pnl <= 0).any() else np.inf)
INC = dict(n=len(inc), wr=float((inc.net_pnl > 0).mean()), pf=float(inc_pf),
           net=float(inc.net_pnl.sum()), gross=float(inc.gross.sum()),
           ret_on_cap=float(inc.net_pnl.sum() / scfg.capital))
print(f"INCUMBENT LIVE RERUN: n={INC['n']} wr={INC['wr']:.1%} pf={INC['pf']:.2f} "
      f"net=Rs.{INC['net']:,.0f} ({INC['ret_on_cap']:+.1%} on Rs.3L) gross=Rs.{INC['gross']:,.0f}")
print("REPORT.md claim (2026-07-01): n=22 wr=45% pf=2.81 +17.1% on Rs.3L")
RESULT["incumbent_live"] = INC
chain.load_expiry.cache_clear()

# strike-convention check: incumbent's "ITM2" (offset=-2) actually resolves to which strike?
print("\n[strike convention] incumbent engine_swing: k = ATM - offset*STEP  with offset=-2"
      "  =>  k = ATM + 100  =  2 strikes OTM for a CE (label 'ITM2' is WRONG).")

sigs_reg = [(pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=19), 1, "emacross") for d in edays]

# Parity config: mirror every incumbent choice exactly.
cfg_parity = H.OptCfg(
    min_dte=3, max_dte=9, strike_offset=+2,          # +2 OTM == incumbent's "-2"
    target_pct=1.00, stop_pct=0.35, trail_pct=0.35,
    max_hold_days=4, squareoff_hhmm="15:15",
    expiry_handling="trade_out",                     # incumbent traded out at 15:15
    levels_off="raw",                                # incumbent set levels off the bar open
    slippage_pct=0.005, slippage_min_rs=0.0, slippage_mode="fixed",
    cost_model="incumbent", exclude_zero_volume=False,
    max_entry_lag_min=10_000, max_strike_miss_steps=50,
    allow_opposite_signal_exit=False, lots=None, capital=3_00_000.0, risk_per_trade=0.03,
)
tr_par = H.run_signals(sigs_reg, cfg_parity)
m_par = H.summarize(tr_par, "HARNESS parity-mode (incumbent rates/rules)", capital=3_00_000.0)
H.fill_report(tr_par)
RESULT["harness_parity"] = {k: v for k, v in m_par.items() if not isinstance(v, dict)}

# Honest-default config: same signals+instrument, binding COST_STANDARDS + liquidity gates.
cfg_honest = H.OptCfg(
    min_dte=3, max_dte=9, strike_offset=+2,
    target_pct=1.00, stop_pct=0.35, trail_pct=0.35,
    max_hold_days=4, squareoff_hhmm="15:15",
    lots=None, allow_opposite_signal_exit=False,
)
tr_hon = H.run_signals(sigs_reg, cfg_honest)
m_hon = H.summarize(tr_hon, "HARNESS honest-default (COST_STANDARDS + dyn slip + liq gates)",
                    capital=3_00_000.0)
RESULT["harness_honest"] = {k: v for k, v in m_hon.items() if not isinstance(v, dict)}

# held-out forward window, reported not selected on
sigs_fwd = [(pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=19), 1, "emacross")
            for d in edays_all if FWD_S <= d <= FWD_E]
tr_fwd = H.run_signals(sigs_fwd, cfg_honest)
m_fwd = H.summarize(tr_fwd, "HELD-OUT 2026 H1 (reported only, nothing selected on it)",
                    capital=3_00_000.0)
RESULT["harness_forward_2026H1"] = {k: v for k, v in m_fwd.items() if not isinstance(v, dict)}

# REG-1 verdict vs pre-registered band
f = tr_par[tr_par.status == "filled"]
band = dict(n=(17, 27), wr=(0.30, 0.60), pf=(1.0, 6.0),
            net=(0.4 * 51420, 2.5 * 51420))
ok = (band["n"][0] <= len(f) <= band["n"][1]
      and band["wr"][0] <= m_par["wr_net"] <= band["wr"][1]
      and band["pf"][0] < m_par["pf_net"] < band["pf"][1]
      and band["net"][0] <= m_par["net_total"] <= band["net"][1])
print(f"\nREG-1 pre-registered band {band}")
print(f"REG-1 VERDICT: {'PASS (consistent in sign and magnitude)' if ok else 'OUTSIDE BAND'}")
print("REG-1 IS A REGRESSION TEST, NOT A CORRECTNESS PROOF. Both engines could share the")
print("same error. Correctness evidence = UNIT-1/2/3 below.")
RESULT["REG1_pass"] = bool(ok)

# =============================================================================
hdr("UNIT-1  arithmetic reconciliation of 6 filled trades vs RAW parquet")
rng = np.random.default_rng(7)
fx = f[f.cash_settled != True]  # noqa: E712
pick = fx.sample(min(6, len(fx)), random_state=7)
bad = 0
for _, r in pick.iterrows():
    raw = pq.read_table(chain.build_expiry_index()[0][r["exp"]]).to_pandas()
    raw["t"] = pd.to_datetime(raw["timestamp"]).dt.tz_localize(None)
    leg = raw[(raw.strike == r["strike"]) & (raw.option_type == r["otype"])] \
        .drop_duplicates("t").set_index("t").sort_index()
    e_open = float(leg.loc[r["entry_t"], "open"])
    x_close = float(leg.loc[r["exit_t"], "close"])
    # independent recompute of the fills under the parity config
    e_fill = e_open + max(0.0, 0.005 * e_open)
    x_fill = max(x_close - max(0.0, 0.005 * x_close), 0.0)
    gross = (x_fill - e_fill) * r["qty"]
    d_e, d_x, d_g = abs(e_open - r.entry_px_raw), abs(x_close - r.exit_px_raw), abs(gross - r.gross)
    flag = "OK " if max(d_e, d_x, d_g) < 1e-6 else "MISMATCH"
    if flag != "OK ":
        bad += 1
    # verify the entry bar is genuinely the FIRST bar after the signal
    first_after = leg[leg.index > r["signal_t"]].index[0]
    seq = "OK" if first_after == r["entry_t"] else f"BAD(first_after={first_after})"
    print(f"{flag} {r['signal_t']} K{r['strike']}{r['otype']} open={e_open:.2f} "
          f"close={x_close:.2f} gross={gross:,.2f} | d_open={d_e:.2e} d_close={d_x:.2e} "
          f"d_gross={d_g:.2e} | next-bar {seq}")
print(f"UNIT-1: {'PASS' if bad == 0 else f'FAIL ({bad} mismatches)'}")
RESULT["UNIT1_pass"] = bad == 0

# =============================================================================
hdr("UNIT-2  expiry intrinsic cash-settlement reconciliation")
# force rides to expiry: no stop/target/trail, long hold, settle_intrinsic
cfg_exp = H.OptCfg(min_dte=3, max_dte=9, strike_offset=0, max_hold_days=30,
                   expiry_handling="settle_intrinsic", lots=1,
                   allow_opposite_signal_exit=False, exclude_zero_volume=True)
sigs_exp = [(pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=19), 1, "toexpiry")
            for d in edays[:14]]
tr_exp = H.run_signals(sigs_exp, cfg_exp)
fe = tr_exp[(tr_exp.status == "filled") & (tr_exp.cash_settled == True)]  # noqa: E712
print(f"cash-settled trades: {len(fe)} of {int((tr_exp.status=='filled').sum())} filled")
sp = H.load_spot()
bad2 = 0
for _, r in fe.head(6).iterrows():
    d = sp[sp.index.date == r["exp"]]
    w = d[d.index >= pd.Timestamp(r["exp"]) + pd.Timedelta(hours=15)]
    ref = float(w["close"].mean())
    ref_intr = max(0.0, ref - r["strike"]) if r["otype"] == "CE" else max(0.0, r["strike"] - ref)
    d1, d2 = abs(ref - r["settle_spot"]), abs(ref_intr - r["exit_px_raw"])
    onexp_opt_bars = int(((sp.index.date == r["exp"])).sum())  # sanity: spot exists
    flag = "OK " if max(d1, d2) < 1e-6 else "MISMATCH"
    if flag != "OK ":
        bad2 += 1
    print(f"{flag} exp={r['exp']} K{r['strike']}{r['otype']} settle_spot={ref:.2f} "
          f"intrinsic={ref_intr:.2f} harness_exit_px={r['exit_px_raw']:.2f} "
          f"exit_t={r['exit_t']} exit_fill={r['exit_fill']:.2f} (no slippage on settlement) "
          f"| d={max(d1,d2):.2e} spot_bars_on_exp={onexp_opt_bars}")
# exit_fill must equal intrinsic exactly (cash settlement => no market slippage)
eq = bool(np.allclose(fe["exit_fill"], fe["exit_px_raw"]))
print(f"exit_fill == intrinsic for all cash-settled: {eq}")
print(f"UNIT-2: {'PASS' if (bad2 == 0 and eq and len(fe) > 0) else 'FAIL'}")
RESULT["UNIT2_pass"] = bool(bad2 == 0 and eq and len(fe) > 0)

# =============================================================================
hdr("UNIT-3  no-lookahead invariants over every trade produced so far")
allf = pd.concat([tr_par, tr_hon, tr_fwd, tr_exp], ignore_index=True)
allf = allf[allf.status == "filled"]
v1 = int((allf.entry_t <= allf.signal_t).sum())
v2 = int((allf.exit_t < allf.entry_t).sum())
v3 = int((pd.to_datetime(allf.entry_t).dt.time < dt.time(9, 15)).sum())
v4 = int((pd.to_datetime(allf.entry_t).dt.date != pd.to_datetime(allf.signal_t).dt.date).sum())
print(f"entry_t <= signal_t      : {v1}   (must be 0)")
print(f"exit_t  <  entry_t       : {v2}   (must be 0)")
print(f"entry before 09:15       : {v3}   (must be 0 -- pre-open auction guard)")
print(f"entry on a different day : {v4}   (must be 0)")
print(f"UNIT-3: {'PASS' if v1 == v2 == v3 == v4 == 0 else 'FAIL'}  (n={len(allf)})")
RESULT["UNIT3_pass"] = bool(v1 == v2 == v3 == v4 == 0)

# =============================================================================
hdr("UNIT-4  degenerate-exit control (no stop/target/trail/time => mandatory exits only)")
# NOTE: the FIRST version of this test used stop_pct=0.99 and asserted no 'stop' could
# fire. That criterion was mis-specified by me -- a long option genuinely can lose >99%
# of its premium, so 'stop' firing was correct. See unit4.py for the evidence and the
# corrected battery (4a/4b/4c). Left recorded rather than quietly rewritten (D-035).
cfg_deg = replace(cfg_honest, stop_pct=None, target_pct=None, trail_pct=None,
                  time_stop_min=None)
tr_deg = H.run_signals(sigs_reg, cfg_deg)
fd = tr_deg[tr_deg.status == "filled"]
vc = fd.exit_reason.value_counts().to_dict()
okd = set(vc) <= {"squareoff", "expiry_settle", "data_end"}
print(f"exit reasons: {vc}")
print(f"UNIT-4: {'PASS' if okd else 'FAIL (an optional exit fired with all of them off)'}")
RESULT["UNIT4_pass"] = bool(okd)

# =============================================================================
hdr("SANITY-5  RANDOM-TIMESTAMP CONTROL -- must be NET-NEGATIVE or the harness is broken")
sp = H.load_spot()
bdays = sorted({d for d in sp.index.date if BUILD_S <= d <= BUILD_E})
rng = np.random.default_rng(20260729)
N = 1800
days_pick = rng.choice(len(bdays), size=N, replace=True)
mins_pick = rng.integers(0, 311, size=N)          # 09:20 .. 14:30 inclusive
dirs = rng.choice([1, -1], size=N)
sigs_rnd = [(pd.Timestamp(bdays[int(di)]) + pd.Timedelta(hours=9, minutes=20 + int(mi)),
             int(dd), "random") for di, mi, dd in zip(days_pick, mins_pick, dirs)]

for name, cfg in [
    ("A: hold-to-15:25, no stop/target (pure theta+cost drag)",
     H.OptCfg(min_dte=1, max_dte=7, strike_offset=0, max_hold_days=0,
              squareoff_hhmm="15:25", lots=1, allow_opposite_signal_exit=False)),
    ("B: target +50% / stop -30% (a realistic intraday buy config)",
     H.OptCfg(min_dte=1, max_dte=7, strike_offset=0, target_pct=0.50, stop_pct=0.30,
              max_hold_days=0, squareoff_hhmm="15:25", lots=1,
              allow_opposite_signal_exit=False)),
    ("C: 0DTE allowed, trade_out at 15:25",
     H.OptCfg(min_dte=0, max_dte=7, strike_offset=0, max_hold_days=0,
              squareoff_hhmm="15:25", expiry_handling="trade_out", lots=1,
              allow_opposite_signal_exit=False)),
]:
    tr = H.run_signals(sigs_rnd, cfg, progress=600)
    m = H.summarize(tr, f"RANDOM CONTROL {name}", capital=3_00_000.0)
    fr = H.fill_report(tr, quiet=True)
    ff = tr[tr.status == "filled"]
    raw_gross = float(((ff.exit_px_raw - ff.entry_px_raw) * ff.qty).sum())
    print(f"   frictionless gross (raw open->close, no slippage/costs): Rs.{raw_gross:,.0f}")
    print(f"   zero-vol entry rejects: {fr['reject_reasons'].get('zero_volume_entry',0)}, "
          f"lag rejects: {fr['reject_reasons'].get('entry_lag_too_large',0)}")
    verdict = "PASS (net-negative as required)" if (m["net_total"] < 0 and m["net_mean"] < 0) \
        else "*** FAIL -- HARNESS SUSPECT, STOP ***"
    print(f"   SANITY-5 {name[0]}: {verdict}")
    RESULT[f"SANITY5_{name[0]}"] = dict(net_total=m["net_total"], gross_total=m["gross_total"],
                                        raw_gross=raw_gross, n=m["filled"],
                                        pass_=bool(m["net_total"] < 0 and m["net_mean"] < 0))
    if name.startswith("B"):
        tr.to_csv(HERE / "random_control_B.csv", index=False)

# =============================================================================
hdr("SANITY-6  cost monotonicity: gross > net on every filled trade")
v = int((allf.gross <= allf.net_pnl).sum())
print(f"trades with gross <= net: {v} (must be 0); min cost Rs.{allf.costs.min():.2f}")
RESULT["SANITY6_pass"] = bool(v == 0)
print(f"SANITY-6: {'PASS' if v == 0 else 'FAIL'}")

# =============================================================================
hdr("ONE-DAY-LAG DEGRADATION (informational, D-028 style)")
sigs_lag = []
allday = sorted({d for d in sp.index.date})
pos = {d: i for i, d in enumerate(allday)}
for d in edays:
    i = pos.get(d)
    if i is not None and i + 1 < len(allday):
        sigs_lag.append((pd.Timestamp(allday[i + 1]) + pd.Timedelta(hours=9, minutes=19), 1, "lag1"))
tr_lag = H.run_signals(sigs_lag, cfg_honest)
m_lag = H.summarize(tr_lag, "emacross signals shifted +1 trading day", capital=3_00_000.0)
RESULT["lag1"] = {k: v for k, v in m_lag.items() if not isinstance(v, dict)}

# =============================================================================
hdr("SUMMARY")
tr_par.to_csv(HERE / "reg1_parity_trades.csv", index=False)
tr_hon.to_csv(HERE / "reg1_honest_trades.csv", index=False)
(HERE / "validation_results.json").write_text(json.dumps(RESULT, indent=2, default=str))
gates = {k: v for k, v in RESULT.items() if k.endswith("_pass") or k.startswith("SANITY5")}
print(json.dumps(gates, indent=2, default=str))
print("\nwrote reg1_parity_trades.csv / reg1_honest_trades.csv / "
      "random_control_B.csv / validation_results.json")
