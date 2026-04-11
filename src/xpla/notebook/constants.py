from pathlib import Path

CURRENT_DIR = Path(__file__).parent
STATIC_DIR = CURRENT_DIR.parent / "static"
SAMPLES_DIR = CURRENT_DIR.parent.parent.parent / "samples"
DIST_DIR = CURRENT_DIR.parent.parent.parent / "dist"
if not DIST_DIR.exists():
    DIST_DIR.mkdir()

ACTIVITIES_DIR = DIST_DIR / "xpln" / "activities"
COURSE_ACTIVITIES_DIR = DIST_DIR / "xpln" / "course_activities"
COURSE_ACTIVITY_SAMPLES_DIR = CURRENT_DIR / "samples" / "courseactivities"

FRONTEND_DIR = CURRENT_DIR / "frontend" / "out"

DB_PATH = DIST_DIR / "xpln.db"
