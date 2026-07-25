"""Build one Obsidian note per Principal ruling (D-xxx) from DECISIONS_LOG.md.

Output: Shreyas_Ionic_AMC/01_COMMAND_CENTER/decisions/D-xxx.md
The DECISIONS_LOG ledger itself is NEVER edited. Backlink value comes from Obsidian's
"unlinked mentions" pane on each D-xxx note (matches plain-text D-xxx citations vault-wide).
Rerunnable: regenerates every note from the ledger.
"""
import re, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOG = ROOT / "Shreyas_Ionic_AMC/01_COMMAND_CENTER/DECISIONS_LOG.md"
OUT = ROOT / "Shreyas_Ionic_AMC/01_COMMAND_CENTER/decisions"
OUT.mkdir(exist_ok=True)

def y(v):
    return json.dumps(v, ensure_ascii=False)

rows = []
for line in LOG.read_text(encoding="utf-8").splitlines():
    if not line.startswith("| D-"):
        continue
    inner = line.strip().strip("|")
    parts = inner.split("|", 2)
    if len(parts) != 3:
        print("SKIP malformed row:", line[:60])
        continue
    did, date, text = (p.strip() for p in parts)
    rows.append((did, date, text))

count = 0
for did, date, text in rows:
    m = re.search(r"\*\*(.+?)\*\*", text)
    title = (m.group(1) if m else text[:70]).strip().rstrip(".").replace('"', "'")
    superseded = "SUPERSEDED" in text.upper()
    fm = [
        "---",
        f"decision: {y(did)}",
        f"date: {y(date)}",
        f"title: {y(title[:120])}",
        f"superseded: {'true' if superseded else 'false'}",
        "tags:",
        "  - decision",
        "---",
    ]
    body = [
        f"# {did} ({date})",
        "",
        text,
        "",
        "---",
        "**Where is this ruling invoked?** Open the *backlinks* pane on this note and expand **Unlinked mentions** — every file citing this decision id appears there (no ledger edits needed).",
        "",
        f"Ledger of record: [[Shreyas_Ionic_AMC/01_COMMAND_CENTER/DECISIONS_LOG|DECISIONS_LOG]] · *Generated note — do not hand-edit; regenerate via `05_DATA_OFFICE/scripts/build_decision_notes.py`.*",
        "",
    ]
    (OUT / f"{did}.md").write_text("\n".join(fm) + "\n" + "\n".join(body), encoding="utf-8")
    count += 1

print(f"decision notes written: {count} -> {OUT}")
print("ids:", ", ".join(r[0] for r in rows))
