# Pre-Fix Audit & Defect Reproduction Report

**Project:** Smart Courier & Parcel Delivery Management System  
**Date:** November 6, 2026  
**Auditor:** Senior Flask Developer, Security Reviewer & Relational Architect  
**Authority:** Master Instruction & `Flask_Project_Rubric.pdf`

---

## 1. Executive Summary

A comprehensive pre-fix audit was conducted against the running codebase and templates to reproduce the reported issues:
1. Users across various roles encounter 403 Forbidden or 500 Internal Server errors when navigating or clicking buttons.
2. Inappropriate navigation links and action buttons are displayed unconditionally regardless of user role.
3. Several state machine transitions allow invalid jumps (e.g. `BOOKED -> IN_TRANSIT` and `IN_TRANSIT -> OUT_FOR_DELIVERY`).
4. Sensitive demo passwords are exposed in publicly served templates.
5. In-memory SQLAlchemy collection state during refunds causes premature calculations before database synchronization.

All reported findings (A01 through A24) have been inspected in the source code and confirmed.

---

## 2. Confirmed Defect Inventory & Root Causes

| ID | Severity | File / Location | Defect Description | Confirmed Root Cause |
|---|---|---|---|---|
| **A01** | CRITICAL | `app/templates/base.html` (lines 152–213) | Sidebar links (Book Parcel, Customers, Hub Scans, Transfers, Dispatch Routes, Driver Workspace, Invoices, COD, Rate Cards) display to all authenticated users. | No permission guards on sidebar list items and section headers. |
| **A02** | CRITICAL | `app/templates/main/dashboard.html` & `app/blueprints/main/routes.py` | Operational dashboard displays global company metrics, all customer shipments, and "New Shipment" button to every role (including Drivers, Customers, Hub Operators). | `main_bp.index` lacks role/branch scoping; queries all records from `Shipment`, `Invoice`, `CodCollection`. |
| **A03** | CRITICAL | `app/services/hub_service.py` (`initiate_transfer`) & `ShipmentService.ALLOWED_TRANSITIONS` | `initiate_transfer()` accepts `BOOKED` shipments and calls `transition(..., 'IN_TRANSIT')`. | `ALLOWED_TRANSITIONS` strictly defines `BOOKED -> [PICKUP_ASSIGNED, AT_ORIGIN_HUB, CANCELLED]`. Jumping directly to `IN_TRANSIT` raises `ValueError: Invalid transition`. Parcels must reach `AT_ORIGIN_HUB` first. |
| **A04** | CRITICAL | `app/services/dispatch_service.py` (`add_route_stop`) & `ALLOWED_TRANSITIONS` | `add_route_stop()` attempts `IN_TRANSIT -> OUT_FOR_DELIVERY`. | `ALLOWED_TRANSITIONS` requires `IN_TRANSIT -> AT_DESTINATION_HUB`. Only parcels at destination hub can be dispatched for delivery. |
| **A05** | HIGH | `app/templates/admin/branches.html` | Branch Manager sees "Add Branch" and "Deactivate" buttons, but backend routes require `SUPER_ADMIN`. | Actions in template lack `current_user.has_role('SUPER_ADMIN')` checks. |
| **A06** | HIGH | `app/templates/admin/users.html` | Branch Manager sees "Register Staff Member" and deactivation buttons, but routes require `SUPER_ADMIN`. | Lacks role-based UI conditional rendering. |
| **A07** | HIGH | `app/templates/base.html` | "Audit Logs" sidebar link shown to Branch Manager, but `/admin/audit-logs` route is `SUPER_ADMIN` only. | Grouped under generic `SUPER_ADMIN or BRANCH_MANAGER` block. |
| **A08** | HIGH | `app/templates/finance/invoices.html` & `invoice_detail.html` | "COD Reconciliation" button and payment settlement form shown to Branch Manager, who gets 403 on submit. | Template checks `not current_user.has_role('CUSTOMER')` rather than checking specific finance roles. |
| **A09** | CRITICAL | `app/blueprints/catalog/routes.py` (`rate_card_detail`) | Any authenticated user can POST to `/catalog/rate-cards/<id>` to add rate card rules. | Missing `@roles_required` or permission check on POST method. |
| **A10** | HIGH | `app/templates/catalog/rates.html` | "New Rate Card" button visible to all users, but route requires `SUPER_ADMIN` or `BRANCH_MANAGER`. | Unconditional `<a href="...">` in template. |
| **A11** | HIGH | `app/templates/customers/show.html` | Support Agent sees "Add Address", "Add Recipient", and "Edit" buttons, leading to 403. | Support Agent has read-only access to customers; edit buttons lack permission gates. |
| **A12** | HIGH | `app/templates/shipments/index.html` & `show.html` | Drivers, Hub Operators, and Support Agents see "Book New Shipment" and "Assign Pickup Courier". | Template conditions check `not current_user.has_role('CUSTOMER')` instead of requiring specific booking/dispatch roles. |
| **A13** | CRITICAL | `app/blueprints/support/routes.py` (`close_ticket`) | Any authenticated user can close any ticket by submitting an arbitrary ticket ID. | Missing object-level authorization and ownership check in `close_ticket`. |
| **A14** | HIGH | `app/blueprints/support/routes.py` (`new_ticket`) | Staff ticket creation falls back to `customer_id = 1` for general inquiries. | Hardcoded fallback attributes tickets to arbitrary customer. |
| **A15** | CRITICAL | Scoping in shipments, finance, and tickets | Non-customer staff can access records across different branches without branch checks. | Queries lack branch scoping for `BRANCH_MANAGER`, `BOOKING_AGENT`, `HUB_OPERATOR`, `DISPATCHER`. |
| **A16** | CRITICAL | `app/blueprints/drivers/routes.py` (`record_attempt`, `record_proof`) | Route handlers accept `driver_id` from form input without verifying it matches `current_user`. | Unchecked form parameters allow driver spoofing. |
| **A17** | HIGH | `drivers/routes.py`, `finance/routes.py`, `shipments/routes.py` | Raw `int(request.form.get(...))` calls before validation. | Missing parameter causes `TypeError` / `ValueError` and HTTP 500 error. |
| **A18** | HIGH | Multiple routes and service exception handlers | Raw exceptions flashed to users; missing `db.session.rollback()`. | Failed database operations leave uncommitted transactions in session. |
| **A19** | CRITICAL | `app/templates/auth/login.html` & `app/templates/main/index.html` | Plaintext demo passwords (`AdminPass@1234`) displayed on public login and landing pages. | Security risk; credentials must reside in documentation or local-only helpers. |
| **A20** | HIGH | Test suite coverage | Tests previously disabled CSRF and focused primarily on GET views. | Need dedicated tests for POST form actions with CSRF, role boundaries, and negative cases. |
| **A21** | HIGH | `run.bat` launcher script | Uses 2-second sleep guess before opening browser; notices printed on non-zero exit. | Needs true HTTP health check polling and strict failure stopping. |
| **A22** | MEDIUM | Git hygiene / packaging | Ensure `.env` and `.venv` are ignored in `.gitignore`. | Keep secrets and virtual environments local. |
| **A23** | MEDIUM | `app/services/finance_service.py` (`process_refund`) | `payment.refunds` relationship collection not updated in memory before calculating `invoice.total_paid_paisa`. | Refunded paid invoices fail to reopen to `ISSUED` status. |
| **A24** | MEDIUM | `app/security/rbac.py` | Need unified, reusable permission helpers for templates and routes. | Prevents duplicating complex role checks across Jinja2 templates. |

---

## 3. Database Safety Confirmation

- SQLite database backed up to `instance/courier.sqlite3.bak`.
- Current schema verified: 55 tables, `PRAGMA foreign_keys = 1`, 0 violations.
- All fixes will be strictly non-destructive. No tables dropped, no data deleted.
