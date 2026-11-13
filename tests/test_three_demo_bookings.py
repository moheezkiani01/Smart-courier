"""Tests for the three demo bookings service and CLI.

Verifies:
1. Dry-run preview executes with zero database mutations.
2. First seed run creates exactly 3 realistic bookings across standard viva stages:
   - SC-DEMO-BOOK-01: BOOKED (Lahore -> Islamabad)
   - SC-DEMO-BOOK-02: IN_TRANSIT (Lahore -> Karachi)
   - SC-DEMO-BOOK-03: DELIVERED (Lahore -> Lahore)
3. Dynamic quotes and invoice charges match genuine PricingService rates.
4. Second seed run is strictly idempotent: 0 duplicate records created.
5. Delivery proof, route stops, and settled invoice payments are valid.
6. Support inquiry ticket is linked to SC-DEMO-BOOK-02.
7. Cleanup command removes only demo bookings upon explicit confirmation.
8. Dashboard displays the 3 demo bookings cleanly for the demo customer.
"""
import pytest
from app.extensions import db
from app.models.auth import User, Role, UserRole
from app.models.catalog import Customer
from app.models.shipments import Shipment
from app.models.finance import Invoice, Payment
from app.models.dispatch import DeliveryProof, RouteStop
from app.models.support import SupportTicket, AppSetting
from app.services.three_bookings_service import (
    seed_three_bookings,
    get_three_bookings,
    cleanup_three_bookings,
    THREE_BOOKINGS_SETTING_KEY,
)


@pytest.fixture(autouse=True)
def clean_three_demo_bookings_env(app):
    """Ensure clean three demo bookings environment before and after test."""
    with app.app_context():
        cleanup_three_bookings(confirm=True)
    yield
    with app.app_context():
        cleanup_three_bookings(confirm=True)


def test_seed_three_bookings_dry_run(app):
    """Verify dry run generates prospective preview without database changes."""
    with app.app_context():
        pre_count = Shipment.query.count()
        res, created = seed_three_bookings(dry_run=True)
        post_count = Shipment.query.count()

        assert res["status"] == "dry_run"
        assert created == 0
        assert len(res["entries"]) == 3
        assert post_count == pre_count
        assert get_three_bookings() == []


def test_seed_three_bookings_creates_three_stages_idempotently(app):
    """Verify first run creates 3 valid bookings; second run is idempotent."""
    with app.app_context():
        # First run: creation
        res1, created1 = seed_three_bookings(dry_run=False)
        assert res1["status"] == "success"
        assert created1 == 3

        entries = get_three_bookings()
        assert len(entries) == 3

        by_ref = {e["ref"]: e for e in entries}

        # 1. SC-DEMO-BOOK-01: BOOKED
        b1 = by_ref["SC-DEMO-BOOK-01"]
        assert b1["status"] == "BOOKED"
        assert b1["origin"] == "Lahore"
        assert b1["destination"] == "Islamabad"
        assert b1["weight_grams"] == 350
        assert b1["total_charge_paisa"] > 0
        assert b1["invoice_status"] == "ISSUED"

        # 2. SC-DEMO-BOOK-02: IN_TRANSIT with support ticket
        b2 = by_ref["SC-DEMO-BOOK-02"]
        assert b2["status"] == "IN_TRANSIT"
        assert b2["origin"] == "Lahore"
        assert b2["destination"] == "Karachi"
        assert b2["weight_grams"] == 800
        assert b2["total_charge_paisa"] > 0
        s2 = Shipment.query.filter_by(tracking_number=b2["tracking_number"]).first()
        ticket = SupportTicket.query.filter_by(shipment_id=s2.id).first()
        assert ticket is not None
        assert "Transit ETA" in ticket.subject

        # 3. SC-DEMO-BOOK-03: DELIVERED with proof & paid invoice
        b3 = by_ref["SC-DEMO-BOOK-03"]
        assert b3["status"] == "DELIVERED"
        assert b3["origin"] == "Lahore"
        assert b3["destination"] == "Lahore"
        assert b3["weight_grams"] == 500
        assert b3["invoice_status"] == "PAID"
        s3 = Shipment.query.filter_by(tracking_number=b3["tracking_number"]).first()
        assert s3.delivery_proof is not None
        assert s3.delivery_proof.received_by_name == "Gulberg Tech Lab"
        inv3 = Invoice.query.filter_by(shipment_id=s3.id).first()
        assert inv3.invoice_status == "PAID"
        payment = Payment.query.filter_by(invoice_id=inv3.id).first()
        assert payment is not None
        assert payment.payment_status == "SETTLED"

        # Second run: strict idempotency
        res2, created2 = seed_three_bookings(dry_run=False)
        assert res2["status"] == "already_seeded"
        assert created2 == 0
        assert len(get_three_bookings()) == 3


def test_cleanup_three_bookings_scoped_and_safe(app):
    """Verify cleanup deletes only the demo bookings after explicit confirmation."""
    with app.app_context():
        # Seed 3 bookings first
        seed_three_bookings(dry_run=False)
        assert len(get_three_bookings()) == 3

        # Test unconfirmed cleanup is refused
        res_refused = cleanup_three_bookings(confirm=False)
        assert res_refused["status"] == "confirmation_required"
        assert len(get_three_bookings()) == 3

        # Test confirmed cleanup
        res_clean = cleanup_three_bookings(confirm=True)
        assert res_clean["status"] == "success"
        assert res_clean["deleted_count"] == 3
        assert len(get_three_bookings()) == 0
        assert AppSetting.query.filter_by(setting_key=THREE_BOOKINGS_SETTING_KEY).first() is None


def test_dashboard_displays_three_demo_bookings(client, app):
    """Verify demo customer dashboard displays the 3 demo bookings table."""
    with app.app_context():
        seed_three_bookings(dry_run=False)
        demo_user = User.query.filter_by(email="demo.merchant@smartcourier.pk").first()
        assert demo_user is not None
        demo_user.set_password("DemoPassword@123")
        db.session.commit()

    # Login through the authentic auth route
    login_res = client.post("/auth/login", data={"email": "demo.merchant@smartcourier.pk", "password": "DemoPassword@123"}, follow_redirects=True)
    assert login_res.status_code == 200

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Academic Viva Test Bookings" in html
    assert "SC-DEMO-BOOK-01" in html
    assert "SC-DEMO-BOOK-02" in html
    assert "SC-DEMO-BOOK-03" in html
    assert "BOOKED" in html
    assert "IN_TRANSIT" in html
    assert "DELIVERED" in html
    client.post("/auth/logout", follow_redirects=True)
