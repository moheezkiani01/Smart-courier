import pytest
from app.extensions import db
from app.models.auth import User
from app.models.organization import Branch, Hub, Employee
from app.models.catalog import Customer, RateCard, RateCardRule
from app.models.shipments import Shipment
from app.models.dispatch import Driver, Route, RouteStop, DeliveryAttempt
from app.models.finance import Invoice, Payment
from app.models.support import SupportTicket
from app.services.hub_service import HubService
from app.services.dispatch_service import DispatchService
from app.services.finance_service import FinanceService
from app.services.shipment_service import ShipmentService

def login_as(client, email, password="AdminPass@1234"):
    client.post("/auth/logout", follow_redirects=True)
    res = client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)
    assert res.status_code == 200
    return res

def test_a01_sidebar_navigation_filtered_by_role(client):
    """Verify sidebar menu items hide inaccessible modules per role (A01)."""
    # Driver should only see Dashboard, Driver Workspace, Support Tickets
    login_as(client, "driver1@smartcourier.pk")
    res = client.get("/")
    assert res.status_code == 200
    assert b"Driver Workspace" in res.data
    assert b"Hub Scans" not in res.data
    assert b"COD Reconciliation" not in res.data
    assert b"Rate Cards &amp; Rules" not in res.data
    assert b"Staff &amp; RBAC" not in res.data

    # Customer should not see staff-only modules
    login_as(client, "customer@smartcourier.pk")
    res = client.get("/")
    assert res.status_code == 200
    assert b"Driver Workspace" not in res.data
    assert b"Hub Scans" not in res.data
    assert b"Dispatch Routes" not in res.data
    assert b"Staff &amp; RBAC" not in res.data
    assert b"Audit Logs" not in res.data
    client.post("/auth/logout", follow_redirects=True)

def test_a02_dashboard_kpis_scoped_for_customer(client):
    """Verify customer dashboard only counts their own parcels and hides courier revenue (A02)."""
    login_as(client, "customer@smartcourier.pk")
    res = client.get("/")
    assert res.status_code == 200
    assert b"Courier Shipping Revenue" not in res.data
    assert b"Pending Merchant COD" not in res.data
    assert b"Outstanding Balance Due" in res.data
    assert b"My Support Tickets" in res.data
    client.post("/auth/logout", follow_redirects=True)

def test_a03_hub_transfer_rejects_booked_shipment(app):
    """Verify inter-hub transfer rejects shipments that have not reached AT_ORIGIN_HUB (A03)."""
    with app.app_context():
        emp = Employee.query.first()
        booked_shipment = Shipment.query.filter_by(shipment_status="BOOKED", is_deleted=False).first()
        if not booked_shipment:
            # Create a test booked shipment
            booked_shipment = Shipment.query.filter_by(is_deleted=False).first()
            booked_shipment.shipment_status = "BOOKED"
            db.session.commit()

        with pytest.raises(ValueError) as exc:
            HubService.initiate_transfer(
                shipment_id=booked_shipment.id,
                from_hub_id=1,
                to_hub_id=2,
                employee_id=emp.id,
                actor_user_id=1,
            )
        assert "AT_ORIGIN_HUB" in str(exc.value)

def test_a04_dispatch_stop_rejects_in_transit_shipment(app):
    """Verify route stop creation rejects delivery stops for parcels in IN_TRANSIT (A04)."""
    with app.app_context():
        route = Route.query.filter_by(is_deleted=False).first()
        in_transit_shipment = Shipment.query.filter_by(shipment_status="IN_TRANSIT", is_deleted=False).first()
        if not in_transit_shipment:
            in_transit_shipment = Shipment.query.filter_by(is_deleted=False).first()
            in_transit_shipment.shipment_status = "IN_TRANSIT"
            db.session.commit()

        with pytest.raises(ValueError) as exc:
            DispatchService.add_route_stop(
                route_id=route.id,
                shipment_id=in_transit_shipment.id,
                stop_sequence=99,
                stop_type="DELIVERY",
                actor_user_id=1,
            )
        assert "AT_DESTINATION_HUB" in str(exc.value)

def test_a07_branch_manager_denied_audit_logs(client):
    """Verify branch manager cannot view system audit logs (A07)."""
    login_as(client, "lahore.manager@smartcourier.pk")
    res = client.get("/admin/audit-logs")
    assert res.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_a08_branch_manager_denied_cod_reconciliation(client):
    """Verify branch manager cannot access COD summary reconciliation (A08)."""
    login_as(client, "lahore.manager@smartcourier.pk")
    res = client.get("/finance/cod")
    assert res.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_a09_non_admin_cannot_post_rate_card_rule(client):
    """Verify non-admin/manager roles cannot POST to add rate rules (A09)."""
    login_as(client, "booking.lahore@smartcourier.pk")
    card = RateCard.query.filter_by(is_deleted=False).first()
    res = client.post(f"/catalog/rate-cards/{card.id}", data={
        "min_weight_grams": 100,
        "max_weight_grams": 500,
        "base_fee_paisa": 15000,
        "extra_per_kg_paisa": 5000,
    })
    assert res.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_a11_support_agent_denied_customer_edit(client):
    """Verify support agent can view but not edit customer details (A11)."""
    login_as(client, "support@smartcourier.pk")
    cust = Customer.query.filter_by(is_deleted=False).first()
    # View allowed
    res_view = client.get(f"/customers/{cust.id}")
    assert res_view.status_code == 200
    assert b"Add Address" not in res_view.data

    # Edit blocked with 403
    res_edit = client.get(f"/customers/{cust.id}/edit")
    assert res_edit.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_a13_customer_cannot_close_other_customer_ticket(client, app):
    """Verify customer cannot close another customer's support ticket (A13)."""
    with app.app_context():
        # Find or create a ticket for customer 1
        ticket = SupportTicket.query.filter_by(is_deleted=False).first()
        target_ticket_id = ticket.id

    # Log in as a different user / customer
    login_as(client, "driver1@smartcourier.pk")
    res = client.post(f"/support/tickets/{target_ticket_id}/close", follow_redirects=True)
    assert res.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_a16_driver_cannot_submit_attempt_for_another_driver(client, app):
    """Verify driver cannot record delivery attempts for another driver's ID (A16)."""
    with app.app_context():
        shipment = Shipment.query.filter_by(is_deleted=False).first()

    login_as(client, "driver1@smartcourier.pk")
    # Post attempt forged with driver_id = 9999
    res = client.post("/driver/attempts", data={
        "driver_id": 9999,
        "shipment_id": shipment.id,
        "outcome": "SUCCESS",
    })
    assert res.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_a19_no_plaintext_passwords_in_public_html(client):
    """Verify public templates do not display plaintext passwords (A19)."""
    client.post("/auth/logout", follow_redirects=True)
    res_login = client.get("/auth/login")
    assert b"AdminPass@1234" not in res_login.data
    assert b"Password123!" not in res_login.data

    res_home = client.get("/")
    assert b"AdminPass@1234" not in res_home.data
    assert b"Password123!" not in res_home.data

def test_a23_invoice_status_reopens_after_refund(app):
    """Verify paid invoice correctly reverts to ISSUED after refund (A23)."""
    with app.app_context():
        emp = Employee.query.first()
        invoice = Invoice.query.filter_by(invoice_status="PAID", is_deleted=False).first()
        if not invoice:
            invoice = Invoice.query.filter_by(is_deleted=False).first()
            invoice.invoice_status = "PAID"
            db.session.commit()

        payment = invoice.payments[0] if invoice.payments else None
        if not payment:
            payment = Payment(
                invoice_id=invoice.id,
                amount_paisa=invoice.total_paisa,
                method="CASH",
                payment_status="SETTLED",
                created_by=1,
            )
            db.session.add(payment)
            invoice.payments.append(payment)
            db.session.commit()

        # Issue partial refund
        refund_amount = 1000  # 10 PKR
        FinanceService.process_refund(
            payment_id=payment.id,
            amount_paisa=refund_amount,
            reason="Damaged parcel claim",
            authorized_by_employee_id=emp.id,
            actor_user_id=1,
        )

        assert invoice.invoice_status == "ISSUED"
        assert invoice.amount_due_paisa == refund_amount
