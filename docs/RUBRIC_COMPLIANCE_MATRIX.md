# Web Engineering Flask Project Rubric Compliance Matrix

**Course:** Web Engineering (CSE601330)  
**Standard:** `Flask_Project_Rubric.pdf` (100 Marks Evaluation Framework)  
**Project:** Smart Courier & Parcel Delivery Management System  
**Notice:** *This matrix documents objective evidence for each academic evaluation criterion. Antigravity does not guarantee or self-award external grades.*

---

## 1. Compliance Evidence Overview

| Evaluation Category | Max Points | Implementation Highlights | Verification Evidence |
|:---|:---:|:---|:---|
| **1. Project Setup & Structure** | 10 | Application Factory (`create_app`), isolated extensions, 10 modular blueprints, `.venv`, `.env` | [`app/__init__.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/__init__.py), [`app/extensions.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/extensions.py), [`run.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/run.py) |
| **2. Routing & View Functions** | 15 | GET/POST separated handlers, dynamic parameters (`<int:id>`), RESTful redirect patterns, RBAC decorators | 10 Blueprint route modules, [`app/security/rbac.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/security/rbac.py) |
| **3. Templates & Jinja2** | 15 | Master `base.html` inheritance, 28+ templates, status badge macros, form macros, printable label | [`app/templates/`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/), [`macros/badges.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/macros/badges.html) |
| **4. Database Integration & CRUD** | 20 | **55 relational SQLAlchemy business tables** (surpassing 40-table threshold), 3NF, universal audit columns, PRAGMA foreign_keys=1, 0 violations | [`app/models/`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/models/), [`scripts/verify_schema.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/scripts/verify_schema.py), [`docs/DATABASE_INTEGRITY_REPORT.md`](file:///C:/Users/hp/Desktop/SMART_COURIER/docs/DATABASE_INTEGRITY_REPORT.md) |
| **5. Forms, Validation & Sessions**| 15 | Flask-WTF CSRF protection, server-side field validators, PRG pattern, HttpOnly SameSite cookies | [`app/forms/`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/forms/), [`tests/test_forms_sessions.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/tests/test_forms_sessions.py) |
| **6. Code Quality & Organization** | 10 | Layered domain services architecture (`PricingService`, `ShipmentService`, `HubService`, `DispatchService`, `FinanceService`, `SupportService`), clean separation of concerns | [`app/services/`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/services/) |
| **7. Functionality & Testing** | 10 | 61 automated tests passing 100%, 0 failures, end-to-end lifecycle verification, 9-role dashboards | [`docs/FINAL_TEST_REPORT.md`](file:///C:/Users/hp/Desktop/SMART_COURIER/docs/FINAL_TEST_REPORT.md) (61/61 Passed) |
| **8. Documentation & Portability** | 5 | One-click Windows batch scripts (`install_dependencies.bat`, `run.bat`), ERD, schema docs, viva guide | [`README.md`](file:///C:/Users/hp/Desktop/SMART_COURIER/README.md), [`docs/`](file:///C:/Users/hp/Desktop/SMART_COURIER/docs/) |
| **TOTAL** | **100** | **Comprehensive Full-Stack Compliance Across All Dimensions** | |

---

## 2. Detailed Category Analysis

### Category 1: Project Setup & Structure (10 Points)
- **Application Factory:** Implemented via `create_app(config_name=None)` in [`app/__init__.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/__init__.py). Reads configurations (`DevelopmentConfig`, `TestingConfig`, `ProductionConfig`) from [`config.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/config.py).
- **Extension Isolation:** Database, login manager, migrate, and CSRF protection are declared unattached in [`app/extensions.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/extensions.py) to prevent cyclic imports.
- **Blueprint Modularity:** 10 domain blueprints registered (`main`, `auth`, `admin`, `customers`, `catalog`, `shipments`, `hubs`, `dispatch`, `drivers`, `finance`, `support`, `tracking`).
- **Dependencies & Environment:** Pinned dependencies in `requirements.txt`, documented `.env.example`, and isolated `.venv`.

### Category 2: Routing & View Functions (15 Points)
- **HTTP Methods:** Clean separation between `GET` display and `POST` mutations.
- **Dynamic Routing:** Resource views parameterized by entity IDs (`/shipments/<int:shipment_id>`, `/customers/<int:customer_id>`).
- **Access Control:** Secured via custom `@roles_required(...)` and `@permission_required(...)` decorators in [`app/security/rbac.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/security/rbac.py). Direct URL tampering returns HTTP 403 Forbidden.
- **PRG Pattern:** All successful mutations redirect using `redirect(url_for(...))` with flash messages.

### Category 3: Templates & Jinja2 (15 Points)
- **Layout Inheritance:** Consistent responsive Bootstrap 5 master template in [`app/templates/base.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/base.html).
- **Component Reusability:** Jinja2 macros in [`app/templates/macros/forms.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/macros/forms.html) and [`app/templates/macros/badges.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/macros/badges.html).
- **Context Processors:** Injects `caps` capability flags, `format_datetime`, and `paisa_to_pkr` helpers globally into every template.
- **Print Optimization:** Printable CSS media queries on shipping waybills ([`shipments/label.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/shipments/label.html)).

### Category 4: Database Integration & CRUD (20 Points)
- **Scale:** **55 relational SQLAlchemy business tables** interconnected through explicit primary and foreign keys.
- **Relational Integrity:** SQLite connection listener executes `PRAGMA foreign_keys = ON`. Automated scan `PRAGMA foreign_key_check;` returns 0 violations.
- **Universal Audit Trail:** 100% of tables inherit 9 audit fields via `AuditMixin` (`id`, `status`, `created_at`, `created_by`, `updated_at`, `updated_by`, `is_deleted`, `deleted_at`, `deleted_by`).
- **Soft Deletion:** Core records are soft-deleted (`is_deleted = True`) to maintain immutable historical logs.

### Category 5: Forms, Validation & Sessions (15 Points)
- **Server-Side Validation:** All forms inherit from `FlaskForm` with WTForms validators (`DataRequired`, `Email`, `Length`, `NumberRange`, `EqualTo`).
- **CSRF Protection:** Enabled globally via Flask-WTF `CSRFProtect(app)`. All POST forms include `{{ form.hidden_tag() }}`.
- **Session Security:** Session cookies enforce `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, and session expiration.
- **Error Feedback:** Inline field-level error messages (`invalid-feedback`) and flash alerts.

### Category 6: Code Quality & Organization (10 Points)
- **Domain Services:** Business logic decoupled from view routes into dedicated service classes:
  - `ShipmentService`: Consignment lifecycle, state machine transitions, address snapshots.
  - `PricingService`: Dynamic distance/zone and tiered weight calculation in integer paisa.
  - `HubService`: Sorting facility barcode scans and inter-hub freight transfers.
  - `DispatchService`: Vehicle delivery routes, stop sequencing, delivery attempts.
  - `FinanceService`: Invoicing, payments, refunds, COD collection reconciliation.
  - `SupportService`: Ticket threads, customer communication, internal note isolation.

### Category 7: Functionality & Testing (10 Points)
- **Test Suite:** 61 automated tests covering models, constraints, security, customer booking, and end-to-end flows.
- **Pass Rate:** **61 passed in 7.52s (100% Pass Rate, 0 Failures, 0 Warnings)**.
- **No Mocking/Faking:** All tests execute against real SQLite relational tables with real SQL queries and constraints.

### Category 8: Documentation & Portability (5 Points)
- **One-Click Batch Launchers:** Standalone `install_dependencies.bat` and `run.bat` scripts for Windows.
- **Comprehensive Documentation:** Full ERD (`docs/erd.md`), schema specification (`docs/schema.md`), user journeys (`docs/USER_JOURNEYS.md`), and viva guide (`docs/viva_guide.md`).
- **Demo Credentials:** Clear reference table in `README.md` for all 9 demo roles.
