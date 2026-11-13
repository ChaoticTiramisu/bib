"""Centrale configuratie voor de bib-applicatie.

Waarden komen uit omgevingsvariabelen; een lokaal `.env`-bestand wordt
automatisch geladen. Zo staan er geen wachtwoorden of sleutels in de code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_DIR = BASE_DIR / "static" / "upload"

INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

# Standaard lokaal SQLite; zet DATABASE_URL voor PostgreSQL.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{INSTANCE_DIR / 'bib.db'}",
)

# Zet SECRET_KEY in .env voordat je de app echt online zet.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-verander-mij")

DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"
SQL_ECHO = os.environ.get("SQL_ECHO", "0") == "1"
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))

# Optionele API-key voor Google Books; zonder key geldt een lagere quota.
GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY", "")
ISBN_LOOKUP_TIMEOUT = float(os.environ.get("ISBN_LOOKUP_TIMEOUT", "8"))

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))
