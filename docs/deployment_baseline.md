# Smart Courier — Production Deployment Baseline Report

**Date:** November 6, 2026  
**Environment:** Windows local workstation (`C:\Users\hp\Desktop\SMART_COURIER`)  
**Target Git Remote:** `https://github.com/moheezkiani01/Smart-courier.git` (`main`)  
**Deployment Target:** Render Python Web Service (Free Tier)  
**Production Database:** External Persistent PostgreSQL (e.g. Supabase Free Postgres)  

---

## 1. Executive Summary

This report establishes the verified baseline of the **Smart Courier & Parcel Delivery Management System** prior to GitHub deployment and Render production release. The application contains 55 relational business models, complete role-based access controls for 9 roles, customer parcel booking workflows, inter-hub freight scans, driver runsheet execution, and financial invoicing.

All tests have been executed natively against Python 3.10.11 and SQLite. Zero tests failed.

---

## 2. Environment & Tooling Verification

| Component | Verified Version / State | Notes |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 Enterprise | Production target: Ubuntu Linux container on Render |
| **Python** | 3.10.11 (`.venv\Scripts\python.exe`) | Compatible with Render Linux Python 3.10/3.11 runtimes |
| **Flask** | 3.0.3 | Application factory pattern (`create_app`) |
| **Flask-SQLAlchemy** | 3.1.1 | SQLAlchemy 2.0 ORM with 55 declarative models |
| **Flask-Migrate** | 4.0.7 | Alembic migrations with dialect-agnostic DDL |
| **WSGI Server** | Gunicorn 26.2.0 | Multi-worker POSIX production server configured |
| **PostgreSQL Driver** | `psycopg` (binary) 3.3.8 | Compatible with Supabase and Render PostgreSQL |
| **Git Tooling** | Git 2.55.0.windows.3 | Clean workspace, ready for branch tracking |

---

## 3. Database Schema Verification

A comprehensive schema verification was conducted using `scripts/verify_schema.py`:

```text
======================================================================
SMART COURIER — SCHEMA VERIFICATION
======================================================================
[*] SQLite PRAGMA foreign_keys: 1 (Expected: 1)
[*] SQLite PRAGMA foreign_key_check violations: 0
[*] Database Business Tables Found: 55 / 55
[+] All 55 business tables verified successfully with all audit columns!
======================================================================
```

### Table Count & Universal Audit Columns
- **Total Business Tables:** 55
- **Universal Audit Columns on every model:**
  - `id`: Integer Primary Key (Autoincrement)
  - `is_deleted`: Boolean (Soft delete flag, default `False`)
  - `created_at`: DateTime (UTC timestamp)
  - `created_by`: Integer ForeignKey (`users.id`, nullable)
  - `updated_at`: DateTime (UTC timestamp, auto-updated)
  - `updated_by`: Integer ForeignKey (`users.id`, nullable)
  - `status`: String(20) (`ACTIVE`, `DEACTIVE`, `PENDING`)
  - `deleted_at`: DateTime (Nullable timestamp)
  - `deleted_by`: Integer ForeignKey (`users.id`, nullable)
- **Local Foreign Key Pragma:** `PRAGMA foreign_keys = ON` strictly enabled via SQLAlchemy connection listener with dialect guard for PostgreSQL portability.

---

## 4. Test Suite Execution Baseline

```text
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\hp\Desktop\SMART_COURIER
configfile: pytest.ini
testpaths: tests
plugins: flask-1.3.0
collected 66 items

tests/test_all_roles_dashboards.py ................ [ 6%]
tests/test_audit_fixes_regression.py .............. [26%]
tests/test_auth_rbac.py ........................... [34%]
tests/test_booking_pricing.py ..................... [37%]
tests/test_constraints.py ......................... [44%]
tests/test_customer_booking_and_journey.py ........ [68%]
tests/test_customers_catalog.py ................... [75%]
tests/test_end_to_end.py .......................... [77%]
tests/test_finance_cod.py ......................... [81%]
tests/test_forms_sessions.py ...................... [86%]
tests/test_models.py .............................. [91%]
tests/test_production_config.py ................... [92%]
tests/test_support_audit.py ....................... [95%]
tests/test_tracking_dispatch.py ................... [100%]

============================= 66 passed in 6.70s ==============================
```

---

## 5. Deployment Architecture Strategy

### Local Development (Preserved)
- **Database:** SQLite (`instance/courier.sqlite3`)
- **Launching:** Double-click `run.bat` or run `install_dependencies.bat`
- **Environment:** `DevelopmentConfig` (`DEBUG = True`, local database URI)

### Render Live Production
- **Runtime:** Python 3 on Render Free Web Service
- **WSGI Entrypoint:** `wsgi.py` (`create_app('production')`)
- **Process Manager:** Gunicorn with 2 workers, 4 threads, port `${PORT:-10000}`
- **Database:** External persistent PostgreSQL via `DATABASE_URL` (`postgresql+psycopg://...`)
- **Storage Strategy:** Render Free filesystem is ephemeral; state must reside in PostgreSQL.
- **Reverse Proxy:** `ProxyFix` middleware mounted with `x_for=1, x_proto=1, x_host=1, x_prefix=1`.
- **Health Endpoint:** `/healthz` returning HTTP 200 on healthy database connection, HTTP 503 on failure.

---

## 6. Pre-Flight Secret & Git Safety Audit

- `.gitignore` configured to exclude `.venv/`, `venv/`, `instance/`, `*.sqlite3`, `*.db`, `.env`, `.env.*`, `uploads/`, `*.log`, `__pycache__/`, `.pytest_cache/`.
- Safe `.env.example` created with variable names and blank placeholders only.
- Confirmed zero hardcoded passwords or session secrets staged for Git tracking.
