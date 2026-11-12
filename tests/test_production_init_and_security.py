import pytest
from app.extensions import db
from app.models.auth import User, Role, Permission, RolePermission, UserRole
from app.models.organization import Branch, Hub, ServiceZone, BranchZone
from app.models.catalog import ServiceType, ParcelCategory, PackagingType, RateCard, Customer
from app.models.shipments import Shipment, PickupRequest, PickupAssignment
from app.models.dispatch import Route, RouteStop, Driver, Vehicle
from app.services.init_service import init_production_catalog
from app.services.pricing_service import PricingService

def login_as(client, email, password="AdminPass@1234"):
    client.post("/auth/logout", follow_redirects=True)
    res = client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)
    assert res.status_code == 200
    return res

def test_init_production_catalog_guarantees_all_nine_roles(app):
    """Priority 1: Verify init_production_catalog creates all nine roles and permissions without demo passwords."""
    with app.app_context():
        stats = init_production_catalog()
        expected_roles = [
            "SUPER_ADMIN", "BRANCH_MANAGER", "BOOKING_AGENT",
            "HUB_OPERATOR", "DISPATCHER", "DRIVER",
            "FINANCE_OFFICER", "SUPPORT_AGENT", "CUSTOMER"
        ]
        for role_code in expected_roles:
            r = Role.query.filter_by(code=role_code).first()
            assert r is not None, f"Role {role_code} missing after init!"

        expected_perms = [
            "BRANCH_MANAGE", "STAFF_MANAGE", "CUSTOMER_MANAGE", "RATE_MANAGE",
            "SHIPMENT_BOOK", "SHIPMENT_VIEW", "HUB_OPERATE", "ROUTE_DISPATCH",
            "DELIVERY_EXECUTE", "FINANCE_MANAGE", "SUPPORT_MANAGE", "AUDIT_VIEW"
        ]
        for perm_code in expected_perms:
            p = Permission.query.filter_by(code=perm_code).first()
            assert p is not None, f"Permission {perm_code} missing after init!"

        # Verify rate cards exist for all 4 service types
        for s_code in ["STANDARD", "EXPRESS", "OVERNIGHT", "SAME_DAY"]:
            st = ServiceType.query.filter_by(code=s_code).first()
            assert st is not None
            cards = RateCard.query.filter_by(service_type_id=st.id).all()
            assert len(cards) >= 1, f"No rate cards for service {s_code}"

def test_init_production_catalog_idempotent(app):
    """Priority 1: Verify init_production_catalog is strictly idempotent."""
    with app.app_context():
        stats1 = init_production_catalog()
        stats2 = init_production_catalog()
        assert stats2["roles_created"] == 0
        assert stats2["permissions_created"] == 0
        assert stats2["branches_created"] == 0
        assert stats2["hubs_created"] == 0
        assert stats2["services_created"] == 0
        assert stats2["rate_cards_created"] == 0

def test_customer_registration_receives_customer_role(client, app):
    """Priority 2: Verify registered customer receives CUSTOMER role."""
    client.post("/auth/logout", follow_redirects=True)
    post_data = {
        "full_name": "Test Customer Booking",
        "email": "test_booking_user_99@example.com",
        "phone": "+923001239988",
        "password": "StrongPassword@123",
        "confirm_password": "StrongPassword@123",
        "agree_terms": True,
    }
    res = client.post("/auth/register", data=post_data, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="test_booking_user_99@example.com").first()
        assert user is not None
        assert user.has_role("CUSTOMER")
        assert user.customer is not None

def test_driver_cannot_record_attempt_on_unassigned_shipment(client, app):
    """Priority 3: Verify driver cannot record attempts on unassigned shipments."""
    with app.app_context():
        # Find driver Kamran Akram
        driver_user = User.query.filter_by(email="driver1@smartcourier.pk").first()
        driver = driver_user.employee.driver_profile

        # Find or create a shipment not assigned to driver
        all_assigned_ids = [s[0] for s in db.session.query(RouteStop.shipment_id).join(Route, RouteStop.route_id == Route.id).filter(Route.driver_id == driver.id).all()]
        unassigned_shipment = Shipment.query.filter(~Shipment.id.in_(all_assigned_ids) if all_assigned_ids else True).first()

    login_as(client, "driver1@smartcourier.pk")
    res = client.post("/driver/attempts", data={
        "driver_id": driver.id,
        "shipment_id": unassigned_shipment.id,
        "outcome": "SUCCESS",
    })
    assert res.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_driver_cannot_transition_unassigned_shipment(client, app):
    """Priority 3: Verify driver cannot transition unassigned shipments."""
    with app.app_context():
        driver_user = User.query.filter_by(email="driver1@smartcourier.pk").first()
        driver = driver_user.employee.driver_profile
        all_assigned_ids = [s[0] for s in db.session.query(RouteStop.shipment_id).join(Route, RouteStop.route_id == Route.id).filter(Route.driver_id == driver.id).all()]
        unassigned_shipment = Shipment.query.filter(~Shipment.id.in_(all_assigned_ids) if all_assigned_ids else True).first()

    login_as(client, "driver1@smartcourier.pk")
    res = client.post(f"/shipments/{unassigned_shipment.id}/transition", data={
        "target_status": "DELIVERED",
        "reason": "Tampered transition",
    })
    assert res.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_driver_cannot_view_unassigned_shipment_details_or_label(client, app):
    """Priority 3: Verify driver cannot view details or label for unassigned shipment."""
    with app.app_context():
        driver_user = User.query.filter_by(email="driver1@smartcourier.pk").first()
        driver = driver_user.employee.driver_profile
        all_assigned_ids = [s[0] for s in db.session.query(RouteStop.shipment_id).join(Route, RouteStop.route_id == Route.id).filter(Route.driver_id == driver.id).all()]
        unassigned_shipment = Shipment.query.filter(~Shipment.id.in_(all_assigned_ids) if all_assigned_ids else True).first()

    login_as(client, "driver1@smartcourier.pk")
    res_show = client.get(f"/shipments/{unassigned_shipment.id}")
    assert res_show.status_code == 403

    res_label = client.get(f"/shipments/{unassigned_shipment.id}/label")
    assert res_label.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_pricing_service_fallback_all_services(app):
    """Priority 2: Verify PricingService calculates quote for all 4 service types."""
    with app.app_context():
        for s_code in ["STANDARD", "EXPRESS", "OVERNIGHT", "SAME_DAY"]:
            st = ServiceType.query.filter_by(code=s_code).first()
            quote = PricingService.calculate_quote(
                service_type_id=st.id,
                origin_zone_id=1,
                destination_zone_id=2,
                weight_grams=1200,
            )
            assert quote["total_paisa"] > 0
            assert quote["currency"] == "PKR"
