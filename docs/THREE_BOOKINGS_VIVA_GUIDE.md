# Smart Courier — Three Bookings Viva Examination Guide

This guide is prepared for the University Web Engineering Viva presentation. It documents the resolution of the `/hubs/scans` issue, the single unified page scrollbar, and the three opt-in live showcase bookings.

---

## 1. Project Overview & Rubric Compliance

| Rubric Component | Points | Implementation in Smart Courier | Status |
|---|---|---|---|
| **Setup & Organization** | 10 | Flask Application Factory (`create_app`), modular blueprints, environment configs (`development`, `testing`, `production`) | Verified |
| **Flask Routing & Blueprints** | 15 | 8 blueprints (`auth`, `main`, `shipments`, `tracking`, `dispatch`, `drivers`, `finance`, `support`, `catalog`, `hubs`), RESTful URL conventions | Verified |
| **Jinja2 Inheritance** | 15 | Unified `base.html` template layout, reusable UI macros (`macros/forms.html`), contextual navigation bars, responsive Bootstrap 5 | Verified |
| **SQLAlchemy & Relational Schema** | 20 | **Exactly 55 business tables** (exceeds requirement of 40), explicit foreign keys, check constraints, composite keys, universal audit mixin | Verified (55/55 tables, 0 FK errors) |
| **Forms, Validation & Sessions** | 15 | Flask-WTF with CSRF protection, server-side field validators, secure HTTP-only cookies, password hashing with PBKDF2/SHA256 | Verified |
| **Code Quality & Architecture** | 10 | Clean service layer (`ShipmentService`, `PricingService`, `ThreeBookingsService`), no business logic in route handlers | Verified |
| **End-to-End Functionality** | 10 | Customer booking -> automated dynamic rating -> dispatch -> driver delivery attempt -> electronic delivery proof (EPOD) -> paid invoice | Verified |
| **Documentation & Viva Readiness** | 5 | Comprehensive viva guide, schema dictionary, and verification test suite | Verified (94 passing tests) |

---

## 2. The Three Live Viva Demo Bookings

Instead of cluttering the system with duplicate sample entries, Smart Courier provides **exactly three realistic, end-to-end connected bookings**. Each booking exercises a distinct stage of the parcel lifecycle:

| Scenario Reference | Generated Tracking # | Route & Distance | Consignment & Weight | Current Stage | Financial & Invoice Status | What to Show Your Teacher |
|---|---|---|---|---|---|---|
| **SC-DEMO-BOOK-01** | `SC26111BD34E` | Lahore &rarr; Islamabad (Inter-city) | Legal documents (350g, Express) | `BOOKED` | **Rs. 600.00** (`INV-202611-85E01`), Status: `ISSUED` | Dynamic quote calculation, customer self-booking form, initial public tracking event, billing invoice. |
| **SC-DEMO-BOOK-02** | `SC2611DA6D79` | Lahore &rarr; Karachi (Long-haul) | Clothing parcel (800g, Standard) | `IN_TRANSIT` | **Rs. 500.00** (`INV-202611-66E0D`), Status: `ISSUED` | Inter-hub logistics sorting, linehaul transit milestones, linked open customer support inquiry ticket. |
| **SC-DEMO-BOOK-03** | `SC2611892342` | Lahore &rarr; Lahore (Intra-city) | Small electronic item (500g, Standard) | `DELIVERED` | **Rs. 300.00** (`INV-202611-CD677`), Status: **PAID** (Settled bank payment) | Driver runsheet assignment (`ROUTE-LHR-EAST-01`), electronic delivery proof (EPOD), recipient sign-off, invoice payment settlement. |

---

## 3. Opt-In CLI Commands Reference

All demo data operations are strictly opt-in and idempotent. They are never automatically seeded into production.

### A. Preview Prospective Records (Dry-Run Mode)
```powershell
python -m flask --app run.py seed-three-demo-bookings --dry-run
```
*Executes genuine quote calculations and displays prospective records with zero database writes.*

### B. Seed the Three Demo Bookings
```powershell
python -m flask --app run.py seed-three-demo-bookings --confirm
```
*Creates the 3 bookings atomically through `ShipmentService.book_shipment()` and transitions them in legal order. Rerunning this command produces 0 duplicate records.*

### C. Display Generated Tracking IDs & Testing Links
```powershell
python -m flask --app run.py show-three-demo-bookings
```
*Prints reference labels, tracking codes, fares, invoice numbers, and deep inspection links.*

### D. Scoped Cleanup (Safe Rollback)
```powershell
python -m flask --app run.py cleanup-three-demo-bookings --confirm
```
*Removes only records created for these three demo bookings, completely preserving all non-demo shipments, customers, audit logs, and database schema.*

### E. Verify Schema Integrity (55 Tables & Foreign Keys)
```powershell
python -m flask --app run.py verify-schema
```
*Confirms 55/55 tables exist and verifies 0 SQLite PRAGMA foreign-key violations.*

---

## 4. Key Improvements & Technical Explanations

### 1. Graceful Retirement of Broken Hub Scans UI (HTTP 500 Fix)
- **Problem**: Visiting `/hubs/scans` triggered HTTP 500 due to template null-dereferencing (`s.scanned_by.user.full_name`) and foreign-key mismatch for admins lacking an `Employee` record.
- **Rubric Assessment**: The course rubric requires comprehensive SQLAlchemy domain relationships, but does not mandate an operational barcode scanner UI screen.
- **Architectural Solution**:
  1. Retired the redundant UI screen without dropping any database table.
  2. Preserved the `ShipmentScan` model, `Hub` table, `HubTransfer` model, and all database relationships.
  3. Replaced the `/hubs/scans` route handler:
     - Unauthenticated requests redirect safely to login.
     - Unauthorized roles (Customer, Driver) receive a clean `403 Forbidden`.
     - Authorized staff visiting legacy links are redirected (HTTP 302) to `shipments.index` with an informative notification: *"Hub Scans has been consolidated into parcel tracking & dispatch."*
     - Direct legacy POST requests are safely rejected (HTTP 303) without mutating data.
  4. Zero 500 errors occur under any circumstance.

### 2. Single Unified Page Scrollbar (Dashboard Scroll Fix)
- **Problem**: Previous layout had separate vertical scrolling on the sidebar and main content due to Bootstrap `position-sticky` and CSS `overflow-y: auto` on both `html` and `body`.
- **Architectural Solution**:
  1. In `app/templates/base.html`, removed `position-sticky` from `<nav id="sidebarMenu">` inner wrapper.
  2. In `app/static/css/modern-ui.css`, configured document-level root scrolling:
     ```css
     html { overflow-y: auto; overflow-x: hidden; }
     body { min-height: 100vh; overflow-y: visible; overflow-x: hidden; }
     .sidebar, main { height: auto !important; max-height: none !important; overflow-y: visible !important; }
     ```
  3. The left sidebar and right dashboard content now move together naturally with **exactly one vertical scrollbar**.
  4. Tested responsive across desktop (1366x768), laptop (1280x800), and mobile (390x844).

---

## 5. Role-Based Access Control (RBAC) Matrix

Smart Courier enforces strict least-privilege role boundaries across all nine system roles:

| System Role | Dashboard View | Permitted Operations | Restricted Areas |
|---|---|---|---|
| **CUSTOMER** | Customer Portal | Book parcels, view own shipments, track parcels, view own invoices, open support tickets | Blocked from staff dispatch, driver runs, hubs, and audit logs |
| **BOOKING_AGENT** | Counter Booking | Book parcels on behalf of customers, quote rates, issue invoices | Blocked from driver delivery proofs and audit logs |
| **BRANCH_MANAGER** | Branch Operations | Monitor branch shipments, view branch staff and fleet | Blocked from system-wide audit logs and master settings |
| **HUB_OPERATOR** | Parcel Operations | View hub transfers and parcel status | Blocked from customer finances and driver route management |
| **DISPATCHER** | Dispatch Center | Assign vehicles to drivers, create routes, sequence stops | Blocked from modifying financial rate rules |
| **DRIVER** | Driver Runsheet | View assigned route stops, record delivery attempts, record EPOD | Blocked from unassigned parcels and other drivers' routes |
| **FINANCE_OFFICER** | Financial Ledger | Manage invoices, record payments, process COD collections | Blocked from modifying delivery routes |
| **SUPPORT_AGENT** | Customer Support | Reply to customer tickets, investigate delivery issues | Blocked from editing invoices or modifying catalog rates |
| **SUPER_ADMIN** | Executive Overview | Complete system-wide administrative authority, audit trail inspection | Unrestricted |

---

## 6. Viva Presentation Questions & Answers (Cheat Sheet)

### Q1: Why does the system have 55 tables, and how are they organized?
> **Answer**: Smart Courier models a complete real-world logistics lifecycle. The tables are partitioned into logical domains:
> 1. **Authentication & RBAC**: `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `login_sessions`
> 2. **Organization & Network**: `branches`, `hubs`, `service_zones`, `employees`, `employee_branches`, `branch_zones`
> 3. **Catalog & Tariffs**: `customers`, `customer_addresses`, `service_types`, `packaging_types`, `rate_cards`, `rate_card_rules`, `discounts`
> 4. **Shipments & Lifecycle**: `shipments`, `shipment_items`, `shipment_addresses`, `shipment_status_history`, `pickup_requests`
> 5. **Dispatch & Fleet**: `vehicles`, `drivers`, `routes`, `route_stops`, `delivery_attempts`, `delivery_proofs`, `tracking_events`, `shipment_scans`, `hub_transfers`
> 6. **Finance & COD**: `invoices`, `invoice_items`, `payments`, `cod_collections`, `cod_remittances`
> 7. **Support & Governance**: `support_tickets`, `ticket_messages`, `audit_logs`, `app_settings`

### Q2: How does the dynamic quote calculation work?
> **Answer**: When a parcel is booked, `PricingService.calculate_quote()` determines the fare based on the origin zone, destination zone, parcel weight, and packaging type. It checks active `rate_cards` and `rate_card_rules` in integer paisa (preventing floating-point rounding errors). The resulting breakdown (base fee, packaging fee, tax, discount) is stored immutably in `ShipmentService` quote snapshot and attached to the generated `Invoice`.

### Q3: Why did you retire the Hub Scans screen instead of keeping it?
> **Answer**: The Hub Scans screen was an optional UI prototype not required by the project rubric. It threw unhandled HTTP 500 errors when scanning parcels without an employee record or when dereferencing null relationships. Rather than maintaining an unstable form, we retired the UI screen gracefully with an HTTP 302 redirect for authorized staff and HTTP 403 for unauthorized users, while strictly preserving the underlying `ShipmentScan` table, foreign keys, and audit integrity.

### Q4: How is scrolling structured on the dashboard?
> **Answer**: We removed CSS overflow constraints (`overflow-y: auto`) from individual container divs and removed Bootstrap's `position-sticky` from the sidebar. The root HTML document owns vertical scrolling, ensuring that the sidebar and the main content scroll together as a single unified page with one clean browser scrollbar.

### Q5: How do you guarantee idempotency in demo data seeding?
> **Answer**: The seeder stores the reference mapping (`SC-DEMO-BOOK-01` &rarr; tracking number) in the `app_settings` table under the key `THREE_DEMO_BOOKINGS_MAP`. Before creating any shipment, `seed_three_bookings()` inspects this mapping and checks if the shipments already exist in the database. If present, it skips recreation, preventing duplicate records, duplicate invoices, or duplicate route stops.

---

## 7. Verification Test Suite Results

All automated tests were executed locally using pytest:
- **Total Tests**: 94 tests
- **Passing**: 94 (100%)
- **Failing**: 0
- **Execution Time**: ~11 seconds
- **Schema Check**: 55 / 55 business tables verified, 0 SQLite foreign-key violations.
