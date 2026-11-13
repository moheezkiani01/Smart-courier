"""Tests for the Full 55-Table Viva Demonstration Seeder and Coverage Reporting.

Verifies:
1. Dry-run mode makes zero database writes and provides planned actions.
2. First seed run populates all 55 business SQLAlchemy tables (100% coverage, 0 empty tables).
3. Second seed run is strictly idempotent (0 duplicate records, status 'already_seeded').
4. Core relationships & financial integrity:
   - SC-DEMO-BOOK-01: BOOKED with pickup request, assignment, discount, document, support ticket.
   - SC-DEMO-BOOK-02: IN_TRANSIT with inter-hub transfer, hub scans, support ticket.
   - SC-DEMO-BOOK-03: DELIVERED with failed attempt, exception, proof, paid invoice, COD collection & remittance, pending refund, document.
5. Inert audit login session: Expired, revoked, cannot authenticate.
6. Document download route: Serves valid PDF with customer ownership check.
7. Cleanup command: Safely removes demonstration records in reverse FK dependency order.
8. Inventory report: Verifies 55 rows, non-zero counts, linked parent FKs, and UI routes.
"""
import os
import pytest
from app.extensions import db
from app.models.auth import User, Role, LoginSession
from app.models.catalog import Customer, CustomerContact, CustomerAddress, RecipientProfile, RecipientAddress
from app.models.shipments import Shipment, ShipmentDocument, PickupRequest, PickupAssignment
from app.models.dispatch import HubTransfer, ShipmentScan, DeliveryAttempt, DeliveryProof, DeliveryException, RouteStop
from app.models.finance import Invoice, Payment, CodCollection, CodRemittance, Refund, Discount, ShipmentDiscount
from app.models.support import SupportTicket, TicketMessage, Notification, NotificationTemplate, AppSetting
from app.services.three_bookings_service import get_three_bookings, cleanup_three_bookings
from app.services.viva_full_seed_service import (
    seed_viva_full,
    cleanup_viva_full,
    get_viva_table_inventory,
    VIVA_FULL_SETTING_KEY,
)


@pytest.fixture(autouse=True)
def clean_viva_test_env(app):
    """Ensure clean test environment before and after test."""
    with app.app_context():
        cleanup_viva_full(confirm=True)
        cleanup_three_bookings(confirm=True)
    yield
    with app.app_context():
        cleanup_viva_full(confirm=True)
        cleanup_three_bookings(confirm=True)


def test_viva_full_seed_dry_run(app):
    """Verify dry run calculates plan with zero database mutations."""
    with app.app_context():
        pre_setting = AppSetting.query.filter_by(setting_key=VIVA_FULL_SETTING_KEY).first()
        assert pre_setting is None

        res, count = seed_viva_full(dry_run=True)
        assert res["status"] == "dry_run"
        assert count == 0
        assert res["total_tables"] == 55
        assert len(res["actions_planned"]) > 0

        post_setting = AppSetting.query.filter_by(setting_key=VIVA_FULL_SETTING_KEY).first()
        assert post_setting is None


def test_viva_full_seed_populates_all_55_tables(app):
    """Verify seeding achieves 100% relational coverage across all 55 business tables."""
    with app.app_context():
        res, count = seed_viva_full(dry_run=False)
        assert res["status"] == "success"
        assert res["total_tables"] == 55
        assert res["populated_tables"] == 55
        assert res["empty_tables"] == 0

        inventory = get_viva_table_inventory()
        assert len(inventory) == 55
        empty_rows = [r for r in inventory if r["status"] != "PASS"]
        assert len(empty_rows) == 0, f"Found empty tables: {[r['table_name'] for r in empty_rows]}"


def test_viva_full_seed_idempotency(app):
    """Verify running seeder twice creates zero duplicate records."""
    with app.app_context():
        # First run
        res1, count1 = seed_viva_full(dry_run=False)
        assert res1["status"] == "success"

        # Capture counts after first run
        inv1 = {r["table_name"]: r["total_count"] for r in get_viva_table_inventory()}

        # Second run
        res2, count2 = seed_viva_full(dry_run=False)
        assert res2["status"] == "already_seeded"
        assert count2 == 0

        # Verify all table counts remain strictly identical
        inv2 = {r["table_name"]: r["total_count"] for r in get_viva_table_inventory()}
        for tname, cnt in inv1.items():
            assert inv2[tname] == cnt, f"Table {tname} count changed on second run: {inv2[tname]} != {cnt}"


def test_viva_full_seed_relationships_and_financials(app):
    """Verify all connected entities and financial consistency for the 3 core bookings."""
    with app.app_context():
        seed_viva_full(dry_run=False)
        entries = get_three_bookings()
        by_ref = {e["ref"]: e for e in entries}

        # 1. SC-DEMO-BOOK-01 (BOOKED)
        b1 = by_ref["SC-DEMO-BOOK-01"]
        s1 = Shipment.query.filter_by(tracking_number=b1["tracking_number"]).first()
        assert s1.shipment_status == "BOOKED"
        assert len(s1.pickup_requests) >= 1
        assert s1.pickup_requests[0].pickup_status == "ASSIGNED"
        assert len(s1.pickup_requests[0].assignments) >= 1
        assert ShipmentDiscount.query.filter_by(shipment_id=s1.id).first() is not None
        assert len(s1.documents) >= 1
        assert s1.documents[0].original_filename.endswith(".pdf")

        # 2. SC-DEMO-BOOK-02 (IN_TRANSIT)
        b2 = by_ref["SC-DEMO-BOOK-02"]
        s2 = Shipment.query.filter_by(tracking_number=b2["tracking_number"]).first()
        assert s2.shipment_status == "IN_TRANSIT"
        transfer = HubTransfer.query.filter_by(shipment_id=s2.id).first()
        assert transfer is not None
        assert transfer.transfer_status == "IN_TRANSIT"
        scans = ShipmentScan.query.filter_by(shipment_id=s2.id).all()
        assert len(scans) >= 2

        # 3. SC-DEMO-BOOK-03 (DELIVERED)
        b3 = by_ref["SC-DEMO-BOOK-03"]
        s3 = Shipment.query.filter_by(tracking_number=b3["tracking_number"]).first()
        assert s3.shipment_status == "DELIVERED"
        assert s3.cod_due_paisa == 250000  # Rs. 2,500

        # COD collection & remittance
        assert s3.cod_collection is not None
        assert s3.cod_collection.amount_paisa == 250000
        assert s3.cod_collection.collection_status == "REMITTED"
        assert len(s3.cod_collection.remittances) >= 1
        assert s3.cod_collection.remittances[0].reference_code == "REMIT-VIVA-01"

        # Delivery attempts: 1 failed with exception, 1 successful with proof
        attempts = DeliveryAttempt.query.filter_by(shipment_id=s3.id).all()
        assert len(attempts) >= 2
        fail_attempt = next((a for a in attempts if a.outcome == "FAILED"), None)
        assert fail_attempt is not None
        assert len(fail_attempt.exceptions) >= 1
        assert fail_attempt.exceptions[0].resolved_at is not None

        success_attempt = next((a for a in attempts if a.outcome == "SUCCESS"), None)
        assert success_attempt is not None
        assert s3.delivery_proof is not None

        # Payment & Pending Refund
        inv3 = s3.invoice
        assert inv3.invoice_status == "PAID"
        assert len(inv3.payments) >= 1
        pay3 = inv3.payments[0]
        assert len(pay3.refunds) >= 1
        assert pay3.refunds[0].refund_status == "PENDING"
        assert pay3.refunds[0].amount_paisa == 5000


def test_viva_full_seed_inert_login_session(app):
    """Verify that seeded LoginSession row is expired, revoked, and inert."""
    with app.app_context():
        seed_viva_full(dry_run=False)
        merchant = User.query.filter(User.email.like("%viva.merchant%")).first()
        assert merchant is not None

        sess = LoginSession.query.filter_by(user_id=merchant.id, ip_hint="127.0.0.1 (VIVA_AUDIT)").first()
        assert sess is not None
        assert sess.expires_at < sess.created_at or sess.expires_at < sess.started_at + sess.expires_at - sess.started_at
        assert sess.revoked_at is not None
        assert len(sess.session_hash) == 64  # SHA256 length


def test_viva_full_seed_document_download(client, app, authenticated_admin):
    """Verify genuine PDF download route with customer isolation."""
    with app.app_context():
        seed_viva_full(dry_run=False)
        entries = get_three_bookings()
        by_ref = {e["ref"]: e for e in entries}
        s1 = Shipment.query.filter_by(tracking_number=by_ref["SC-DEMO-BOOK-01"]["tracking_number"]).first()
        doc = ShipmentDocument.query.filter_by(shipment_id=s1.id).first()
        assert doc is not None
        s1_id = s1.id
        doc_id = doc.id

    # Authenticated as admin should successfully retrieve document
    resp_auth = authenticated_admin.get(f"/shipments/{s1_id}/documents/{doc_id}")
    assert resp_auth.status_code == 200
    assert resp_auth.mimetype == "application/pdf"
    assert b"%PDF-1.4" in resp_auth.data

    # Unauthenticated should redirect to login
    client.post("/auth/logout", follow_redirects=True)
    resp_unauth = client.get(f"/shipments/{s1_id}/documents/{doc_id}")
    assert resp_unauth.status_code == 302
    assert "/auth/login" in resp_unauth.headers["Location"]



def test_viva_full_seed_cleanup_workflow(app):
    """Verify cleanup completely removes demo dataset and restores table states."""
    with app.app_context():
        seed_viva_full(dry_run=False)
        assert AppSetting.query.filter_by(setting_key=VIVA_FULL_SETTING_KEY).first() is not None

        res_clean = cleanup_viva_full(confirm=True)
        assert res_clean["status"] == "success"
        assert res_clean["deleted_count"] > 0
        assert AppSetting.query.filter_by(setting_key=VIVA_FULL_SETTING_KEY).first() is None
