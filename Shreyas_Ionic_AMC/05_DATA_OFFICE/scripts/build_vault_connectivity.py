"""
build_vault_connectivity.py — Vault Connectivity Upgrade
Spec: Shreyas_Ionic_AMC/05_DATA_OFFICE/VAULT_CONNECTIVITY_SPEC.md

Additive-only: merges missing frontmatter keys (type/tags/moc/program) into
firm-content notes and (re)generates MOC (Map-of-Content) hub files. Never
touches existing frontmatter keys, never touches body prose, never writes to
FROZEN/legacy-read-only/skill-agent files (those get MOC-only linking).

Usage:
    python build_vault_connectivity.py --vault-root <path> --dry-run
    python build_vault_connectivity.py --vault-root <path> --apply
"""
import argparse
import re
import sys
from pathlib import Path

# excluded wherever they occur in the path (structural, can be nested)
EXCLUDE_ANYWHERE = {".git", ".obsidian", ".remember", "worktrees"}

# excluded ONLY as an immediate child of the vault root — matching these by
# name anywhere would wrongly nuke legitimate nested folders of the same name
# (e.g. STOCK_SCORECARD_750/results/, already linked from HOME.md)
EXCLUDE_TOPLEVEL = {
    "intraday_options_strategy", "swing_momentum", "alpha_research",
    "datasets", "FINAL_STRATEGY_FORWARD_CHECK",
    "raw", "logs", "options", "Strategy_Results", "results", "other2",
}

# folders whose files get MOC-linked but NEVER frontmatter-written
NO_WRITE_DIR_SUFFIXES = [
    ("Shreyas_Ionic_AMC", "03_RESEARCH_DESK", "forward_tests"),
    ("Shreyas_Ionic_AMC", "06_TRADING_DESK", "specs"),
    (".claude", "agents"),
    (".claude", "skills"),
]

RND_PROGRAMS = {
    "BROAD_RESEARCH_2036", "PMS_STUDY_20260712", "SYSTEM_SCIENCE_PROGRAM",
    "FUND_METHODOLOGY_2036", "ALPHA_FORGE", "INDEX_PROGRAM_2026",
    "IDEA_FACTORY", "STOCKS_PROGRAM_2026", "STOCK_SCORECARD_750",
}

# ordered (most specific first) regex -> type
FOLDER_TYPE_RULES = [
    (r"^Shreyas_Ionic_AMC/01_COMMAND_CENTER/decisions/", "decision"),
    (r"^Shreyas_Ionic_AMC/01_COMMAND_CENTER/daily/", "daily-digest"),
    (r"^Shreyas_Ionic_AMC/04_RND_LAB/ideas/", "idea-intake"),
    (r"^Shreyas_Ionic_AMC/04_RND_LAB/KILLED_IDEAS", "killed-idea"),
    (r"^Shreyas_Ionic_AMC/04_RND_LAB/imported_research/", "paper-summary"),
    (r"^Shreyas_Ionic_AMC/04_RND_LAB/KNOWLEDGE_BASE", "lesson"),
    (r"^Shreyas_Ionic_AMC/00_GOVERNANCE/", "governance"),
    (r"^Shreyas_Ionic_AMC/02_PROMPT_LIBRARY/", "prompt"),
    (r"^Shreyas_Ionic_AMC/03_RESEARCH_DESK/", "research-memo"),
    (r"^Shreyas_Ionic_AMC/05_DATA_OFFICE/", "data-office"),
    (r"^Shreyas_Ionic_AMC/06_TRADING_DESK/", "trading-desk"),
    (r"^Shreyas_Ionic_AMC/07_RISK_OFFICE/", "risk"),
    (r"^Shreyas_Ionic_AMC/08_BOARD_ROOM/", "board"),
    (r"^Shreyas_Ionic_AMC/09_PRODUCT/", "product"),
    (r"^Shreyas_Ionic_AMC/10_BRAND_DESK/", "brand"),
    (r"^Shreyas_Ionic_AMC/90_PRINCIPALS_DESK/", "principal-task"),
    (r"^Shreyas_Ionic_AMC/99_OPS/", "ops"),
    (r"^Shreyas_Ionic_AMC/01_COMMAND_CENTER/", "command-center"),
    (r"^ALPHA_RANKER/", "alpha-ranker-research"),
    (r"^Xorlog/", "xorlog-venture"),
]


def classify(rel_posix: str) -> str:
    if rel_posix.startswith(".claude/agents/"):
        return "agent-persona"
    if rel_posix.startswith(".claude/skills/"):
        return "skill"
    for folder in RND_PROGRAMS:
        if rel_posix.startswith(f"Shreyas_Ionic_AMC/04_RND_LAB/{folder}/"):
            return "rnd-program"
    for pattern, type_ in FOLDER_TYPE_RULES:
        if re.match(pattern, rel_posix):
            return type_
    if rel_posix.startswith("Shreyas_Ionic_AMC/04_RND_LAB/"):
        return "rnd"
    return "note"


def is_excluded(rel_parts) -> bool:
    if any(p in EXCLUDE_ANYWHERE for p in rel_parts):
        return True
    return len(rel_parts) > 1 and rel_parts[0] in EXCLUDE_TOPLEVEL


def is_no_write(rel_parts) -> bool:
    joined = "/".join(rel_parts)
    for suffix in NO_WRITE_DIR_SUFFIXES:
        s = "/".join(suffix)
        if joined.startswith(s + "/") or joined == s:
            return True
    return False


def slug_moc_path(rel_posix: str) -> str:
    """Return the MOC path (posix, no extension) that owns this file's top folder.
    Never returns a path that could collide with a real existing file (HOME.md etc)."""
    parts = rel_posix.split("/")
    if len(parts) == 1:
        return "ROOT_MOC"  # loose file directly at vault root (HOME.md, README.md, ...)
    if parts[0] == "Shreyas_Ionic_AMC":
        if len(parts) == 2:
            return "Shreyas_Ionic_AMC/_MOC"  # loose file directly in Shreyas_Ionic_AMC/
        return f"Shreyas_Ionic_AMC/{parts[1]}/_MOC"
    if parts[0] == ".claude" and len(parts) > 1 and parts[1] == "agents":
        return "AGENTS_MOC"
    if parts[0] == ".claude" and len(parts) > 1 and parts[1] == "skills":
        return "SKILLS_MOC"
    return f"{parts[0]}/_MOC"


def read_existing_frontmatter_keys(text: str):
    """Return (has_frontmatter, end_line_idx_of_closing_dashes, existing_keys_set)."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return False, -1, set()
    lines = text.splitlines(keepends=True)
    keys = set()
    close_idx = -1
    for i in range(1, len(lines)):
        stripped = lines[i].strip()
        if stripped == "---":
            close_idx = i
            break
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):", lines[i])
        if m:
            keys.add(m.group(1))
    return True, close_idx, keys


def merge_frontmatter(text: str, new_fields: dict) -> str:
    """Additive-only merge: never overwrite/reorder existing keys."""
    has_fm, close_idx, existing_keys = read_existing_frontmatter_keys(text)
    to_add = {k: v for k, v in new_fields.items() if k not in existing_keys}
    if not to_add:
        return text
    add_lines = "".join(f"{k}: {v}\n" for k, v in to_add.items())
    lines = text.splitlines(keepends=True)
    if has_fm and close_idx != -1:
        return "".join(lines[:close_idx]) + add_lines + "".join(lines[close_idx:])
    # no existing frontmatter — create a new block
    block = "---\n" + add_lines + "---\n\n"
    return block + text


def wikilink(rel_posix_no_ext: str, label: str = None) -> str:
    if label:
        return f"[[{rel_posix_no_ext}|{label}]]"
    return f"[[{rel_posix_no_ext}]]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault-root", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.dry_run == args.apply:
        print("ERROR: pass exactly one of --dry-run or --apply", file=sys.stderr)
        sys.exit(1)
    dry = args.dry_run

    root = Path(args.vault_root).resolve()
    if not root.is_dir():
        print(f"ERROR: vault root not found: {root}", file=sys.stderr)
        sys.exit(1)

    md_files = []
    for p in root.rglob("*.md"):
        rel = p.relative_to(root)
        parts = rel.parts
        if is_excluded(parts):
            continue
        md_files.append((p, rel))

    frontmatter_written = 0
    frontmatter_skipped_no_write = 0
    frontmatter_skipped_no_new_fields = 0
    moc_groups = {}  # moc_rel_posix -> list of (file_rel_posix_no_ext, folder_type)

    for p, rel in md_files:
        rel_posix = rel.as_posix()
        parts = rel.parts
        type_ = classify(rel_posix)
        no_write = is_no_write(parts)

        moc_path = slug_moc_path(rel_posix)
        if rel_posix.replace(".md", "") != moc_path:  # don't list a MOC in itself
            moc_groups.setdefault(moc_path, []).append((rel_posix[:-3], type_))

        if no_write:
            frontmatter_skipped_no_write += 1
            continue

        new_fields = {
            "type": type_,
            "tags": f"[{type_}, {parts[0].lower()}]",
            "moc": f'"{wikilink(moc_path)}"',
        }
        text = p.read_text(encoding="utf-8", errors="ignore")
        merged = merge_frontmatter(text, new_fields)
        if merged == text:
            frontmatter_skipped_no_new_fields += 1
            continue
        frontmatter_written += 1
        if not dry:
            p.write_text(merged, encoding="utf-8")

    MARKER = "Auto-generated by build_vault_connectivity.py"
    moc_written = 0
    moc_clobber_blocked = []
    for moc_path, entries in sorted(moc_groups.items()):
        moc_file = root / (moc_path + ".md")
        if moc_file.exists():
            existing = moc_file.read_text(encoding="utf-8", errors="ignore")
            if MARKER not in existing:
                moc_clobber_blocked.append(moc_path)
                continue  # never overwrite a file we didn't generate ourselves
        lines = [f"# {moc_path.split('/')[-2] if '/' in moc_path else moc_path} — MOC\n\n",
                 f"*{MARKER} — regenerate on source change, do not hand-edit.*\n\n"]
        by_type = {}
        for file_rel, type_ in sorted(entries):
            by_type.setdefault(type_, []).append(file_rel)
        for type_, files in sorted(by_type.items()):
            lines.append(f"## {type_} ({len(files)})\n\n")
            for f in files:
                label = f.split("/")[-1]
                lines.append(f"- {wikilink(f, label)}\n")
            lines.append("\n")
        content = "".join(lines)
        moc_written += 1
        if not dry:
            moc_file.parent.mkdir(parents=True, exist_ok=True)
            moc_file.write_text(content, encoding="utf-8")

    mode = "DRY-RUN (no writes)" if dry else "APPLIED"
    print(f"=== build_vault_connectivity.py — {mode} ===")
    print(f"vault root: {root}")
    print(f"total .md files scanned (post-exclusion): {len(md_files)}")
    print(f"frontmatter merged: {frontmatter_written}")
    print(f"frontmatter skipped (no-write zone: frozen/legacy/agents/skills): {frontmatter_skipped_no_write}")
    print(f"frontmatter skipped (already had all fields): {frontmatter_skipped_no_new_fields}")
    print(f"MOC files {'planned' if dry else 'written'}: {moc_written}")
    for moc_path, entries in sorted(moc_groups.items()):
        print(f"  {moc_path}.md  <- {len(entries)} files")


if __name__ == "__main__":
    main()
