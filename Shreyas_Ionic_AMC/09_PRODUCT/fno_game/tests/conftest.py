"""Pytest bootstrap: make server/ importable. ASCII-only (cp1252 console)."""
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))
