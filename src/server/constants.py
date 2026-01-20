from pathlib import Path

CURRENT_DIR = Path(__file__).parent
STATIC_DIR = CURRENT_DIR / "static"
SAMPLES_DIR = CURRENT_DIR.parent.parent / "samples"
TEMPLATES_DIR = CURRENT_DIR / "templates"

DIST_DIR = CURRENT_DIR.parent.parent / "dist"
if not DIST_DIR.exists():
    DIST_DIR.mkdir()
