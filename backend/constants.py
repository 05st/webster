import os

FRONTEND_URL = os.getenv("FRONTEND_URL")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///webster.db")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
SESSION_COOKIE_NAME = "webster_auth"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(60 * 60 * 24)))
FRONTEND_ORIGIN = FRONTEND_URL.rstrip("/") if FRONTEND_URL else ""
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
BACKEND_URL = os.getenv("BACKEND_URL", "").rstrip("/")
GITHUB_APP_SLUG = os.getenv("GITHUB_APP_SLUG", "")
