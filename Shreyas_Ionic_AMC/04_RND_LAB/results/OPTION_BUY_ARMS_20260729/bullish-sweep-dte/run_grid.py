"""ARM 1 -- run the pre-registered grid. BUILD first, entirely; FORWARD only afterwards.

Usage:  python run_grid.py T1     (36 primary cells + 12 multi-day probe cells)
        python run_grid.py T2     (36 primary cells)
Two processes so the 84 pre-registered cells finish in wall-clock half the time.

84 cells total: T1 x 36 + T2 x 36 + T1 multi-day probe x 12 (PRE_REGISTRATION section 4).

Signals are processed in chronological chunks so each expiry parquet is read once per
chunk and reused by every cell in it; `run_parity.py` proved chunking + the pruned store
reproduce the unmodified harness EXACTLY (all 42 columns, 0.00e+00).

Everything is banked to disk as it completes, so a token/OOM cut cannot lose work.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT))
import arm1_lib as L                                     # noqa: E402
import opt_pl as H                                       # noqa: E402

TRADES = OUT / "trades"
TRADES.mkdir(exist_ok=True)
BUILD_CHUNKS = [2021, 2022, 2023, 2024, 2025]
FWD_CHUNKS = [2026]
T1, T2 = "T1_sweep_priorday_reclaim", "T2_sweep_intraday_continue"

# a reject that reflects a MACHINE limit, not an untradeable market -- must never appear
MACHINE_REJECTS = ("expiry_read_error",)


def say(s="", logf: Path | None = None):
    print(s, flush=True)
    if logf is not None:
        with logf.open("a", encoding="utf-8") as fh:
            fh.write(str(s) + "\n")


def run_phase(name: str, cells: list, sig_by_trigger: dict, chunks: list[int],
              lo, hi, store, logf: Path | None = None) -> dict:
    """Run every cell over the phase window, chunk-major so the cache is reused."""
    acc = {lab: {"filled": [], "n_sig": 0, "rej": Counter()} for lab, _ in cells}
    for yr in chunks:
        store.clear()                       # bound memory: one year's expiries at a time
        t_chunk = time.time()
        for lab, cfg in cells:
            trig = lab.split("|")[0]
            s = L.split(sig_by_trigger[trig], lo, hi)
            s = s[pd.to_datetime(s["t"]).dt.year == yr]
            if s.empty:
                continue
            tr = H.run_signals(s, cfg)
            a = acc[lab]
            a["n_sig"] += len(tr)
            a["rej"].update(tr.loc[tr.status == "rejected", "reject_reason"]
                            .astype(str).value_counts().to_dict())
            fl = tr[tr.status == "filled"]
            if len(fl):
                a["filled"].append(fl)
        say(f"  [{name}] chunk {yr} done in {time.time()-t_chunk:.0f}s "
            f"(parquet reads {store.reads}, cached {len(store._d)}, "
            f"mem-retries {store.mem_retries})", logf)

    res = {}
    for lab, _ in cells:
        a = acc[lab]
        fl = (pd.concat(a["filled"], ignore_index=True) if a["filled"]
              else pd.DataFrame(columns=H._TRADE_COLS))
        assert len(fl) + sum(a["rej"].values()) == a["n_sig"], lab   # nothing dropped
        bad = {k: v for k, v in a["rej"].items() if k.startswith(MACHINE_REJECTS)}
        if bad:
            raise RuntimeError(f"{lab}: machine-caused rejects contaminate the sample: {bad}")
        res[lab] = L.metrics(fl, a["n_sig"], a["rej"], lab)
        if len(fl):
            fn = TRADES / f"{name}__{lab.replace('|','__')}.csv"
            fl.to_csv(fn, index=False)
            res[lab]["trades_csv"] = fn.name
    return res


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "T1"
    logf = OUT / f"run_log_{which}.txt"
    logf.write_text("", encoding="utf-8")
    t_all = time.time()
    say(f"=== ARM 1 grid, process {which} ===", logf)

    sigs = L.build_signals()
    for k, v in sigs.items():
        b = L.split(v, L.BUILD_START, L.BUILD_END)
        f = L.split(v, L.FWD_START, L.FWD_END)
        say(f"{k}: {len(v)} total | BUILD {len(b)} ({b['t'].min()} .. {b['t'].max()}) "
            f"| FORWARD {len(f)}"
            + (f" ({f['t'].min()} .. {f['t'].max()})" if len(f) else ""), logf)

    need = L.needed_strikes(list(sigs.values()))
    say(f"needed-strike map: {len(need)} expiries, "
        f"{np.mean([len(v) for v in need.values()]):.1f} strikes/expiry avg", logf)
    store = L.install_global_store(needed=need, maxsize=70)

    trig = T1 if which == "T1" else T2
    cells = L.grid(trig)
    probe = L.probe_grid(T1) if which == "T1" else []
    say(f"cells: primary {len(cells)} + probe {len(probe)}", logf)

    # ---------------- BUILD (all of it, before the forward set is touched)
    say(f"\n--- BUILD {L.BUILD_START} .. {L.BUILD_END} ---", logf)
    build = run_phase("build", cells, sigs, BUILD_CHUNKS, L.BUILD_START, L.BUILD_END, store, logf)
    (OUT / f"grid_build_{which}.json").write_text(json.dumps(build, indent=1, default=str),
                                                  encoding="utf-8")
    say(f"  banked grid_build_{which}.json ({len(build)} cells)", logf)
    build_probe = {}
    if probe:
        build_probe = run_phase("build_probe", probe, sigs, BUILD_CHUNKS,
                                L.BUILD_START, L.BUILD_END, store, logf)
        (OUT / "grid_build_probe.json").write_text(json.dumps(build_probe, indent=1, default=str),
                                                   encoding="utf-8")
        say(f"  banked grid_build_probe.json ({len(build_probe)} cells)", logf)

    # ---------------- FORWARD (held out; reported, never selected on)
    say(f"\n--- FORWARD {L.FWD_START} .. {L.FWD_END} (HELD OUT) ---", logf)
    fwd = run_phase("forward", cells, sigs, FWD_CHUNKS, L.FWD_START, L.FWD_END, store, logf)
    (OUT / f"grid_forward_{which}.json").write_text(json.dumps(fwd, indent=1, default=str),
                                                    encoding="utf-8")
    fwd_probe = {}
    if probe:
        fwd_probe = run_phase("forward_probe", probe, sigs, FWD_CHUNKS,
                              L.FWD_START, L.FWD_END, store, logf)
        (OUT / "grid_forward_probe.json").write_text(json.dumps(fwd_probe, indent=1, default=str),
                                                     encoding="utf-8")
    say(f"  banked forward jsons for {which}", logf)

    gates = {}
    for lab in list(build) + list(build_probe):
        bm = build.get(lab, build_probe.get(lab, {}))
        fm = fwd.get(lab, fwd_probe.get(lab, {}))
        gates[lab] = L.pass_bar(bm, fm)
    (OUT / f"pass_bar_{which}.json").write_text(json.dumps(gates, indent=1, default=str),
                                                encoding="utf-8")
    n_p1 = sum(1 for v in gates.values() if v["P1_build_net_positive"])
    n_pass = sum(1 for v in gates.values() if v["PASS"])
    say(f"\n{which}: P1 (build net>0) {n_p1}/{len(gates)} | ALL FOUR GATES {n_pass}/{len(gates)}", logf)
    say(f"wall time {(time.time()-t_all)/60:.1f} min, parquet reads {store.reads}, "
        f"mem-retries {store.mem_retries}", logf)
