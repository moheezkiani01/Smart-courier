# Customer Booking Defect Remediation & Guided UX Report

**Defect Scope:** Customer self-service booking blocked with HTTP 403 Forbidden, cluttered administrative booking form, missing customer registration, untrusted customer identity, and cross-customer data exposure.  
**Resolution Status:** **COMPLETELY RESOLVED & VERIFIED**  
**Associated Automated Tests:** `tests/test_customer_booking_and_journey.py` (15 tests passing)

---

## 1. Root Cause Analysis (Before Fix)

Prior to this remediation, when a registered or demo customer logged into Smart Courier and attempted to book a consignment, they encountered several systemic architectural blocks:

1. **Decorator Exclusion (HTTP 403):**  
   In [`app/blueprints/shipments/routes.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/blueprints/shipments/routes.py), the `/shipments/new` route was decorated with:
   ```python
   @roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "BOOKING_AGENT")
   ```
   The `CUSTOMER` role was omitted entirely, resulting in immediate HTTP 403 Forbidden when any customer clicked "Book Parcel".

2. **Empty Seed Permissions:**  
   In [`app/services/seed_service.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/services/seed_service.py), the `role_perms_map` defined `"CUSTOMER": []`. The `CUSTOMER` role lacked `SHIPMENT_BOOK` and `SHIPMENT_VIEW` database permissions.

3. **Untrusted Identity Parameter:**  
   The existing form [`ShipmentBookingForm`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/forms/shipment_forms.py) contained a mandatory `customer_id` dropdown displaying all customers in the database. When submitted, the route directly trusted `customer_id = form.customer_id.data` without validating whether the caller owned that account.

4. **Service Boundary Gap:**  
   [`ShipmentService.book_shipment()`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/services/shipment_service.py) accepted `customer_id` directly without asserting that non-admin callers could only book for their own customer record.

5. **Cluttered Administrative UI with Paisa Inputs:**  
   The template [`shipments/new.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/shipments/new.html) was a single administrative form requiring users to select internal branch IDs, entered monetary figures in raw *paisa* instead of *PKR*, and lacked saved address/recipient pickers.

6. **Missing Self-Registration:**  
   The authentication blueprint lacked a public customer registration flow (`/auth/register`), preventing new users from signing up and booking parcels without admin intervention.

---

## 2. Comprehensive Solutions Implemented

### A. Authorization & Centralized Capabilities
- Added `CUSTOMER` to the `@roles_required` decorator on `/shipments/new`.
- Updated [`seed_service.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/services/seed_service.py) with `"CUSTOMER": ["SHIPMENT_BOOK", "SHIPMENT_VIEW"]` and idempotently synced database role permissions.
- In [`app/security/rbac.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/security/rbac.py), structured `caps["is_customer"]` and `caps["show_customer_section"]` to provide customers with an exclusive, clutter-free navigation sidebar and dashboard.

### B. Secure Customer Identity Binding
- In [`app/blueprints/shipments/routes.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/blueprints/shipments/routes.py), `new()` detects `is_customer`.
- If the customer lacks a linked `Customer` record, one is safely auto-provisioned (`f"CUST-{current_user.id:04d}"`).
- `target_customer_id = current_user.customer.id` is enforced strictly server-side. Any tampered `customer_id` in form data, POST bodies, or URL parameters is completely ignored.
- In [`ShipmentService.book_shipment()`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/services/shipment_service.py), the domain service explicitly validates the actor:
  ```python
  if is_customer and not is_admin_or_staff:
      if not (actor_user.customer and actor_user.customer.id == customer_id):
          raise PermissionError("Customers can only book shipments for their own customer account.")
  ```

### C. 4-Step Guided Booking Wizard (TCS/Daraz-Style Convenience)
Rebuilt [`app/templates/shipments/new.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/shipments/new.html) into a clean, 4-step guided booking journey:
- **Step 1: Sender & Recipient:**
  - Auto-fills sender name and phone from the logged-in customer profile.
  - Offers "Use Saved Address" and "Use Saved Recipient" dropdowns.
  - Checkboxes to save entered address and recipient to address books with one click.
- **Step 2: Parcel Specifications:**
  - Category, service type (Standard/Express), pieces, weight in grams (with helpful kg notes).
  - Declared value in **PKR**.
  - Packaging type with transparent fee indicator.
- **Step 3: Pickup & COD Preferences:**
  - Choice between Doorstep Pickup and Branch Drop-off.
  - Pickup time slot selection (Morning, Afternoon, Evening) and special access instructions.
  - Cash on Delivery (COD) amount in **PKR** with an explicit notice that COD is money collected from the recipient on behalf of the sender.
- **Step 4: Quote, Review & Confirm:**
  - Real-time JSON quote preview via [`/catalog/api/quote`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/blueprints/catalog/routes.py).
  - Clear itemized breakdown: Base Freight + Packaging Fee - Discount = Total Shipping Charge in PKR.
  - Double-submit protection with button spinner upon submission.

### D. Customer Self-Registration Flow
- Implemented [`RegisterForm`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/forms/auth_forms.py) validating full name, normalized email, phone, and password match.
- Created [`/auth/register`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/blueprints/auth/routes.py) view function:
  - Atomically creates `User`, assigns `CUSTOMER` role, and creates linked `Customer` record.
  - Automatically logs the user in and redirects to the customer dashboard.
  - Rejects duplicate emails with a helpful alert.
  - Strictly prevents injecting staff roles.
- Created [`app/templates/auth/register.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/auth/register.html) with reciprocal sign-in links.

### E. Data Scoping & Cross-Customer Isolation
- In `shipments.show()`, `shipments.label()`, `finance.invoice_detail()`, and `customers.show()`, enforced object-level ownership checks:
  ```python
  if current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN"):
      if not (current_user.customer and current_user.customer.id == resource.customer_id):
          abort(403)
  ```
- Customer A cannot view, print, or access Customer B's shipment, label, address, or invoice even by guessing sequential IDs.

---

## 3. Files Modified & Added

| File Path | Action | Description |
|:---|:---|:---|
| [`app/blueprints/shipments/routes.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/blueprints/shipments/routes.py) | Modified | Added `CUSTOMER` to `@roles_required`, implemented server-side customer ID binding, auto-provisioning, branch inference, PKR handling |
| [`app/forms/shipment_forms.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/forms/shipment_forms.py) | Modified | Made `customer_id` optional on form, added saved address selectors, PKR currency fields, pickup options |
| [`app/services/shipment_service.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/services/shipment_service.py) | Modified | Added service-boundary actor validation and customer identity ownership assertion |
| [`app/templates/shipments/new.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/shipments/new.html) | Modified | Complete rebuild into 4-step guided booking wizard with PKR, live quote preview, double-submit protection |
| [`app/services/seed_service.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/services/seed_service.py) | Modified | Granted `SHIPMENT_BOOK` and `SHIPMENT_VIEW` to `CUSTOMER` role |
| [`app/security/rbac.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/security/rbac.py) | Modified | Configured `caps["is_customer"]` and dedicated `caps["show_customer_section"]` |
| [`app/forms/auth_forms.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/forms/auth_forms.py) | Modified | Added `RegisterForm` |
| [`app/blueprints/auth/routes.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/blueprints/auth/routes.py) | Modified | Added `/auth/register` endpoint with atomic User + Role + Customer creation |
| [`app/templates/auth/register.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/auth/register.html) | Created | New customer registration template |
| [`app/templates/auth/login.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/auth/login.html) | Modified | Added link to customer registration |
| [`app/blueprints/catalog/routes.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/blueprints/catalog/routes.py) | Modified | Added `/catalog/api/quote` JSON endpoint for real-time calculation |
| [`app/blueprints/customers/routes.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/blueprints/customers/routes.py) | Modified | Allowed customers to access `show`, `add_address`, and `add_recipient` for their own profile with 403 isolation |
| [`app/templates/main/dashboard.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/main/dashboard.html) | Modified | Customer "My Parcels" header, + Book Parcel CTA, empty state, Quick Action cards |
| [`app/templates/base.html`](file:///C:/Users/hp/Desktop/SMART_COURIER/app/templates/base.html) | Modified | Added dedicated Customer Portal sidebar and top nav Register link |
| [`tests/test_customer_booking_and_journey.py`](file:///C:/Users/hp/Desktop/SMART_COURIER/tests/test_customer_booking_and_journey.py) | Created | 15 comprehensive automated tests for customer booking and isolation |

---

## 4. Verification & Testing Evidence

All 15 automated customer journey tests pass cleanly:

```text
tests/test_customer_booking_and_journey.py::test_01_customer_can_open_booking_get PASSED
tests/test_customer_booking_and_journey.py::test_02_customer_can_book_valid_parcel PASSED
tests/test_customer_booking_and_journey.py::test_03_customer_booking_sets_own_customer_id PASSED
tests/test_customer_booking_and_journey.py::test_04_customer_cannot_post_other_customer_id PASSED
tests/test_customer_booking_and_journey.py::test_05_customer_without_profile_auto_provisioned_safely PASSED
tests/test_customer_booking_and_journey.py::test_06_customer_booking_atomic_records PASSED
tests/test_customer_booking_and_journey.py::test_07_customer_booking_rollback_on_pricing_failure PASSED
tests/test_customer_booking_and_journey.py::test_08_customer_dashboard_contains_book_action PASSED
tests/test_customer_booking_and_journey.py::test_09_customer_cannot_see_other_customer_shipment PASSED
tests/test_customer_booking_and_journey.py::test_10_customer_cannot_see_other_customer_label_or_invoice PASSED
tests/test_customer_booking_and_journey.py::test_11_customer_service_boundary_rejects_forged_customer_id PASSED
tests/test_customer_booking_and_journey.py::test_12_customer_registration_success PASSED
tests/test_customer_booking_and_journey.py::test_13_customer_registration_duplicate_email_rejected PASSED
tests/test_customer_booking_and_journey.py::test_14_customer_address_book_isolation PASSED
tests/test_customer_booking_and_journey.py::test_15_live_quote_api_calculation PASSED
```
