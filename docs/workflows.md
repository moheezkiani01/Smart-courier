# Smart Courier & Parcel Delivery Management System — Workflows & Business Rules

This document describes the key lifecycle state machines, authorization rules, financial rules, and operational workflows.

---

## 1. Shipment Lifecycle State Machine

A centralized transition engine (`app/services/shipment_service.py`) controls all shipment status changes.
Every valid transition:
1. Validates current status and allowed target status.
2. Checks user permissions and branch authorization.
3. Appends a record to `shipment_status_history` (`previous_status`, `new_status`, `changed_at`, `actor_user_id`, `reason`).
4. Optionally creates a customer-visible `tracking_events` entry.
5. Updates `shipments.shipment_status` in an atomic database transaction.

### Allowed Status Transitions

```text
DRAFT
  └── BOOKED
        ├── PICKUP_ASSIGNED
        │     ├── PICKED_UP
        │     │     └── AT_ORIGIN_HUB
        │     └── CANCELLED (if not yet picked up)
        ├── AT_ORIGIN_HUB (direct counter drop-off)
        ├── CANCELLED
        
AT_ORIGIN_HUB
  └── IN_TRANSIT
        └── AT_DESTINATION_HUB
              └── OUT_FOR_DELIVERY
                    ├── DELIVERED (requires valid delivery proof)
                    └── DELIVERY_FAILED
                          ├── OUT_FOR_DELIVERY (retry delivery attempt)
                          └── RETURN_INITIATED
                                └── RETURNED_TO_SENDER
```

---

## 2. Nine Roles & Permission Scopes

The system enforces nine distinct roles with strict server-side authorization checks:

| Role | Responsibilities & Access Scope |
|---|---|
| `SUPER_ADMIN` | Global access: all branches, users, roles, system audit logs, application settings, rate cards. |
| `BRANCH_MANAGER` | Branch scoped: manages own branch employees, hubs, assigned routes, and local reporting. |
| `BOOKING_AGENT` | Desk operations: customer creation, address management, rate quote generation, shipment booking. |
| `HUB_OPERATOR` | Hub operations: parcel scans (in/out), hub transfers, receiving inbound transfers. |
| `DISPATCHER` | Logistics: vehicle assignments, route creation, driver dispatching, stop sequence management. |
| `DRIVER` | Field execution: assigned pickup requests, route stops, delivery attempt logging, proof of delivery. |
| `FINANCE_OFFICER` | Financial operations: invoice generation, payment settlements, refunds, COD collection reconciliation and remittance. |
| `SUPPORT_AGENT` | Customer service: managing support tickets, ticket message correspondence, shipment tracking diagnostics. |
| `CUSTOMER` | Self-service: own profile, saved recipient addresses, booking shipments, tracking own parcels, viewing own invoices, opening support tickets. |

---

## 3. Financial & Pricing Workflows

### 3.1 Integer Paisa Arithmetic
All monetary amounts are stored as **integers representing Paisa** (1 PKR = 100 Paisa).
- Example: PKR 450.50 is stored as `45050`.
- Display formatting helper converts `paisa_to_pkr(45050)` -> `"Rs. 450.50"`.
- Avoids floating-point precision loss.

### 3.2 Pricing Calculation
Quote formula:
$$\text{Total} = \text{Base Fee} + (\max(0, \text{Weight} - \text{Base Weight Band Max}) \times \text{Extra Rate Per Kg}) + \text{Packaging Fee} - \text{Discount} + \text{Tax}$$
- Frozen quote is captured into `shipment_services` at booking time.
- Changes to rate cards never retroactively alter booked shipments.

### 3.3 Cash on Delivery (COD) Rules
- COD represents merchant/sender parcel value collected from the recipient by the driver.
- Courier shipping charge is recorded as Courier Revenue on `invoices`.
- COD collected is recorded in `cod_collections` and remitted to the merchant in `cod_remittances`. COD money is NOT courier revenue.

---

## 4. Soft Delete and Audit Trail

- In editable entities, deletion sets `is_deleted = True`, `status = 'DEACTIVE'`, `deleted_at = UTC_NOW()`, and `deleted_by = current_user.id`.
- Queries filter out soft-deleted records (`Model.is_deleted == False`) for active CRUD.
- Immutable records (`shipment_status_history`, `shipment_scans`, `tracking_events`, `payments`, `audit_logs`) cannot be updated or soft-deleted via CRUD; corrections require reversal entries.
