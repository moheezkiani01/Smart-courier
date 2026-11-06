#!/usr/bin/env python3
"""
Schema Verification Script for Smart Courier & Parcel Delivery Management System.
Verifies all 55 SQLAlchemy business tables, audit mixin columns, SQLite foreign key enforcement,
and integrity constraints.
"""
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import inspect, text

EXPECTED_TABLES = [
    # Group A: Authentication & Access Control (6)
    "users",
    "roles",
    "permissions",
    "user_roles",
    "role_permissions",
    "login_sessions",
    # Group B: Organization & Employees (6)
    "branches",
    "hubs",
    "employees",
    "employee_branches",
    "service_zones",
    "branch_zones",
    # Group C: Customers & Catalog (10)
    "customers",
    "customer_contacts",
    "customer_addresses",
    "recipient_profiles",
    "recipient_addresses",
    "service_types",
    "parcel_categories",
    "packaging_types",
    "rate_cards",
    "rate_card_rules",
    # Group D: Shipments & Booking (8)
    "shipments",
    "shipment_items",
    "shipment_addresses",
    "shipment_services",
    "shipment_documents",
    "pickup_requests",
    "pickup_assignments",
    "shipment_status_history",
    # Group E: Dispatch, Routing & Delivery (11)
    "routes",
    "route_stops",
    "hub_transfers",
    "shipment_scans",
    "tracking_events",
    "delivery_attempts",
    "delivery_proofs",
    "delivery_exceptions",
    "vehicles",
    "drivers",
    "vehicle_assignments",
    # Group F: Finance & Payments (8)
    "invoices",
    "invoice_items",
    "payments",
    "cod_collections",
    "cod_remittances",
    "refunds",
    "discounts",
    "shipment_discounts",
    # Group G: Support & Auditing (6)
    "support_tickets",
    "ticket_messages",
    "notifications",
    "notification_templates",
    "audit_logs",
    "app_settings",
]

REQUIRED_AUDIT_COLUMNS = {
    "id",
    "is_deleted",
    "created_at",
    "created_by",
    "updated_at",
    "updated_by",
    "status",
    "deleted_at",
    "deleted_by",
}

def verify_schema(app, db):
    print("=" * 70)
    print("SMART COURIER — SCHEMA VERIFICATION")
    print("=" * 70)

    with app.app_context():
        with db.engine.connect() as connection:
            inspector = inspect(db.engine)
            dialect_name = connection.dialect.name

            # 1. Check SQLite Foreign Keys Pragma (only on SQLite engines)
            if dialect_name == "sqlite":
                fk_pragma = connection.execute(text("PRAGMA foreign_keys")).scalar()
                print(f"[*] SQLite PRAGMA foreign_keys: {fk_pragma} (Expected: 1)")
                if fk_pragma != 1:
                    print("[!] ERROR: SQLite foreign key enforcement is NOT enabled!")
                    return False

                # 2. Check SQLite Foreign Key Integrity Check
                fk_violations = connection.execute(text("PRAGMA foreign_key_check")).fetchall()
                print(f"[*] SQLite PRAGMA foreign_key_check violations: {len(fk_violations)}")
                if fk_violations:
                    print("[!] Foreign key violations found:")
                    for v in fk_violations:
                        print(f"    Table: {v[0]}, RowId: {v[1]}, Target: {v[2]}, FkId: {v[3]}")
                    return False
            else:
                print(f"[*] Relational database engine: {dialect_name} (foreign keys enforced natively)")

            # 3. Tables in database vs metadata
            db_tables = set(inspector.get_table_names())
            # Filter out alembic_version if present
            business_tables = [t for t in db_tables if t != "alembic_version"]
            print(f"[*] Database Business Tables Found: {len(business_tables)} / 55")

            missing_tables = set(EXPECTED_TABLES) - set(business_tables)
            if missing_tables:
                print(f"[!] Missing Tables ({len(missing_tables)}):")
                for t in sorted(missing_tables):
                    print(f"    - {t}")
                return False

            # 4. Check Audit Columns on each table
            missing_audit_cols = {}
            for table_name in EXPECTED_TABLES:
                cols = {col["name"] for col in inspector.get_columns(table_name)}
                missing = REQUIRED_AUDIT_COLUMNS - cols
                if missing:
                    missing_audit_cols[table_name] = missing

            if missing_audit_cols:
                print("[!] Missing Audit Columns:")
                for table_name, missing in missing_audit_cols.items():
                    print(f"    {table_name}: {missing}")
                return False

            print("[+] All 55 business tables verified successfully with all audit columns!")
            print("=" * 70)
            return True

if __name__ == "__main__":
    from app import create_app
    from app.extensions import db
    app = create_app()
    success = verify_schema(app, db)
    sys.exit(0 if success else 1)
