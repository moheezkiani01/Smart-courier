import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def normalize_database_url(url: str | None) -> str | None:
    """Normalize PostgreSQL database URL for SQLAlchemy 2.0 + psycopg3 compatibility."""
    if not url:
        return url
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "smart-courier-dev-secret-key-3.10")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY", "PKR")
    SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "AdminPass@1234")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # Viva Demonstration Settings (Disabled by default)
    VIVA_LOGIN_PICKER_ENABLED = os.environ.get("VIVA_LOGIN_PICKER_ENABLED", "false").lower() in ("true", "1", "yes")
    VIVA_LOGIN_ACCOUNTS_JSON = os.environ.get("VIVA_LOGIN_ACCOUNTS_JSON", "")


class DevelopmentConfig(Config):
    DEBUG = True
    # Instance-relative database
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.environ.get("DATABASE_URL")) or (
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'courier.sqlite3')}"
    )

class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.environ.get("DATABASE_URL", ""))
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
