import os
import sys
from pathlib import Path

# Add project root to Python search path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Ensure VERCEL environment is recognized for /tmp database path
os.environ["VERCEL"] = "1"

from seed import seed_database
from app.main import app

# On Vercel serverless cold start, auto-seed /tmp/opsdesk.db if it does not exist
tmp_db = Path("/tmp/opsdesk.db")
if not tmp_db.exists():
    try:
        seed_database()
    except Exception as e:
        print(f"Vercel auto-seed notice: {e}")
