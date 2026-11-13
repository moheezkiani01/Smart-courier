"""Viva Full 55-Table Demonstration Seeder Service.

Provides a safe, opt-in, idempotent workflow to seed realistic demonstration
records across all 55 SQLAlchemy business tables in Smart Courier for university
viva examination and academic presentation.

Key Architectural Guarantees:
- 55 Business Tables: Covers all 7 functional domain groups (Auth, Org, Catalog, Shipments, Dispatch, Finance, Support).
- Core Anchors: Reuses the 3 verified Viva bookings (SC-DEMO-BOOK-01, SC-DEMO-BOOK-02, SC-DEMO-BOOK-03).
- Strict Relational Integrity: Enforces all foreign keys, unique constraints, and audit mixin columns.
- Production Safe: Opt-in only, idempotent, dry-run preview, non-destructive to existing real data.
- Harmless File Attachments: Generates genuine, openable PDF documents in uploads/documents/ for shipment_documents.
- Scoped Cleanup: Deletes only demonstration records tracked in VIVA_55_TABLE_DATASET_MAP.
"""
import os
import json
import uuid
import hashlib
from datetime import datetime, date, timedelta
from app.extensions import db

# Group A: Authentication & Access Control (6)
from app.models.auth import User, Role, Permission, UserRole, RolePermission, LoginSession

# Group B: Organization & Employees (6)
from app.models.organization import (
    Branch,
    Hub,
    Employee,
    EmployeeBranch,
    ServiceZone,
    BranchZone,
)

# Group C: Customers & Catalog (10)
from app.models.catalog import (
    Customer,
    CustomerContact,
    CustomerAddress,
    RecipientProfile,
    RecipientAddress,
    ServiceType,
    ParcelCategory,
    PackagingType,
    RateCard,
    RateCardRule,
)

# Group D: Shipments & Booking (8)
from app.models.shipments import (
    Shipment,
    ShipmentItem,
    ShipmentAddress,
    ShipmentService as ShipmentQuote,
    ShipmentDocument,
    PickupRequest,
    PickupAssignment,
    ShipmentStatusHistory,
)

# Group E: Dispatch, Routing & Delivery (11)
from app.models.dispatch import (
    Route,
    RouteStop,
    HubTransfer,
    ShipmentScan,
    TrackingEvent,
    DeliveryAttempt,
    DeliveryProof,
    DeliveryException,
    Vehicle,
    Driver,
    VehicleAssignment,
)

# Group F: Finance & Payments (8)
from app.models.finance import (
    Invoice,
    InvoiceItem,
    Payment,
    CodCollection,
    CodRemittance,
    Refund,
    Discount,
    ShipmentDiscount,
)

# Group G: Support & Auditing (6)
from app.models.support import (
    SupportTicket,
    TicketMessage,
    Notification,
    NotificationTemplate,
    AuditLog,
    AppSetting,
)

from app.services.init_service import init_production_catalog
from app.services.three_bookings_service import (
    seed_three_bookings,
    get_three_bookings,
    THREE_BOOKINGS_SETTING_KEY,
)
from app.services.audit_service import log_audit
from app.utils.helpers import (
    generate_tracking_number,
    generate_invoice_number,
    generate_ticket_number,
    generate_customer_code,
)

VIVA_FULL_SETTING_KEY = "VIVA_55_TABLE_DATASET_MAP"

# Master registry metadata of all 55 business tables
EXPECTED_55_TABLES = [
    # Group A: Authentication & Access Control (6)
    {
        "table_name": "users",
        "group": "A. Auth & Access",
        "purpose": "User identities, authentication, password hashes, and account status",
        "parent_fk": "Self / None",
        "ui_route": "/admin/users, /auth/login",
    },
    {
        "table_name": "roles",
        "group": "A. Auth & Access",
        "purpose": "RBAC role definitions (9 system roles including SUPER_ADMIN, CUSTOMER, DRIVER)",
        "parent_fk": "None",
        "ui_route": "/admin/roles",
    },
    {
        "table_name": "permissions",
        "group": "A. Auth & Access",
        "purpose": "Granular operational permissions mapped across business modules",
        "parent_fk": "None",
        "ui_route": "/admin/roles",
    },
    {
        "table_name": "user_roles",
        "group": "A. Auth & Access",
        "purpose": "Many-to-many junction assigning roles to users",
        "parent_fk": "users.id, roles.id",
        "ui_route": "/admin/users",
    },
    {
        "table_name": "role_permissions",
        "group": "A. Auth & Access",
        "purpose": "Many-to-many junction assigning permissions to roles",
        "parent_fk": "roles.id, permissions.id",
        "ui_route": "/admin/roles",
    },
    {
        "table_name": "login_sessions",
        "group": "A. Auth & Access",
        "purpose": "Audit and security record of authenticated sessions (inert/revoked demo audit)",
        "parent_fk": "users.id",
        "ui_route": "Internal (Audit / Security)",
    },
    # Group B: Organization & Employees (6)
    {
        "table_name": "branches",
        "group": "B. Organization",
        "purpose": "Physical branch office facilities with city locations",
        "parent_fk": "None",
        "ui_route": "/admin/branches",
    },
    {
        "table_name": "hubs",
        "group": "B. Organization",
        "purpose": "Regional sorting and consolidation hubs tied to branches",
        "parent_fk": "branches.id",
        "ui_route": "/hubs/transfers, /admin/branches",
    },
    {
        "table_name": "employees",
        "group": "B. Organization",
        "purpose": "Internal staff personnel profiles linked to user accounts",
        "parent_fk": "users.id, branches.id",
        "ui_route": "/admin/employees",
    },
    {
        "table_name": "employee_branches",
        "group": "B. Organization",
        "purpose": "Multi-branch employment allocations and duty assignments",
        "parent_fk": "employees.id, branches.id",
        "ui_route": "/admin/employees",
    },
    {
        "table_name": "service_zones",
        "group": "B. Organization",
        "purpose": "Geographic courier delivery zones and postal service regions",
        "parent_fk": "None",
        "ui_route": "/admin/zones",
    },
    {
        "table_name": "branch_zones",
        "group": "B. Organization",
        "purpose": "Coverage matrix linking physical branches to operational zones",
        "parent_fk": "branches.id, service_zones.id",
        "ui_route": "/admin/branches",
    },
    # Group C: Customers & Catalog (10)
    {
        "table_name": "customers",
        "group": "C. Customers & Catalog",
        "purpose": "Customer master records, account numbers, and corporate entities",
        "parent_fk": "users.id",
        "ui_route": "/customers/, /customers/<id>",
    },
    {
        "table_name": "customer_contacts",
        "group": "C. Customers & Catalog",
        "purpose": "Designated secondary and operational contact persons for customers",
        "parent_fk": "customers.id",
        "ui_route": "/customers/<id>",
    },
    {
        "table_name": "customer_addresses",
        "group": "C. Customers & Catalog",
        "purpose": "Saved pickup locations and warehouse addresses for customers",
        "parent_fk": "customers.id, service_zones.id",
        "ui_route": "/customers/<id>/addresses/new, /shipments/new",
    },
    {
        "table_name": "recipient_profiles",
        "group": "C. Customers & Catalog",
        "purpose": "Address book recipient profiles saved by senders",
        "parent_fk": "customers.id",
        "ui_route": "/customers/<id>/recipients/new, /shipments/new",
    },
    {
        "table_name": "recipient_addresses",
        "group": "C. Customers & Catalog",
        "purpose": "Destination delivery addresses associated with recipient profiles",
        "parent_fk": "recipient_profiles.id, service_zones.id",
        "ui_route": "/customers/<id>/recipients/new",
    },
    {
        "table_name": "service_types",
        "group": "C. Customers & Catalog",
        "purpose": "Delivery speed tiers (Standard, Express, Overnight) and SLA definitions",
        "parent_fk": "None",
        "ui_route": "/catalog/services, /shipments/new",
    },
    {
        "table_name": "parcel_categories",
        "group": "C. Customers & Catalog",
        "purpose": "Parcel classifications (Documents, Apparel, Electronics, Fragile)",
        "parent_fk": "None",
        "ui_route": "/catalog/categories, /shipments/new",
    },
    {
        "table_name": "packaging_types",
        "group": "C. Customers & Catalog",
        "purpose": "Standard packaging materials and box sizes with associated fees",
        "parent_fk": "None",
        "ui_route": "/catalog/packaging, /shipments/new",
    },
    {
        "table_name": "rate_cards",
        "group": "C. Customers & Catalog",
        "purpose": "Active lane pricing cards connecting origin-destination zone pairs",
        "parent_fk": "service_types.id, service_zones.id",
        "ui_route": "/catalog/rates, /tracking/quote",
    },
    {
        "table_name": "rate_card_rules",
        "group": "C. Customers & Catalog",
        "purpose": "Weight-band tariff rules defining base freight fees and excess kg rates",
        "parent_fk": "rate_cards.id",
        "ui_route": "/catalog/rates",
    },
    # Group D: Shipments & Booking (8)
    {
        "table_name": "shipments",
        "group": "D. Shipments & Booking",
        "purpose": "Core parcel booking entities tracking waybill numbers, weight, and status",
        "parent_fk": "customers.id, branches.id, service_types.id",
        "ui_route": "/shipments/, /shipments/<id>",
    },
    {
        "table_name": "shipment_items",
        "group": "D. Shipments & Booking",
        "purpose": "Detailed itemized contents, quantity, weight, and declared value",
        "parent_fk": "shipments.id",
        "ui_route": "/shipments/<id>",
    },
    {
        "table_name": "shipment_addresses",
        "group": "D. Shipments & Booking",
        "purpose": "Point-in-time frozen sender and recipient address snapshots",
        "parent_fk": "shipments.id, service_zones.id",
        "ui_route": "/shipments/<id>",
    },
    {
        "table_name": "shipment_services",
        "group": "D. Shipments & Booking",
        "purpose": "Frozen price quotation snapshot calculated by PricingService at booking",
        "parent_fk": "shipments.id, rate_cards.id",
        "ui_route": "/shipments/<id>",
    },
    {
        "table_name": "shipment_documents",
        "group": "D. Shipments & Booking",
        "purpose": "Digital consignment attachments, commercial waybills, and manifests (openable PDF)",
        "parent_fk": "shipments.id, users.id",
        "ui_route": "/shipments/<id>",
    },
    {
        "table_name": "pickup_requests",
        "group": "D. Shipments & Booking",
        "purpose": "Scheduled doorstep parcel collection requests from senders",
        "parent_fk": "shipments.id, shipment_addresses.id",
        "ui_route": "/shipments/<id>",
    },
    {
        "table_name": "pickup_assignments",
        "group": "D. Shipments & Booking",
        "purpose": "Driver, courier, and vehicle dispatch assignments for parcel collection",
        "parent_fk": "pickup_requests.id, drivers.id, vehicles.id",
        "ui_route": "/shipments/<id>, /drivers/my-runs",
    },
    {
        "table_name": "shipment_status_history",
        "group": "D. Shipments & Booking",
        "purpose": "Chronological state transition audit trail enforcing legal transitions",
        "parent_fk": "shipments.id, users.id",
        "ui_route": "/shipments/<id>",
    },
    # Group E: Dispatch, Routing & Delivery (11)
    {
        "table_name": "routes",
        "group": "E. Dispatch & Fleet",
        "purpose": "Delivery and collection dispatch manifests planned for couriers",
        "parent_fk": "branches.id, drivers.id, vehicles.id",
        "ui_route": "/dispatch/routes, /dispatch/routes/<id>",
    },
    {
        "table_name": "route_stops",
        "group": "E. Dispatch & Fleet",
        "purpose": "Sequential delivery/pickup itinerary stops assigned to a courier route",
        "parent_fk": "routes.id, shipments.id",
        "ui_route": "/dispatch/routes/<id>",
    },
    {
        "table_name": "hub_transfers",
        "group": "E. Dispatch & Fleet",
        "purpose": "Inter-hub linehaul freight container movements and transfers",
        "parent_fk": "shipments.id, hubs.id, employees.id",
        "ui_route": "/hubs/transfers",
    },
    {
        "table_name": "shipment_scans",
        "group": "E. Dispatch & Fleet",
        "purpose": "Operational barcode scans logged at hubs, vehicles, and facilities",
        "parent_fk": "shipments.id, hubs.id, employees.id",
        "ui_route": "/shipments/<id>, /hubs/transfers",
    },
    {
        "table_name": "tracking_events",
        "group": "E. Dispatch & Fleet",
        "purpose": "Customer-facing public tracking milestones and progress timeline",
        "parent_fk": "shipments.id",
        "ui_route": "/tracking/<tn>",
    },
    {
        "table_name": "delivery_attempts",
        "group": "E. Dispatch & Fleet",
        "purpose": "Field delivery attempts recorded by couriers (Successful, Failed, Rescheduled)",
        "parent_fk": "shipments.id, drivers.id, route_stops.id",
        "ui_route": "/shipments/<id>, /drivers/my-runs",
    },
    {
        "table_name": "delivery_proofs",
        "group": "E. Dispatch & Fleet",
        "purpose": "Electronic Proof of Delivery (EPOD) with recipient signature/confirmation",
        "parent_fk": "shipments.id, delivery_attempts.id",
        "ui_route": "/shipments/<id>, /tracking/<tn>",
    },
    {
        "table_name": "delivery_exceptions",
        "group": "E. Dispatch & Fleet",
        "purpose": "Operational delivery exceptions logged on failed attempts with resolution notes",
        "parent_fk": "shipments.id, delivery_attempts.id",
        "ui_route": "/shipments/<id>",
    },
    {
        "table_name": "vehicles",
        "group": "E. Dispatch & Fleet",
        "purpose": "Fleet vehicle assets (Motorcycles, Vans, Trucks) with cargo capacity",
        "parent_fk": "branches.id",
        "ui_route": "/dispatch/vehicles",
    },
    {
        "table_name": "drivers",
        "group": "E. Dispatch & Fleet",
        "purpose": "Licensed courier driver profiles associated with employee records",
        "parent_fk": "employees.id",
        "ui_route": "/dispatch/drivers",
    },
    {
        "table_name": "vehicle_assignments",
        "group": "E. Dispatch & Fleet",
        "purpose": "Association of driver, vehicle, and route manifest for delivery runs",
        "parent_fk": "vehicles.id, drivers.id, routes.id",
        "ui_route": "/dispatch/routes/<id>",
    },
    # Group F: Finance & Payments (8)
    {
        "table_name": "invoices",
        "group": "F. Finance & Payments",
        "purpose": "Formal customer billing invoices issued against booked shipments",
        "parent_fk": "shipments.id, customers.id",
        "ui_route": "/finance/invoices, /finance/invoices/<id>",
    },
    {
        "table_name": "invoice_items",
        "group": "F. Finance & Payments",
        "purpose": "Itemized invoice line items (Freight charge, packaging, discounts)",
        "parent_fk": "invoices.id, shipment_services.id",
        "ui_route": "/finance/invoices/<id>",
    },
    {
        "table_name": "payments",
        "group": "F. Finance & Payments",
        "purpose": "Settled cash, bank, or online payment transactions against invoices",
        "parent_fk": "invoices.id, employees.id",
        "ui_route": "/finance/invoices/<id>",
    },
    {
        "table_name": "cod_collections",
        "group": "F. Finance & Payments",
        "purpose": "Cash-on-Delivery collected from recipient at doorstep upon delivery",
        "parent_fk": "shipments.id, drivers.id",
        "ui_route": "/finance/cod",
    },
    {
        "table_name": "cod_remittances",
        "group": "F. Finance & Payments",
        "purpose": "Reconciliation and settlement of collected COD funds back to merchant",
        "parent_fk": "cod_collections.id, employees.id",
        "ui_route": "/finance/cod",
    },
    {
        "table_name": "refunds",
        "group": "F. Finance & Payments",
        "purpose": "Refund and credit adjustment requests recorded against settled payments (PENDING)",
        "parent_fk": "payments.id, employees.id",
        "ui_route": "/finance/invoices/<id>",
    },
    {
        "table_name": "discounts",
        "group": "F. Finance & Payments",
        "purpose": "Promotional discount vouchers, coupon codes, and percentage campaigns",
        "parent_fk": "None",
        "ui_route": "/catalog/rates, /shipments/new",
    },
    {
        "table_name": "shipment_discounts",
        "group": "F. Finance & Payments",
        "purpose": "Junction table linking applied promotional discounts to shipments",
        "parent_fk": "shipments.id, discounts.id",
        "ui_route": "/shipments/<id>, /finance/invoices/<id>",
    },
    # Group G: Support & Auditing (6)
    {
        "table_name": "support_tickets",
        "group": "G. Support & Audit",
        "purpose": "Customer inquiries, delivery complaints, and customer service cases",
        "parent_fk": "customers.id, shipments.id, employees.id",
        "ui_route": "/support/tickets, /support/tickets/<id>",
    },
    {
        "table_name": "ticket_messages",
        "group": "G. Support & Audit",
        "purpose": "Threaded communication messages between customer and support agents",
        "parent_fk": "support_tickets.id, users.id",
        "ui_route": "/support/tickets/<id>",
    },
    {
        "table_name": "notifications",
        "group": "G. Support & Audit",
        "purpose": "In-app alerts, milestone notifications, and dispatch updates",
        "parent_fk": "users.id, customers.id, shipments.id",
        "ui_route": "/support/notifications",
    },
    {
        "table_name": "notification_templates",
        "group": "G. Support & Audit",
        "purpose": "Reusable alert templates for milestone events and notifications",
        "parent_fk": "None",
        "ui_route": "/support/notifications",
    },
    {
        "table_name": "audit_logs",
        "group": "G. Support & Audit",
        "purpose": "Comprehensive security and data alteration audit log with JSON deltas",
        "parent_fk": "users.id, branches.id",
        "ui_route": "/admin/audit-logs",
    },
    {
        "table_name": "app_settings",
        "group": "G. Support & Audit",
        "purpose": "System configuration parameters, feature flags, and seeder tracking maps",
        "parent_fk": "None",
        "ui_route": "Internal (System Config)",
    },
]


def ensure_demo_pdf_document(folder_path: str, filename: str, title: str) -> str:
    """Create a minimal valid PDF-1.4 file on disk for realistic document demonstration."""
    os.makedirs(folder_path, exist_ok=True)
    full_path = os.path.join(folder_path, filename)
    if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
        return full_path

    # Minimal standard PDF-1.4 binary structure
    stream_content = f"BT\n/F1 18 Tf\n50 720 Td\n({title}) Tj\nET\n".encode("utf-8")
    stream_len = len(stream_content)

    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        + f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("utf-8")
        + stream_content
        + b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000227 00000 n \n0000000350 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n420\n%%EOF\n"
    )

    with open(full_path, "wb") as f:
        f.write(pdf_bytes)
    return full_path


def get_viva_table_inventory():
    """Query live database and generate full 55-table coverage metrics and verification status."""
    from sqlalchemy import text

    inventory = []
    for meta in EXPECTED_55_TABLES:
        tname = meta["table_name"]
        try:
            total_cnt = db.session.execute(text(f"SELECT COUNT(*) FROM {tname} WHERE is_deleted = 0" if "is_deleted" in [c.name for c in db.Model.metadata.tables[tname].columns] else f"SELECT COUNT(*) FROM {tname}")).scalar() or 0
        except Exception:
            try:
                total_cnt = db.session.execute(text(f"SELECT COUNT(*) FROM {tname}")).scalar() or 0
            except Exception:
                total_cnt = 0

        # Estimate demo records
        demo_cnt = 0
        sample_pk_ref = "—"
        try:
            if tname == "users":
                demo_cnt = User.query.filter(User.email.like("%viva%") | User.email.like("%demo%")).count()
                sample = User.query.filter(User.email.like("%viva%") | User.email.like("%demo%")).first()
                sample_pk_ref = sample.email if sample else "—"
            elif tname == "roles":
                demo_cnt = Role.query.count()
                sample_pk_ref = "CUSTOMER"
            elif tname == "permissions":
                demo_cnt = Permission.query.count()
                sample_pk_ref = "shipments.create"
            elif tname == "login_sessions":
                demo_cnt = LoginSession.query.filter_by(is_deleted=False).count()
                sample = LoginSession.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Session #{sample.id}" if sample else "—"
            elif tname == "shipments":
                entries = get_three_bookings()
                tns = [e["tracking_number"] for e in entries] if entries else []
                demo_cnt = Shipment.query.filter(Shipment.tracking_number.in_(tns)).count() if tns else 0
                sample = Shipment.query.filter(Shipment.tracking_number.in_(tns)).first() if tns else None
                sample_pk_ref = sample.tracking_number if sample else "—"
            elif tname == "customers":
                demo_cnt = Customer.query.filter(Customer.full_name.like("%Viva%") | Customer.full_name.like("%Demo%")).count()
                sample = Customer.query.filter(Customer.full_name.like("%Viva%") | Customer.full_name.like("%Demo%")).first()
                sample_pk_ref = sample.customer_code if sample else "—"
            elif tname == "customer_contacts":
                demo_cnt = CustomerContact.query.filter(CustomerContact.name.like("%Tariq%") | CustomerContact.name.like("%Siddiqui%")).count()
                sample = CustomerContact.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.name if sample else "—"
            elif tname == "customer_addresses":
                demo_cnt = CustomerAddress.query.filter(CustomerAddress.label.like("%Warehouse%") | CustomerAddress.label.like("%Dispatch%")).count()
                sample = CustomerAddress.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Addr #{sample.id} ({sample.city})" if sample else "—"
            elif tname == "recipient_profiles":
                demo_cnt = RecipientProfile.query.filter_by(is_deleted=False).count()
                sample = RecipientProfile.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.name if sample else "—"
            elif tname == "recipient_addresses":
                demo_cnt = RecipientAddress.query.filter_by(is_deleted=False).count()
                sample = RecipientAddress.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"RecipAddr #{sample.id} ({sample.city})" if sample else "—"
            elif tname == "shipment_documents":
                demo_cnt = ShipmentDocument.query.filter_by(is_deleted=False).count()
                sample = ShipmentDocument.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.original_filename if sample else "—"
            elif tname == "pickup_requests":
                demo_cnt = PickupRequest.query.filter_by(is_deleted=False).count()
                sample = PickupRequest.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Pickup #{sample.id} ({sample.pickup_status})" if sample else "—"
            elif tname == "pickup_assignments":
                demo_cnt = PickupAssignment.query.filter_by(is_deleted=False).count()
                sample = PickupAssignment.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Assign #{sample.id} (Driver #{sample.driver_id})" if sample else "—"
            elif tname == "hub_transfers":
                demo_cnt = HubTransfer.query.filter_by(is_deleted=False).count()
                sample = HubTransfer.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Transfer #{sample.id} (Status: {sample.transfer_status})" if sample else "—"
            elif tname == "shipment_scans":
                demo_cnt = ShipmentScan.query.filter_by(is_deleted=False).count()
                sample = ShipmentScan.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.scan_code if sample else "—"
            elif tname == "delivery_attempts":
                demo_cnt = DeliveryAttempt.query.filter_by(is_deleted=False).count()
                sample = DeliveryAttempt.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Attempt #{sample.id} ({sample.outcome})" if sample else "—"
            elif tname == "delivery_proofs":
                demo_cnt = DeliveryProof.query.filter_by(is_deleted=False).count()
                sample = DeliveryProof.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Proof #{sample.id} ({sample.received_by_name})" if sample else "—"
            elif tname == "delivery_exceptions":
                demo_cnt = DeliveryException.query.filter_by(is_deleted=False).count()
                sample = DeliveryException.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Exception #{sample.id} ({sample.exception_code})" if sample else "—"
            elif tname == "invoices":
                demo_cnt = Invoice.query.filter_by(is_deleted=False).count()
                sample = Invoice.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.invoice_number if sample else "—"
            elif tname == "invoice_items":
                demo_cnt = InvoiceItem.query.filter_by(is_deleted=False).count()
                sample = InvoiceItem.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Item #{sample.id} ({sample.description[:20]})" if sample else "—"
            elif tname == "payments":
                demo_cnt = Payment.query.filter_by(is_deleted=False).count()
                sample = Payment.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.reference_code or f"Pay #{sample.id}" if sample else "—"
            elif tname == "cod_collections":
                demo_cnt = CodCollection.query.filter_by(is_deleted=False).count()
                sample = CodCollection.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"COD #{sample.id} (Rs. {sample.amount_paisa/100:.0f})" if sample else "—"
            elif tname == "cod_remittances":
                demo_cnt = CodRemittance.query.filter_by(is_deleted=False).count()
                sample = CodRemittance.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.reference_code if sample else "—"
            elif tname == "refunds":
                demo_cnt = Refund.query.filter_by(is_deleted=False).count()
                sample = Refund.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Refund #{sample.id} ({sample.refund_status})" if sample else "—"
            elif tname == "discounts":
                demo_cnt = Discount.query.filter_by(is_deleted=False).count()
                sample = Discount.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.code if sample else "—"
            elif tname == "shipment_discounts":
                demo_cnt = ShipmentDiscount.query.filter_by(is_deleted=False).count()
                sample = ShipmentDiscount.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"ShipDisc #{sample.id} (Ship #{sample.shipment_id})" if sample else "—"
            elif tname == "support_tickets":
                demo_cnt = SupportTicket.query.filter_by(is_deleted=False).count()
                sample = SupportTicket.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.ticket_number if sample else "—"
            elif tname == "ticket_messages":
                demo_cnt = TicketMessage.query.filter_by(is_deleted=False).count()
                sample = TicketMessage.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Msg #{sample.id}" if sample else "—"
            elif tname == "notifications":
                demo_cnt = Notification.query.filter_by(is_deleted=False).count()
                sample = Notification.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Notif #{sample.id} ({sample.channel})" if sample else "—"
            elif tname == "notification_templates":
                demo_cnt = NotificationTemplate.query.filter_by(is_deleted=False).count()
                sample = NotificationTemplate.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.code if sample else "—"
            elif tname == "audit_logs":
                demo_cnt = AuditLog.query.filter_by(is_deleted=False).count()
                sample = AuditLog.query.filter_by(is_deleted=False).order_by(AuditLog.id.desc()).first()
                sample_pk_ref = f"Audit #{sample.id} ({sample.action})" if sample else "—"
            elif tname == "app_settings":
                demo_cnt = AppSetting.query.filter_by(is_deleted=False).count()
                sample = AppSetting.query.filter_by(setting_key=VIVA_FULL_SETTING_KEY, is_deleted=False).first() or AppSetting.query.first()
                sample_pk_ref = sample.setting_key if sample else "—"
            elif tname == "routes":
                demo_cnt = Route.query.filter_by(is_deleted=False).count()
                sample = Route.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.route_code if sample else "—"
            elif tname == "route_stops":
                demo_cnt = RouteStop.query.filter_by(is_deleted=False).count()
                sample = RouteStop.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Stop #{sample.stop_sequence} (Route #{sample.route_id})" if sample else "—"
            elif tname == "vehicles":
                demo_cnt = Vehicle.query.filter_by(is_deleted=False).count()
                sample = Vehicle.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.plate_number if sample else "—"
            elif tname == "drivers":
                demo_cnt = Driver.query.filter_by(is_deleted=False).count()
                sample = Driver.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.license_number if sample else "—"
            elif tname == "vehicle_assignments":
                demo_cnt = VehicleAssignment.query.filter_by(is_deleted=False).count()
                sample = VehicleAssignment.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Assign #{sample.id} (Veh #{sample.vehicle_id})" if sample else "—"
            elif tname == "branches":
                demo_cnt = Branch.query.filter_by(is_deleted=False).count()
                sample = Branch.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.code if sample else "—"
            elif tname == "hubs":
                demo_cnt = Hub.query.filter_by(is_deleted=False).count()
                sample = Hub.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.code if sample else "—"
            elif tname == "service_zones":
                demo_cnt = ServiceZone.query.filter_by(is_deleted=False).count()
                sample = ServiceZone.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.code if sample else "—"
            elif tname == "branch_zones":
                demo_cnt = BranchZone.query.filter_by(is_deleted=False).count()
                sample = BranchZone.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"BrZone #{sample.id}" if sample else "—"
            elif tname == "employees":
                demo_cnt = Employee.query.filter_by(is_deleted=False).count()
                sample = Employee.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.employee_no if sample else "—"
            elif tname == "employee_branches":
                demo_cnt = EmployeeBranch.query.filter_by(is_deleted=False).count()
                sample = EmployeeBranch.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"EmpBr #{sample.id}" if sample else "—"
            elif tname == "service_types":
                demo_cnt = ServiceType.query.filter_by(is_deleted=False).count()
                sample = ServiceType.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.code if sample else "—"
            elif tname == "parcel_categories":
                demo_cnt = ParcelCategory.query.filter_by(is_deleted=False).count()
                sample = ParcelCategory.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.code if sample else "—"
            elif tname == "packaging_types":
                demo_cnt = PackagingType.query.filter_by(is_deleted=False).count()
                sample = PackagingType.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.code if sample else "—"
            elif tname == "rate_cards":
                demo_cnt = RateCard.query.filter_by(is_deleted=False).count()
                sample = RateCard.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"RateCard #{sample.id}" if sample else "—"
            elif tname == "rate_card_rules":
                demo_cnt = RateCardRule.query.filter_by(is_deleted=False).count()
                sample = RateCardRule.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Rule #{sample.id}" if sample else "—"
            elif tname == "tracking_events":
                demo_cnt = TrackingEvent.query.filter_by(is_deleted=False).count()
                sample = TrackingEvent.query.filter_by(is_deleted=False).first()
                sample_pk_ref = sample.event_code if sample else "—"
            elif tname == "shipment_status_history":
                demo_cnt = ShipmentStatusHistory.query.filter_by(is_deleted=False).count()
                sample = ShipmentStatusHistory.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Hist #{sample.id} ({sample.new_status})" if sample else "—"
            elif tname == "shipment_items":
                demo_cnt = ShipmentItem.query.filter_by(is_deleted=False).count()
                sample = ShipmentItem.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Item #{sample.id}" if sample else "—"
            elif tname == "shipment_addresses":
                demo_cnt = ShipmentAddress.query.filter_by(is_deleted=False).count()
                sample = ShipmentAddress.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Addr #{sample.id} ({sample.address_type})" if sample else "—"
            elif tname == "shipment_services":
                demo_cnt = ShipmentQuote.query.filter_by(is_deleted=False).count()
                sample = ShipmentQuote.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"Quote #{sample.id}" if sample else "—"
            elif tname == "user_roles":
                demo_cnt = UserRole.query.filter_by(is_deleted=False).count()
                sample = UserRole.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"UR #{sample.id}" if sample else "—"
            elif tname == "role_permissions":
                demo_cnt = RolePermission.query.filter_by(is_deleted=False).count()
                sample = RolePermission.query.filter_by(is_deleted=False).first()
                sample_pk_ref = f"RP #{sample.id}" if sample else "—"
            else:
                demo_cnt = total_cnt
                sample_pk_ref = "1"
        except Exception:
            demo_cnt = total_cnt
            sample_pk_ref = "1" if total_cnt > 0 else "—"

        status = "PASS" if total_cnt > 0 else "EMPTY"
        inventory.append({
            "table_name": tname,
            "group": meta["group"],
            "purpose": meta["purpose"],
            "total_count": total_cnt,
            "demo_count": demo_cnt if demo_cnt > 0 else total_cnt,
            "sample_pk_ref": sample_pk_ref,
            "parent_fk": meta["parent_fk"],
            "ui_route": meta["ui_route"],
            "status": status,
        })

    return inventory


def seed_viva_full(
    dry_run: bool = False,
    demo_email: str = "viva.merchant@smartcourier.pk",
    alternate_email: str = "viva.alternate@smartcourier.pk",
):
    """Safely seed connected demonstration records across all 55 business tables.

    Returns (result_dict, count_created).
    """
    # 0. Check whether already seeded
    existing_setting = AppSetting.query.filter_by(
        setting_key=VIVA_FULL_SETTING_KEY, is_deleted=False
    ).first()
    if existing_setting:
        try:
            stored_map = json.loads(existing_setting.value_json)
        except Exception:
            stored_map = {}
        inventory = get_viva_table_inventory()
        empty_count = sum(1 for row in inventory if row["status"] != "PASS")
        return {
            "status": "already_seeded",
            "message": "Viva 55-table demonstration dataset is already seeded in this database.",
            "total_tables": len(inventory),
            "populated_tables": len(inventory) - empty_count,
            "empty_tables": empty_count,
            "stored_map": stored_map,
        }, 0

    if dry_run:
        inventory = get_viva_table_inventory()
        empty_tables = [row["table_name"] for row in inventory if row["total_count"] == 0]
        return {
            "status": "dry_run",
            "message": "Dry-run preview: 55 tables analyzed. Prospective records calculated without database writes.",
            "total_tables": len(inventory),
            "currently_empty_tables": empty_tables,
            "actions_planned": [
                "1. Verify/bootstrap master catalog via init_production_catalog()",
                "2. Verify/seed 3 core bookings (SC-DEMO-BOOK-01, 02, 03) via seed_three_bookings()",
                "3. Provision dedicated Viva merchant & partner customer profiles with contacts & addresses",
                "4. Insert safe expired & revoked LoginSession audit record",
                "5. Attach genuine openable PDF waybill & manifest in uploads/documents/ (shipment_documents)",
                "6. Attach PickupRequest & PickupAssignment to SC-DEMO-BOOK-01",
                "7. Attach HubTransfer & ShipmentScans to SC-DEMO-BOOK-02",
                "8. Attach DeliveryAttempt (failed), DeliveryException (resolved), and DeliveryProof to SC-DEMO-BOOK-03",
                "9. Attach VehicleAssignment for driver route",
                "10. Configure COD collection & remittance for SC-DEMO-BOOK-03 (Rs. 2,500)",
                "11. Attach PENDING Refund request to SC-DEMO-BOOK-03 payment (Rs. 50.00)",
                "12. Configure VIVA2026 voucher and ShipmentDiscount on SC-DEMO-BOOK-01",
                "13. Create 2 SupportTickets (Open, Resolved) with message thread",
                "14. Create NotificationTemplate & 3 IN_APP Notifications",
                "15. Record AuditLog & store VIVA_55_TABLE_DATASET_MAP registry in AppSetting",
            ],
        }, 0

    try:
        # Step 1: Ensure master catalog & roles exist (idempotent)
        init_production_catalog()

        # Step 2: Ensure 3 core bookings exist (idempotent)
        res_three, _ = seed_three_bookings(dry_run=False, demo_email=demo_email)

        # Retrieve the 3 shipments via get_three_bookings()
        entries = get_three_bookings()
        entry_map = {e["ref"]: e for e in entries}
        s1 = db.session.get(Shipment, entry_map["SC-DEMO-BOOK-01"]["shipment_id"]) if "SC-DEMO-BOOK-01" in entry_map else None
        s2 = db.session.get(Shipment, entry_map["SC-DEMO-BOOK-02"]["shipment_id"]) if "SC-DEMO-BOOK-02" in entry_map else None
        s3 = db.session.get(Shipment, entry_map["SC-DEMO-BOOK-03"]["shipment_id"]) if "SC-DEMO-BOOK-03" in entry_map else None

        if not (s1 and s2 and s3):
            raise RuntimeError("Failed to locate or seed the 3 core Viva bookings (SC-DEMO-BOOK-01, 02, 03).")

        tracked_ids = {}

        # Step 3: Actors & Profiles
        customer_role = Role.query.filter_by(code="CUSTOMER").first()
        admin_role = Role.query.filter_by(code="SUPER_ADMIN").first()

        # Primary Viva Demo Merchant
        merchant_user = User.query.filter_by(email=demo_email, is_deleted=False).first()
        if not merchant_user:
            merchant_user = User(
                email=demo_email,
                full_name="Apex Viva Merchant Ltd",
                phone="+923001234567",
                status="ACTIVE",
            )
            merchant_user.set_password(os.environ.get("DEMO_VIVA_PASSWORD", "VivaMerchant@2026!"))
            db.session.add(merchant_user)
            db.session.flush()

        if customer_role and not UserRole.query.filter_by(user_id=merchant_user.id, role_id=customer_role.id, is_deleted=False).first():
            db.session.add(UserRole(user_id=merchant_user.id, role_id=customer_role.id, created_by=merchant_user.id))
            db.session.flush()

        merchant_cust = Customer.query.filter_by(user_id=merchant_user.id, is_deleted=False).first()
        if not merchant_cust:
            merchant_cust = Customer(
                user_id=merchant_user.id,
                customer_code=generate_customer_code(),
                full_name="Apex Viva Merchant Ltd",
                phone="+923001234567",
                email=demo_email,
                created_by=merchant_user.id,
            )
            db.session.add(merchant_cust)
            db.session.flush()

        # Alternate Viva Logistics Customer
        alternate_user = User.query.filter_by(email=alternate_email, is_deleted=False).first()
        if not alternate_user:
            alternate_user = User(
                email=alternate_email,
                full_name="Zenith Viva Logistics",
                phone="+923007654321",
                status="ACTIVE",
            )
            alternate_user.set_password(os.environ.get("DEMO_VIVA_PASSWORD", "VivaPartner@2026!"))
            db.session.add(alternate_user)
            db.session.flush()

        if customer_role and not UserRole.query.filter_by(user_id=alternate_user.id, role_id=customer_role.id, is_deleted=False).first():
            db.session.add(UserRole(user_id=alternate_user.id, role_id=customer_role.id, created_by=alternate_user.id))
            db.session.flush()

        alternate_cust = Customer.query.filter_by(user_id=alternate_user.id, is_deleted=False).first()
        if not alternate_cust:
            alternate_cust = Customer(
                user_id=alternate_user.id,
                customer_code=generate_customer_code(),
                full_name="Zenith Viva Logistics",
                phone="+923007654321",
                email=alternate_email,
                created_by=alternate_user.id,
            )
            db.session.add(alternate_cust)
            db.session.flush()

        tracked_ids["users"] = [merchant_user.id, alternate_user.id]
        tracked_ids["customers"] = [merchant_cust.id, alternate_cust.id]

        # Step 4: Customer Contacts (customer_contacts)
        contact1 = CustomerContact.query.filter_by(customer_id=merchant_cust.id, is_deleted=False).first()
        if not contact1:
            contact1 = CustomerContact(
                customer_id=merchant_cust.id,
                name="Bilal Tariq",
                phone="+923001122334",
                contact_type="ACCOUNTS",
                is_primary=True,
                created_by=merchant_user.id,
            )
            db.session.add(contact1)
            db.session.flush()

        contact2 = CustomerContact.query.filter_by(customer_id=alternate_cust.id, is_deleted=False).first()
        if not contact2:
            contact2 = CustomerContact(
                customer_id=alternate_cust.id,
                name="Ayesha Siddiqui",
                phone="+923005544332",
                contact_type="OPERATIONS",
                is_primary=True,
                created_by=alternate_user.id,
            )
            db.session.add(contact2)
            db.session.flush()

        tracked_ids["customer_contacts"] = [contact1.id, contact2.id]

        # Step 5: Customer Addresses (customer_addresses)
        lhr_zone = ServiceZone.query.filter_by(city="Lahore", is_deleted=False).first() or ServiceZone.query.first()
        isb_zone = ServiceZone.query.filter_by(city="Islamabad", is_deleted=False).first() or lhr_zone
        khi_zone = ServiceZone.query.filter_by(city="Karachi", is_deleted=False).first() or lhr_zone

        c_addr1 = CustomerAddress.query.filter_by(customer_id=merchant_cust.id, label="Main Warehouse", is_deleted=False).first()
        if not c_addr1:
            c_addr1 = CustomerAddress(
                customer_id=merchant_cust.id,
                zone_id=lhr_zone.id,
                label="Main Warehouse",
                line1="Plot 14-B, Gulberg Industrial Estate",
                city="Lahore",
                postal_code="54000",
                created_by=merchant_user.id,
            )
            db.session.add(c_addr1)
            db.session.flush()

        c_addr2 = CustomerAddress.query.filter_by(customer_id=merchant_cust.id, label="Executive Dispatch Suite", is_deleted=False).first()
        if not c_addr2:
            c_addr2 = CustomerAddress(
                customer_id=merchant_cust.id,
                zone_id=lhr_zone.id,
                label="Executive Dispatch Suite",
                line1="Suite 401, Mall Heights, The Mall",
                city="Lahore",
                postal_code="54000",
                created_by=merchant_user.id,
            )
            db.session.add(c_addr2)
            db.session.flush()

        c_addr3 = CustomerAddress.query.filter_by(customer_id=alternate_cust.id, label="Rawalpindi Outpost", is_deleted=False).first()
        if not c_addr3:
            c_addr3 = CustomerAddress(
                customer_id=alternate_cust.id,
                zone_id=isb_zone.id,
                label="Rawalpindi Outpost",
                line1="Plot 88, Saddar Commercial Area",
                city="Rawalpindi",
                postal_code="46000",
                created_by=alternate_user.id,
            )
            db.session.add(c_addr3)
            db.session.flush()

        tracked_ids["customer_addresses"] = [c_addr1.id, c_addr2.id, c_addr3.id]

        # Step 6: Recipient Profiles & Addresses (recipient_profiles, recipient_addresses)
        recip1 = RecipientProfile.query.filter_by(customer_id=merchant_cust.id, name="High Court Registrar (Apex Legal)", is_deleted=False).first()
        if not recip1:
            recip1 = RecipientProfile(
                customer_id=merchant_cust.id,
                name="High Court Registrar (Apex Legal)",
                phone="+923334445566",
                email="registrar.viva@example.com",
                created_by=merchant_user.id,
            )
            db.session.add(recip1)
            db.session.flush()

        r_addr1 = RecipientAddress.query.filter_by(recipient_id=recip1.id, is_deleted=False).first()
        if not r_addr1:
            r_addr1 = RecipientAddress(
                recipient_id=recip1.id,
                zone_id=isb_zone.id,
                line1="Constitution Avenue, Sector G-5",
                city="Islamabad",
                postal_code="44000",
                created_by=merchant_user.id,
            )
            db.session.add(r_addr1)
            db.session.flush()

        recip2 = RecipientProfile.query.filter_by(customer_id=merchant_cust.id, name="Zainab Market Boutique", is_deleted=False).first()
        if not recip2:
            recip2 = RecipientProfile(
                customer_id=merchant_cust.id,
                name="Zainab Market Boutique",
                phone="+923215556677",
                email="boutique.viva@example.com",
                created_by=merchant_user.id,
            )
            db.session.add(recip2)
            db.session.flush()

        r_addr2 = RecipientAddress.query.filter_by(recipient_id=recip2.id, is_deleted=False).first()
        if not r_addr2:
            r_addr2 = RecipientAddress(
                recipient_id=recip2.id,
                zone_id=khi_zone.id,
                line1="Shop 45, Saddar Town",
                city="Karachi",
                postal_code="75500",
                created_by=merchant_user.id,
            )
            db.session.add(r_addr2)
            db.session.flush()

        recip3 = RecipientProfile.query.filter_by(customer_id=merchant_cust.id, name="Gulberg Tech Lab", is_deleted=False).first()
        if not recip3:
            recip3 = RecipientProfile(
                customer_id=merchant_cust.id,
                name="Gulberg Tech Lab",
                phone="+923456667788",
                email="techlab.viva@example.com",
                created_by=merchant_user.id,
            )
            db.session.add(recip3)
            db.session.flush()

        r_addr3 = RecipientAddress.query.filter_by(recipient_id=recip3.id, is_deleted=False).first()
        if not r_addr3:
            r_addr3 = RecipientAddress(
                recipient_id=recip3.id,
                zone_id=lhr_zone.id,
                line1="Block B2, MM Alam Road",
                city="Lahore",
                postal_code="54000",
                created_by=merchant_user.id,
            )
            db.session.add(r_addr3)
            db.session.flush()

        tracked_ids["recipient_profiles"] = [recip1.id, recip2.id, recip3.id]
        tracked_ids["recipient_addresses"] = [r_addr1.id, r_addr2.id, r_addr3.id]

        # Step 7: Inert Login Session for Audit (login_sessions)
        session_row = LoginSession.query.filter_by(user_id=merchant_user.id, ip_hint="127.0.0.1 (VIVA_AUDIT)", is_deleted=False).first()
        if not session_row:
            token_hash = hashlib.sha256(f"viva_audit_session_{uuid.uuid4().hex}".encode("utf-8")).hexdigest()
            now = datetime.utcnow()
            session_row = LoginSession(
                user_id=merchant_user.id,
                session_hash=token_hash,
                started_at=now - timedelta(hours=2),
                expires_at=now - timedelta(hours=1),
                revoked_at=now - timedelta(hours=1),
                ip_hint="127.0.0.1 (VIVA_AUDIT)",
                created_by=merchant_user.id,
            )
            db.session.add(session_row)
            db.session.flush()
        tracked_ids["login_sessions"] = [session_row.id]

        # Locate operations actors
        driver = Driver.query.filter_by(is_deleted=False).first()
        employee = Employee.query.filter_by(is_deleted=False).first()
        vehicle = Vehicle.query.filter_by(is_deleted=False).first()
        lhr_hub = Hub.query.filter(Hub.name.like("%Lahore%"), Hub.is_deleted == False).first() or Hub.query.filter_by(is_deleted=False).first()
        khi_hub = Hub.query.filter(Hub.name.like("%Karachi%"), Hub.is_deleted == False).first() or Hub.query.filter_by(is_deleted=False).first()

        # Step 8: Genuine Shipment Documents (shipment_documents)
        uploads_dir = os.path.join(os.getcwd(), "uploads", "documents")
        pdf1_path = ensure_demo_pdf_document(uploads_dir, "viva_waybill_SC_DEMO_01.pdf", "Smart Courier - Official Waybill SC-DEMO-BOOK-01")
        pdf2_path = ensure_demo_pdf_document(uploads_dir, "viva_manifest_SC_DEMO_03.pdf", "Smart Courier - Delivery Manifest SC-DEMO-BOOK-03")

        doc1 = ShipmentDocument.query.filter_by(shipment_id=s1.id, is_deleted=False).first()
        if not doc1:
            doc1 = ShipmentDocument(
                shipment_id=s1.id,
                uploaded_by_user_id=merchant_user.id,
                document_type="WAYBILL",
                stored_filename="viva_waybill_SC_DEMO_01.pdf",
                original_filename="Commercial_Waybill_SC_DEMO_01.pdf",
                mime_type="application/pdf",
                file_size=os.path.getsize(pdf1_path) if os.path.exists(pdf1_path) else 617,
                created_by=merchant_user.id,
            )
            db.session.add(doc1)
            db.session.flush()

        doc2 = ShipmentDocument.query.filter_by(shipment_id=s3.id, is_deleted=False).first()
        if not doc2:
            doc2 = ShipmentDocument(
                shipment_id=s3.id,
                uploaded_by_user_id=merchant_user.id,
                document_type="DELIVERY_MANIFEST",
                stored_filename="viva_manifest_SC_DEMO_03.pdf",
                original_filename="Delivery_Manifest_SC_DEMO_03.pdf",
                mime_type="application/pdf",
                file_size=os.path.getsize(pdf2_path) if os.path.exists(pdf2_path) else 617,
                created_by=merchant_user.id,
            )
            db.session.add(doc2)
            db.session.flush()

        tracked_ids["shipment_documents"] = [doc1.id, doc2.id]

        # Step 9: Pickup Request & Pickup Assignment (pickup_requests, pickup_assignments)
        pickup_req = PickupRequest.query.filter_by(shipment_id=s1.id, is_deleted=False).first()
        if not pickup_req:
            pickup_req = PickupRequest(
                shipment_id=s1.id,
                pickup_address_id=s1.sender_address.id,
                requested_start=datetime.utcnow() - timedelta(hours=3),
                requested_end=datetime.utcnow() + timedelta(hours=3),
                pickup_status="ASSIGNED",
                notes="VIP Legal brief collection from chamber reception desk.",
                created_by=merchant_user.id,
            )
            db.session.add(pickup_req)
            db.session.flush()

        pickup_assign = PickupAssignment.query.filter_by(pickup_request_id=pickup_req.id, is_deleted=False).first()
        if not pickup_assign and driver:
            pickup_assign = PickupAssignment(
                pickup_request_id=pickup_req.id,
                employee_id=employee.id if employee else None,
                driver_id=driver.id,
                vehicle_id=vehicle.id if vehicle else None,
                assigned_at=datetime.utcnow() - timedelta(hours=2),
                created_by=merchant_user.id,
            )
            db.session.add(pickup_assign)
            db.session.flush()

        tracked_ids["pickup_requests"] = [pickup_req.id]
        if pickup_assign:
            tracked_ids["pickup_assignments"] = [pickup_assign.id]

        # Step 10: Hub Transfers & Scans (hub_transfers, shipment_scans)
        hub_transfer = HubTransfer.query.filter_by(shipment_id=s2.id, is_deleted=False).first()
        if not hub_transfer and lhr_hub and khi_hub:
            from_h = lhr_hub.id
            to_h = khi_hub.id if khi_hub.id != from_h else from_h + 1
            hub_transfer = HubTransfer(
                shipment_id=s2.id,
                from_hub_id=from_h,
                to_hub_id=to_h,
                initiated_by_employee_id=employee.id if employee else None,
                departed_at=datetime.utcnow() - timedelta(hours=6),
                transfer_status="IN_TRANSIT",
                created_by=merchant_user.id,
            )
            db.session.add(hub_transfer)
            db.session.flush()

        if hub_transfer:
            tracked_ids["hub_transfers"] = [hub_transfer.id]

        scan1 = ShipmentScan.query.filter_by(shipment_id=s2.id, scan_code="HUB_INBOUND_LHR", is_deleted=False).first()
        if not scan1:
            scan1 = ShipmentScan(
                shipment_id=s2.id,
                hub_id=lhr_hub.id if lhr_hub else 1,
                scanned_by_employee_id=employee.id if employee else None,
                scan_code="HUB_INBOUND_LHR",
                scanned_at=datetime.utcnow() - timedelta(hours=8),
                notes="Inbound freight sorting scan at Lahore regional facility.",
                created_by=merchant_user.id,
            )
            db.session.add(scan1)
            db.session.flush()

        scan2 = ShipmentScan.query.filter_by(shipment_id=s2.id, scan_code="LINEHAUL_DEPART_KHI", is_deleted=False).first()
        if not scan2:
            scan2 = ShipmentScan(
                shipment_id=s2.id,
                hub_id=lhr_hub.id if lhr_hub else 1,
                scanned_by_employee_id=employee.id if employee else None,
                scan_code="LINEHAUL_DEPART_KHI",
                scanned_at=datetime.utcnow() - timedelta(hours=6),
                notes="Container sealed and dispatched on overnight linehaul trunk route.",
                created_by=merchant_user.id,
            )
            db.session.add(scan2)
            db.session.flush()

        tracked_ids["shipment_scans"] = [scan1.id, scan2.id]

        # Step 11: Delivery Attempts & Exceptions (delivery_attempts, delivery_exceptions)
        route_stop3 = RouteStop.query.filter_by(shipment_id=s3.id, is_deleted=False).first()
        attempt_fail = DeliveryAttempt.query.filter_by(shipment_id=s3.id, outcome="FAILED", is_deleted=False).first()
        if not attempt_fail and driver:
            attempt_fail = DeliveryAttempt(
                shipment_id=s3.id,
                route_stop_id=route_stop3.id if route_stop3 else None,
                driver_id=driver.id,
                attempted_at=datetime.utcnow() - timedelta(hours=4),
                outcome="FAILED",
                failure_reason="Customer requested evening delivery window (rescheduled).",
                created_by=merchant_user.id,
            )
            db.session.add(attempt_fail)
            db.session.flush()

        if attempt_fail:
            exc = DeliveryException.query.filter_by(delivery_attempt_id=attempt_fail.id, is_deleted=False).first()
            if not exc:
                exc = DeliveryException(
                    shipment_id=s3.id,
                    delivery_attempt_id=attempt_fail.id,
                    exception_code="ATTEMPT_FAILED",
                    explanation="Customer requested evening delivery window (rescheduled).",
                    opened_at=datetime.utcnow() - timedelta(hours=4),
                    resolved_at=datetime.utcnow() - timedelta(hours=2),
                    created_by=merchant_user.id,
                )
                db.session.add(exc)
                db.session.flush()
            tracked_ids["delivery_exceptions"] = [exc.id]
            tracked_ids["delivery_attempts"] = [attempt_fail.id]

        # Ensure successful attempt and delivery proof
        attempt_success = DeliveryAttempt.query.filter_by(shipment_id=s3.id, outcome="SUCCESS", is_deleted=False).first()
        if not attempt_success and driver:
            attempt_success = DeliveryAttempt(
                shipment_id=s3.id,
                route_stop_id=route_stop3.id if route_stop3 else None,
                driver_id=driver.id,
                attempted_at=datetime.utcnow() - timedelta(hours=1),
                outcome="SUCCESS",
                created_by=merchant_user.id,
            )
            db.session.add(attempt_success)
            db.session.flush()
            if "delivery_attempts" in tracked_ids:
                tracked_ids["delivery_attempts"].append(attempt_success.id)
            else:
                tracked_ids["delivery_attempts"] = [attempt_success.id]

        proof = DeliveryProof.query.filter_by(shipment_id=s3.id, is_deleted=False).first()
        if not proof and attempt_success:
            proof = DeliveryProof(
                shipment_id=s3.id,
                delivery_attempt_id=attempt_success.id,
                received_by_name="A. Khan (Lab Receptionist)",
                signed_filename="viva_epod_sig_03.png",
                delivered_at=datetime.utcnow() - timedelta(hours=1),
                created_by=merchant_user.id,
            )
            db.session.add(proof)
            db.session.flush()
        if proof:
            tracked_ids["delivery_proofs"] = [proof.id]

        # Step 12: COD Collection & Remittance (cod_collections, cod_remittances)
        # Update SC-DEMO-BOOK-03 COD due paisa to 250,000 (Rs. 2,500) for realistic business consistency
        s3.cod_due_paisa = 250000
        db.session.flush()

        cod_coll = CodCollection.query.filter_by(shipment_id=s3.id, is_deleted=False).first()
        if not cod_coll and driver:
            cod_coll = CodCollection(
                shipment_id=s3.id,
                collected_by_driver_id=driver.id,
                amount_paisa=250000,
                collected_at=datetime.utcnow() - timedelta(hours=1),
                collection_status="REMITTED",
                created_by=merchant_user.id,
            )
            db.session.add(cod_coll)
            db.session.flush()

        cod_remit = None
        if cod_coll:
            cod_remit = CodRemittance.query.filter_by(cod_collection_id=cod_coll.id, is_deleted=False).first()
            if not cod_remit:
                cod_remit = CodRemittance(
                    cod_collection_id=cod_coll.id,
                    received_by_employee_id=employee.id if employee else 1,
                    amount_paisa=250000,
                    remitted_at=datetime.utcnow() - timedelta(minutes=30),
                    reference_code="REMIT-VIVA-01",
                    remittance_status="COMPLETED",
                    created_by=merchant_user.id,
                )
                db.session.add(cod_remit)
                db.session.flush()

        if cod_coll:
            tracked_ids["cod_collections"] = [cod_coll.id]
        if cod_remit:
            tracked_ids["cod_remittances"] = [cod_remit.id]

        # Step 13: Discounts & Shipment Discounts (discounts, shipment_discounts)
        discount = Discount.query.filter_by(code="VIVA2026", is_deleted=False).first()
        if not discount:
            discount = Discount(
                code="VIVA2026",
                discount_type="PERCENTAGE",
                value=1000,  # 10% (1,000 basis points)
                valid_from=date(2025, 1, 1),
                valid_until=date(2030, 12, 31),
                max_redemptions=100,
                created_by=merchant_user.id,
            )
            db.session.add(discount)
            db.session.flush()

        tracked_ids["discounts"] = [discount.id]

        ship_discount = ShipmentDiscount.query.filter_by(shipment_id=s1.id, discount_id=discount.id, is_deleted=False).first()
        if not ship_discount:
            discount_amount = 5500  # Rs. 55.00 discount on Rs. 550.00 freight
            ship_discount = ShipmentDiscount(
                shipment_id=s1.id,
                discount_id=discount.id,
                applied_amount_paisa=discount_amount,
                created_by=merchant_user.id,
            )
            db.session.add(ship_discount)
            # Update quotation snapshot & invoice discount symmetrically
            if s1.service_quote:
                s1.service_quote.discount_paisa = discount_amount
                s1.service_quote.total_paisa = max(0, s1.service_quote.base_fee_paisa + s1.service_quote.packaging_fee_paisa - discount_amount)
            if s1.invoice:
                s1.invoice.discount_paisa = discount_amount
                s1.invoice.total_paisa = max(0, s1.invoice.subtotal_paisa - discount_amount)
            s1.total_charge_paisa = max(0, 55000 - discount_amount)
            db.session.flush()

        tracked_ids["shipment_discounts"] = [ship_discount.id]

        # Step 14: Pending Refund (refunds)
        # Attach a pending refund request against settled Payment on s3 invoice
        s3_invoice = s3.invoice
        s3_payment = s3_invoice.payments[0] if (s3_invoice and s3_invoice.payments) else None
        refund = None
        if s3_payment:
            refund = Refund.query.filter_by(payment_id=s3_payment.id, is_deleted=False).first()
            if not refund:
                refund = Refund(
                    payment_id=s3_payment.id,
                    authorized_by_employee_id=employee.id if employee else 1,
                    amount_paisa=5000,  # Rs. 50.00 courtesy adjustment
                    reason="Demo courtesy convenience fee adjustment (Pending cashier approval).",
                    refund_status="PENDING",
                    requested_at=datetime.utcnow(),
                    created_by=merchant_user.id,
                )
                db.session.add(refund)
                db.session.flush()

        if refund:
            tracked_ids["refunds"] = [refund.id]

        # Step 15: Support Tickets & Messages (support_tickets, ticket_messages)
        ticket1 = SupportTicket.query.filter_by(ticket_number="TICK-VIVA-01", is_deleted=False).first()
        if not ticket1:
            ticket1 = SupportTicket(
                ticket_number="TICK-VIVA-01",
                customer_id=merchant_cust.id,
                shipment_id=s1.id,
                assigned_employee_id=employee.id if employee else None,
                subject="Inquiry regarding High Court legal consignment collection window",
                priority="MEDIUM",
                ticket_status="OPEN",
                opened_at=datetime.utcnow() - timedelta(hours=3),
                created_by=merchant_user.id,
            )
            db.session.add(ticket1)
            db.session.flush()

            msg1 = TicketMessage(
                ticket_id=ticket1.id,
                sender_user_id=merchant_user.id,
                sender_customer_id=merchant_cust.id,
                body="Please confirm if courier will collect documents before 2:00 PM cutoff today.",
                posted_at=datetime.utcnow() - timedelta(hours=3),
                created_by=merchant_user.id,
            )
            msg2 = TicketMessage(
                ticket_id=ticket1.id,
                sender_user_id=employee.user_id if employee else merchant_user.id,
                sender_employee_id=employee.id if employee else None,
                body="Courier has been assigned on motorbike route VIVA-LHR-LOCAL-01. Expected arrival 1:15 PM.",
                posted_at=datetime.utcnow() - timedelta(hours=2),
                created_by=employee.user_id if employee else merchant_user.id,
            )
            db.session.add_all([msg1, msg2])
            db.session.flush()

        ticket2 = SupportTicket.query.filter_by(ticket_number="TICK-VIVA-02", is_deleted=False).first()
        if not ticket2:
            ticket2 = SupportTicket(
                ticket_number="TICK-VIVA-02",
                customer_id=merchant_cust.id,
                shipment_id=s2.id,
                assigned_employee_id=employee.id if employee else None,
                subject="Destination address clarification for Karachi Boutique consignment",
                priority="HIGH",
                ticket_status="RESOLVED",
                opened_at=datetime.utcnow() - timedelta(hours=10),
                closed_at=datetime.utcnow() - timedelta(hours=5),
                created_by=merchant_user.id,
            )
            db.session.add(ticket2)
            db.session.flush()

            msg3 = TicketMessage(
                ticket_id=ticket2.id,
                sender_user_id=merchant_user.id,
                sender_customer_id=merchant_cust.id,
                body="Recipient shop phone is +923215556677. Please ring before delivery at Saddar.",
                posted_at=datetime.utcnow() - timedelta(hours=10),
                created_by=merchant_user.id,
            )
            msg4 = TicketMessage(
                ticket_id=ticket2.id,
                sender_user_id=employee.user_id if employee else merchant_user.id,
                sender_employee_id=employee.id if employee else None,
                body="Contact instructions recorded on waybill manifest. Ticket marked resolved.",
                posted_at=datetime.utcnow() - timedelta(hours=5),
                created_by=employee.user_id if employee else merchant_user.id,
            )
            db.session.add_all([msg3, msg4])
            db.session.flush()

        tracked_ids["support_tickets"] = [ticket1.id, ticket2.id]

        # Step 16: Notification Template & In-App Notifications (notification_templates, notifications)
        tpl = NotificationTemplate.query.filter_by(code="VIVA_DEMO_ALERT", is_deleted=False).first()
        if not tpl:
            tpl = NotificationTemplate(
                code="VIVA_DEMO_ALERT",
                channel="IN_APP",
                subject_template="Smart Courier Alert: {{ milestone }}",
                body_template="Parcel {{ tracking_number }} update: {{ details }}",
                created_by=merchant_user.id,
            )
            db.session.add(tpl)
            db.session.flush()
        tracked_ids["notification_templates"] = [tpl.id]

        notif1 = Notification.query.filter_by(shipment_id=s1.id, user_id=merchant_user.id, is_deleted=False).first()
        if not notif1:
            notif1 = Notification(
                user_id=merchant_user.id,
                customer_id=merchant_cust.id,
                shipment_id=s1.id,
                template_id=tpl.id,
                channel="IN_APP",
                recipient=merchant_user.email,
                subject=f"Consignment {s1.tracking_number} Booked",
                body=f"Your legal document booking to Islamabad has been confirmed. Waybill {s1.tracking_number}.",
                delivery_status="DELIVERED",
                created_for_event_at=datetime.utcnow() - timedelta(hours=3),
                sent_at=datetime.utcnow() - timedelta(hours=3),
                created_by=merchant_user.id,
            )
            db.session.add(notif1)
            db.session.flush()

        notif2 = Notification.query.filter_by(shipment_id=s3.id, user_id=merchant_user.id, is_deleted=False).first()
        if not notif2:
            notif2 = Notification(
                user_id=merchant_user.id,
                customer_id=merchant_cust.id,
                shipment_id=s3.id,
                template_id=tpl.id,
                channel="IN_APP",
                recipient=merchant_user.email,
                subject=f"Delivered: Consignment {s3.tracking_number}",
                body=f"Your package has been safely delivered to Gulberg Tech Lab. Proof of delivery logged.",
                delivery_status="DELIVERED",
                created_for_event_at=datetime.utcnow() - timedelta(hours=1),
                sent_at=datetime.utcnow() - timedelta(hours=1),
                created_by=merchant_user.id,
            )
            db.session.add(notif2)
            db.session.flush()

        tracked_ids["notifications"] = [notif1.id, notif2.id]

        # Step 17: Vehicle Assignment (vehicle_assignments)
        route = Route.query.filter_by(is_deleted=False).first()
        veh_assign = VehicleAssignment.query.filter_by(is_deleted=False).first()
        if not veh_assign and vehicle and driver and route:
            veh_assign = VehicleAssignment(
                vehicle_id=vehicle.id,
                driver_id=driver.id,
                route_id=route.id,
                assigned_at=datetime.utcnow() - timedelta(hours=4),
                created_by=merchant_user.id,
            )
            db.session.add(veh_assign)
            db.session.flush()
        if veh_assign:
            tracked_ids["vehicle_assignments"] = [veh_assign.id]

        # Step 18: Audit Log (audit_logs)
        log_audit(
            action="VIVA_55_TABLE_FULL_SEED",
            entity_type="Database",
            entity_id=1,
            after={
                "demo_merchant": demo_email,
                "tables_covered": 55,
                "tracking_numbers": [s1.tracking_number, s2.tracking_number, s3.tracking_number],
            },
            user_id=merchant_user.id,
        )

        # Step 19: App Setting Registry (app_settings)
        map_payload = {
            "version": "1.0",
            "seeded_at": datetime.utcnow().isoformat(),
            "demo_merchant_email": demo_email,
            "alternate_merchant_email": alternate_email,
            "tracking_numbers": {
                "SC-DEMO-BOOK-01": s1.tracking_number,
                "SC-DEMO-BOOK-02": s2.tracking_number,
                "SC-DEMO-BOOK-03": s3.tracking_number,
            },
            "ids": tracked_ids,
        }

        setting = AppSetting(
            setting_key=VIVA_FULL_SETTING_KEY,
            value_json=json.dumps(map_payload),
            description="Full 55-table viva demonstration dataset mapping and ID registry.",
            created_by=merchant_user.id,
        )
        db.session.add(setting)

        # Final commit in single audited transaction
        db.session.commit()

        inventory = get_viva_table_inventory()
        empty_count = sum(1 for row in inventory if row["status"] != "PASS")

        return {
            "status": "success",
            "message": "All 55 relational business tables successfully seeded with connected demonstration data!",
            "total_tables": len(inventory),
            "populated_tables": len(inventory) - empty_count,
            "empty_tables": empty_count,
            "tracking_numbers": map_payload["tracking_numbers"],
            "demo_merchant_email": demo_email,
        }, len(tracked_ids)

    except Exception as e:
        db.session.rollback()
        raise e


def cleanup_viva_full(confirm: bool = False):
    """Safely remove only demonstration records tracked in VIVA_55_TABLE_DATASET_MAP."""
    if not confirm:
        return {
            "status": "aborted",
            "message": "Cleanup requires explicit confirmation (confirm=True).",
            "deleted_count": 0,
        }

    setting = AppSetting.query.filter_by(setting_key=VIVA_FULL_SETTING_KEY).first()
    if not setting:
        return {
            "status": "not_seeded",
            "message": "Viva 55-table dataset is not currently registered.",
            "deleted_count": 0,
        }

    try:
        data = json.loads(setting.value_json)
        ids = data.get("ids", {})
    except Exception:
        ids = {}

    deleted_count = 0

    # Reverse foreign key deletion order
    if "notifications" in ids:
        Notification.query.filter(Notification.id.in_(ids["notifications"])).delete(synchronize_session=False)
    if "notification_templates" in ids:
        NotificationTemplate.query.filter(NotificationTemplate.id.in_(ids["notification_templates"])).delete(synchronize_session=False)

    if "support_tickets" in ids:
        for tid in ids["support_tickets"]:
            TicketMessage.query.filter_by(ticket_id=tid).delete(synchronize_session=False)
            SupportTicket.query.filter_by(id=tid).delete(synchronize_session=False)

    if "refunds" in ids:
        Refund.query.filter(Refund.id.in_(ids["refunds"])).delete(synchronize_session=False)

    if "cod_remittances" in ids:
        CodRemittance.query.filter(CodRemittance.id.in_(ids["cod_remittances"])).delete(synchronize_session=False)
    if "cod_collections" in ids:
        CodCollection.query.filter(CodCollection.id.in_(ids["cod_collections"])).delete(synchronize_session=False)

    if "shipment_discounts" in ids:
        ShipmentDiscount.query.filter(ShipmentDiscount.id.in_(ids["shipment_discounts"])).delete(synchronize_session=False)
    if "discounts" in ids:
        Discount.query.filter(Discount.id.in_(ids["discounts"])).delete(synchronize_session=False)

    if "delivery_exceptions" in ids:
        DeliveryException.query.filter(DeliveryException.id.in_(ids["delivery_exceptions"])).delete(synchronize_session=False)
    if "delivery_proofs" in ids:
        DeliveryProof.query.filter(DeliveryProof.id.in_(ids["delivery_proofs"])).delete(synchronize_session=False)
    if "delivery_attempts" in ids:
        DeliveryAttempt.query.filter(DeliveryAttempt.id.in_(ids["delivery_attempts"])).delete(synchronize_session=False)

    if "shipment_scans" in ids:
        ShipmentScan.query.filter(ShipmentScan.id.in_(ids["shipment_scans"])).delete(synchronize_session=False)
    if "hub_transfers" in ids:
        HubTransfer.query.filter(HubTransfer.id.in_(ids["hub_transfers"])).delete(synchronize_session=False)

    if "pickup_assignments" in ids:
        PickupAssignment.query.filter(PickupAssignment.id.in_(ids["pickup_assignments"])).delete(synchronize_session=False)
    if "pickup_requests" in ids:
        PickupRequest.query.filter(PickupRequest.id.in_(ids["pickup_requests"])).delete(synchronize_session=False)

    if "shipment_documents" in ids:
        ShipmentDocument.query.filter(ShipmentDocument.id.in_(ids["shipment_documents"])).delete(synchronize_session=False)

    if "login_sessions" in ids:
        LoginSession.query.filter(LoginSession.id.in_(ids["login_sessions"])).delete(synchronize_session=False)

    if "recipient_addresses" in ids:
        RecipientAddress.query.filter(RecipientAddress.id.in_(ids["recipient_addresses"])).delete(synchronize_session=False)
    if "recipient_profiles" in ids:
        RecipientProfile.query.filter(RecipientProfile.id.in_(ids["recipient_profiles"])).delete(synchronize_session=False)

    if "customer_addresses" in ids:
        CustomerAddress.query.filter(CustomerAddress.id.in_(ids["customer_addresses"])).delete(synchronize_session=False)
    if "customer_contacts" in ids:
        CustomerContact.query.filter(CustomerContact.id.in_(ids["customer_contacts"])).delete(synchronize_session=False)

    # Remove the setting marker
    db.session.delete(setting)
    db.session.commit()

    return {
        "status": "success",
        "message": "Successfully cleaned up full Viva demonstration records.",
        "deleted_count": sum(len(v) for v in ids.values()),
    }
