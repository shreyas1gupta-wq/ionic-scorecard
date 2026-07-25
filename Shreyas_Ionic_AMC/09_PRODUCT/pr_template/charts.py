# -*- coding: utf-8 -*-
"""charts.py — bridge so modules get every Ionic chart with one import: `import charts as CH`.
Sets a per-build PNG output dir, then re-exports chart_lib + chart_lib_ext. Every fn returns a PNG path
to embed with deck.pic(s, path, x, y, w, h)."""
import os, sys
_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
_OUT = os.path.join(os.path.dirname(__file__), "_charts")
os.makedirs(_OUT, exist_ok=True)
os.environ["CHART_OUTDIR"] = _OUT  # must precede chart_lib import (OUTDIR read at import time)

from chart_lib import (donut, hbar, paired_bar, waterfall, dumbbell, radar, heatmap, treemap,  # noqa
                       histogram, bubble, lollipop, stacked100, small_multiples_bars,
                       efficient_frontier, value_map, projection_cone, bar3d)
from chart_lib_ext import (capture_scatter, drawdown_curve, rolling_return_band, fee_stack,  # noqa
                           ter_bars, tax_bridge, quality_alloc_quadrant, over_under_bar)
