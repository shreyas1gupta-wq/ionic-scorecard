"""Build the Obsidian portfolio book: one markdown note per pf_qual_*.json research file.

Output: Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/book/<SYMBOL>.md
Frontmatter properties feed the vault-root PORTFOLIO_BOOK.base views.
Rerunnable: regenerates every note from source JSONs (notes are generated artifacts — do not hand-edit).
"""
import json, glob, csv, os, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results"
BOOK = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/book"
BOOK.mkdir(exist_ok=True)

def load_csv(path, encoding="utf-8"):
    with open(path, encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))

holdings = {r["symbol"]: r for r in load_csv(RES / "portfolio_quant.csv")}
full750 = {r["symbol"]: r for r in load_csv(RES / "full750_scored.csv")}
n100 = {r["symbol"]: r for r in load_csv(RES / "N100_RESEARCH_SUMMARY.csv", encoding="utf-8-sig")}

def y(v):  # JSON-encode = YAML-safe scalar
    return json.dumps(v, ensure_ascii=False)

_STOP = {"and", "of", "the", "&", "or", "for", "in", "on"}
def titlecase(s):
    # Preserve source casing that's already mixed; only fix all-lower sector strings.
    # Keeps stop-words lower so "automobile and auto components" -> "Automobile and Auto Components"
    # (matches the holdings-CSV canonical form exactly).
    words = str(s).split()
    out = []
    for i, w in enumerate(words):
        out.append(w if (w.lower() in _STOP and i != 0) else (w[:1].upper() + w[1:]))
    return " ".join(out)

def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

count, esc_count = 0, 0
for p in sorted(glob.glob(str(RES / "pf_qual_*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    sym = d["symbol"]
    h, f, n = holdings.get(sym), full750.get(sym), n100.get(sym)
    universe = "holdings" if h else ("nifty100" if n else "universe750")
    company = (h or {}).get("Company Name") or (n or {}).get("company") or sym
    sector = (h or {}).get("sector") or (f or {}).get("sector") or (n or {}).get("industry") or "unknown"
    quant_rec = (h or {}).get("recommendation") or (f or {}).get("recommendation_overall") or "n/a"
    value = fnum((h or {}).get("value_inr"))
    growth = d.get("expected_next_3y_growth_pct")
    if not isinstance(growth, (int, float)):
        growth = fnum(growth)
    rec = d.get("your_recommendation", "n/a")
    esc = bool(d.get("escalation_flag"))
    esc_count += esc
    mtime = datetime.date.fromtimestamp(os.path.getmtime(p)).isoformat()

    fm = [
        "---",
        f"symbol: {y(sym)}",
        f"company: {y(company)}",
        f"sector: {y(titlecase(sector))}",
        f"universe: {y(universe)}",
        f"rec: {y(rec)}",
        f"quant_rec: {y(quant_rec)}",
        f"growth_3y_pct: {growth if growth is not None else 'null'}",
        f"escalation: {'true' if esc else 'false'}",
        f"holding_value_inr: {int(value) if value is not None else 'null'}",
        f"updated: {mtime}",
        "tags:",
        "  - stock-note",
        "---",
    ]
    heading = sym if str(company).strip() == sym else f"{sym} — {company}"
    body = [f"# {heading}", ""]
    if d.get("summary"):
        body += ["> [!summary]"] + ["> " + ln for ln in str(d["summary"]).splitlines()] + [""]
    body += [f"## Recommendation — {rec}", "", str(d.get("recommendation_rationale", "")).strip(), ""]
    body += ["## Bull case", "", str(d.get("positive_para", "")).strip(), ""]
    body += ["## Bear case", "", str(d.get("negative_para", "")).strip(), ""]
    body += ["## Valuation (reverse-DCF judgment)", "", str(d.get("reverse_dcf_judgment", "")).strip(), ""]
    if esc:
        reason = str(d.get("escalation_reason") or "(no reason text — see detailed rationale)")
        body += ["## Escalation", "", "> [!warning] Escalated for Principal review"] + ["> " + ln for ln in reason.splitlines()] + [""]
    body += ["## Detailed rationale", "", str(d.get("detailed_rationale", "")).strip(), ""]
    srcs = d.get("research_sources") or []
    body += ["## Sources", ""] + [f"- {s}" for s in srcs] + [""]
    body += ["---", f"*Generated from `results/{Path(p).name}` — do not hand-edit; regenerate via `05_DATA_OFFICE/scripts/build_obsidian_book.py`.*", ""]

    out = BOOK / f"{sym}.md"
    out.write_text("\n".join(fm) + "\n" + "\n".join(body), encoding="utf-8")
    count += 1

print(f"book notes written: {count} (escalated: {esc_count}) -> {BOOK}")
by_u = {}
for p in glob.glob(str(RES / "pf_qual_*.json")):
    s = json.load(open(p, encoding="utf-8"))["symbol"]
    u = "holdings" if s in holdings else ("nifty100" if s in n100 else "universe750")
    by_u[u] = by_u.get(u, 0) + 1
print("by universe:", by_u)
