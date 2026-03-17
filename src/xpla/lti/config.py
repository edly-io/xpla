"""Configuration for the xPLA LTI app."""

import os
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
TEMPLATES_DIR = CURRENT_DIR / "templates"
STATIC_DIR = CURRENT_DIR.parent / "static"
SAMPLES_DIR = CURRENT_DIR.parent.parent.parent / "samples"

DATA_DIR = CURRENT_DIR.parent.parent.parent / "dist" / "lti"
DB_PATH = DATA_DIR / "lti.db"
KEY_PATH = DATA_DIR / "private.pem"

BASE_URL = os.environ.get("LTI_BASE_URL", "http://127.0.0.1:9754")
