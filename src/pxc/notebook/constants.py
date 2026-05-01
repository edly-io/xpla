import os
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
STATIC_DIR = CURRENT_DIR.parent / "static"
SAMPLES_DIR = CURRENT_DIR.parent.parent.parent / "samples"
DIST_DIR = CURRENT_DIR.parent.parent.parent / "dist"
if not DIST_DIR.exists():
    DIST_DIR.mkdir()

ACTIVITIES_DIR = DIST_DIR / "notebook" / "activities"
COURSE_ACTIVITIES_DIR = DIST_DIR / "notebook" / "course_activities"
COURSE_ACTIVITY_SAMPLES_DIR = CURRENT_DIR / "samples" / "courseactivities"

FRONTEND_DIR = CURRENT_DIR / "frontend" / "out"

DB_PATH = DIST_DIR / "notebook.db"

# LTI 1.3
LTI_KEY_PATH = DIST_DIR / "notebook" / "lti" / "private.pem"
LTI_BASE_URL = os.environ.get("NOTEBOOK_LTI_BASE_URL", "http://127.0.0.1:9753/lti")
