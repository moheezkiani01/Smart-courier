import pytest
from flask import url_for
from app.extensions import db
from app.models.auth import User, Role, UserRole
from app.models.catalog import Customer, CustomerAddress, RecipientProfile, RecipientAddress, RateCard
from app.models.shipments import Shipment, ShipmentItem, ShipmentAddress, PickupRequest
from app.models.finance import Invoice
from app.services.shipment_service import ShipmentService

def login_as(client, email, password="AdminPass@1234"):
    client.post("/auth/logout", follow_redirects=True)
    res = client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)
    assert res.status_code == 200
    return res

def test_01_customer_can_open_booking_get(client):
    """1. Verify CUSTOMER receives HTTP 200 for booking form without 403."""
    login_as(client, "customer@smartcourier.pk")
    res = client.get("/shipments/new")
    assert res.status_code == 200
    assert b"Book New Shipment" in res.data
    assert b"Sender &amp; Recipient Details" in res.data or b"Sender & Recipient Details" in res.data
    client.post("/auth/logout", follow_redirects=True)

def test_02_customer_can_book_valid_parcel(client, app):
    """2. Verify customer can complete POST booking and redirect to shipment detail."""
    login_as(client, "customer@smartcourier.pk")
    
    post_data = {
        "sender_name": "Usman Malik",
        "sender_phone": "+923009990011",
        "sender_zone_id": 1,
        "sender_city": "Lahore",
        "sender_line1": "Flat 4B, Gulberg Heights",
        "sender_postal": "54000",
        "recipient_name": "Babar Azam",
        "recipient_phone": "+923215554433",
        "recipient_zone_id": 2,
        "recipient_city": "Karachi",
        "recipient_line1": "House 12, DHA Phase 5",
        "recipient_postal": "75500",
        "service_type_id": 1,
        "parcel_category_id": 1,
        "packaging_type_id": 1,
        "item_description": "Electronics Component",
        "item_quantity": 1,
        "weight_grams": 650,
        "declared_value_pkr": 5000,
        "cod_due_pkr": 3500,
        "pickup_type": "PICKUP",
        "pickup_time_slot": "MORNING",
        "pickup_notes": "Call upon gate arrival",
    }
    res = client.post("/shipments/new", data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Shipment booked successfully!" in res.data or b"Tracking Number:" in res.data

    with app.app_context():
        cust = Customer.query.filter_by(email="customer@smartcourier.pk").first()
        latest = Shipment.query.filter_by(customer_id=cust.id).order_by(Shipment.id.desc()).first()
        assert latest is not None
        assert latest.customer_id == cust.id
        assert latest.weight_grams == 650
        assert latest.declared_value_paisa == 500000
        assert latest.cod_due_paisa == 350000
        assert latest.shipment_status == "BOOKED"
        assert len(latest.pickup_requests) == 1

    client.post("/auth/logout", follow_redirects=True)

def test_03_customer_booking_sets_own_customer_id(client, app):
    """3. Verify DB owner strictly matches current user's customer record."""
    login_as(client, "customer@smartcourier.pk")
    
    with app.app_context():
        cust = Customer.query.filter_by(email="customer@smartcourier.pk").first()
        initial_count = Shipment.query.filter_by(customer_id=cust.id).count()

    post_data = {
        "sender_name": "Usman Merchant",
        "sender_phone": "+923009990011",
        "sender_zone_id": 1,
        "sender_city": "Lahore",
        "sender_line1": "Shop 14, Hafeez Centre",
        "recipient_name": "Haris Rauf",
        "recipient_phone": "+923334445566",
        "recipient_zone_id": 1,
        "recipient_city": "Lahore",
        "recipient_line1": "Street 9, Model Town",
        "service_type_id": 1,
        "parcel_category_id": 1,
        "packaging_type_id": 1,
        "item_description": "Documents",
        "item_quantity": 1,
        "weight_grams": 300,
        "declared_value_pkr": 0,
        "cod_due_pkr": 0,
        "pickup_type": "DROP_OFF",
    }
    res = client.post("/shipments/new", data=post_data, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        new_count = Shipment.query.filter_by(customer_id=cust.id).count()
        assert new_count == initial_count + 1

    client.post("/auth/logout", follow_redirects=True)

def test_04_customer_cannot_post_other_customer_id(client, app):
    """4. Verify tampered customer_id in POST is safely ignored and bound to current user."""
    login_as(client, "customer@smartcourier.pk")

    with app.app_context():
        cust = Customer.query.filter_by(email="customer@smartcourier.pk").first()

    post_data = {
        "customer_id": 9999,  # Malicious attempt to forge customer ID
        "sender_name": "Usman Malik",
        "sender_phone": "+923009990011",
        "sender_zone_id": 1,
        "sender_city": "Lahore",
        "sender_line1": "Office 1, Main Blvd",
        "recipient_name": "Shaheen Afridi",
        "recipient_phone": "+923217778899",
        "recipient_zone_id": 2,
        "recipient_city": "Karachi",
        "recipient_line1": "Block 4, Clifton",
        "service_type_id": 1,
        "parcel_category_id": 1,
        "packaging_type_id": 1,
        "item_description": "Apparel Sample",
        "item_quantity": 1,
        "weight_grams": 400,
        "declared_value_pkr": 1000,
        "cod_due_pkr": 0,
    }
    res = client.post("/shipments/new", data=post_data, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        latest = Shipment.query.order_by(Shipment.id.desc()).first()
        # Verify it was NOT assigned to 9999, but to logged in customer
        assert latest.customer_id == cust.id

    client.post("/auth/logout", follow_redirects=True)

def test_05_customer_without_profile_auto_provisioned_safely(client, app):
    """5. Verify customer user without customer record gets safely auto-provisioned."""
    with app.app_context():
        # Create a user with CUSTOMER role but no Customer profile
        orphan_user = User.query.filter_by(email="orphan.customer@smartcourier.pk").first()
        if not orphan_user:
            orphan_user = User(
                email="orphan.customer@smartcourier.pk",
                full_name="Orphan Customer",
                phone="+923001239999",
                is_email_verified=True,
            )
            orphan_user.set_password("AdminPass@1234")
            db.session.add(orphan_user)
            db.session.flush()

            cust_role = Role.query.filter_by(code="CUSTOMER").first()
            ur = UserRole(user_id=orphan_user.id, role_id=cust_role.id)
            db.session.add(ur)
            db.session.commit()

    login_as(client, "orphan.customer@smartcourier.pk")
    res = client.get("/shipments/new")
    assert res.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="orphan.customer@smartcourier.pk").first()
        assert user.customer is not None
        assert user.customer.user_id == user.id

    client.post("/auth/logout", follow_redirects=True)

def test_06_customer_booking_atomic_records(app):
    """6. Verify booking creates shipment, item, addresses, status history, and invoice."""
    with app.app_context():
        admin = User.query.filter_by(email="admin@smartcourier.pk").first()
        cust = Customer.query.first()
        sender = {"name": "Test S", "phone": "03001", "zone_id": 1, "line1": "L1", "city": "LHR"}
        recip = {"name": "Test R", "phone": "03002", "zone_id": 2, "line1": "L2", "city": "KHI"}
        items = [{"description": "Box", "quantity": 1, "weight_grams": 500, "declared_value_paisa": 100000}]

        shipment = ShipmentService.book_shipment(
            customer_id=cust.id,
            origin_branch_id=1,
            destination_branch_id=2,
            service_type_id=1,
            parcel_category_id=1,
            packaging_type_id=1,
            sender_data=sender,
            recipient_data=recip,
            items_data=items,
            actor_user_id=admin.id,
            schedule_pickup=True,
        )

        assert shipment.id is not None
        assert len(shipment.items) == 1
        assert shipment.sender_address is not None
        assert shipment.recipient_address is not None
        assert shipment.invoice is not None
        assert len(shipment.status_history) >= 1
        assert len(shipment.pickup_requests) == 1

def test_07_customer_booking_rollback_on_pricing_failure(app):
    """7. Verify booking rolls back completely on pricing or zone failure."""
    with app.app_context():
        cust = Customer.query.first()
        sender = {"name": "Test S", "phone": "03001", "zone_id": 9999, "line1": "L1", "city": "LHR"}
        recip = {"name": "Test R", "phone": "03002", "zone_id": 9998, "line1": "L2", "city": "KHI"}
        items = [{"description": "Box", "quantity": 1, "weight_grams": 500}]

        count_before = Shipment.query.count()
        with pytest.raises(Exception):
            ShipmentService.book_shipment(
                customer_id=cust.id,
                origin_branch_id=1,
                destination_branch_id=2,
                service_type_id=1,
                parcel_category_id=1,
                packaging_type_id=1,
                sender_data=sender,
                recipient_data=recip,
                items_data=items,
                actor_user_id=1,
            )
        db.session.rollback()
        count_after = Shipment.query.count()
        assert count_before == count_after

def test_08_customer_dashboard_contains_book_action(client):
    """8. Verify customer dashboard header has Book a Parcel action."""
    login_as(client, "customer@smartcourier.pk")
    res = client.get("/")
    assert res.status_code == 200
    assert b"Book a Parcel" in res.data
    assert b"My Parcels" in res.data
    assert b"Rate Estimator" in res.data
    client.post("/auth/logout", follow_redirects=True)

def test_09_customer_cannot_see_other_customer_shipment(client, app):
    """9. Verify Customer A cannot view Customer B's shipment (403 Forbidden)."""
    with app.app_context():
        # Create second customer user
        cust_b_user = User.query.filter_by(email="customer_b@smartcourier.pk").first()
        if not cust_b_user:
            cust_b_user = User(
                email="customer_b@smartcourier.pk",
                full_name="Customer B",
                phone="+923007770000",
                is_email_verified=True,
            )
            cust_b_user.set_password("AdminPass@1234")
            db.session.add(cust_b_user)
            db.session.flush()

            cust_role = Role.query.filter_by(code="CUSTOMER").first()
            ur = UserRole(user_id=cust_b_user.id, role_id=cust_role.id)
            db.session.add(ur)

            cust_b_profile = Customer(
                user_id=cust_b_user.id,
                customer_code=f"CUST-{cust_b_user.id:04d}",
                full_name="Customer B",
                phone="+923007770000",
                email="customer_b@smartcourier.pk",
            )
            db.session.add(cust_b_profile)
            db.session.commit()

        # Find or create a shipment for customer A
        cust_a = Customer.query.filter_by(email="customer@smartcourier.pk").first()
        shipment_a = Shipment.query.filter_by(customer_id=cust_a.id, is_deleted=False).first()

    # Log in as Customer B and try to view Customer A's shipment
    login_as(client, "customer_b@smartcourier.pk")
    res = client.get(f"/shipments/{shipment_a.id}")
    assert res.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_10_customer_cannot_see_other_customer_label_or_invoice(client, app):
    """10. Verify Customer B cannot view Customer A's shipping label or invoice."""
    with app.app_context():
        cust_a = Customer.query.filter_by(email="customer@smartcourier.pk").first()
        shipment_a = Shipment.query.filter_by(customer_id=cust_a.id, is_deleted=False).first()
        invoice_a = Invoice.query.filter_by(customer_id=cust_a.id, is_deleted=False).first()

    login_as(client, "customer_b@smartcourier.pk")
    # Label
    res_label = client.get(f"/shipments/{shipment_a.id}/label")
    assert res_label.status_code == 403

    # Invoice
    res_inv = client.get(f"/finance/invoices/{invoice_a.id}")
    assert res_inv.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_11_customer_service_boundary_rejects_forged_customer_id(app):
    """11. Verify service layer blocks customer from booking for another customer."""
    with app.app_context():
        cust_user = User.query.filter_by(email="customer@smartcourier.pk").first()
        other_cust = Customer.query.filter(Customer.id != cust_user.customer.id).first()

        sender = {"name": "S", "phone": "1", "zone_id": 1, "line1": "A", "city": "LHR"}
        recip = {"name": "R", "phone": "2", "zone_id": 2, "line1": "B", "city": "KHI"}
        items = [{"description": "Item", "quantity": 1, "weight_grams": 500}]

        with pytest.raises(PermissionError) as exc:
            ShipmentService.book_shipment(
                customer_id=other_cust.id,
                origin_branch_id=1,
                destination_branch_id=2,
                service_type_id=1,
                parcel_category_id=1,
                packaging_type_id=1,
                sender_data=sender,
                recipient_data=recip,
                items_data=items,
                actor_user_id=cust_user.id,
            )
        assert "Customers can only book shipments for their own" in str(exc.value)

def test_12_customer_registration_success(client, app):
    """12. Verify public self-registration creates User, Customer profile, and auto-logs in."""
    client.post("/auth/logout", follow_redirects=True)
    post_data = {
        "full_name": "Zahid Hussain",
        "email": "zahid.new@example.com",
        "phone": "+923001122445",
        "password": "CustomerSecret@123",
        "confirm_password": "CustomerSecret@123",
        "agree_terms": True,
    }
    res = client.post("/auth/register", data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Welcome to Smart Courier, Zahid Hussain!" in res.data or b"My Parcels" in res.data

    with app.app_context():
        new_user = User.query.filter_by(email="zahid.new@example.com").first()
        assert new_user is not None
        assert new_user.has_role("CUSTOMER")
        assert not new_user.has_role("SUPER_ADMIN")
        assert new_user.customer is not None
        assert new_user.customer.full_name == "Zahid Hussain"

    client.post("/auth/logout", follow_redirects=True)

def test_13_customer_registration_duplicate_email_rejected(client):
    """13. Verify registration rejects duplicate email with friendly message."""
    client.post("/auth/logout", follow_redirects=True)
    post_data = {
        "full_name": "Duplicate User",
        "email": "customer@smartcourier.pk",  # Already exists
        "phone": "+923009990011",
        "password": "CustomerSecret@123",
        "confirm_password": "CustomerSecret@123",
        "agree_terms": True,
    }
    res = client.post("/auth/register", data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"already exists" in res.data

def test_14_customer_address_book_isolation(client, app):
    """14. Verify Customer B cannot view or add address to Customer A's account."""
    with app.app_context():
        cust_a = Customer.query.filter_by(email="customer@smartcourier.pk").first()
        cust_b = Customer.query.filter_by(email="customer_b@smartcourier.pk").first()

    # Customer B attempts to view Customer A's customer profile
    login_as(client, "customer_b@smartcourier.pk")
    res_view = client.get(f"/customers/{cust_a.id}")
    assert res_view.status_code == 403

    # Customer B attempts to add address to Customer A
    res_add = client.post(f"/customers/{cust_a.id}/addresses/new", data={
        "label": "Hacked Address",
        "zone_id": 1,
        "line1": "Fake St",
        "city": "Lahore",
    })
    assert res_add.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_15_live_quote_api_calculation(client):
    """15. Verify real-time quote API endpoint returns valid JSON with correct rates."""
    res = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 500,
        "packaging_type_id": 1,
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "quote" in data
    assert data["quote"]["total_pkr"] > 0
    assert data["quote"]["currency"] == "PKR"
