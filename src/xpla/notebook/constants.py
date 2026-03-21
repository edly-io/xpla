from pathlib import Path

CURRENT_DIR = Path(__file__).parent
STATIC_DIR = CURRENT_DIR.parent / "static"
SAMPLES_DIR = CURRENT_DIR.parent.parent.parent / "samples"
SAMPLE_ACTIVITIES = [
    "chat",
    "collab-editor",
    "interactive-video",
    # "markdown",
    "math",
    "mcq",
    "python",
    "quiz",
    "slideshow",
    "video",
    "youtube",
    "zoom",
]
DIST_DIR = CURRENT_DIR.parent.parent.parent / "dist"
if not DIST_DIR.exists():
    DIST_DIR.mkdir()

ACTIVITIES_DIR = DIST_DIR / "xpln" / "activities"

FRONTEND_DIR = CURRENT_DIR / "frontend" / "out"

DB_PATH = DIST_DIR / "xpln.db"
