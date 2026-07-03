"""Kaggle retry with truststore injected (corporate-proxy SSL fix).

Must inject truststore BEFORE kagglehub/requests are imported.
"""
from __future__ import annotations

import sys
from pathlib import Path

import truststore

truststore.inject_into_ssl()  # use Windows cert store → trusts corporate MITM CA

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.download_data import main  # noqa: E402

if __name__ == "__main__":
    main()
