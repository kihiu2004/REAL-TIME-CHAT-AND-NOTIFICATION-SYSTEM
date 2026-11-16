"""Compatibility shim - do not add settings here.

The real configuration lives in ConnectHub/app/config.py. This file only exists
so that anything still pointing at the project root (a VS Code debug tab, a
launch config, `python config.py` from the root) keeps working.
"""

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent / "ConnectHub"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app.config import BASE_DIR, Settings, settings  # noqa: E402,F401


if __name__ == "__main__":
    print(f"{settings.APP_NAME} {settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    print(f"env file : {BASE_DIR / '.env'}")
    print(f"database : {settings.DATABASE_URL}")
