import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "agent_fleet.db"))

# Workspace target
# Inside docker, this defaults to /workspace. Locally, defaults to ./sandbox
TARGET_WORKSPACE = Path(os.getenv("TARGET_WORKSPACE", str(BASE_DIR / "sandbox")))
TARGET_WORKSPACE.mkdir(exist_ok=True, parents=True)

# Project Mode (Existing codebase vs Brand-new project)
IS_EXISTING_PROJECT = os.getenv("IS_EXISTING_PROJECT", "true").lower() in ("true", "1", "yes")

# Persistent Architecture Memory Cache (avoids repeating token-heavy codebase scans)
PROJECT_MEMORY_FILE = DATA_DIR / "codebase_understanding.json"

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# Watchdog thresholds
MAX_TASK_RETRY_COUNT = int(os.getenv("MAX_TASK_RETRY_COUNT", "3"))
HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "120"))
