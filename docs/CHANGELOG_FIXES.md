# Complete Changelog & Discovered Defects Remediation

**Project:** Smart Courier & Parcel Delivery Management System  
**Audit Scope:** Defects A01–A24 and Customer Self-Service Booking & Journey Fixes  
**Status:** **All Discovered Defects Remediated & Covered by Automated Tests**

---

## 1. Critical Severity Defects

| Defect Code | Component | Description & Root Cause | Resolution Implemented | Impact & Verification |
|:---|:---|:---|:---|:---|
| **CRIT-01** | `shipments/routes.py` | Customer received HTTP 403 on `/shipments/new` because `@roles_required` omitted `CUSTOMER`. | Added `CUSTOMER` to decorator. Handled customer vs staff branch logic. | Customers can open booking form and book parcels. Tested in `test_customer_booking_and_journey.py::test_01_customer_can_open_booking_get`. |
| **CRIT-02** | `seed_service.py` | Role permissions mapping in database seed had `"CUSTOMER": []`, granting zero DB permissions. | Granted `SHIPMENT_BOOK` and `SHIPMENT_VIEW` to `CUSTOMER` role. | Customer role now possesses real relational database permissions. |
| **CRIT-03** | `shipments/routes.py` | Booking route trusted client-submitted `customer_id` from form/POST, enabling identity spoofing. | Bound `customer_id = current_user.customer.id` server-side; ignores client overrides. | Customer can only book for self. Tested in `test_customer_booking_and_journey.py::test_04_customer_cannot_post_other_customer_id`. |
| **CRIT-04** | `shipment_service.py` | Service layer trusted caller-provided `customer_id` without ownership checks. | Added domain-level validation: customer actors must own the `customer_id` argument. | Prevents API-level bypass. Tested in `test_customer_booking_and_journey.py::test_11_customer_service_boundary_rejects_forged_customer_id`. |
| **CRIT-05** | `auth/routes.py` | System had login but no customer self-registration, blocking new users from onboarding. | Implemented `/auth/register` with atomic User + CUSTOMER role + Customer profile creation. | New users can sign up and book immediately. Tested in `test_customer_booking_and_journey.py::test_12_customer_registration_success`. |
| **CRIT-06** | `hub_service.py` | Hub transfer could be initiated on parcels in `BOOKED` status, causing illegal state jumps. | Added prerequisite validation: parcels must be physically received at hub (`AT_ORIGIN_HUB`). | Enforces legal logistics state machine. Tested in `test_audit_fixes_regression.py::test_a03_hub_transfer_rejects_booked_shipment`. |

---

## 2. High Severity Defects

| Defect Code | Component | Description & Root Cause | Resolution Implemented | Impact & Verification |
|:---|:---|:---|:---|:---|
| **HIGH-01** | `dispatch_service.py` | Route stops permitted adding `IN_TRANSIT` parcels directly to delivery runsheet before destination arrival. | Added prerequisite: delivery stops require `AT_DESTINATION_HUB`, `DELIVERY_FAILED`, or `OUT_FOR_DELIVERY`. | Prevents premature delivery dispatch. Tested in `test_audit_fixes_regression.py::test_a04_dispatch_stop_rejects_in_transit_shipment`. |
| **HIGH-02** | `catalog/routes.py` | Rate card weight band endpoint checked permission on GET but omitted check on POST. | Added explicit `abort(403)` on POST for non-admin/manager roles. | Prevents unauthorized rate tampering. Tested in `test_audit_fixes_regression.py::test_a09_non_admin_cannot_post_rate_card_rule`. |
| **HIGH-03** | `support/routes.py` | Support ticket close route lacked object-level ownership check, allowing users to close others' tickets. | Added ownership assertion: customers can only close tickets where `ticket.customer_id == current_user.customer.id`. | Prevents ticket tampering across tenants. Tested in `test_audit_fixes_regression.py::test_a13_customer_cannot_close_other_customer_ticket`. |
| **HIGH-04** | `drivers/routes.py` | Driver delivery attempt POST accepted arbitrary `driver_id` from client form data. | Enforced session-backed driver identity: `driver_id = current_user.employee.driver_profile.id`. | Prevents drivers forging attempts for others. Tested in `test_audit_fixes_regression.py::test_a16_driver_cannot_submit_attempt_for_another_driver`. |
| **HIGH-05** | `finance_service.py` | Invoices remained in `PAID` status after full refund because in-memory refund relationship was not flushed. | Added in-memory `payment.refunds.append(refund)` and flush prior to recalculating balance; reverts to `ISSUED`. | Restores correct billing state. Tested in `test_audit_fixes_regression.py::test_a23_invoice_status_reopens_after_refund`. |

---

## 3. Medium Severity Defects

| Defect Code | Component | Description & Root Cause | Resolution Implemented | Impact & Verification |
|:---|:---|:---|:---|:---|
| **MED-01** | `base.html` & `rbac.py` | Sidebar navigation rendered inaccessible modules (Hub Scans, Dispatch, Staff, Rates) to low-privileged roles. | Implemented `caps` context processor and dedicated `show_customer_section` to filter navigation. | Clean, role-scoped menus with zero 403 dead ends. Tested in `test_audit_fixes_regression.py::test_a01_sidebar_navigation_filtered_by_role`. |
| **MED-02** | `main/routes.py` | Customer dashboard displayed company-wide shipment volume and financial metrics. | Scoped dashboard queries by `current_user.customer.id`; non-admins only see own shipments, dues, and tickets. | Customer data privacy guaranteed. Tested in `test_audit_fixes_regression.py::test_a02_dashboard_kpis_scoped_for_customer`. |
| **MED-03** | `customers/routes.py` | Customer profile, address addition, and recipient addition endpoints omitted `CUSTOMER` from `@roles_required`. | Added `CUSTOMER` with strict ownership checks (`customer_id == current_user.customer.id`). | Customers can manage their own address book without 403s. Tested in `test_customer_booking_and_journey.py::test_14_customer_address_book_isolation`. |
| **MED-04** | `finance/routes.py` | Parsing `int(request.form.get("amount_paisa"))` threw unhandled `ValueError` on bad or empty inputs. | Added defensive integer parsing, flash validation errors, and `db.session.rollback()`. | Prevents 500 crashes on invalid inputs. |
| **MED-05** | `main/routes.py` | Accessed `current_user.employee.driver` instead of `driver_profile`, crashing when driver logged in. | Corrected relationship attribute to `current_user.employee.driver_profile`. | Drivers can access dashboard cleanly. |

---

## 4. Low Severity & Usability Polish Defects

| Defect Code | Component | Description & Root Cause | Resolution Implemented | Impact & Verification |
|:---|:---|:---|:---|:---|
| **LOW-01** | `login.html` & `index.html` | Public HTML source displayed hardcoded demo passwords. | Removed plaintext credentials; added safe instructions pointing to `README.md`. | Verified in `test_audit_fixes_regression.py::test_a19_no_plaintext_passwords_in_public_html`. |
| **LOW-02** | `install_dependencies.bat` & `run.bat` | Batch files crashed when directory paths contained spaces or when double-clicked from another folder. | Added `cd /d "%~dp0"` and wrapped all path variables in quotes (`"%~dp0"`). | Standalone one-click execution verified on Windows. |
| **LOW-03** | `run.bat` | Browser launched before Flask development server finished binding to port 5000. | Added background PowerShell health-check polling loop before opening the browser. | Browser only opens once the server is healthy. |
| **LOW-04** | `shipment_service.py` | SQLAlchemy 2.0 `LegacyAPIWarning` when calling `User.query.get()`. | Updated to modern `db.session.get(User, actor_user_id)`. | Clean pytest execution with zero warnings. |
