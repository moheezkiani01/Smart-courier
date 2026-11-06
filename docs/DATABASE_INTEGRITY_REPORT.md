# Relational Database Schema & Integrity Report

**Project:** Smart Courier & Parcel Delivery Management System  
**Engine:** SQLite 3 (Persistent File: `instance/courier.sqlite3`)  
**ORM:** SQLAlchemy 2.0 + Flask-SQLAlchemy 3.1 + Flask-Migrate  
**Audit Standard:** Universal 9 Audit Columns (`AuditMixin`)  
**Foreign Key Enforcement:** Enabled on all connections via SQLite connection listener (`PRAGMA foreign_keys = ON`)

---

## 1. Relational Database Health & Integrity Verification

Execution of [`scripts/verify_schema.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/scripts/verify_schema.py):

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

### Direct SQLite Pragma Checks
- **Foreign Key Enforcement:** `PRAGMA foreign_keys;` &rarr; `1` (Active)
- **Foreign Key Violation Scan:** `PRAGMA foreign_key_check;` &rarr; `[]` (**Zero Violations**)
- **B-Tree Database Integrity:** `PRAGMA integrity_check;` &rarr; `[('ok',)]` (**100% Intact**)
- **Data Persistence:** Customer bookings, tracking events, invoices, and users persist unchanged across server and batch launcher restarts.

---

## 2. Universal Audit Columns (`AuditMixin`)

Every single one of the 55 business tables inherits all 9 mandatory audit fields defined in [`app/models/base.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/models/base.py):

| Column Name | SQL Type | Nullable | Default | Description |
|:---|:---|:---:|:---:|:---|
| `id` | `INTEGER` | No | Auto-increment PK | Unique surrogate primary key |
| `status` | `VARCHAR(30)` | No | `'ACTIVE'` | Record lifecycle state (`ACTIVE`, `INACTIVE`, `PENDING`) |
| `created_at` | `DATETIME` | No | `datetime.utcnow` | Timestamp of row creation (UTC) |
| `created_by` | `INTEGER` | Yes | FK to `users.id` | User identity who created the record |
| `updated_at` | `DATETIME` | No | `datetime.utcnow` | Timestamp of latest record modification (UTC) |
| `updated_by` | `INTEGER` | Yes | FK to `users.id` | User identity who performed last update |
| `is_deleted` | `BOOLEAN` | No | `False` | Soft deletion flag (preserves historical relational integrity) |
| `deleted_at` | `DATETIME` | Yes | `None` | Timestamp when soft-deleted |
| `deleted_by` | `INTEGER` | Yes | FK to `users.id` | User identity who soft-deleted the record |

---

## 3. Inventory of All 55 Business Tables by Domain

### Group A: Authentication & RBAC (6 Tables)
1. `users` — Primary user identity, hashed passwords, contact details, verification flags.
2. `roles` — 9 enterprise system roles (`SUPER_ADMIN`, `BRANCH_MANAGER`, `BOOKING_AGENT`, `HUB_OPERATOR`, `DISPATCHER`, `DRIVER`, `FINANCE_OFFICER`, `SUPPORT_AGENT`, `CUSTOMER`).
3. `permissions` — Atomic permission grants across organization, catalog, shipments, dispatch, finance, and security modules.
4. `user_roles` — Junction mapping users to roles (many-to-many).
5. `role_permissions` — Junction mapping roles to granular permission codes (many-to-many).
6. `login_sessions` — User session records, IP hints, and security tokens for audit inspection.

### Group B: Organization & Employees (6 Tables)
7. `branches` — Physical branch offices (Lahore Central, Karachi Port, Islamabad Capital).
8. `hubs` — Major sorting facilities and parcel cross-docking facilities.
9. `employees` — Staff member records linked to User identities and primary branches.
10. `employee_branches` — Multi-branch operational authority mappings.
11. `service_zones` — Geographical delivery and pickup coverage zones with postal code prefixes.
12. `branch_zones` — Operational zone coverage assignments per branch.

### Group C: Customers & Catalog (10 Tables)
13. `customers` — Customer master accounts linked to User identities.
14. `customer_contacts` — Alternate contacts and corporate dispatch personnel.
15. `customer_addresses` — Saved sender pickup addresses.
16. `recipient_profiles` — Saved recurring recipient profiles for senders.
17. `recipient_addresses` — Saved destination delivery addresses.
18. `service_types` — Courier service tiers (Standard Ground, Express Overnight, Urgent Same-Day).
19. `parcel_categories` — Classification categories (Documents, Electronics, Apparel, Fragile).
20. `packaging_types` — Standard packaging materials with fees (Flyer Bag, Small Box, Padded Carton).
21. `rate_cards` — Zone-to-zone pricing contracts with validity date windows.
22. `rate_card_rules` — Tiered weight pricing bands and extra per-kg rates in integer paisa.

### Group D: Shipments & Booking (8 Tables)
23. `shipments` — Core parcel consignments, tracking numbers, weights, financial dues, and operational status.
24. `shipment_items` — Itemized package content descriptions, quantities, and declared values.
25. `shipment_addresses` — Immutable point-in-time snapshots of sender and recipient addresses.
26. `shipment_services` — Quoted shipping rate snapshot capturing base fee, packaging, discount, and tax.
27. `shipment_documents` — Waybill document references, shipping manifests, and export files.
28. `pickup_requests` — Doorstep pickup scheduling requests with time windows and special notes.
29. `pickup_assignments` — Dispatch assignment of pickup requests to drivers and fleet vehicles.
30. `shipment_status_history` — Immutable state transition audit trail with timestamps and actors.

### Group E: Dispatch, Routing & Delivery (11 Tables)
31. `routes` — Daily vehicle delivery routes planned by dispatchers.
32. `route_stops` — Ordered delivery and pickup stop sequences on active routes.
33. `hub_transfers` — Inter-hub linehaul freight movements between sorting facilities.
34. `shipment_scans` — Individual barcode scan events at hubs and counters.
35. `tracking_events` — Sanitized public tracking timeline entries visible to customers and guests.
36. `delivery_attempts` — Recorded delivery attempts with outcomes (SUCCESS, FAILED, RESCHEDULED).
37. `delivery_proofs` — Recipient verification, digital signatures, and proof of delivery tokens.
38. `delivery_exceptions` — Recorded reasons for delivery failure (Customer Unavailable, Address Incorrect, etc.).
39. `vehicles` — Fleet delivery vans, motorcycles, and linehaul trucks.
40. `drivers` — Delivery driver profile records linked to staff employees and commercial driving licenses.
41. `vehicle_assignments` — Assignment history of fleet vehicles to drivers.

### Group F: Finance & Invoicing (8 Tables)
42. `invoices` — Billing invoices for freight charges and services with integer paisa precision.
43. `invoice_items` — Itemized invoice line items for freight, packaging, and handling.
44. `payments` — Recorded invoice payment transactions (Cash, Bank Transfer, Counter Settlement).
45. `cod_collections` — Cash collected from recipients by courier drivers upon delivery.
46. `cod_remittances` — Remittance settlements transferring collected COD funds back to senders.
47. `refunds` — Authorized payment refunds with transaction rollback and invoice reopening.
48. `discounts` — Promotional discount coupons and corporate discount contracts.
49. `shipment_discounts` — Applied discount ledger entries tied to shipments and invoices.

### Group G: Support, Notifications & System (6 Tables)
50. `support_tickets` — Customer service inquiries and delivery complaint cases.
51. `ticket_messages` — Conversation threads between customers and support agents, with internal staff note isolation.
52. `notifications` — Role-scoped notification center messages.
53. `notification_templates` — System notification message templates.
54. `audit_logs` — Immutable security audit trail capturing before/after JSON states and actor IPs.
55. `app_settings` — System-wide configuration flags and business operating policies.

*(Plus `alembic_version` schema migration metadata tracking table = 56 total SQLite tables).*
