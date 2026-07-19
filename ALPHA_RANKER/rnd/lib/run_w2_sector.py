"""
WAVE-2 W2-sector worker -- pre-register + harness-test 3 money-first
sector hypotheses (S1/S2/S3), basis='resid', horizons 1M & 1Y.

S1: sector-momentum tilt -- own-sector RS (macro_sector) as a stock factor.
S2: within-sub-sector residual momentum (peer-relative demean of
    build_mom_resid_12_1), compared against the PLAIN (non-peer-relative)
    residual momentum to see whether sector-neutralizing it adds edge.
S3: within-sub-sector earnings-yield (peer-relative demean of
    build_H014_earnings_yield), compared against PLAIN earnings yield.

Cards land in rnd/cards/W2_sector_*.json via the shared harness
(rnd/lib/harness.py). Pre-registration happens FIRST (backlog.json), status
flipped queued->done with verdicts written back after the harness runs
(RESEARCH_PROTOCOL.md S0 -- register before results exist).
"""
import json
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parent))

from harness import run_experiment, load_panel, CARDS_DIR  # noqa: E402
import builders_mom as bm  # noqa: E402
import builders_value as bv  # noqa: E402
from sector_analytics import own_sector_rs_factor, peer_relative  # noqa: E402

BACKLOG_PATH = _THIS.parent.parent / "backlog.json"
FAMILY = "W2sector"

panel, src = load_panel()
print(f"panel_source={src} rows={len(panel)} dates={panel['date'].nunique()} symbols={panel['symbol'].nunique()}")

# --------------------------------------------------------------------------
# Pre-registration (RESEARCH_PROTOCOL S0) -- add S1/S2/S3 to backlog.json
# BEFORE running, if not already present.
# --------------------------------------------------------------------------
NEW_HYPOTHESES = [
    {
        "id": "W2SEC-S1", "cat": "sector", "horizon": ["1M", "1Y"],
        "name": "sector-momentum tilt (own macro-sector RS as stock factor)",
        "construct": "own_sector_rs_factor(panel, level='macro_sector', lookback=252, skip=21) "
                     "= (sector composite mom - NIFTY mom), broadcast to every stock in that sector; "
                     "closes FRAMEWORK_CATALOG.md's flagged HIGH-PRIORITY GAP #1 (sector-momentum tilt).",
        "sign": "+", "kill": "default", "priority": 1,
        "rationale": "KNOWLEDGE_BASE.md #11 / MULTIBAGGER_DNA.md: every era's giant winners cluster in one hot sector.",
        "status": "queued",
    },
    {
        "id": "W2SEC-S2", "cat": "sector", "horizon": ["1M", "1Y"],
        "name": "within-sub-sector residual momentum (peer-relative) vs plain",
        "construct": "PLAIN=build_mom_resid_12_1(panel) (builders_mom.py H003); "
                     "PEER=peer_relative(PLAIN, level='sub_sector', method='z') -- z-score demeaned "
                     "within sub_sector at each date. Tests whether sector-neutralizing residual "
                     "momentum adds edge over the raw factor.",
        "sign": "+", "kill": "default", "priority": 1,
        "rationale": "FRAMEWORK_CATALOG.md #1 'Residual/idiosyncratic momentum' + 'Relative strength vs sector' rows.",
        "status": "queued",
    },
    {
        "id": "W2SEC-S3", "cat": "sector", "horizon": ["1M", "1Y"],
        "name": "within-sub-sector earnings yield (peer-relative) vs plain",
        "construct": "PLAIN=build_H014_earnings_yield(panel) (builders_value.py); "
                     "PEER=peer_relative(PLAIN, level='sub_sector', method='z'). Tests whether "
                     "sector-relative value beats absolute value cross-sectionally.",
        "sign": "+", "kill": "default", "priority": 1,
        "rationale": "FRAMEWORK_CATALOG.md #2 'Valuation vs own history percentile + vs sector peers'.",
        "status": "queued",
    },
]

backlog = json.loads(BACKLOG_PATH.read_text(encoding="utf-8"))
existing_ids = {h["id"] for h in backlog["hypotheses"]}
added = 0
for h in NEW_HYPOTHESES:
    if h["id"] not in existing_ids:
        backlog["hypotheses"].append(h)
        added += 1
if added:
    BACKLOG_PATH.write_text(json.dumps(backlog, indent=1), encoding="utf-8")
print(f"pre-registered {added} new hypotheses to backlog.json (already-present ones left as-is)")

# --------------------------------------------------------------------------
# Build factors once
# --------------------------------------------------------------------------
print("building factors...")
s1_factor = own_sector_rs_factor(panel, level="macro_sector", lookback=252, skip=21)

s2_plain = bm.build_mom_resid_12_1(panel)
s2_peer = peer_relative(s2_plain, level="sub_sector", method="z")

s3_plain = bv.build_H014_earnings_yield(panel)
s3_peer = peer_relative(s3_plain, level="sub_sector", method="z")

print(f"S1 n_obs={len(s1_factor)}  S2_plain n_obs={len(s2_plain)}  S2_peer n_obs={len(s2_peer)}  "
      f"S3_plain n_obs={len(s3_plain)}  S3_peer n_obs={len(s3_peer)}")

RUNS = [
    ("W2_sector_S1_secRS_macro", s1_factor),
    ("W2_sector_S2_plain_residmom", s2_plain),
    ("W2_sector_S2_peer_residmom_subsector", s2_peer),
    ("W2_sector_S3_plain_earnyield", s3_plain),
    ("W2_sector_S3_peer_earnyield_subsector", s3_peer),
]

summary = {}
for base_id, factor in RUNS:
    for h in ["1M", "1Y"]:
        fid = f"{base_id}_{h}"
        existing = CARDS_DIR / f"{fid}.json"
        if existing.exists():
            card = json.loads(existing.read_text(encoding="utf-8"))
            if card.get("status") not in (None, "FAIL_NO_OVERLAP"):
                print(f"-- RESUME (already on disk): {fid} -> {card.get('verdict')}")
            else:
                print(f"-- running {fid} ...")
                card = run_experiment(fid, lambda p, f=factor: f, h, basis="resid",
                                       panel=panel, panel_source=src, family=FAMILY)
        else:
            print(f"-- running {fid} ...")
            card = run_experiment(fid, lambda p, f=factor: f, h, basis="resid",
                                   panel=panel, panel_source=src, family=FAMILY)
        summary[fid] = {
            "status": card.get("status"),
            "verdict": card.get("verdict"),
            "ic_mean": card.get("ic", {}).get("ic_mean"),
            "ic_ir": card.get("ic", {}).get("ic_ir"),
            "n_obs": card.get("n_obs"), "n_dates": card.get("n_dates"),
            "net_of_cost_ann_return": card.get("costs", {}).get("net_of_cost_ann_return"),
            "monotonicity": card.get("deciles", {}).get("monotonicity"),
            "pbo": card.get("pbo", {}).get("pbo"),
            "lag_test_delta": card.get("lag_test", {}).get("lag_test_delta"),
            "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
        }
        print(f"   -> {summary[fid]}")

OUT = _THIS.parent.parent / "reports" / "W2_sector_results.json"
OUT.write_text(json.dumps(summary, indent=1), encoding="utf-8")
print(f"wrote {OUT}")

# --------------------------------------------------------------------------
# Update backlog.json S1/S2/S3 rows with a status+verdict summary now that
# cards exist (RESEARCH_PROTOCOL S0: results filled in AFTER pre-registration,
# never before).
# --------------------------------------------------------------------------
backlog = json.loads(BACKLOG_PATH.read_text(encoding="utf-8"))
verdict_map = {
    "W2SEC-S1": ["W2_sector_S1_secRS_macro_1M", "W2_sector_S1_secRS_macro_1Y"],
    "W2SEC-S2": ["W2_sector_S2_plain_residmom_1M", "W2_sector_S2_plain_residmom_1Y",
                 "W2_sector_S2_peer_residmom_subsector_1M", "W2_sector_S2_peer_residmom_subsector_1Y"],
    "W2SEC-S3": ["W2_sector_S3_plain_earnyield_1M", "W2_sector_S3_plain_earnyield_1Y",
                 "W2_sector_S3_peer_earnyield_subsector_1M", "W2_sector_S3_peer_earnyield_subsector_1Y"],
}
for h in backlog["hypotheses"]:
    if h["id"] in verdict_map:
        cids = verdict_map[h["id"]]
        h["status"] = "done"
        h["cards"] = [f"rnd/cards/{c}.json" for c in cids]
        h["verdict_by_card"] = {c: summary.get(c, {}).get("verdict") for c in cids}
BACKLOG_PATH.write_text(json.dumps(backlog, indent=1), encoding="utf-8")
print("backlog.json S1/S2/S3 rows updated with verdicts.")
