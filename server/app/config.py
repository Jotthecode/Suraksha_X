"""Settings, read from environment variables (see server/.env.example)."""

import os
import secrets

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(SERVER_DIR, "models")
DATA_DIR = os.path.join(SERVER_DIR, "data")


def _load_dotenv():
    """Minimal .env loader for local runs; real environment variables always win."""
    path = os.path.join(SERVER_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _database_url():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///" + os.path.join(SERVER_DIR, "surakshax.db")
    # Render / Heroku hand out postgres:// URLs; SQLAlchemy + psycopg 3 needs postgresql+psycopg://
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = _database_url()

# Signs login tokens. Must be set in production, otherwise every restart logs everyone out.
JWT_SECRET = os.environ.get("JWT_SECRET") or secrets.token_hex(32)
JWT_SECRET_IS_EPHEMERAL = "JWT_SECRET" not in os.environ
TOKEN_TTL_DAYS = int(os.environ.get("TOKEN_TTL_DAYS", "180"))

# Police / admin incident dashboard (HTTP Basic). Dashboard is disabled while unset.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

# Optional: server-side SMS + voice call through Twilio
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")
TWILIO_ENABLED = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER)

# Limits server-side SOS sends per user, so a stolen token cannot run up a Twilio bill
SOS_MAX_PER_WINDOW = int(os.environ.get("SOS_MAX_PER_WINDOW", "5"))
SOS_WINDOW_MINUTES = int(os.environ.get("SOS_WINDOW_MINUTES", "10"))

TRACKING_TTL_HOURS = float(os.environ.get("TRACKING_TTL_HOURS", "2"))

# Comma-separated list of allowed browser origins; the Android app is not affected by CORS
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]

# Public base URL used in tracking links (e.g. https://surakshax-api.onrender.com).
# Falls back to the URL of the incoming request.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

APP_VERSION = "3.0.0"
