"""Objective auto-grade of the two exact-answer grid puzzles (MG05, MG06) across all model rows present.
Ground truth: MG05 E[D]=n(1-(1-1/n)^n), limit E[D]/n -> 1-1/e (0.6321). MG06 E[T]=4*H4=25/3 (8.3333).
Pure text-signature check (human-auditable); prints the matched signal per model. No judge, no model tokens.
"""
import re
from pathlib import Path

MG = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\SYSTEM_SCIENCE_PROGRAM\MODEL_GRID")
RES = MG / "results"

def despace(t):
    return re.sub(r"\s+", "", t.lower())

def grade_mg05(t):
    d = despace(t)
    formula = any(s in d for s in ["n(1-(1-1/n)", "1-(1-1/n)^n", "(1-1/n)^n", "(1-1/n)**n", "n*(1-(1-1/n)"])
    limit = any(s in d for s in ["1-1/e", "0.632", "0.6321", "(e-1)/e"])
    if formula and limit:
        return 1.0, "formula+limit"
    if limit:
        return 0.5, "limit only"
    if formula:
        return 0.5, "formula only"
    return 0.0, "neither"

def grade_mg06(t):
    d = despace(t)
    exact = any(s in d for s in ["25/3", "8.333", "8.33"])
    method = any(s in d for s in ["1+1/2+1/3+1/4", "4*(1+1/2+1/3+1/4)", "harmonic", "couponcollector", "coupon-collector"])
    if exact:
        return 1.0, "exact 25/3"
    if method:
        return 0.5, "method, wrong number"
    return 0.0, "neither"

models = sorted({p.name.split("_", 1)[1].replace(".md", "") for p in RES.glob("MG05_*.md")} |
                {p.name.split("_", 1)[1].replace(".md", "") for p in RES.glob("MG06_*.md")})
print(f"{'model':<10} {'MG05':>5} {'basis':<18} {'MG06':>5} {'basis':<22} {'puzzle/2':>8}")
rows = []
for m in models:
    f5, f6 = RES / f"MG05_{m}.md", RES / f"MG06_{m}.md"
    s5, b5 = grade_mg05(f5.read_text(encoding="utf-8")) if f5.exists() else (None, "missing")
    s6, b6 = grade_mg06(f6.read_text(encoding="utf-8")) if f6.exists() else (None, "missing")
    tot = (s5 or 0) + (s6 or 0) if (s5 is not None and s6 is not None) else None
    rows.append((m, s5, b5, s6, b6, tot))
    print(f"{m:<10} {str(s5):>5} {b5:<18} {str(s6):>5} {b6:<22} {str(tot):>8}")
out_lines = ["OBJECTIVE PUZZLE GRADE (MG05 exact=n(1-(1-1/n)^n), lim 1-1/e; MG06 exact=25/3). Text-signature, human-auditable.",
             "MEASURED:"] + [f"{m}: MG05={s5}({b5}) MG06={s6}({b6}) total={tot}" for m, s5, b5, s6, b6, tot in rows]

# Principal directive 2026-07-13: where OPUS scores an OBJECTIVE item 1.0, IMPUTE Fable=1.0.
# Basis: Fable 5 is Mythos-class, documented >= Opus 4.8 in capability. LABELED [IMPUTED], never "measured".
# Scope: objective exact-answer puzzles ONLY (MG05/MG06). NEVER applied to judge-scored tasks or defect-finding.
# A real Fable run (if account-2 executes it) SUPERSEDES the imputed value.
opus_row = next((r for r in rows if r[0] == "opus"), None)
if opus_row and not any(r[0] == "fable" for r in rows):
    _, os5, _, os6, _, _ = opus_row
    i5 = 1.0 if os5 == 1.0 else None
    i6 = 1.0 if os6 == 1.0 else None
    itot = (i5 or 0) + (i6 or 0) if (i5 is not None or i6 is not None) else None
    print(f"\n[IMPUTED] fable    MG05={i5} MG06={i6} total={itot}  (from Opus=1.0; NOT measured; supersede with real run)")
    out_lines += ["", "IMPUTED (Principal directive; Fable>=Opus capability; objective cells where Opus=1.0; NOT measured):",
                  f"fable: MG05={i5} MG06={i6} total={itot} [IMPUTED-from-opus]"]
(MG / "MG_PUZZLE_SCORES.txt").write_text("\n".join(out_lines), encoding="utf-8")
print("\n-> MG_PUZZLE_SCORES.txt (measured rows + labeled imputed fable; system pending account-2)")
