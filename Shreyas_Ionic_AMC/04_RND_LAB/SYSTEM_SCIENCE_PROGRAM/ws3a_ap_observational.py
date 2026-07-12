"""WS-3a: AlphaPoints ledger observational analysis (script-first, no causal claims).
Parses the AP event ledger in TEAM_ROSTER.md; categorizes awards; behavior mix over time.
"""
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
txt = (ROOT / "Shreyas_Ionic_AMC/00_GOVERNANCE/TEAM_ROSTER.md").read_text(encoding="utf-8")

rows = []
for m in re.finditer(r"^\|\s*(2026-\d\d-\d\d)\s*\|([^|]*)\|([^|]*)\|\s*([+\-−]?\d+)\s*\|(.*)$", txt, flags=re.M):
    date, who, what, pts, note = m.group(1), m.group(2).strip(), m.group(3).strip(), m.group(4), m.group(5).strip()
    pts = int(pts.replace("−", "-").replace("+", ""))
    rows.append((date, who, what, pts, note))
print(f"ledger events parsed: {len(rows)}")

def classify(what, note):
    s = (what + " " + note).lower()
    if any(k in s for k in ("bug", "bias catch", "leak", "landmine", "lookahead", "corrupt")):
        return "integrity: bug/bias/leak catch"
    if any(k in s for k in ("kill", "refut", "fail held", "stays-killed", "not confirmed")):
        return "integrity: honest kill / kill defense"
    if any(k in s for k in ("red team", "adversarial", "attack")):
        return "integrity: red-team work"
    if any(k in s for k in ("gate", "promoted", "pass")):
        return "progress: gate pass"
    if any(k in s for k in ("paper", "live")):
        return "progress: paper/live"
    if any(k in s for k in ("memo", "report", "letter", "study", "curat", "catalog", "pipeline", "data")):
        return "operations: memo/data/ops"
    return "other"

cat_pts, cat_n = Counter(), Counter()
by_person = Counter()
neg = []
for date, who, what, pts, note in rows:
    c = classify(what, note)
    cat_pts[c] += pts
    cat_n[c] += 1
    by_person[re.sub(r"\s*\(E-\d+\)", "", who)] += pts
    if pts < 0:
        neg.append((date, who, pts, note[:80]))

total = sum(p for *_, p, _ in [(r[0], r[1], r[3], r[4]) for r in rows])
lines = [f"WS-3a AP OBSERVATIONAL (n={len(rows)} events, {rows[0][0]}..{rows[-1][0]}, net {total:+d} AP)", ""]
lines.append("Category mix (the question: what does the economy actually reward?):")
for c, p in cat_pts.most_common():
    lines.append(f"  {c}: {p:+d} AP across {cat_n[c]} events ({p/max(total,1)*100:.0f}% of net)")
integ = sum(p for c, p in cat_pts.items() if c.startswith("integrity"))
prog = sum(p for c, p in cat_pts.items() if c.startswith("progress"))
lines.append("")
lines.append(f"INTEGRITY-class share: {integ:+d} AP ({integ/max(total,1)*100:.0f}%) vs PROGRESS-class {prog:+d} ({prog/max(total,1)*100:.0f}%)")
lines.append(f"negative events: {len(neg)}" + (f" -> {neg}" if neg else " (only honesty failures are scoreable negative; none recorded)"))
lines.append("")
lines.append("Top earners: " + " | ".join(f"{w} {p:+d}" for w, p in by_person.most_common(8)))
lines.append("")
lines.append("HONEST LIMITS: observational only - no counterfactual; cannot distinguish 'AP causes honesty' from")
lines.append("'the constitution causes honesty and AP just records it'. Causal test = WS-3b pre-registered ablation")
lines.append("(AP framing stripped from matched review tasks, blind-graded). THEATER verdict remains possible.")
out = "\n".join(lines)
print(out)
(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/SYSTEM_SCIENCE_PROGRAM/WS3A_RESULTS.txt").write_text(out, encoding="utf-8")
