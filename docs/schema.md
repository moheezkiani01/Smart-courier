# Smart Courier & Parcel Delivery Management System — Database Schema Specification

This document provides the authoritative inventory and technical specification for all **55 relational SQLAlchemy business tables** in the Smart Courier system.

---

## 1. Universal Audit Columns & Lifecycle Policy

Every single business model in the system inherits from `AuditMixin` (`app/models/base.py`).

| Column | Data Type | Nullable | Default | Description / Constraints |
|---|---|---|---|---|
| `id` | `INTEGER` | No | Auto (PK) | Primary Key integer |
| `is_deleted` | `BOOLEAN` | No | `False` | Soft deletion flag |
| `created_at` | `DATETIME` | No | UTC Now | Record creation timestamp |
| `created_by` | `INTEGER` | Yes | `NULL` | FK -> `users.id` (RESTRICT) |
| `updated_at` | `DATETIME` | Yes | `NULL` | Last modification timestamp |
| `updated_by` | `INTEGER` | Yes | `NULL` | FK -> `users.id` (RESTRICT) |
| `status` | `VARCHAR(20)`| No | `'ACTIVE'` | CHECK (`status IN ('ACTIVE','DEACTIVE','PENDING')`) |
| `deleted_at` | `DATETIME` | Yes | `NULL` | Soft deletion timestamp |
| `deleted_by` | `INTEGER` | Yes | `NULL` | FK -> `users.id` (RESTRICT) |

### SQLite Pragma & Foreign Keys
SQLite does not enforce foreign keys by default. We register an event listener on the SQLAlchemy connection engine:
```python
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```
`PRAGMA foreign_keys = 1` and `PRAGMA foreign_key_check` are run in schema validation and automated test suites.

---

## 2. Table Inventory (Grouped by Business Domain)

### Group A: Authentication & Access Control (6 Tables, #1–6)

#### 1. `users`
- **Domain Columns:**
  - `full_name`: `VARCHAR(150)`, NOT NULL
  - `email`: `VARCHAR(180)`, NOT NULL, UNIQUE, INDEXED
  - `phone`: `VARCHAR(30)`, NULLABLE
  - `password_hash`: `VARCHAR(255)`, NOT NULL
  - `last_login_at`: `DATETIME`, NULLABLE
  - `is_email_verified`: `BOOLEAN`, DEFAULT TRUE
- **Relationships:**
  - `user_roles`: 1:N with `user_roles`
  - `employee`: 1:1 with `employees`
  - `customer`: 1:1 with `customers`
  - `login_sessions`: 1:N with `login_sessions`

#### 2. `roles`
- **Domain Columns:**
  - `code`: `VARCHAR(50)`, NOT NULL, UNIQUE (e.g. `SUPER_ADMIN`, `BRANCH_MANAGER`, `BOOKING_AGENT`, `HUB_OPERATOR`, `DISPATCHER`, `DRIVER`, `FINANCE_OFFICER`, `SUPPORT_AGENT`, `CUSTOMER`)
  - `name`: `VARCHAR(100)`, NOT NULL
  - `description`: `VARCHAR(255)`, NULLABLE
- **Relationships:**
  - `user_roles`: 1:N with `user_roles`
  - `role_permissions`: 1:N with `role_permissions`

#### 3. `permissions`
- **Domain Columns:**
  - `code`: `VARCHAR(80)`, NOT NULL, UNIQUE (e.g. `SHIPMENT_CREATE`, `DISPATCH_MANAGE`, etc.)
  - `module`: `VARCHAR(50)`, NOT NULL
  - `description`: `VARCHAR(255)`, NULLABLE
- **Relationships:**
  - `role_permissions`: 1:N with `role_permissions`

#### 4. `user_roles`
- **Domain Columns:**
  - `user_id`: `INTEGER`, NOT NULL, FK -> `users.id`
  - `role_id`: `INTEGER`, NOT NULL, FK -> `roles.id`
  - `assigned_at`: `DATETIME`, NOT NULL, DEFAULT UTC Now
  - `assigned_by_user_id`: `INTEGER`, NULLABLE, FK -> `users.id`
- **Constraints:** UNIQUE(`user_id`, `role_id`)

#### 5. `role_permissions`
- **Domain Columns:**
  - `role_id`: `INTEGER`, NOT NULL, FK -> `roles.id`
  - `permission_id`: `INTEGER`, NOT NULL, FK -> `permissions.id`
- **Constraints:** UNIQUE(`role_id`, `permission_id`)

#### 6. `login_sessions`
- **Domain Columns:**
  - `user_id`: `INTEGER`, NOT NULL, FK -> `users.id`
  - `session_hash`: `VARCHAR(128)`, NOT NULL, UNIQUE
  - `started_at`: `DATETIME`, NOT NULL, DEFAULT UTC Now
  - `expires_at`: `DATETIME`, NOT NULL
  - `revoked_at`: `DATETIME`, NULLABLE
  - `ip_hint`: `VARCHAR(64)`, NULLABLE

---

### Group B: Organization, Employees & Service Zones (6 Tables, #7–12)

#### 7. `branches`
- **Domain Columns:**
  - `code`: `VARCHAR(30)`, NOT NULL, UNIQUE
  - `name`: `VARCHAR(150)`, NOT NULL
  - `phone`: `VARCHAR(30)`, NULLABLE
  - `address_line`: `VARCHAR(255)`, NOT NULL
  - `city`: `VARCHAR(100)`, NOT NULL
- **Relationships:**
  - `hubs`: 1:N
  - `employees`: 1:N
  - `routes`: 1:N

#### 8. `hubs`
- **Domain Columns:**
  - `branch_id`: `INTEGER`, NOT NULL, FK -> `branches.id`
  - `code`: `VARCHAR(30)`, NOT NULL, UNIQUE
  - `name`: `VARCHAR(150)`, NOT NULL
  - `location_note`: `VARCHAR(255)`, NULLABLE
- **Relationships:**
  - `branch`: FK reference
  - `incoming_transfers`: 1:N -> `hub_transfers.to_hub_id`
  - `outgoing_transfers`: 1:N -> `hub_transfers.from_hub_id`

#### 9. `employees`
- **Domain Columns:**
  - `user_id`: `INTEGER`, NOT NULL, UNIQUE, FK -> `users.id`
  - `primary_branch_id`: `INTEGER`, NOT NULL, FK -> `branches.id`
  - `employee_no`: `VARCHAR(40)`, NOT NULL, UNIQUE
  - `job_title`: `VARCHAR(100)`, NOT NULL
  - `hired_on`: `DATE`, NOT NULL
- **Relationships:**
  - `user`: FK reference
  - `branch`: FK reference
  - `employee_branches`: 1:N
  - `driver_profile`: 1:1 -> `drivers`

#### 10. `employee_branches`
- **Domain Columns:**
  - `employee_id`: `INTEGER`, NOT NULL, FK -> `employees.id`
  - `branch_id`: `INTEGER`, NOT NULL, FK -> `branches.id`
  - `is_primary`: `BOOLEAN`, NOT NULL DEFAULT FALSE
  - `assigned_on`: `DATE`, NOT NULL
- **Constraints:** UNIQUE(`employee_id`, `branch_id`)

#### 11. `service_zones`
- **Domain Columns:**
  - `code`: `VARCHAR(30)`, NOT NULL, UNIQUE
  - `name`: `VARCHAR(100)`, NOT NULL
  - `city`: `VARCHAR(100)`, NOT NULL
  - `region`: `VARCHAR(100)`, NOT NULL
  - `postal_prefix`: `VARCHAR(20)`, NULLABLE
- **Relationships:**
  - `branch_zones`: 1:N
  - `customer_addresses`: 1:N

#### 12. `branch_zones`
- **Domain Columns:**
  - `branch_id`: `INTEGER`, NOT NULL, FK -> `branches.id`
  - `zone_id`: `INTEGER`, NOT NULL, FK -> `service_zones.id`
  - `pickup_enabled`: `BOOLEAN`, NOT NULL DEFAULT TRUE
  - `delivery_enabled`: `BOOLEAN`, NOT NULL DEFAULT TRUE
- **Constraints:** UNIQUE(`branch_id`, `zone_id`)

---

### Group C: Customers, Addresses & Rate Catalogs (10 Tables, #13–22)

#### 13. `customers`
- **Domain Columns:**
  - `user_id`: `INTEGER`, NULLABLE, UNIQUE, FK -> `users.id`
  - `customer_code`: `VARCHAR(40)`, NOT NULL, UNIQUE
  - `full_name`: `VARCHAR(150)`, NOT NULL
  - `phone`: `VARCHAR(30)`, NOT NULL
  - `email`: `VARCHAR(180)`, NULLABLE
- **Relationships:**
  - `contacts`: 1:N
  - `addresses`: 1:N
  - `recipients`: 1:N
  - `shipments`: 1:N

#### 14. `customer_contacts`
- **Domain Columns:**
  - `customer_id`: `INTEGER`, NOT NULL, FK -> `customers.id`
  - `name`: `VARCHAR(150)`, NOT NULL
  - `phone`: `VARCHAR(30)`, NOT NULL
  - `contact_type`: `VARCHAR(40)`, DEFAULT 'PRIMARY'
  - `is_primary`: `BOOLEAN`, DEFAULT FALSE

#### 15. `customer_addresses`
- **Domain Columns:**
  - `customer_id`: `INTEGER`, NOT NULL, FK -> `customers.id`
  - `zone_id`: `INTEGER`, NOT NULL, FK -> `service_zones.id`
  - `label`: `VARCHAR(60)`, DEFAULT 'Office'
  - `line1`: `VARCHAR(255)`, NOT NULL
  - `city`: `VARCHAR(100)`, NOT NULL
  - `postal_code`: `VARCHAR(20)`, NULLABLE

#### 16. `recipient_profiles`
- **Domain Columns:**
  - `customer_id`: `INTEGER`, NOT NULL, FK -> `customers.id`
  - `name`: `VARCHAR(150)`, NOT NULL
  - `phone`: `VARCHAR(30)`, NOT NULL
  - `email`: `VARCHAR(180)`, NULLABLE
- **Relationships:**
  - `addresses`: 1:N -> `recipient_addresses`

#### 17. `recipient_addresses`
- **Domain Columns:**
  - `recipient_id`: `INTEGER`, NOT NULL, FK -> `recipient_profiles.id`
  - `zone_id`: `INTEGER`, NOT NULL, FK -> `service_zones.id`
  - `line1`: `VARCHAR(255)`, NOT NULL
  - `city`: `VARCHAR(100)`, NOT NULL
  - `postal_code`: `VARCHAR(20)`, NULLABLE

#### 18. `service_types`
- **Domain Columns:**
  - `code`: `VARCHAR(40)`, NOT NULL, UNIQUE (e.g. `STANDARD`, `EXPRESS`, `OVERNIGHT`, `SAME_DAY`)
  - `name`: `VARCHAR(100)`, NOT NULL
  - `target_days`: `INTEGER`, NOT NULL DEFAULT 2
  - `description`: `VARCHAR(255)`, NULLABLE

#### 19. `parcel_categories`
- **Domain Columns:**
  - `code`: `VARCHAR(40)`, NOT NULL, UNIQUE (e.g. `DOC`, `ELECTRONICS`, `APPAREL`, `FRAGILE`, `GENERAL`)
  - `name`: `VARCHAR(100)`, NOT NULL
  - `is_fragile`: `BOOLEAN`, NOT NULL DEFAULT FALSE

#### 20. `packaging_types`
- **Domain Columns:**
  - `code`: `VARCHAR(40)`, NOT NULL, UNIQUE (e.g. `FLYER_S`, `BOX_M`, `WOODEN_CRATE`)
  - `name`: `VARCHAR(100)`, NOT NULL
  - `fee_paisa`: `INTEGER`, NOT NULL DEFAULT 0 (CHECK fee_paisa >= 0)
  - `max_weight_grams`: `INTEGER`, NOT NULL DEFAULT 5000

#### 21. `rate_cards`
- **Domain Columns:**
  - `service_type_id`: `INTEGER`, NOT NULL, FK -> `service_types.id`
  - `origin_zone_id`: `INTEGER`, NOT NULL, FK -> `service_zones.id`
  - `destination_zone_id`: `INTEGER`, NOT NULL, FK -> `service_zones.id`
  - `valid_from`: `DATE`, NOT NULL
  - `valid_until`: `DATE`, NOT NULL
  - `currency`: `VARCHAR(10)`, NOT NULL DEFAULT 'PKR'
- **Constraints:** UNIQUE(`service_type_id`, `origin_zone_id`, `destination_zone_id`, `valid_from`)

#### 22. `rate_card_rules`
- **Domain Columns:**
  - `rate_card_id`: `INTEGER`, NOT NULL, FK -> `rate_cards.id`
  - `min_weight_grams`: `INTEGER`, NOT NULL DEFAULT 0
  - `max_weight_grams`: `INTEGER`, NOT NULL
  - `base_fee_paisa`: `INTEGER`, NOT NULL
  - `extra_per_kg_paisa`: `INTEGER`, NOT NULL DEFAULT 0
- **Constraints:** CHECK(`min_weight_grams` < `max_weight_grams`), CHECK(`base_fee_paisa` >= 0)

---

### Group D: Shipment Booking & Pickup (8 Tables, #23–30)

#### 23. `shipments`
- **Domain Columns:**
  - `tracking_number`: `VARCHAR(40)`, NOT NULL, UNIQUE, INDEXED
  - `customer_id`: `INTEGER`, NOT NULL, FK -> `customers.id`
  - `origin_branch_id`: `INTEGER`, NOT NULL, FK -> `branches.id`
  - `destination_branch_id`: `INTEGER`, NULLABLE, FK -> `branches.id`
  - `service_type_id`: `INTEGER`, NOT NULL, FK -> `service_types.id`
  - `parcel_category_id`: `INTEGER`, NOT NULL, FK -> `parcel_categories.id`
  - `packaging_type_id`: `INTEGER`, NOT NULL, FK -> `packaging_types.id`
  - `booking_employee_id`: `INTEGER`, NULLABLE, FK -> `employees.id`
  - `current_hub_id`: `INTEGER`, NULLABLE, FK -> `hubs.id`
  - `weight_grams`: `INTEGER`, NOT NULL (CHECK weight_grams > 0)
  - `declared_value_paisa`: `INTEGER`, NOT NULL DEFAULT 0
  - `cod_due_paisa`: `INTEGER`, NOT NULL DEFAULT 0
  - `booked_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `shipment_status`: `VARCHAR(40)`, NOT NULL DEFAULT 'BOOKED'
  - `total_charge_paisa`: `INTEGER`, NOT NULL DEFAULT 0

#### 24. `shipment_items`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `description`: `VARCHAR(255)`, NOT NULL
  - `quantity`: `INTEGER`, NOT NULL DEFAULT 1 (CHECK quantity > 0)
  - `weight_grams`: `INTEGER`, NOT NULL DEFAULT 1 (CHECK weight_grams > 0)
  - `declared_value_paisa`: `INTEGER`, NOT NULL DEFAULT 0

#### 25. `shipment_addresses`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `address_role`: `VARCHAR(20)`, NOT NULL CHECK(`address_role` IN ('SENDER', 'RECIPIENT'))
  - `person_name`: `VARCHAR(150)`, NOT NULL
  - `phone`: `VARCHAR(30)`, NOT NULL
  - `line1`: `VARCHAR(255)`, NOT NULL
  - `city`: `VARCHAR(100)`, NOT NULL
  - `postal_code`: `VARCHAR(20)`, NULLABLE
  - `zone_id`: `INTEGER`, NOT NULL, FK -> `service_zones.id`
- **Constraints:** UNIQUE(`shipment_id`, `address_role`)

#### 26. `shipment_services`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `service_type_id`: `INTEGER`, NOT NULL, FK -> `service_types.id`
  - `quoted_rate_card_id`: `INTEGER`, NOT NULL, FK -> `rate_cards.id`
  - `quoted_rule_id`: `INTEGER`, NOT NULL, FK -> `rate_card_rules.id`
  - `base_fee_paisa`: `INTEGER`, NOT NULL
  - `packaging_fee_paisa`: `INTEGER`, NOT NULL DEFAULT 0
  - `discount_paisa`: `INTEGER`, NOT NULL DEFAULT 0
  - `tax_paisa`: `INTEGER`, NOT NULL DEFAULT 0
  - `total_paisa`: `INTEGER`, NOT NULL
  - `currency`: `VARCHAR(10)`, NOT NULL DEFAULT 'PKR'

#### 27. `shipment_documents`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `uploaded_by_user_id`: `INTEGER`, NOT NULL, FK -> `users.id`
  - `document_type`: `VARCHAR(50)`, NOT NULL
  - `stored_filename`: `VARCHAR(255)`, NOT NULL
  - `original_filename`: `VARCHAR(255)`, NOT NULL
  - `mime_type`: `VARCHAR(100)`, NOT NULL
  - `file_size`: `INTEGER`, NOT NULL

#### 28. `pickup_requests`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `pickup_address_id`: `INTEGER`, NOT NULL, FK -> `shipment_addresses.id`
  - `requested_start`: `DATETIME`, NOT NULL
  - `requested_end`: `DATETIME`, NOT NULL
  - `pickup_status`: `VARCHAR(30)`, NOT NULL DEFAULT 'PENDING'
  - `notes`: `VARCHAR(255)`, NULLABLE

#### 29. `pickup_assignments`
- **Domain Columns:**
  - `pickup_request_id`: `INTEGER`, NOT NULL, FK -> `pickup_requests.id`
  - `employee_id`: `INTEGER`, NOT NULL, FK -> `employees.id`
  - `driver_id`: `INTEGER`, NULLABLE, FK -> `drivers.id`
  - `vehicle_id`: `INTEGER`, NULLABLE, FK -> `vehicles.id`
  - `assigned_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `completed_at`: `DATETIME`, NULLABLE

#### 30. `shipment_status_history`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `previous_status`: `VARCHAR(40)`, NULLABLE
  - `new_status`: `VARCHAR(40)`, NOT NULL
  - `changed_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `actor_user_id`: `INTEGER`, NULLABLE, FK -> `users.id`
  - `reason`: `VARCHAR(255)`, NULLABLE
- **Immutability:** Append-only history.

---

### Group E: Dispatch, Routing, Scans & Delivery (11 Tables, #31–41)

#### 31. `routes`
- **Domain Columns:**
  - `branch_id`: `INTEGER`, NOT NULL, FK -> `branches.id`
  - `driver_id`: `INTEGER`, NOT NULL, FK -> `drivers.id`
  - `vehicle_id`: `INTEGER`, NOT NULL, FK -> `vehicles.id`
  - `route_code`: `VARCHAR(40)`, NOT NULL, UNIQUE
  - `route_date`: `DATE`, NOT NULL
  - `route_status`: `VARCHAR(30)`, NOT NULL DEFAULT 'PLANNED'

#### 32. `route_stops`
- **Domain Columns:**
  - `route_id`: `INTEGER`, NOT NULL, FK -> `routes.id`
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `stop_sequence`: `INTEGER`, NOT NULL
  - `stop_type`: `VARCHAR(30)`, NOT NULL DEFAULT 'DELIVERY'
  - `scheduled_at`: `DATETIME`, NULLABLE
  - `completed_at`: `DATETIME`, NULLABLE
- **Constraints:** UNIQUE(`route_id`, `stop_sequence`)

#### 33. `hub_transfers`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `from_hub_id`: `INTEGER`, NOT NULL, FK -> `hubs.id`
  - `to_hub_id`: `INTEGER`, NOT NULL, FK -> `hubs.id`
  - `initiated_by_employee_id`: `INTEGER`, NOT NULL, FK -> `employees.id`
  - `received_by_employee_id`: `INTEGER`, NULLABLE, FK -> `employees.id`
  - `departed_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `received_at`: `DATETIME`, NULLABLE
  - `transfer_status`: `VARCHAR(30)`, NOT NULL DEFAULT 'IN_TRANSIT'
- **Constraints:** CHECK(`from_hub_id` != `to_hub_id`)

#### 34. `shipment_scans`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `hub_id`: `INTEGER`, NULLABLE, FK -> `hubs.id`
  - `scanned_by_employee_id`: `INTEGER`, NOT NULL, FK -> `employees.id`
  - `scan_code`: `VARCHAR(40)`, NOT NULL
  - `scanned_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `notes`: `VARCHAR(255)`, NULLABLE

#### 35. `tracking_events`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `status_history_id`: `INTEGER`, NULLABLE, FK -> `shipment_status_history.id`
  - `event_code`: `VARCHAR(50)`, NOT NULL
  - `public_message`: `VARCHAR(255)`, NOT NULL
  - `occurred_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `hub_id`: `INTEGER`, NULLABLE, FK -> `hubs.id`
  - `actor_user_id`: `INTEGER`, NULLABLE, FK -> `users.id`
  - `visible_to_customer`: `BOOLEAN`, NOT NULL DEFAULT TRUE

#### 36. `delivery_attempts`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `route_stop_id`: `INTEGER`, NULLABLE, FK -> `route_stops.id`
  - `driver_id`: `INTEGER`, NOT NULL, FK -> `drivers.id`
  - `attempted_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `outcome`: `VARCHAR(30)`, NOT NULL CHECK(`outcome` IN ('SUCCESS', 'FAILED', 'RESCHEDULED'))
  - `failure_reason`: `VARCHAR(255)`, NULLABLE

#### 37. `delivery_proofs`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `delivery_attempt_id`: `INTEGER`, NOT NULL, UNIQUE, FK -> `delivery_attempts.id`
  - `received_by_name`: `VARCHAR(150)`, NOT NULL
  - `signed_filename`: `VARCHAR(255)`, NULLABLE
  - `photo_filename`: `VARCHAR(255)`, NULLABLE
  - `delivered_at`: `DATETIME`, NOT NULL DEFAULT UTC Now

#### 38. `delivery_exceptions`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `delivery_attempt_id`: `INTEGER`, NULLABLE, FK -> `delivery_attempts.id`
  - `exception_code`: `VARCHAR(50)`, NOT NULL
  - `explanation`: `VARCHAR(255)`, NOT NULL
  - `opened_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `resolved_at`: `DATETIME`, NULLABLE

#### 39. `vehicles`
- **Domain Columns:**
  - `branch_id`: `INTEGER`, NOT NULL, FK -> `branches.id`
  - `plate_number`: `VARCHAR(30)`, NOT NULL, UNIQUE
  - `vehicle_type`: `VARCHAR(40)`, NOT NULL (e.g. `MOTORCYCLE`, `VAN`, `TRUCK`)
  - `capacity_grams`: `INTEGER`, NOT NULL DEFAULT 50000
  - `service_due_on`: `DATE`, NULLABLE

#### 40. `drivers`
- **Domain Columns:**
  - `employee_id`: `INTEGER`, NOT NULL, UNIQUE, FK -> `employees.id`
  - `license_number`: `VARCHAR(50)`, NOT NULL, UNIQUE
  - `license_expires_on`: `DATE`, NOT NULL

#### 41. `vehicle_assignments`
- **Domain Columns:**
  - `vehicle_id`: `INTEGER`, NOT NULL, FK -> `vehicles.id`
  - `driver_id`: `INTEGER`, NOT NULL, FK -> `drivers.id`
  - `route_id`: `INTEGER`, NULLABLE, FK -> `routes.id`
  - `assigned_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `released_at`: `DATETIME`, NULLABLE

---

### Group F: Finance, Payments & Discounts (8 Tables, #42–49)

#### 42. `invoices`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, UNIQUE, FK -> `shipments.id`
  - `customer_id`: `INTEGER`, NOT NULL, FK -> `customers.id`
  - `invoice_number`: `VARCHAR(50)`, NOT NULL, UNIQUE, INDEXED
  - `subtotal_paisa`: `INTEGER`, NOT NULL
  - `discount_paisa`: `INTEGER`, NOT NULL DEFAULT 0
  - `tax_paisa`: `INTEGER`, NOT NULL DEFAULT 0
  - `total_paisa`: `INTEGER`, NOT NULL (CHECK total_paisa >= 0)
  - `currency`: `VARCHAR(10)`, NOT NULL DEFAULT 'PKR'
  - `invoice_status`: `VARCHAR(30)`, NOT NULL DEFAULT 'ISSUED'
  - `issued_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `due_at`: `DATETIME`, NOT NULL

#### 43. `invoice_items`
- **Domain Columns:**
  - `invoice_id`: `INTEGER`, NOT NULL, FK -> `invoices.id`
  - `shipment_service_id`: `INTEGER`, NULLABLE, FK -> `shipment_services.id`
  - `description`: `VARCHAR(255)`, NOT NULL
  - `quantity`: `INTEGER`, NOT NULL DEFAULT 1
  - `unit_price_paisa`: `INTEGER`, NOT NULL
  - `line_total_paisa`: `INTEGER`, NOT NULL

#### 44. `payments`
- **Domain Columns:**
  - `invoice_id`: `INTEGER`, NOT NULL, FK -> `invoices.id`
  - `received_by_employee_id`: `INTEGER`, NULLABLE, FK -> `employees.id`
  - `amount_paisa`: `INTEGER`, NOT NULL (CHECK amount_paisa > 0)
  - `method`: `VARCHAR(30)`, NOT NULL (e.g. `CASH`, `BANK_TRANSFER`, `SIMULATED_ONLINE`)
  - `reference_code`: `VARCHAR(60)`, NULLABLE
  - `paid_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `payment_status`: `VARCHAR(30)`, NOT NULL DEFAULT 'SETTLED'

#### 45. `cod_collections`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, UNIQUE, FK -> `shipments.id`
  - `collected_by_driver_id`: `INTEGER`, NOT NULL, FK -> `drivers.id`
  - `amount_paisa`: `INTEGER`, NOT NULL (CHECK amount_paisa > 0)
  - `collected_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `collection_status`: `VARCHAR(30)`, NOT NULL DEFAULT 'COLLECTED'

#### 46. `cod_remittances`
- **Domain Columns:**
  - `cod_collection_id`: `INTEGER`, NOT NULL, FK -> `cod_collections.id`
  - `received_by_employee_id`: `INTEGER`, NOT NULL, FK -> `employees.id`
  - `amount_paisa`: `INTEGER`, NOT NULL (CHECK amount_paisa > 0)
  - `remitted_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `reference_code`: `VARCHAR(60)`, NOT NULL
  - `remittance_status`: `VARCHAR(30)`, NOT NULL DEFAULT 'COMPLETED'

#### 47. `refunds`
- **Domain Columns:**
  - `payment_id`: `INTEGER`, NOT NULL, FK -> `payments.id`
  - `authorized_by_employee_id`: `INTEGER`, NOT NULL, FK -> `employees.id`
  - `amount_paisa`: `INTEGER`, NOT NULL (CHECK amount_paisa > 0)
  - `reason`: `VARCHAR(255)`, NOT NULL
  - `refund_status`: `VARCHAR(30)`, NOT NULL DEFAULT 'PROCESSED'
  - `requested_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `processed_at`: `DATETIME`, NULLABLE

#### 48. `discounts`
- **Domain Columns:**
  - `code`: `VARCHAR(40)`, NOT NULL, UNIQUE
  - `discount_type`: `VARCHAR(20)`, NOT NULL CHECK(`discount_type` IN ('FIXED', 'PERCENTAGE'))
  - `value`: `INTEGER`, NOT NULL (paisa or percent basis point)
  - `valid_from`: `DATE`, NOT NULL
  - `valid_until`: `DATE`, NOT NULL
  - `max_redemptions`: `INTEGER`, NULLABLE

#### 49. `shipment_discounts`
- **Domain Columns:**
  - `shipment_id`: `INTEGER`, NOT NULL, FK -> `shipments.id`
  - `discount_id`: `INTEGER`, NOT NULL, FK -> `discounts.id`
  - `applied_amount_paisa`: `INTEGER`, NOT NULL
- **Constraints:** UNIQUE(`shipment_id`, `discount_id`)

---

### Group G: Support, Notifications & Auditing (6 Tables, #50–55)

#### 50. `support_tickets`
- **Domain Columns:**
  - `ticket_number`: `VARCHAR(50)`, NOT NULL, UNIQUE, INDEXED
  - `customer_id`: `INTEGER`, NOT NULL, FK -> `customers.id`
  - `shipment_id`: `INTEGER`, NULLABLE, FK -> `shipments.id`
  - `assigned_employee_id`: `INTEGER`, NULLABLE, FK -> `employees.id`
  - `subject`: `VARCHAR(200)`, NOT NULL
  - `priority`: `VARCHAR(20)`, NOT NULL DEFAULT 'MEDIUM'
  - `ticket_status`: `VARCHAR(30)`, NOT NULL DEFAULT 'OPEN'
  - `opened_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `closed_at`: `DATETIME`, NULLABLE

#### 51. `ticket_messages`
- **Domain Columns:**
  - `ticket_id`: `INTEGER`, NOT NULL, FK -> `support_tickets.id`
  - `sender_user_id`: `INTEGER`, NULLABLE, FK -> `users.id`
  - `sender_employee_id`: `INTEGER`, NULLABLE, FK -> `employees.id`
  - `sender_customer_id`: `INTEGER`, NULLABLE, FK -> `customers.id`
  - `body`: `TEXT`, NOT NULL
  - `is_internal`: `BOOLEAN`, NOT NULL DEFAULT FALSE
  - `posted_at`: `DATETIME`, NOT NULL DEFAULT UTC Now

#### 52. `notifications`
- **Domain Columns:**
  - `user_id`: `INTEGER`, NULLABLE, FK -> `users.id`
  - `customer_id`: `INTEGER`, NULLABLE, FK -> `customers.id`
  - `shipment_id`: `INTEGER`, NULLABLE, FK -> `shipments.id`
  - `template_id`: `INTEGER`, NULLABLE, FK -> `notification_templates.id`
  - `channel`: `VARCHAR(20)`, NOT NULL DEFAULT 'IN_APP'
  - `recipient`: `VARCHAR(180)`, NOT NULL
  - `subject`: `VARCHAR(200)`, NOT NULL
  - `body`: `TEXT`, NOT NULL
  - `delivery_status`: `VARCHAR(30)`, NOT NULL DEFAULT 'SENT'
  - `created_for_event_at`: `DATETIME`, NOT NULL DEFAULT UTC Now
  - `sent_at`: `DATETIME`, NULLABLE

#### 53. `notification_templates`
- **Domain Columns:**
  - `code`: `VARCHAR(50)`, NOT NULL, UNIQUE
  - `channel`: `VARCHAR(20)`, NOT NULL DEFAULT 'IN_APP'
  - `subject_template`: `VARCHAR(200)`, NOT NULL
  - `body_template`: `TEXT`, NOT NULL

#### 54. `audit_logs`
- **Domain Columns:**
  - `actor_user_id`: `INTEGER`, NULLABLE, FK -> `users.id`
  - `branch_id`: `INTEGER`, NULLABLE, FK -> `branches.id`
  - `entity_type`: `VARCHAR(60)`, NOT NULL
  - `entity_id`: `INTEGER`, NOT NULL
  - `action`: `VARCHAR(40)`, NOT NULL
  - `before_json`: `TEXT`, NULLABLE
  - `after_json`: `TEXT`, NULLABLE
  - `occurred_at`: `DATETIME`, NOT NULL DEFAULT UTC Now

#### 55. `app_settings`
- **Domain Columns:**
  - `setting_key`: `VARCHAR(60)`, NOT NULL, UNIQUE
  - `value_json`: `TEXT`, NOT NULL
  - `description`: `VARCHAR(255)`, NULLABLE

---

## 3. Total Schema Count Summary
- Group A: 6
- Group B: 6
- Group C: 10
- Group D: 8
- Group E: 11
- Group F: 8
- Group G: 6
- **Total Relational Business Tables: Exactly 55**
