import pytest
from app.models.auth import User

def login_as(client, email, password="AdminPass@1234"):
    client.post("/auth/logout", follow_redirects=True)
    res = client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)
    assert res.status_code == 200
    return res

def test_all_nine_roles_dashboard_access(client):
    """Verify each of the 9 roles can successfully log in and access their primary module."""
    role_check_map = [
        ("admin@smartcourier.pk", "/admin/branches", 200, b"Branch Management"),
        ("lahore.manager@smartcourier.pk", "/admin/branches", 200, b"Branch Management"),
        ("booking.lahore@smartcourier.pk", "/shipments/new", 200, b"Book New Shipment"),
        ("hub.lahore@smartcourier.pk", "/hubs/scans", 200, b"Hub Sorting &amp; Scans" if False else b"Hub Sorting"),
        ("dispatcher.lahore@smartcourier.pk", "/dispatch/routes", 200, b"Delivery Routes"),
        ("driver1@smartcourier.pk", "/driver/my-runs", 200, b"Driver Runsheet Workspace"),
        ("finance@smartcourier.pk", "/finance/invoices", 200, b"Invoices &amp; Receivables" if False else b"Invoices"),
        ("support@smartcourier.pk", "/support/tickets", 200, b"Support Tickets"),
        ("customer@smartcourier.pk", "/shipments/", 200, b"Shipment Consignments"),
    ]

    for email, target_url, expected_code, expected_content in role_check_map:
        login_as(client, email)
        res = client.get(target_url)
        assert res.status_code == expected_code, f"Failed for {email} accessing {target_url}: got {res.status_code}"
        assert expected_content in res.data, f"Content {expected_content} not found in {target_url} for {email}"

def test_strict_role_boundary_enforcement(client):
    """Verify non-authorized roles are blocked with 403 Forbidden on restricted modules."""
    # Customer cannot access dispatch routes or admin
    login_as(client, "customer@smartcourier.pk")
    res = client.get("/dispatch/routes")
    assert res.status_code == 403

    res = client.get("/admin/users")
    assert res.status_code == 403

    # Driver cannot access finance invoices or admin hubs
    login_as(client, "driver1@smartcourier.pk")
    res = client.get("/finance/invoices")
    assert res.status_code == 403

    res = client.get("/admin/hubs")
    assert res.status_code == 403

    # Booking agent cannot access audit logs
    login_as(client, "booking.lahore@smartcourier.pk")
    res = client.get("/admin/audit-logs")
    assert res.status_code == 403

def test_operational_dashboard_render(client):
    """Verify the main operational dashboard renders KPI metrics and shipment tables."""
    login_as(client, "admin@smartcourier.pk")
    res = client.get("/")
    assert res.status_code == 200
    assert b"Operational Overview" in res.data
    assert b"Total Bookings" in res.data
    assert b"In Transit" in res.data

def test_catalog_rate_calculator_route(client):
    """Verify rate calculator view loads correctly."""
    login_as(client, "booking.lahore@smartcourier.pk")
    res = client.get("/catalog/calculator")
    assert res.status_code == 200
    assert b"Shipping Rate Calculator" in res.data
    client.post("/auth/logout", follow_redirects=True)
