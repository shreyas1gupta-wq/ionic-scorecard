"""Frontend static checks (no node on this machine):
- / and /app.js serve 200 through the real app's StaticFiles mount
- every element id referenced from app.js ($('id') / getElementById('id'))
  exists either in index.html or is created dynamically by app.js itself
  (id="..." inside a JS template literal).
ASCII-only (cp1252 console).
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

import app

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_static_served():
    with TestClient(app.app) as c:
        r = c.get("/")
        assert r.status_code == 200
        assert 'id="chart"' in r.text
        r = c.get("/app.js")
        assert r.status_code == 200
        assert "FnO Replay Game frontend" in r.text
        r = c.get("/lib/lightweight-charts.standalone.production.js")
        assert r.status_code == 200


def test_all_referenced_ids_exist():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    referenced = set(re.findall(r"\$\('([^']+)'\)", js))
    referenced |= set(re.findall(r"getElementById\('([^']+)'\)", js))
    static_ids = set(re.findall(r'id="([^"]+)"', html))
    # ids the JS itself injects via template literals / innerHTML strings
    dynamic_ids = set(re.findall(r'id="([^"]+)"', js))
    dynamic_ids |= set(re.findall(r"id='([^']+)'", js))

    orphans = referenced - static_ids - dynamic_ids
    assert not orphans, f"ids referenced but never defined: {sorted(orphans)}"


def test_no_real_dates_hardcoded_in_frontend():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    # fake-anchor epoch constants (94689....) are fine; real ISO dates are not
    assert not re.search(r"20[12]\d-\d\d-\d\d", js.replace("YYYY-MM-DD", ""))
