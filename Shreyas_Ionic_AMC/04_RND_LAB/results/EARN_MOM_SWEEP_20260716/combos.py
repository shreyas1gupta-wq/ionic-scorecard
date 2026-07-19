"""
EARN_MOM_SWEEP_20260716 — FROZEN 30-combo registry. Do not edit after any combo has been run
(D-030-style discipline: this is pre-registration for a screen, no post-hoc tuning per SPEC.md).

cfg schema (consumed by engine.run_combo):
  combo_id, family, signal (descriptive str), cut (tuple), price_filter (tuple|None), hold (tuple)
  [, sizing]

cut kinds:      ('pctile', <signal_col>, <thresh>)   signal_col + '_pctile' >= thresh
                ('abs_ge', <signal_col>, <thresh>)   signal_col >= thresh (absolute, not ranked)
                ('bool',  <signal_col>)              signal_col truthy (turnaround / accel)
                ('or'/'and', [cut, cut, ...])         boolean combine
price_filter kinds: None | ('above_50dma',) | ('above_200dma',) | ('ret_6m_pos',)
                | ('ret_12m_tophalf',) | ('near_52w_high', thresh) | ('reaction_pos',)
                | ('reaction_gt', thresh) | ('and', [pf, pf, ...])
hold kinds:     ('fixed', N) | ('dma', 50) | ('fixed_stop', N, stop_pct)

Percentile thresholds used: top-decile = 0.90, top-quintile = 0.80, top-tercile = 2/3,
top-half = 0.50 (all causal/expanding — see engine.py doc #1).
"""
TERCILE = 2.0 / 3.0

COMBOS: dict[str, dict] = {

    # ---------------- Family A — pure earnings momentum / PEAD ----------------
    "A1": dict(combo_id="A1", family="A", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.90), price_filter=None, hold=("fixed", 20)),
    "A2": dict(combo_id="A2", family="A", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.90), price_filter=None, hold=("fixed", 63)),
    "A3": dict(combo_id="A3", family="A", signal="np_yoy",
               cut=("abs_ge", "np_yoy", 1.00), price_filter=None, hold=("dma", 50)),
    "A4": dict(combo_id="A4", family="A", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.80), price_filter=None, hold=("fixed", 40)),
    "A5": dict(combo_id="A5", family="A", signal="sue",
               cut=("pctile", "sue", 0.90), price_filter=None, hold=("fixed", 20)),
    "A6": dict(combo_id="A6", family="A", signal="sue",
               cut=("pctile", "sue", 0.90), price_filter=None, hold=("fixed", 63)),
    "A7": dict(combo_id="A7", family="A", signal="sue",
               cut=("pctile", "sue", 0.80), price_filter=None, hold=("dma", 50)),
    "A8": dict(combo_id="A8", family="A", signal="eps_yoy",
               cut=("pctile", "eps_yoy", 0.90), price_filter=None, hold=("fixed", 63)),
    "A9": dict(combo_id="A9", family="A", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.90), price_filter=None, hold=("fixed_stop", 63, 0.08)),
    "A10": dict(combo_id="A10", family="A", signal="sue",
                cut=("abs_ge", "sue", 2.0), price_filter=None, hold=("fixed", 40)),

    # ---------------- Family B — earnings + price-action mixed ----------------
    "B1": dict(combo_id="B1", family="B", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.80), price_filter=("above_50dma",), hold=("fixed", 63)),
    "B2": dict(combo_id="B2", family="B", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.80), price_filter=("ret_6m_pos",), hold=("fixed", 63)),
    "B3": dict(combo_id="B3", family="B", signal="sue",
               cut=("pctile", "sue", 0.80), price_filter=("above_50dma",), hold=("fixed", 40)),
    "B4": dict(combo_id="B4", family="B", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.80), price_filter=("reaction_pos",), hold=("fixed", 20)),
    "B5": dict(combo_id="B5", family="B", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.80), price_filter=("near_52w_high", 0.85), hold=("fixed", 63)),
    "B6": dict(combo_id="B6", family="B", signal="sue",
               cut=("pctile", "sue", 0.80), price_filter=("ret_12m_tophalf",), hold=("fixed", 63)),
    "B7": dict(combo_id="B7", family="B", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.80), price_filter=("above_200dma",), hold=("fixed", 63)),
    "B8": dict(combo_id="B8", family="B", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.80), price_filter=("above_50dma",), hold=("dma", 50)),
    "B9": dict(combo_id="B9", family="B", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.90), price_filter=("reaction_gt", 0.03), hold=("fixed", 40)),
    "B10": dict(combo_id="B10", family="B", signal="sue",
                cut=("pctile", "sue", 0.80),
                price_filter=("and", [("above_50dma",), ("ret_6m_pos",)]), hold=("fixed", 63)),

    # ---------------- Family C — surprise-magnitude / turnaround / other ----------------
    "C1": dict(combo_id="C1", family="C", signal="turnaround",
               cut=("bool", "turnaround"), price_filter=None, hold=("fixed", 63)),
    "C2": dict(combo_id="C2", family="C", signal="turnaround",
               cut=("bool", "turnaround"), price_filter=None, hold=("dma", 50)),
    "C3": dict(combo_id="C3", family="C", signal="sales_yoy",
               cut=("pctile", "sales_yoy", 0.90), price_filter=None, hold=("fixed", 63)),
    "C4": dict(combo_id="C4", family="C", signal="opm_delta",
               cut=("pctile", "opm_delta", 0.90), price_filter=None, hold=("fixed", 63)),
    "C5": dict(combo_id="C5", family="C", signal="qoq",
               cut=("pctile", "qoq", 0.90), price_filter=None, hold=("fixed", 40)),
    "C6": dict(combo_id="C6", family="C", signal="np_yoy_or_turnaround",
               cut=("or", [("abs_ge", "np_yoy", 1.00), ("bool", "turnaround")]),
               price_filter=None, hold=("fixed", 63)),
    "C7": dict(combo_id="C7", family="C", signal="np_yoy",
               cut=("pctile", "np_yoy", 0.90), price_filter=None, hold=("fixed", 126)),
    "C8": dict(combo_id="C8", family="C", signal="np_yoy_and_sales_yoy",
               cut=("and", [("pctile", "np_yoy", TERCILE), ("pctile", "sales_yoy", TERCILE)]),
               price_filter=None, hold=("fixed", 63)),
    "C9": dict(combo_id="C9", family="C", signal="accel",
               cut=("bool", "accel"), price_filter=None, hold=("fixed", 63)),
    "C10": dict(combo_id="C10", family="C", signal="np_yoy",
                cut=("pctile", "np_yoy", 0.90), price_filter=None, hold=("fixed", 63),
                sizing="surprise_weighted"),
}

assert len(COMBOS) == 30, f"registry must have exactly 30 combos, has {len(COMBOS)}"
