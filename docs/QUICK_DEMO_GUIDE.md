# Smart Courier — Quick Academic Demo & Viva Guide

This guide provides simple, step-by-step instructions for demonstrating the Smart Courier system during a university viva or project presentation.

---

## 1. Quick Start Commands

From your project virtual environment:

```powershell
# 1. Inspect the 55 relational business tables (confirms SQLite FKs and audit columns)
flask --app run.py verify-schema

# 2. Seed or preview the 5 academic showcase entries
flask --app run.py seed-showcase --confirm

# 3. View the generated test tracking numbers and routes
flask --app run.py show-demo-entries

# 4. Run the full automated test suite
python -m pytest tests/
```

---

## 2. Five Illustrative Showcase Entries

These entries demonstrate the core shipment lifecycle stages using **real dynamic pricing** (computed via `PricingService` from active rate cards):

| Reference | Consignment | Weight | Route | Stage | What to Demonstrate |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **`DEMO-DOC-01`** | Legal documents | 350g | Lahore &rarr; Islamabad | **BOOKED** | Initial consignment booking, dynamic price quote, invoice creation, and public tracking event. |
| **`DEMO-CLOTH-02`** | Clothing parcel | 800g | Lahore &rarr; Karachi | **IN_TRANSIT** | Origin hub sorting scan, linehaul transit departure, and inter-city movement timeline. |
| **`DEMO-ELEC-03`** | Small electronic item | 500g | Lahore &rarr; Lahore | **OUT_FOR_DELIVERY** | Dispatch route creation, courier rider stop assignment, and rider runsheet workspace. |
| **`DEMO-SHOE-04`** | Shoes | 900g | Karachi &rarr; Lahore | **DELIVERED** | Final successful delivery verification, recipient electronic delivery proof, and paid invoice settlement. |
| **`DEMO-GLASS-05`** | Fragile household item | 700g | Islamabad &rarr; Lahore | **DELIVERY_FAILED** | Unsuccessful delivery attempt (recipient unavailable), delivery exception logging, and linked customer support ticket. |

---

## 3. How to Demonstrate in 3 Minutes

1. **Direct Login Page (`/auth/login`):**
   * Open `http://localhost:5000/` as a guest. Notice it redirects smoothly to `/auth/login`.
   * Point out the modern split-screen design: left delivery branding and graphics, right clean card with CSRF-protected form.
   * Test the public tracking input at the bottom of the login form using any of the 5 tracking numbers from `show-demo-entries`.

2. **Role-Aware Dashboard (`/`):**
   * Log in as the showcase demo customer (`demo.merchant@smartcourier.pk`) or standard demo customer (`customer@smartcourier.pk`).
   * Show the 4 summary count cards (Total Parcels, In Transit, Delivered, Delivery Failed).
   * Explain the **7-Day Activity Bar Chart**: Computed in Python using `datetime` arithmetic, scaled to 100%, and rendered with clean CSS without heavy JavaScript libraries.
   * Explain the **Delivery Status Donut**: Rendered using CSS `conic-gradient` with angles calculated from actual database records.

3. **Secure Logout (`POST /auth/logout`):**
   * Click user profile &rarr; Logout.
   * Point out that it sends a secure CSRF-protected POST request, clears the session, and redirects directly back to the redesigned login page with a success flash message.
   * Click the browser **Back button** to prove that the private dashboard is never served from cache thanks to `Cache-Control: no-store`.

4. **Staff Data Scoping & RBAC:**
   * Log in as `driver1@smartcourier.pk` &rarr; Driver workspace shows assigned runsheets.
   * Attempting to access `/admin/users` or `/finance/invoices` yields strict **403 Forbidden**.

---

## 4. Key Viva Questions & Answers

### Q: Why did you redirect `/` and `/auth/logout` to `/auth/login`?
> **Answer:** "In a commercial logistics web application, visitors and logged-out users should arrive directly at the sign-in and public tracking portal. Redirecting guest traffic from root `/` to `/auth/login` ensures a seamless, modern entry experience without exposing internal staff emails or obsolete landing pages."

### Q: How did you fix the scrolling problem on the login page?
> **Answer:** "Previously, the split layout had hardcoded minimum heights and large padding that pushed controls below 768px laptop viewports. We streamlined the CSS grid dimensions, reduced decorative white space, and removed nested scrollbars. Now, the entire page fits on standard 1366x768 screens without scrolling, and uses exactly one smooth document scrollbar if viewed on smaller mobile displays."

### Q: How is showcase demo data kept separate from real production records?
> **Answer:** "Showcase demo records are completely opt-in. The CLI command `seed-showcase` requires `--confirm` and will not run automatically in deployment scripts (`start.sh`) or migrations. The sample shipments are tagged with demo reference labels stored in `AppSetting` without altering the 55-table database schema."
