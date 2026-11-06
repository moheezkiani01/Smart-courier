# UI Action & Button Permission Matrix

This document provides a complete inventory of interactive buttons, links, forms, and triggers across the **Smart Courier & Parcel Delivery Management System**, mapping each action to its Flask endpoint, HTTP method, authorized roles, object scope, lifecycle prerequisites, success redirect, and persistent database effect.

---

## 1. Top Navigation & Global Layout (`app/templates/base.html`)

| UI Label / Action | Element Type | Endpoint | HTTP | Allowed Roles | Object Scope / Prerequisite | Success Redirect | Database Effect |
|---|---|---|:---:|---|---|---|---|
| **Logo / Brand** | Link | `main.index` | GET | All (Public / Auth) | None | `/` | None |
| **Track Search** | Form / Input | `tracking.search` | GET | All (Public / Auth) | Valid tracking number format | `/tracking/<tracking_code>` | None (Read-only) |
| **Profile** | Dropdown Link | `auth.profile` | GET | All Authenticated | Current user session | `/auth/profile` | None |
| **Support Tickets** | Dropdown Link | `support.tickets` | GET | All Authenticated | User ownership / branch scope | `/support/tickets` | None |
| **Logout** | Form Button | `auth.logout` | POST | All Authenticated | CSRF token required | `/` (Flashed: "Logged out") | Updates `login_sessions.ended_at` |

---

## 2. Left Sidebar Navigation (`app/templates/base.html`)

| Section Header | Nav Item | Endpoint | HTTP | Permission Guard (`caps`) | Authorized Roles | Destination View |
|---|---|---|:---:|---|---|---|
| *Top* | **Dashboard** | `main.index` | GET | `can_view_dashboard` | All authenticated roles | Role-personalized dashboard |
| **Shipments & Desk** | **Shipments** | `shipments.index` | GET | `can_view_shipments` | All authenticated roles | Consignments directory |
| **Shipments & Desk** | **Book Parcel** | `shipments.new` | GET | `can_book_shipment` | `SUPER_ADMIN`, `BRANCH_MANAGER`, `BOOKING_AGENT`, `CUSTOMER` | Booking wizard form |
| **Shipments & Desk** | **Customers** | `customers.index` | GET | `can_view_customers` | `SUPER_ADMIN`, `BRANCH_MANAGER`, `BOOKING_AGENT`, `SUPPORT_AGENT` | Customer accounts directory |
| **Operations & Hubs** | **Hub Scans** | `hubs.scans` | GET | `can_scan_hubs` | `SUPER_ADMIN`, `BRANCH_MANAGER`, `HUB_OPERATOR` | Barcode sorting console |
| **Operations & Hubs** | **Transfers** | `hubs.transfers` | GET | `can_transfer_hubs` | `SUPER_ADMIN`, `BRANCH_MANAGER`, `HUB_OPERATOR` | Freight linehaul manifest |
| **Operations & Hubs** | **Dispatch Routes** | `dispatch.routes` | GET | `can_manage_routes` | `SUPER_ADMIN`, `BRANCH_MANAGER`, `DISPATCHER` | Daily vehicle routes list |
| **Operations & Hubs** | **Driver Workspace** | `drivers.my_runs` | GET | `can_view_driver_workspace` | `SUPER_ADMIN`, `DRIVER` | Assigned stop runsheet |
| **Finance & Billing** | **Invoices** | `finance.invoices` | GET | `can_view_invoices` | `SUPER_ADMIN`, `BRANCH_MANAGER`, `FINANCE_OFFICER`, `CUSTOMER` | Billing invoice ledger |
| **Finance & Billing** | **COD Reconciliation**| `finance.cod_summary`| GET | `can_view_cod` | `SUPER_ADMIN`, `FINANCE_OFFICER` | Merchant COD payouts |
| **Support & Admin** | **Support Tickets** | `support.tickets` | GET | `can_view_tickets` | All authenticated roles | Ticket resolution desk |
| **Support & Admin** | **Rate Cards & Rules**| `catalog.rates` | GET | `can_view_rates` | `SUPER_ADMIN`, `BRANCH_MANAGER`, `BOOKING_AGENT` | Tariff bands catalog |
| **Support & Admin** | **Branches & Hubs** | `admin.branches` | GET | `can_view_branches` | `SUPER_ADMIN`, `BRANCH_MANAGER` | Facilities management |
| **Support & Admin** | **Staff & RBAC** | `admin.users` | GET | `can_view_staff` | `SUPER_ADMIN`, `BRANCH_MANAGER` | Employee directory |
| **Support & Admin** | **Audit Logs** | `admin.audit_logs` | GET | `can_view_audit_logs` | `SUPER_ADMIN` only | Security audit trail |

---

## 3. Shipment Domain Actions (`app/templates/shipments/`)

| Action / Button | Template | Endpoint | HTTP | Allowed Roles | Prerequisites | Success Redirect | Database Mutations |
|---|---|---|:---:|---|---|---|---|
| **Book New Shipment** | `index.html` / `dashboard.html` | `shipments.new` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER`, `BOOKING_AGENT`, `CUSTOMER` | Sender, recipient, item details, valid rate card | `/shipments/<id>` | Inserts `Shipment`, `ShipmentItem`, `ShipmentAddress` (x2), `ShipmentService`, `Invoice`, `InvoiceItem`, `ShipmentStatusHistory` |
| **Print Label** | `show.html` | `shipments.label` | GET | Authorized viewer | Active shipment | Opens printable label | None |
| **Transition Status** | `show.html` | `shipments.transition` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER`, `BOOKING_AGENT`, `HUB_OPERATOR`, `DISPATCHER`, `DRIVER` | Allowed target state in `ALLOWED_TRANSITIONS` | `/shipments/<id>` | Updates `shipments.shipment_status`; appends `shipment_status_history` and `tracking_events` |
| **Assign Pickup** | `show.html` | `shipments.assign_pickup` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER`, `DISPATCHER` | Status is `BOOKED`; pending `PickupRequest` | `/shipments/<id>` | Inserts `PickupAssignment`; transitions shipment to `PICKUP_ASSIGNED` |

---

## 4. Hubs & Linehaul Transfers (`app/templates/hubs/`)

| Action / Button | Template | Endpoint | HTTP | Allowed Roles | Prerequisites | Success Redirect | Database Mutations |
|---|---|---|:---:|---|---|---|---|
| **Record Scan** | `scans.html` | `hubs.scans` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER`, `HUB_OPERATOR` | Valid shipment ID and scan type | `/hubs/scans` | Inserts `ShipmentScan`, `TrackingEvent`; updates `shipments.current_hub_id` |
| **Initiate Transfer** | `transfers.html` | `hubs.transfers` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER`, `HUB_OPERATOR` | Parcel in `AT_ORIGIN_HUB` or `AT_DESTINATION_HUB` | `/hubs/transfers` | Inserts `HubTransfer`; transitions shipment to `IN_TRANSIT` |
| **Receive Transfer** | `transfers.html` | `hubs.receive_transfer` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER`, `HUB_OPERATOR` | Transfer is `IN_TRANSIT` | `/hubs/transfers` | Updates `hub_transfers.transfer_status='RECEIVED'`; transitions shipment to `AT_DESTINATION_HUB` |

---

## 5. Dispatch & Route Execution (`app/templates/dispatch/` & `app/templates/drivers/`)

| Action / Button | Template | Endpoint | HTTP | Allowed Roles | Prerequisites | Success Redirect | Database Mutations |
|---|---|---|:---:|---|---|---|---|
| **Create Route** | `new_route.html` | `dispatch.new_route` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER`, `DISPATCHER` | Active driver and vehicle | `/dispatch/routes/<id>` | Inserts `Route`, `VehicleAssignment` |
| **Add Route Stop** | `route_detail.html` | `dispatch.route_detail` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER`, `DISPATCHER` | Unique sequence; delivery stop requires `AT_DESTINATION_HUB` | `/dispatch/routes/<id>` | Inserts `RouteStop`; transitions parcel to `OUT_FOR_DELIVERY` |
| **Record Delivery Attempt** | `my_runs.html` | `drivers.record_attempt` | POST | `SUPER_ADMIN`, `DRIVER` | Driver assigned to route; parcel in `OUT_FOR_DELIVERY` | `/driver/my-runs` | Inserts `DeliveryAttempt`; records `DELIVERY_FAILED` if failure |
| **Confirm Proof of Delivery** | `my_runs.html` | `drivers.record_proof` | POST | `SUPER_ADMIN`, `DRIVER` | Successful attempt; receiver name | `/driver/my-runs` | Inserts `DeliveryProof`; transitions parcel to `DELIVERED` |

---

## 6. Finance & Cash-on-Delivery (`app/templates/finance/`)

| Action / Button | Template | Endpoint | HTTP | Allowed Roles | Prerequisites | Success Redirect | Database Mutations |
|---|---|---|:---:|---|---|---|---|
| **Post Payment** | `invoice_detail.html` | `finance.record_payment` | POST | `SUPER_ADMIN`, `FINANCE_OFFICER`, `BOOKING_AGENT` | `amount_due_paisa > 0`; valid amount | `/finance/invoices/<id>` | Inserts `Payment`; updates invoice status to `PAID` if settled |
| **Process Refund** | `invoice_detail.html` | `finance.process_refund` | POST | `SUPER_ADMIN`, `FINANCE_OFFICER` | Settled payment; `amount <= payment.amount_paisa` | `/finance/invoices/<id>` | Inserts `Refund`; updates payment and reopens invoice to `ISSUED` |
| **Remit COD Funds** | `cod_summary.html` | `finance.remit_cod` | POST | `SUPER_ADMIN`, `FINANCE_OFFICER` | Collection status `COLLECTED`; valid reference | `/finance/cod` | Inserts `CodRemittance`; updates `cod_collections.collection_status='REMITTED'` |

---

## 7. Customer & Commercial Catalog (`app/templates/customers/` & `app/templates/catalog/`)

| Action / Button | Template | Endpoint | HTTP | Allowed Roles | Prerequisites | Success Redirect | Database Mutations |
|---|---|---|:---:|---|---|---|---|
| **Create Customer** | `form.html` | `customers.new_customer` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER`, `BOOKING_AGENT` | Unique business/person name | `/customers/<id>` | Inserts `Customer`, `CustomerContact` |
| **Add Customer Address** | `address_form.html` | `customers.add_address` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER`, `BOOKING_AGENT` | Valid customer account and zone | `/customers/<id>` | Inserts `CustomerAddress` |
| **Add Recipient Profile** | `recipient_form.html` | `customers.add_recipient` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER`, `BOOKING_AGENT` | Valid customer account | `/customers/<id>` | Inserts `RecipientProfile`, `RecipientAddress` |
| **Deactivate Customer** | `index.html` | `customers.deactivate_customer` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER` | Active customer | `/customers` | Sets `is_deleted=True`, `status='DEACTIVE'` |
| **Create Rate Card** | `rate_card_form.html` | `catalog.new_rate_card` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER` | Unique service type + origin/destination zones | `/catalog/rate-cards/<id>` | Inserts `RateCard` |
| **Add Weight Band Rule** | `rate_card_detail.html` | `catalog.rate_card_detail` | POST | `SUPER_ADMIN`, `BRANCH_MANAGER` | Valid weight min/max range | `/catalog/rate-cards/<id>` | Inserts `RateCardRule` |

---

## 8. Support & Ticket Resolution (`app/templates/support/`)

| Action / Button | Template | Endpoint | HTTP | Allowed Roles | Prerequisites | Success Redirect | Database Mutations |
|---|---|---|:---:|---|---|---|---|
| **Open Ticket** | `new_ticket.html` | `support.new_ticket` | POST | All Authenticated | Subject and body; valid customer account | `/support/tickets/<id>` | Inserts `SupportTicket`, initial `TicketMessage` |
| **Reply to Ticket** | `ticket_detail.html` | `support.ticket_detail` | POST | Ticket Owner or Staff | Non-empty message | `/support/tickets/<id>` | Inserts `TicketMessage`; updates ticket status to `IN_PROGRESS` |
| **Close Ticket** | `ticket_detail.html` | `support.close_ticket` | POST | Ticket Owner or Staff | Open or in-progress ticket | `/support/tickets/<id>` | Updates `support_tickets.ticket_status='RESOLVED'`, `closed_at=UTC` |

---

## 9. Administrative Facilities & RBAC (`app/templates/admin/`)

| Action / Button | Template | Endpoint | HTTP | Allowed Roles | Prerequisites | Success Redirect | Database Mutations |
|---|---|---|:---:|---|---|---|---|
| **Add Branch** | `branch_form.html` | `admin.new_branch` | POST | `SUPER_ADMIN` only | Unique branch code | `/admin/branches` | Inserts `Branch` |
| **Deactivate Branch** | `branches.html` | `admin.deactivate_branch` | POST | `SUPER_ADMIN` only | Branch has no active routes | `/admin/branches` | Sets `is_deleted=True`, `status='DEACTIVE'` |
| **Register Staff** | `user_form.html` | `admin.new_user` | POST | `SUPER_ADMIN` only | Unique email, password >= 8 chars | `/admin/users` | Inserts `User`, `UserRole`, `Employee` |
| **Deactivate Staff** | `users.html` | `admin.deactivate_user` | POST | `SUPER_ADMIN` only | Cannot deactivate own user | `/admin/users` | Sets `is_deleted=True`, `status='DEACTIVE'` |
