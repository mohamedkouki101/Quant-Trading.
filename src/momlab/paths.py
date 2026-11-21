"""Repository paths used by the data layer and scripts.

``MOMLAB_DATA_DIR`` overrides the data folder (tests use a temporary folder instead).
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]
DATA_DIR: Path = Path(os.environ.get("MOMLAB_DATA_DIR", ROOT / "data"))
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
MANIFEST: Path = DATA_DIR / "manifest.json"
REPORTS_DIR: Path = ROOT / "reports"
