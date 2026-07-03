"""FIRM BACKUP — emergency/accidental-delete protection (Principal order, D-027).
Destination is OUTSIDE OneDrive (survives OneDrive sync accidents/ransomware of the synced tree):
  C:\\Users\\Shreyas.1Gupta\\ShreyasIonicAMC_BACKUP\\<YYYYMMDD_HHMM>\\
Contents per backup:
  1. git_full.bundle           — ENTIRE git history (command layer) in one restorable file
  2. firm_tree.zip             — Shreyas_Ionic_AMC/ + .claude/ + root md files (raw copy, git-independent)
  3. critical_data.zip         — small irreplaceable-ish parquets (strategy outputs, derived, ETF/index pulls)
Rotation: keep newest 5 backups. Raw HF dumps NOT included (re-downloadable, 28GB).
Restore: `git clone git_full.bundle restored/` + unzip the two archives.
"""
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
DEST_BASE = Path(r"C:\Users\Shreyas.1Gupta\ShreyasIonicAMC_BACKUP")
stamp = datetime.now().strftime("%Y%m%d_%H%M")
dest = DEST_BASE / stamp
dest.mkdir(parents=True, exist_ok=True)

# 1. git bundle (full history)
r = subprocess.run(["git", "bundle", "create", str(dest / "git_full.bundle"), "--all"],
                   cwd=str(ROOT), capture_output=True, text=True)
print("git bundle:", "OK" if r.returncode == 0 else r.stderr[:200])

# 2. firm tree zip
def zip_tree(zf, base: Path, arc_prefix: str, exclude_dirs=()):
    for f in base.rglob("*"):
        if f.is_file() and not any(part in exclude_dirs for part in f.parts):
            zf.write(f, arc_prefix + "/" + str(f.relative_to(base)))

with zipfile.ZipFile(dest / "firm_tree.zip", "w", zipfile.ZIP_DEFLATED) as zf:
    zip_tree(zf, ROOT / "Shreyas_Ionic_AMC", "Shreyas_Ionic_AMC", exclude_dirs=("__pycache__",))
    zip_tree(zf, ROOT / ".claude", ".claude", exclude_dirs=("__pycache__",))
    for name in ("CLAUDE.md", "RESUME_TOMORROW.md", "HANDOFF.md", ".gitignore"):
        f = ROOT / name
        if f.exists():
            zf.write(f, name)
print("firm_tree.zip:", (dest / "firm_tree.zip").stat().st_size // 1024, "KB")

# 3. critical data zip (small, high-value)
DATA = [
    "intraday_options_strategy/buying/rv_iv_vol.parquet",
    "intraday_options_strategy/buying/forward_factor_v2.parquet",
    "intraday_options_strategy/buying/stock_earnings_vol.parquet",
    "intraday_options_strategy/buying/shortlist_shortvol.parquet",
    "intraday_options_strategy/buying/portfolio_monthly_v2.parquet",
    "datasets/derived", "datasets/etf_gold_silver", "datasets/index_daily",
    "datasets/nifty_factor_indices", "datasets/nse_earnings_dates",
    "datasets/earnings_pit/unified_quarterly_pit.parquet",
    "NIFTY500_TICKER_2005_2025_Final.xlsx",
]
with zipfile.ZipFile(dest / "critical_data.zip", "w", zipfile.ZIP_DEFLATED) as zf:
    for rel in DATA:
        p = ROOT / rel
        if p.is_file():
            zf.write(p, rel)
        elif p.is_dir():
            zip_tree(zf, p, rel)
print("critical_data.zip:", (dest / "critical_data.zip").stat().st_size // (1024 * 1024), "MB")

# rotation: keep newest 5
backups = sorted([d for d in DEST_BASE.iterdir() if d.is_dir()])
for old in backups[:-5]:
    shutil.rmtree(old)
    print("rotated out:", old.name)
print(f"BACKUP COMPLETE -> {dest}")
