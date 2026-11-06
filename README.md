# Smart Courier & Parcel Delivery Management System

A production-grade, local-first Flask web application for enterprise parcel booking, courier hub logistics, vehicle routing, driver delivery dispatch, automated rate calculation, invoicing, and customer support.

Developed for **Web Engineering (CSE601330)** according to the authoritative **Flask Project Rubric** and **Antigravity Complete Master Specification**.

---

## Key Highlights & Architectural Features

- **Relational Scope:** **Exactly 55 fully interconnected SQLAlchemy business tables** (surpassing the rubric requirement of 40).
- **Relational Integrity:** SQLite foreign key enforcement enabled on every connection via connection listener (`PRAGMA foreign_keys = ON`). Zero foreign key violations.
- **Universal Audit Trail & Lifecycle:** Every business table inherits 9 universal audit columns from `AuditMixin` (`id`, `is_deleted`, `created_at`, `created_by`, `updated_at`, `updated_by`, `status`, `deleted_at`, `deleted_by`).
- **Precision Money & Weight:** Monetary values stored as integer Paisa (1 PKR = 100 Paisa) to eliminate floating-point drift. Weights stored in integer grams.
- **9 Role-Based Access Control (RBAC):** SUPER_ADMIN, BRANCH_MANAGER, BOOKING_AGENT, HUB_OPERATOR, DISPATCHER, DRIVER, FINANCE_OFFICER, SUPPORT_AGENT, CUSTOMER.
- **Robust Security:** Werkzeug password hashing, Flask-WTF CSRF protection, Post/Redirect/Get pattern, secure sessions, input sanitization.
- **Jinja2 Design System:** Template inheritance, responsive Bootstrap 5 layout, status badge macros, form error rendering.
- **Comprehensive Testing:** Automated pytest test suite (**66 passed, 0 failures, 0 warnings, 100% pass rate**) covering models, constraints, RBAC, CRUD, pricing engine, defect regression tests, customer booking journeys, production security configuration, and end-to-end workflows.

---

## 55 Relational Database Tables Inventory

| Domain Group | Count | Tables |
|---|---|---|
| **A. Authentication & RBAC** | 6 | `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `login_sessions` |
| **B. Organization & Staff** | 6 | `branches`, `hubs`, `employees`, `employee_branches`, `service_zones`, `branch_zones` |
| **C. Customers & Catalog** | 10 | `customers`, `customer_contacts`, `customer_addresses`, `recipient_profiles`, `recipient_addresses`, `service_types`, `parcel_categories`, `packaging_types`, `rate_cards`, `rate_card_rules` |
| **D. Shipment Booking** | 8 | `shipments`, `shipment_items`, `shipment_addresses`, `shipment_services`, `shipment_documents`, `pickup_requests`, `pickup_assignments`, `shipment_status_history` |
| **E. Dispatch & Delivery** | 11 | `routes`, `route_stops`, `hub_transfers`, `shipment_scans`, `tracking_events`, `delivery_attempts`, `delivery_proofs`, `delivery_exceptions`, `vehicles`, `drivers`, `vehicle_assignments` |
| **F. Finance & Payments** | 8 | `invoices`, `invoice_items`, `payments`, `cod_collections`, `cod_remittances`, `refunds`, `discounts`, `shipment_discounts` |
| **G. Support & Auditing** | 6 | `support_tickets`, `ticket_messages`, `notifications`, `notification_templates`, `audit_logs`, `app_settings` |
| **Total Business Models** | **55** | **All 55 tables connected via explicit primary & foreign keys** |

---

## Production Cloud Deployment (Render & Persistent PostgreSQL)

The system is configured for cloud deployment on **Render's Free Web Service** backed by **persistent external PostgreSQL** (such as Supabase Free Postgres):

- **Repository:** `https://github.com/moheezkiani01/Smart-courier`
- **Branch:** `main`
- **WSGI Server:** Gunicorn multi-worker POSIX production server via `wsgi.py`
- **Launch Script:** `start.sh` (automatic Alembic migrations + Gunicorn startup)
- **Blueprint Config:** `render.yaml`
- **Health Check Path:** `/healthz`
- **Detailed Step-by-Step Guide:** See [Render & PostgreSQL Deployment Guide](docs/RENDER_DEPLOYMENT_GUIDE.md)

### Deployment Architecture & Data Persistence
- **Ephemeral Storage Guard:** Render Free web service container disks are ephemeral. All bookings, parcels, users, and audit records reside in external persistent PostgreSQL.
- **Dialect Portability:** Local development continues using SQLite (`instance/courier.sqlite3`), while production automatically utilizes PostgreSQL via `DATABASE_URL`.
- **Fail-Fast Security:** In production, the system strictly halts on startup if `DATABASE_URL` is missing or configured for SQLite, or if a development `SECRET_KEY` is detected.

### How to Make an Edit and Deploy Again
After your initial Render deployment is online:
1. Make your changes in your local workspace.
2. Run local tests: `python -m pytest -v` (ensure all 66 tests pass).
3. If database models were modified, create a migration: `flask --app wsgi.py db migrate -m "Description of changes"`.
4. Commit and push your verified code:
   ```bash
   git add <modified files>
   git commit -m "Your descriptive commit message"
   git push origin main
   ```
5. Render detects the push to `main` and automatically rebuilds, migrates, and redeploys the service without downtime or data loss.

---

## One-Click Setup & Launch (Windows)

The repository provides two automated, zero-configuration batch scripts designed for Windows evaluation:

### 1. One-Click Dependency Installer (`install_dependencies.bat`)
Double-click `install_dependencies.bat` or run from terminal:
```cmd
install_dependencies.bat
```
- Automatically detects Python 3.10+.
- Automatically provisions `.venv` in the project root if not already present.
- Activates `.venv` and installs/updates all dependencies from `requirements.txt`.
- Verifies core imports and creates `.env` from `.env.example`.
- Safely handles paths with spaces and keeps terminal open.

### 2. One-Click Application Launcher (`run.bat`)
Double-click `run.bat` or run from terminal:
```cmd
run.bat
```
- Automatically detects and verifies `.venv` and required libraries.
- Inspects SQLite database (`instance/courier.sqlite3`); safely applies pending migrations without overwriting existing data.
- Executes automated schema check confirming 55 relational business tables.
- Automatically launches your default web browser to `http://127.0.0.1:5000/`.
- Starts the Flask development server and keeps terminal open with live operational logs.

---

## Manual Setup & Development Workflow

### 1. Environment & Dependencies

#### Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

#### Linux / macOS (Bash):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Database Migration & Schema Verification
```bash
# Apply database schema
python -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"

# Run automated schema integrity verification
python scripts/verify_schema.py
```

### 3. Seed Demo Data
```bash
flask --app run.py seed-demo
```

### 4. Run Automated Test Suite
```bash
python -m pytest -v
```

### 5. Launch the Local Web Application
```bash
python run.py
```
Open your browser at `http://127.0.0.1:5000`.

---

## Default Seed Demo Accounts

| Role | Email | Password | Primary Scope |
|---|---|---|---|
| **Super Admin** | `admin@smartcourier.pk` | `AdminPass@1234` | Global System Access |
| **Branch Manager** | `lahore.manager@smartcourier.pk` | `AdminPass@1234` | Lahore Branch Operations |
| **Booking Agent** | `booking.lahore@smartcourier.pk` | `AdminPass@1234` | Lahore Booking Counter |
| **Hub Operator** | `hub.lahore@smartcourier.pk` | `AdminPass@1234` | Lahore Central Sorting Hub |
| **Dispatcher** | `dispatcher.lahore@smartcourier.pk` | `AdminPass@1234` | Route & Vehicle Dispatch |
| **Driver** | `driver1@smartcourier.pk` | `AdminPass@1234` | Vehicle Delivery & Run Sheet |
| **Finance Officer** | `finance@smartcourier.pk` | `AdminPass@1234` | Invoicing, Payments, COD |
| **Support Agent** | `support@smartcourier.pk` | `AdminPass@1234` | Customer Tickets & Inquiry |
| **Customer** | `customer@smartcourier.pk` | `AdminPass@1234` | Parcel Booking & Tracking |

---

## Project Documentation Directory

- [Render Cloud Deployment Guide](docs/RENDER_DEPLOYMENT_GUIDE.md)
- [Production Deployment Verification Report (66/66 Passed)](docs/DEPLOYMENT_VERIFICATION.md)
- [Deployment Baseline Report](docs/deployment_baseline.md)
- [Final Test Execution Report](docs/FINAL_TEST_REPORT.md)
- [Customer Booking Defect Remediation & Guided UX Report](docs/CUSTOMER_BOOKING_FIX_REPORT.md)
- [Role & Permission Matrix (9 Roles)](docs/ROLE_PERMISSION_MATRIX.md)
- [Action Audit Matrix (Exhaustive UI Controls Inventory)](docs/ACTION_AUDIT_MATRIX.md)
- [Operational User Journeys (8 Distinct Paths)](docs/USER_JOURNEYS.md)
- [Relational Database Schema & Integrity Report](docs/DATABASE_INTEGRITY_REPORT.md)
- [Rubric Compliance Matrix (100 Marks Standard)](docs/RUBRIC_COMPLIANCE_MATRIX.md)
- [Defects Changelog & Remediation Log](docs/CHANGELOG_FIXES.md)
- [Pre-Fix Defect Inventory & Reproductions (A01–A24)](docs/pre_fix_audit.md)
- [Complete ERD (Mermaid)](docs/erd.md)
- [Detailed Database Schema Specification](docs/schema.md)
- [Operational Workflows & Lifecycle State Machines](docs/workflows.md)
- [Viva Voce Examination Guide](docs/viva_guide.md)

---

## Academic Demonstration & Real Service Scope

- **Local-First Architecture:** Designed for local evaluation using Python, Flask, and persistent SQLite (`instance/courier.sqlite3`).
- **Original Smart Courier Identity:** Workflows are inspired by the operational ease and step-by-step clarity of courier platforms (such as TCS parcel booking and Daraz tracking) without using any proprietary assets, logos, copyrighted material, or brand affiliations.
- **Simulated External Integrations:** In accordance with academic scope, live third-party bank payment gateways, real-time vehicle GPS satellite tracking, and commercial SMS/WhatsApp gateways are simulated through local event logs and database records. All pricing and billing math operates in integer paisa (1 PKR = 100 paisa) to eliminate floating-point rounding errors.
