"""WAVE-2 spec generator: ~1000 crafted specs from ~45 reasoned families (Principal scale mandate).
Each family = a deliberate hypothesis (rationale in 'source'); variants are CANONICAL enumerations
(literature-standard parameter points), every one logged to the denominator. No random search.
"""
import json
import itertools
from pathlib import Path

OUT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\IDEA_FACTORY\waves")
specs = []
IDX_UNIVERSES = ["Nifty 50", "Nifty Bank", "Nifty Midcap 100", "Nifty Smallcap 100", "Nifty IT", "Nifty Pharma", "Nifty Auto", "Nifty FMCG", "Nifty Metal", "Nifty Energy"]
CRYPTO = ["BTCUSDT", "ETHUSDT"]

def add(fid, name, why, asset, universe, signal, direction, exit_, ):
    specs.append({"id": f"W2-{fid}-{len(specs):04d}", "name": name, "source": why, "asset": asset,
                  "universe": universe, "signal": signal, "direction": direction, "entry": "next_close",
                  "exit": exit_})

# F1: pullback-in-trend across indices (hypothesis: index dips in uptrends are bought by SIP/institutional flows)
for u in IDX_UNIVERSES:
    for k in (2, 3, 4):
        for n_exit in (3, 5, 10):
            add("F1", f"{u} {k}-down-days in >200dma, hold {n_exit}", "structural dip-buying flow in index uptrends",
                "index_daily", u, [{"type": "dma_above", "params": {"n": 200}}, {"type": "consec_days", "params": {"k": k, "dir": "down"}}],
                "long", {"type": "bars", "params": {"n": n_exit}})
# F2: RSI regime split on indices (reversion works BELOW trend, momentum ABOVE — regime asymmetry hypothesis)
for u in IDX_UNIVERSES[:6]:
    for lt in (20, 30):
        add("F2a", f"{u} RSI2<{lt} above 200dma", "index short-term panic in uptrend mean-reverts",
            "index_daily", u, [{"type": "dma_above", "params": {"n": 200}}, {"type": "rsi_thresh", "params": {"n": 2, "lt": lt}}],
            "long", {"type": "trail_dma", "params": {"dma": 5, "n": 10}})
    for gt in (70, 80):
        add("F2b", f"{u} RSI14>{gt} above 200dma continuation", "index overbought-in-trend continues (crowding)",
            "index_daily", u, [{"type": "dma_above", "params": {"n": 200}}, {"type": "rsi_thresh", "params": {"n": 14, "gt": gt}}],
            "long", {"type": "bars", "params": {"n": 10}})
# F3: gap dynamics on indices by size bucket (hypothesis: small gaps continue, large gaps fade)
for u in IDX_UNIVERSES[:6]:
    for g, d_, why in [(0.5, "long", "small gap-up = information, continues"), (1.5, "short", "large gap-up = overreaction, fades (index short OK)"),
                       (-0.5, "short", "small gap-down continues"), (-1.5, "long", "large gap-down = panic, fades")]:
        sig = {"type": "gap_pct", "params": ({"gt": g} if g > 0 else {"lt": g})}
        add("F3", f"{u} gap {g:+}% {d_}", why, "index_daily", u, [sig], d_, {"type": "bars", "params": {"n": 3}})
# F4: VIX conditioning grid (hypothesis: vol regime determines equity forward returns nonlinearly)
for u in ["Nifty 50", "Nifty Midcap 100", "Nifty Smallcap 100"]:
    for vt, d_, why in [(13, "long", "complacency grind-up"), (18, "long", "moderate fear pays"), (25, "long", "panic rebound")]:
        for n_ in (5, 15):
            add("F4", f"{u} VIX>{vt} hold {n_}", why, "index_daily", u,
                [{"type": "vix_thresh", "params": {"gt": vt}}], d_, {"type": "bars", "params": {"n": n_}})
    add("F4", f"{u} VIX<12 low-vol carry", "low-vol regimes persist", "index_daily", u,
        [{"type": "vix_thresh", "params": {"lt": 12}}], "long", {"type": "bars", "params": {"n": 10}})
# F5: seasonality lattice (hypothesis: settlement/flow calendar effects differ by index)
for u in IDX_UNIVERSES[:6]:
    for dow in range(5):
        add("F5", f"{u} dow={dow}", "weekday flow patterns (expiry/settlement cycles)", "index_daily", u,
            [{"type": "seasonality_dow", "params": {"dow": dow}}], "long", {"type": "bars", "params": {"n": 1}})
    add("F5", f"{u} turn-of-month", "month-end institutional inflows", "index_daily", u,
        [{"type": "seasonality_dom", "params": {"turn": True, "first_n": 3}}], "long", {"type": "bars", "params": {"n": 3}})
# F6: breakout half-life by index (hypothesis: breakout edge decays with n; find the knee)
for u in IDX_UNIVERSES[:6]:
    for n in (10, 20, 55, 100):
        add("F6", f"{u} {n}d breakout trail", "index breakouts trend (no single-stock noise)",
            "index_daily", u, [{"type": "nday_breakout", "params": {"n": n}}], "long",
            {"type": "trail_dma", "params": {"dma": 20, "n": 40}})
# F7: index SHORT side (allowed) — breakdown momentum in downtrends
for u in IDX_UNIVERSES[:6]:
    for n in (20, 55):
        add("F7", f"{u} {n}d breakdown short", "index breakdowns trend down (hedging alpha)",
            "index_daily", u, [{"type": "nday_low", "params": {"n": n}}], "short",
            {"type": "bars", "params": {"n": 10}})
# F8: vol-expansion regime entries (hypothesis: vol expansion after quiet = new trend leg)
for u in IDX_UNIVERSES[:6]:
    for mult in (1.5, 2.0):
        add("F8", f"{u} vol-expansion x{mult}", "quiet->expansion marks regime shifts",
            "index_daily", u, [{"type": "dma_above", "params": {"n": 100}}, {"type": "vol_expansion", "params": {"n": 5, "base": 60, "mult": mult}}],
            "long", {"type": "bars", "params": {"n": 10}})
# F9: zscore band grid on indices (hypothesis: distance-from-mean has asymmetric payoffs by band)
for u in IDX_UNIVERSES[:6]:
    for z, d_ in [(-2.0, "long"), (-1.0, "long"), (2.0, "short")]:
        add("F9", f"{u} z20={z:+} {d_}", "band-dependent reversion asymmetry", "index_daily", u,
            [{"type": "zscore", "params": {"n": 20, ("lt" if z < 0 else "gt"): z}}], d_,
            {"type": "bars", "params": {"n": 5}})
# F10: gold family (hypothesis: gold trends persist at weekly scale; INR demand seasonal)
for n in (10, 20, 55):
    add("F10", f"gold {n}d breakout trail", "gold trend persistence", "gold_1m", None,
        [{"type": "nday_breakout", "params": {"n": n}}], "long", {"type": "trail_dma", "params": {"dma": 10, "n": 20}})
for k in (2, 3, 4, 5):
    add("F10", f"gold {k}-down reversion", "gold dip-buying (central-bank bid)", "gold_1m", None,
        [{"type": "consec_days", "params": {"k": k, "dir": "down"}}], "long", {"type": "bars", "params": {"n": 5}})
for dow in range(5):
    add("F10", f"gold dow={dow}", "gold fixing-day flows", "gold_1m", None,
        [{"type": "seasonality_dow", "params": {"dow": dow}}], "long", {"type": "bars", "params": {"n": 1}})
# F11: crypto structural (24/7 market microstructure differs; weekend/Monday effects real)
for c in CRYPTO:
    for dow in range(7):
        add("F11", f"{c} dow={dow}", "crypto weekly flow cycle", "crypto_1m", c,
            [{"type": "seasonality_dow", "params": {"dow": dow}}], "long", {"type": "bars", "params": {"n": 1}})
    for n in (20, 55):
        add("F11", f"{c} {n}d breakout", "crypto trend persistence strongest documented", "crypto_1m", c,
            [{"type": "nday_breakout", "params": {"n": n}}], "long", {"type": "trail_dma", "params": {"dma": 20, "n": 30}})
    for k in (3, 5):
        add("F11", f"{c} {k}-down rev", "crypto capitulation bounce", "crypto_1m", c,
            [{"type": "consec_days", "params": {"k": k, "dir": "down"}}], "long", {"type": "bars", "params": {"n": 3}})
# F12: stocks LONG-HOLD momentum composites (hypothesis: only multi-month holds clear stock friction)
for n_sig, n_hold in [(55, 60), (100, 90), (252, 120)]:
    for rs_gate in (True, False):
        sig = [{"type": "nday_breakout", "params": {"n": n_sig}}, {"type": "dma_above", "params": {"n": 200}}]
        add("F12", f"stocks {n_sig}d-breakout hold{n_hold} rs={rs_gate}", "long holds amortize friction; trend+breakout",
            "stocks_daily", None, sig, "long", {"type": "bars", "params": {"n": n_hold}})
# F13: stocks distance-from-high bands (hypothesis: 'fresh high' vs 'deep value zone' payoff structure)
for lo, hi_n, d_ in [(-3, 10, "near-high momentum"), (-25, 60, "shallow-correction recovery")]:
    add("F13", f"stocks within {abs(lo)}% of 100d-high hold {hi_n}", d_, "stocks_daily", None,
        [{"type": "distance_from_dma", "params": {"n": 100, "gt": lo}}, {"type": "dma_above", "params": {"n": 200}}],
        "long", {"type": "bars", "params": {"n": hi_n}})
# F14: consec-up exhaustion SHORT on INDICES only
for u in IDX_UNIVERSES[:4]:
    for k in (6, 8):
        add("F14", f"{u} {k}-up-days exhaustion short", "streak exhaustion (index short allowed)",
            "index_daily", u, [{"type": "consec_days", "params": {"k": k, "dir": "up"}}], "short",
            {"type": "bars", "params": {"n": 3}})
# F15: cross-index relative plays via composite (midcap vs nifty via distance filters)
for u, why in [("Nifty Midcap 100", "midcap beta amplification in trend"), ("Nifty Smallcap 100", "smallcap melt-up regime")]:
    for n in (50, 100):
        add("F15", f"{u} > {n}dma + vol-expand", why, "index_daily", u,
            [{"type": "dma_above", "params": {"n": n}}, {"type": "vol_expansion", "params": {"n": 5, "base": 60, "mult": 1.3}}],
            "long", {"type": "bars", "params": {"n": 15}})

print(f"total specs: {len(specs)}")
fams = {}
for s in specs:
    fams[s["id"].split("-")[1]] = fams.get(s["id"].split("-")[1], 0) + 1
print("families:", fams)
# chunk into 3 files for parallel runners
n = len(specs)
for c in range(3):
    chunk = specs[c::3]
    (OUT / f"wave2_chunk{c}.json").write_text(json.dumps(chunk, indent=0), encoding="utf-8")
    print(f"chunk{c}: {len(chunk)} specs")
