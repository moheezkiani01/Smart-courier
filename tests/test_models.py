from app.extensions import db
from app.models.base import AuditMixin
from app.models.organization import Branch

EXPECTED_55_TABLES = [
    # Group A: Authentication & Access Control (6)
    "users", "roles", "permissions", "user_roles", "role_permissions", "login_sessions",
    # Group B: Organization & Employees (6)
    "branches", "hubs", "employees", "employee_branches", "service_zones", "branch_zones",
    # Group C: Customers & Catalog (10)
    "customers", "customer_contacts", "customer_addresses", "recipient_profiles",
    "recipient_addresses", "service_types", "parcel_categories", "packaging_types",
    "rate_cards", "rate_card_rules",
    # Group D: Shipments & Booking (8)
    "shipments", "shipment_items", "shipment_addresses", "shipment_services",
    "shipment_documents", "pickup_requests", "pickup_assignments", "shipment_status_history",
    # Group E: Dispatch, Routing & Delivery (11)
    "routes", "route_stops", "hub_transfers", "shipment_scans", "tracking_events",
    "delivery_attempts", "delivery_proofs", "delivery_exceptions", "vehicles", "drivers",
    "vehicle_assignments",
    # Group F: Finance & Payments (8)
    "invoices", "invoice_items", "payments", "cod_collections", "cod_remittances",
    "refunds", "discounts", "shipment_discounts",
    # Group G: Support & Auditing (6)
    "support_tickets", "ticket_messages", "notifications", "notification_templates",
    "audit_logs", "app_settings"
]

REQUIRED_AUDIT_COLUMNS = {
    "id", "is_deleted", "created_at", "created_by", "updated_at", "updated_by",
    "status", "deleted_at", "deleted_by"
}

def test_exact_55_business_tables_registered(app):
    """Ensure exactly 55 business tables exist in SQLAlchemy metadata."""
    metadata_tables = set(db.metadata.tables.keys())
    for expected_table in EXPECTED_55_TABLES:
        assert expected_table in metadata_tables, f"Missing expected table: {expected_table}"
    assert len(EXPECTED_55_TABLES) == 55

def test_all_models_inherit_universal_audit_columns(app):
    """Verify all 55 business tables implement the 9 universal audit fields."""
    for table_name in EXPECTED_55_TABLES:
        table = db.metadata.tables[table_name]
        cols = {col.name for col in table.columns}
        missing = REQUIRED_AUDIT_COLUMNS - cols
        assert not missing, f"Table {table_name} missing audit columns: {missing}"

def test_soft_delete_and_restore(app):
    """Verify soft_delete and restore lifecycle methods work correctly."""
    with app.app_context():
        branch = Branch.query.first()
        assert branch is not None
        assert branch.is_deleted is False
        assert branch.status == "ACTIVE"

        # Perform soft delete
        branch.soft_delete(user_id=1)
        db.session.commit()

        assert branch.is_deleted is True
        assert branch.status == "DEACTIVE"
        assert branch.deleted_at is not None
        assert branch.deleted_by == 1

        # Restore entity
        branch.restore(user_id=1)
        db.session.commit()

        assert branch.is_deleted is False
        assert branch.status == "ACTIVE"
        assert branch.deleted_at is None
        assert branch.deleted_by is None
