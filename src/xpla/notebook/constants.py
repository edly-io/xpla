from pathlib import Path

CURRENT_DIR = Path(__file__).parent
STATIC_DIR = CURRENT_DIR.parent / "static"
SAMPLES_DIR = CURRENT_DIR.parent.parent.parent / "samples"
DIST_DIR = CURRENT_DIR.parent.parent.parent / "dist"
if not DIST_DIR.exists():
    DIST_DIR.mkdir()

ACTIVITIES_DIR = DIST_DIR / "xpln" / "activities"

DB_PATH = DIST_DIR / "xpln.db"
