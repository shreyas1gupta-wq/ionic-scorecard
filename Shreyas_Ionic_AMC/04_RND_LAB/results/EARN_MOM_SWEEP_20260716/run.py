"""
EARN_MOM_SWEEP_20260716 — CLI runner.
Usage:  python run.py A1 A2 B1 ...
Writes ledgers/<ID>.csv per combo and appends/overwrites the combo's row in results.csv
(idempotent: re-running an ID replaces its existing row rather than duplicating).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine  # noqa: E402
from combos import COMBOS  # noqa: E402

LEDGER_DIR = HERE / "ledgers"
RESULTS_CSV = HERE / "results.csv"

CONTRACT_COLS = [
    "combo_id", "family", "signal", "cut", "price_filter", "hold",
    "n_trades", "win_pct", "mean_net_pct", "median_net_pct", "t_stat",
    "mean_ex_top1", "mean_ex_top2", "cens_pct", "cagr", "sharpe", "maxdd",
    "placebo_mean", "placebo_p95", "excess_vs_placebo_mean", "beats_placebo95",
    "mean_net_pct_2x", "mean_net_pct_sw",
]

LEDGER_COLS = ["symbol", "avail_date", "entry_date", "exit_date", "gross_pct", "net_pct", "censored"]


def run_ids(ids: list[str]) -> None:
    LEDGER_DIR.mkdir(exist_ok=True)
    if RESULTS_CSV.exists():
        results = pd.read_csv(RESULTS_CSV)
    else:
        results = pd.DataFrame(columns=CONTRACT_COLS)

    for cid in ids:
        if cid not in COMBOS:
            print(f"[SKIP] unknown combo_id: {cid}")
            continue
        cfg = COMBOS[cid]
        print(f"[RUN] {cid} ({cfg['family']}) signal={cfg['signal']} cut={cfg['cut']} "
              f"pf={cfg.get('price_filter')} hold={cfg['hold']}")
        out = engine.run_combo(cfg)
        ledger = out.pop("_ledger")
        flags = out.pop("_flags")

        ledger_out = ledger.copy()
        if len(ledger_out):
            ledger_out = ledger_out.rename(columns={"avail_date": "avail_date"})
            ledger_out = ledger_out[[c for c in LEDGER_COLS if c in ledger_out.columns]]
        ledger_out.to_csv(LEDGER_DIR / f"{cid}.csv", index=False)

        row = {k: out.get(k) for k in CONTRACT_COLS}
        results = results[results["combo_id"] != cid]
        results = pd.concat([results, pd.DataFrame([row])], ignore_index=True)

        print(f"       n_trades={row['n_trades']} mean_net_pct={row['mean_net_pct']} "
              f"placebo_p95={row['placebo_p95']} beats_placebo95={row['beats_placebo95']} "
              f"cens_pct={row['cens_pct']}")
        if flags:
            print(f"       DEGENERATE FLAGS: {flags}")

    results = results.sort_values("combo_id").reset_index(drop=True)
    results.to_csv(RESULTS_CSV, index=False)
    print(f"[DONE] results.csv now has {len(results)} rows -> {RESULTS_CSV}")


if __name__ == "__main__":
    ids = sys.argv[1:]
    if not ids:
        print("usage: run.py <combo_id> [combo_id ...]  e.g. run.py A1 A2 B1")
        sys.exit(1)
    run_ids(ids)
