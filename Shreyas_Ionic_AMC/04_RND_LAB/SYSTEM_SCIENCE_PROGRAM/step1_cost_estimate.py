"""Step 1 (free): estimate battery single-call cost per model from text lengths x published per-token prices.
Tokens ~= words*1.35. Input = arm prompt + task text; output = answer. LABELED ESTIMATE (web runs have no
exact token counts; harness Opus could be exact later). Cost is the headline metric per Principal."""
from pathlib import Path
SSP = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM")
BAT = SSP / "ws4_battery"
PRICE = {"fable": (15, 75), "opus": (15, 75), "sonnet": (3, 15), "haiku": (1, 5)}  # $/MTok in,out
COLS = {"fable": "webrun_fable", "opus": "ws4run_opus_20260713", "sonnet": "webrun_sonnetweb", "haiku": "webrun_haiku"}
TPW = 1.35
armp = (BAT / "PROTOCOL.md").read_text(encoding="utf-8").split("```")[1]
armp_w = len(armp.split())
taskw = {f"T{i:02d}": len((BAT / f"T{i:02d}" / "task.md").read_text(encoding="utf-8").split()) for i in range(1, 21)}

print(f"{'model':<9}{'n':>4}{'in_tok(est)':>12}{'out_tok(est)':>13}{'$cost(est)':>11}{'$/answer':>10}")
rows = {}
for m, d in COLS.items():
    fs = sorted((BAT / "results" / d / "raw").glob("T*_armA.md"))
    tin = tout = 0.0
    for f in fs:
        tid = f.name[:3]
        tin += (armp_w + taskw.get(tid, 250)) * TPW
        tout += len(f.read_text(encoding="utf-8").split()) * TPW
    pin, pout = PRICE[m]
    cost = tin / 1e6 * pin + tout / 1e6 * pout
    rows[m] = (len(fs), int(tin), int(tout), cost)
    print(f"{m:<9}{len(fs):>4}{int(tin):>12,}{int(tout):>13,}{cost:>10.3f}{cost/max(len(fs),1):>10.4f}")
out = "STEP1 COST ESTIMATE (battery single-call arm A) — ESTIMATE from word-length x published prices; not exact tokens.\n"
out += f"prices $/MTok in/out: {PRICE}\n"
out += "\n".join(f"{m}: n={n} in~{ti:,} out~{to:,} cost~${c:.3f} (${c/max(n,1):.4f}/answer)" for m, (n, ti, to, c) in rows.items())
(SSP / "MODEL_GRID" / "COST_ESTIMATE.txt").write_text(out, encoding="utf-8")
print("\ncheapest -> priciest:", ", ".join(f"{m} ${c:.3f}" for m, (_, _, _, c) in sorted(rows.items(), key=lambda x: x[1][3])))
