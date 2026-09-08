# -*- coding: utf-8 -*-
"""charts.py — bridge so modules get every Ionic chart with one import: `import charts as CH`.
Sets a per-build PNG output dir, then re-exports chart_lib + chart_lib_ext. Every fn returns a PNG path
to embed with deck.pic(s, path, x, y, w, h)."""
import atexit
import time
import os, shutil, sys
_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
# ONE DIRECTORY PER PROCESS. Every chart in this kit is written under a FIXED name
# ("cover_art", "qc_quadrant", "fe_vs_bm", ...) chosen per page, not per client. With a single
# shared directory, two builds running at the same time overwrite each other's images: the second
# build reads a half-written PNG and loses the page, or worse, finishes cleanly having embedded the
# FIRST client's chart in the SECOND client's deck. Both were observed. A cross-client chart in a
# client deck is a confidentiality incident, not a rendering bug, so the images are separated by
# process id. The probe pass and the real pass share a process, so they still share the cache and
# the second pass simply rewrites identical files.
_OUT = os.path.join(os.path.dirname(__file__), "_charts", "run-%d" % os.getpid())
os.makedirs(_OUT, exist_ok=True)
os.environ["CHART_OUTDIR"] = _OUT  # must precede chart_lib import (OUTDIR read at import time)


# The per-process directory is scratch: python-pptx embeds each image's BYTES when the picture is
# added, so once the deck is saved nothing needs the files. Left behind they accumulate one
# directory per build, each holding that client's charts, in a working tree people copy around.
# art.py resolves to this same path for this same process, so cleaning it here covers both.
@atexit.register
def _sweep_chart_scratch():
    shutil.rmtree(_OUT, ignore_errors=True)
    # Also retire the flat layout this replaced, and any run directory orphaned by a build that
    # was killed before its atexit could fire.
    root = os.path.dirname(_OUT)
    try:
        for e in os.listdir(root):
            f = os.path.join(root, e)
            if e.endswith(".png") and os.path.isfile(f):
                os.remove(f)
            elif e.startswith("run-") and os.path.isdir(f):
                # Another build may be running right now and OWN its directory, so age is the
                # test, not emptiness. A deck takes well under a minute to build, so anything
                # untouched for an hour belongs to a process that died before it could sweep.
                if time.time() - os.path.getmtime(f) > 3600:
                    shutil.rmtree(f, ignore_errors=True)
    except OSError:
        pass

from chart_lib import (donut, hbar, paired_bar, waterfall, dumbbell, radar, heatmap, treemap,  # noqa
                       histogram, bubble, lollipop, stacked100, small_multiples_bars,
                       efficient_frontier, value_map, projection_cone, bar3d)
from chart_lib_ext import (capture_scatter, drawdown_curve, rolling_return_band, fee_stack,  # noqa
                           ter_bars, tax_bridge, quality_alloc_quadrant, over_under_bar)
