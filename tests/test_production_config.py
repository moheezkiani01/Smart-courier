import os
import pytest
from app.config import normalize_database_url
from app import create_app

def test_normalize_database_url():
    """Verify PostgreSQL URL normalizer converts postgres:// and postgresql:// to postgresql+psycopg://."""
    assert normalize_database_url(None) is None
    assert normalize_database_url("") == ""
    assert normalize_database_url("sqlite:///instance/courier.sqlite3") == "sqlite:///instance/courier.sqlite3"
    
    # Standard Render / Supabase prefixes
    render_url = "postgres://user:pass@ep-cool-fog.render.com/db"
    assert normalize_database_url(render_url) == "postgresql+psycopg://user:pass@ep-cool-fog.render.com/db"
    
    pg_url = "postgresql://user:pass@db.supabase.co:5432/postgres"
    assert normalize_database_url(pg_url) == "postgresql+psycopg://user:pass@db.supabase.co:5432/postgres"
    
    # Already explicit psycopg3 prefix
    psycopg_url = "postgresql+psycopg://user:pass@db.supabase.co:5432/postgres"
    assert normalize_database_url(psycopg_url) == "postgresql+psycopg://user:pass@db.supabase.co:5432/postgres"

def test_production_fails_without_database_url(monkeypatch):
    """Verify production fails fast if DATABASE_URL is missing or uses SQLite."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SECRET_KEY", "super-secret-production-key-xyz-123456789")
    
    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")
    assert "DATABASE_URL" in str(exc_info.value)
    assert "ephemeral" in str(exc_info.value).lower()

def test_production_fails_with_sqlite_url(monkeypatch):
    """Verify production fails fast if DATABASE_URL attempts to point to SQLite."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///instance/courier.sqlite3")
    monkeypatch.setenv("SECRET_KEY", "super-secret-production-key-xyz-123456789")
    
    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")
    assert "DATABASE_URL" in str(exc_info.value)

def test_production_fails_without_secret_key(monkeypatch):
    """Verify production fails fast if SECRET_KEY is missing or uses the dev default."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@host:5432/db")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    
    with pytest.raises(RuntimeError) as exc_info:
        create_app("production")
    assert "SECRET_KEY" in str(exc_info.value)

def test_healthz_endpoint(client):
    """Verify /healthz returns 200 with service metadata when healthy."""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "smart-courier"
