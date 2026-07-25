"""EOD hook: write the firm's daily digest into the Obsidian daily note.

Output: Shreyas_Ionic_AMC/01_COMMAND_CENTER/daily/YYYY-MM-DD.md (matches .obsidian/daily-notes.json)
Idempotent per run: appends a timestamped digest section (multiple runs a day = multiple sections).
Wire into the EOD routine (see 99_OPS/EOD_ROUTINE.md §Obsidian daily digest).
"""
import re, os, glob, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CC = ROOT / "Shreyas_Ionic_AMC/01_COMMAND_CENTER"
DAILY = CC / "daily"
DAILY.mkdir(exist_ok=True)
today = datetime.date.today().isoformat()
now = datetime.datetime.now().strftime("%H:%M")

lines = [f"## Desk digest — {now}", ""]

# 1. Session journal entries dated today
journal = (CC / "SESSION_JOURNAL.md").read_text(encoding="utf-8")
todays = [m.strip("# ").strip() for m in re.findall(r"^## .*$", journal, re.M) if today in m]
lines += ["**Journal entries today:**"]
lines += [f"- {t}" for t in todays] if todays else ["- (none yet)"]
lines += [""]

# 2. Escalations board column counts
board = CC / "ESCALATIONS_BOARD.md"
if board.exists():
    col, counts = None, {}
    for ln in board.read_text(encoding="utf-8").splitlines():
        if ln.startswith("## "):
            col = ln[3:].strip()
            counts[col] = 0
        elif col and ln.lstrip().startswith("- [ ]"):
            counts[col] += 1
    pretty = " · ".join(f"{re.sub(r'\\s*\\(\\d+\\)$', '', k)}: {v}" for k, v in counts.items() if not k.startswith("%%"))
    lines += [f"**Escalations board:** {pretty}", ""]

# 3. CURRENT_STATE top sections (urgent flags + latest entry)
state = (CC / "CURRENT_STATE.md").read_text(encoding="utf-8")
tops = [m[3:].strip() for m in re.findall(r"^## .*$", state, re.M)][:4]
lines += ["**CURRENT_STATE top sections:**"] + [f"- {t}" for t in tops] + [""]

# 4. Most recently modified firm files (yesterday/today)
firm = ROOT / "Shreyas_Ionic_AMC"
recent = sorted(
    (p for p in glob.glob(str(firm / "**/*.md"), recursive=True)),
    key=os.path.getmtime, reverse=True,
)[:8]
lines += ["**Recently touched firm files:**"]
for p in recent:
    rel = Path(p).relative_to(ROOT).as_posix()
    ts = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%d-%b %H:%M")
    lines += [f"- [[{rel[:-3]}|{Path(p).stem}]] ({ts})"]
lines += [""]

note = DAILY / f"{today}.md"
if note.exists():
    note.write_text(note.read_text(encoding="utf-8").rstrip() + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
else:
    header = f"---\ntags:\n  - daily\n---\n# {today}\n\n"
    note.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
print(f"daily digest written -> {note}")
