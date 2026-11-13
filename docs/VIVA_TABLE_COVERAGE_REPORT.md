# Smart Courier — 55 Business Table Coverage & Verification Report

**Verification Date:** November 13, 2026  
**Target Architecture:** 55 Normalized Relational SQLAlchemy Business Tables  
**Relational Coverage Level:** 100% (55 / 55 Populated Business Tables, 0 Empty Tables)  
**Database Foreign Key Status:** Strict Referential Integrity Enforced (0 Violations)  
**Automated Pytest Test Suite:** 101 Passed (100% Pass Rate)

---

## 1. Executive Verification Summary

| Metric | Measured Value | Standard / Requirement | Status |
|---|---|---|:---:|
| **Total Registered Business Tables** | **55** | >= 40 Relational Tables (Rubric) | **PASS** |
| **Populated Business Tables** | **55** | 100% Table Coverage | **PASS** |
| **Empty Tables** | **0** | Zero Empty Tables Allowed | **PASS** |
| **Relational Coverage Percentage** | **100.0%** | Comprehensive viva showcase | **PASS** |
| **Foreign Key Check Violations** | **0** | SQLite PRAGMA `foreign_key_check` | **PASS** |
| **Audit Mixin Columns Enforced** | **55 / 55** | `id`, `created_at`, `created_by`, `status`, `is_deleted` | **PASS** |
| **Pytest Automated Regression Suite** | **101 / 101 Passed** | Zero regressions | **PASS** |
| **Seeder Repeat-Run Idempotency** | **Verified (0 Duplicates)** | Status: `already_seeded` on 2nd run | **PASS** |
| **Dry-Run Non-Destructive Mode** | **Verified (0 Writes)** | Pure simulation preview | **PASS** |
| **Customer Scoping & RBAC Isolation** | **Enforced** | Cross-customer access prohibited (403) | **PASS** |

---

## 2. Master 55-Table Relational Inventory

The following table details the live verification state of all 55 business tables in the Smart Courier database:

| # | Table Name | Domain Group | Total Rows | Demo Rows | Sample PK / Ref | Linked Parent FK | Visible UI Route / Scope | Status |
|---|---|---|---:|---:|---|---|---|:---:|
| 1 | `users` | A. Auth & Access | 12 | 3 | `demo.merchant@smartcourier.pk` | `Self / None` | `/admin/users, /auth/login` | **PASS** |
| 2 | `roles` | A. Auth & Access | 9 | 9 | `CUSTOMER` | `None` | `/admin/roles` | **PASS** |
| 3 | `permissions` | A. Auth & Access | 12 | 12 | `shipments.create` | `None` | `/admin/roles` | **PASS** |
| 4 | `user_roles` | A. Auth & Access | 12 | 12 | `UR #1` | `users.id, roles.id` | `/admin/users` | **PASS** |
| 5 | `role_permissions` | A. Auth & Access | 33 | 33 | `RP #1` | `roles.id, permissions.id` | `/admin/roles` | **PASS** |
| 6 | `login_sessions` | A. Auth & Access | 6 | 6 | `Session #1 (Inert/Revoked)` | `users.id` | `Internal (Audit / Security)` | **PASS** |
| 7 | `branches` | B. Organization | 3 | 3 | `BR-LHR-01` | `None` | `/admin/branches` | **PASS** |
| 8 | `hubs` | B. Organization | 3 | 3 | `HUB-LHR-01` | `branches.id` | `/hubs/transfers, /admin/branches` | **PASS** |
| 9 | `employees` | B. Organization | 7 | 7 | `EMP-1001` | `users.id, branches.id` | `/admin/employees` | **PASS** |
| 10 | `employee_branches` | B. Organization | 7 | 7 | `EmpBr #1` | `employees.id, branches.id` | `/admin/employees` | **PASS** |
| 11 | `service_zones` | B. Organization | 4 | 4 | `ZONE-LHR` | `None` | `/admin/zones` | **PASS** |
| 12 | `branch_zones` | B. Organization | 4 | 4 | `BrZone #1` | `branches.id, service_zones.id` | `/admin/branches` | **PASS** |
| 13 | `customers` | C. Customers & Catalog | 4 | 2 | `CUST-2611-CEB6` | `users.id` | `/customers/, /customers/<id>` | **PASS** |
| 14 | `customer_contacts` | C. Customers & Catalog | 3 | 2 | `Bilal Tariq` | `customers.id` | `/customers/<id>` | **PASS** |
| 15 | `customer_addresses` | C. Customers & Catalog | 4 | 3 | `Addr #1 (Lahore Warehouse)` | `customers.id, service_zones.id` | `/customers/<id>/addresses/new` | **PASS** |
| 16 | `recipient_profiles` | C. Customers & Catalog | 4 | 4 | `High Court Registrar` | `customers.id` | `/customers/<id>/recipients/new` | **PASS** |
| 17 | `recipient_addresses` | C. Customers & Catalog | 4 | 4 | `RecipAddr #1 (Islamabad G-5)`| `recipient_profiles.id, service_zones.id` | `/customers/<id>/recipients/new` | **PASS** |
| 18 | `service_types` | C. Customers & Catalog | 4 | 4 | `STANDARD` | `None` | `/catalog/services, /shipments/new` | **PASS** |
| 19 | `parcel_categories` | C. Customers & Catalog | 5 | 5 | `DOC` | `None` | `/catalog/categories, /shipments/new` | **PASS** |
| 20 | `packaging_types` | C. Customers & Catalog | 4 | 4 | `FLYER_S` | `None` | `/catalog/packaging, /shipments/new` | **PASS** |
| 21 | `rate_cards` | C. Customers & Catalog | 64 | 64 | `RateCard #1` | `service_types.id, service_zones.id` | `/catalog/rates, /tracking/quote` | **PASS** |
| 22 | `rate_card_rules` | C. Customers & Catalog | 127 | 127 | `Rule #1` | `rate_cards.id` | `/catalog/rates` | **PASS** |
| 23 | `shipments` | D. Shipments & Booking | 15 | 3 | `SC26111BD34E` | `customers.id, branches.id, service_types.id` | `/shipments/, /shipments/<id>` | **PASS** |
| 24 | `shipment_items` | D. Shipments & Booking | 15 | 15 | `Item #1 (Legal docs)` | `shipments.id` | `/shipments/<id>` | **PASS** |
| 25 | `shipment_addresses` | D. Shipments & Booking | 30 | 30 | `AddrSnap #1 (Sender/Recip)` | `shipments.id, service_zones.id` | `/shipments/<id>` | **PASS** |
| 26 | `shipment_services` | D. Shipments & Booking | 15 | 15 | `Quote #1 (Pricing Snapshot)` | `shipments.id, rate_cards.id` | `/shipments/<id>` | **PASS** |
| 27 | `shipment_documents` | D. Shipments & Booking | 2 | 2 | `viva_waybill_SC_DEMO_01.pdf` | `shipments.id, users.id` | `/shipments/<id>` | **PASS** |
| 28 | `pickup_requests` | D. Shipments & Booking | 2 | 2 | `Pickup #1 (ASSIGNED)` | `shipments.id, shipment_addresses.id` | `/shipments/<id>` | **PASS** |
| 29 | `pickup_assignments` | D. Shipments & Booking | 1 | 1 | `Assign #1 (Driver #1)` | `pickup_requests.id, drivers.id, vehicles.id` | `/shipments/<id>, /drivers/my-runs` | **PASS** |
| 30 | `shipment_status_history` | D. Shipments & Booking | 13 | 13 | `Hist #1 (DRAFT->BOOKED)` | `shipments.id, users.id` | `/shipments/<id>` | **PASS** |
| 31 | `routes` | E. Dispatch & Fleet | 1 | 1 | `ROUTE-LHR-EAST-01` | `branches.id, drivers.id, vehicles.id` | `/dispatch/routes, /dispatch/routes/<id>` | **PASS** |
| 32 | `route_stops` | E. Dispatch & Fleet | 5 | 5 | `Stop #1 (DELIVERY)` | `routes.id, shipments.id` | `/dispatch/routes/<id>` | **PASS** |
| 33 | `hub_transfers` | E. Dispatch & Fleet | 1 | 1 | `Transfer #1 (IN_TRANSIT)` | `shipments.id, hubs.id, employees.id` | `/hubs/transfers` | **PASS** |
| 34 | `shipment_scans` | E. Dispatch & Fleet | 3 | 3 | `HUB_INBOUND_LHR` | `shipments.id, hubs.id, employees.id` | `/shipments/<id>, /hubs/transfers` | **PASS** |
| 35 | `tracking_events` | E. Dispatch & Fleet | 34 | 34 | `SCAN_HUB_INBOUND_LHR` | `shipments.id` | `/tracking/<tn>` | **PASS** |
| 36 | `delivery_attempts` | E. Dispatch & Fleet | 6 | 6 | `Attempt #1 (FAILED)` | `shipments.id, drivers.id, route_stops.id` | `/shipments/<id>, /drivers/my-runs` | **PASS** |
| 37 | `delivery_proofs` | E. Dispatch & Fleet | 3 | 3 | `Proof #1 (A. Khan)` | `shipments.id, delivery_attempts.id` | `/shipments/<id>, /tracking/<tn>` | **PASS** |
| 38 | `delivery_exceptions` | E. Dispatch & Fleet | 3 | 3 | `Exception #1 (RESCHEDULED)` | `shipments.id, delivery_attempts.id` | `/shipments/<id>` | **PASS** |
| 39 | `vehicles` | E. Dispatch & Fleet | 3 | 3 | `LE-24-9001` | `branches.id` | `/dispatch/vehicles` | **PASS** |
| 40 | `drivers` | E. Dispatch & Fleet | 1 | 1 | `PK-LHR-DRV-9988` | `employees.id` | `/dispatch/drivers` | **PASS** |
| 41 | `vehicle_assignments` | E. Dispatch & Fleet | 1 | 1 | `Assign #1 (Veh #2)` | `vehicles.id, drivers.id, routes.id` | `/dispatch/routes/<id>` | **PASS** |
| 42 | `invoices` | F. Finance & Payments | 15 | 15 | `INV-202611-85E01` | `shipments.id, customers.id` | `/finance/invoices, /finance/invoices/<id>` | **PASS** |
| 43 | `invoice_items` | F. Finance & Payments | 10 | 10 | `Item #1 (Freight Charge)` | `invoices.id, shipment_services.id` | `/finance/invoices/<id>` | **PASS** |
| 44 | `payments` | F. Finance & Payments | 3 | 3 | `TRX-MCB-998811` | `invoices.id, employees.id` | `/finance/invoices/<id>` | **PASS** |
| 45 | `cod_collections` | F. Finance & Payments | 1 | 1 | `COD #1 (Rs. 2,500.00)` | `shipments.id, drivers.id` | `/finance/cod` | **PASS** |
| 46 | `cod_remittances` | F. Finance & Payments | 1 | 1 | `REMIT-VIVA-01` | `cod_collections.id, employees.id` | `/finance/cod` | **PASS** |
| 47 | `refunds` | F. Finance & Payments | 1 | 1 | `Refund #1 (PENDING)` | `payments.id, employees.id` | `/finance/invoices/<id>` | **PASS** |
| 48 | `discounts` | F. Finance & Payments | 2 | 2 | `VIVA2026 (10%)` | `None` | `/catalog/rates, /shipments/new` | **PASS** |
| 49 | `shipment_discounts` | F. Finance & Payments | 1 | 1 | `ShipDisc #1 (Rs. 55.00)` | `shipments.id, discounts.id` | `/shipments/<id>, /finance/invoices/<id>` | **PASS** |
| 50 | `support_tickets` | G. Support & Audit | 5 | 5 | `TICK-VIVA-01` | `customers.id, shipments.id, employees.id` | `/support/tickets, /support/tickets/<id>` | **PASS** |
| 51 | `ticket_messages` | G. Support & Audit | 9 | 9 | `Msg #1 (Customer Inquiry)` | `support_tickets.id, users.id` | `/support/tickets/<id>` | **PASS** |
| 52 | `notifications` | G. Support & Audit | 3 | 3 | `Notif #1 (IN_APP)` | `users.id, customers.id, shipments.id` | `/support/notifications` | **PASS** |
| 53 | `notification_templates` | G. Support & Audit | 4 | 4 | `VIVA_DEMO_ALERT` | `None` | `/support/notifications` | **PASS** |
| 54 | `audit_logs` | G. Support & Audit | 25 | 25 | `Audit #25 (VIVA_SEED)` | `users.id, branches.id` | `/admin/audit-logs` | **PASS** |
| 55 | `app_settings` | G. Support & Audit | 5 | 5 | `VIVA_55_TABLE_DATASET_MAP` | `None` | `Internal (System Config)` | **PASS** |

---

## 3. Schema & Foreign Key Integrity Audit

Running the automated schema verifier (`python -m flask --app run.py verify-schema`):

```
======================================================================
SMART COURIER — SCHEMA VERIFICATION
======================================================================
[*] SQLite PRAGMA foreign_keys: 1 (Expected: 1)
[*] SQLite PRAGMA foreign_key_check violations: 0
[*] Database Business Tables Found: 55 / 55
[+] All 55 business tables verified successfully with all audit columns!
======================================================================
[+] Schema verification passed!
```

---

## 4. Demonstrative Data Safety & Governance Guardrails

1. **Strict Idempotency:** The seeder creates records only if they do not already exist. Subsequent runs detect `VIVA_55_TABLE_DATASET_MAP` and return `status: already_seeded` with **zero duplicate records**.
2. **Zero Live Communications / Payments:** No real emails, SMS, WhatsApp notifications, or live bank payouts are triggered. All communications use `IN_APP` channels, and payment transactions are marked `SETTLED` in demonstrative bookkeeping ledgers.
3. **Inert Session Audit Row:** The `login_sessions` table includes an expired, revoked session with an uncrackable SHA-256 hash that cannot authenticate or bypass access controls.
4. **Harmless Genuine PDF Files:** Waybill and manifest documents attached in `shipment_documents` reference genuine, minimal valid PDF-1.4 files located on disk at `uploads/documents/`. Opening them via the web interface displays authentic PDF consignment notes.
5. **Customer Isolation & Ownership:** Demonstration data preserves full multi-tenant isolation. A customer can only access their own demo shipments, while staff and admin views enforce proper RBAC privileges.

---

## 5. CLI Execution Reference

### Preview Prospective Changes (Dry-Run):
```bash
python -m flask --app run.py seed-viva-full --dry-run
```

### Seed Full 55-Table Dataset (Local Development):
```bash
python -m flask --app run.py seed-viva-full --confirm
```

### Generate 55-Table Terminal or Markdown Report:
```bash
python -m flask --app run.py viva-table-report
python -m flask --app run.py viva-table-report --markdown
```

### Clean Up Demo Records Safely (Reversible):
```bash
python -m flask --app run.py cleanup-viva-full --confirm
```
