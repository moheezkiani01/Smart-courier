import pytest
from app.models.dispatch import ShipmentScan
from app.models.organization import Hub

def login_as(client, email, password="AdminPass@1234"):
    client.post("/auth/logout", follow_redirects=True)
    res = client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)
    assert res.status_code == 200
    return res

def test_unauthenticated_scans_redirects_to_login(client):
    """Unauthenticated access to /hubs/scans must redirect to login."""
    client.post("/auth/logout", follow_redirects=True)
    res = client.get("/hubs/scans", follow_redirects=False)
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]

def test_customer_and_driver_forbidden_on_scans(client):
    """Customer and Driver roles must receive 403 Forbidden on /hubs/scans."""
    login_as(client, "customer@smartcourier.pk")
    res = client.get("/hubs/scans")
    assert res.status_code == 403

    login_as(client, "driver1@smartcourier.pk")
    res = client.get("/hubs/scans")
    assert res.status_code == 403
    client.post("/auth/logout", follow_redirects=True)

def test_authorized_staff_gracefully_redirected_on_scans(client):
    """Authorized staff accessing retired /hubs/scans must be gracefully redirected without HTTP 500."""
    login_as(client, "hub.lahore@smartcourier.pk")
    res = client.get("/hubs/scans", follow_redirects=False)
    assert res.status_code == 302
    assert "/shipments/" in res.headers["Location"]

    # Follow redirect and verify informative flash message
    res_followed = client.get(res.headers["Location"])
    assert res_followed.status_code == 200
    assert "consolidated into parcel tracking" in res_followed.data.decode("utf-8")
    client.post("/auth/logout", follow_redirects=True)

def test_legacy_post_to_scans_safely_rejected(client):
    """Legacy POST to /hubs/scans must be redirected safely without 500 or corrupting state."""
    login_as(client, "admin@smartcourier.pk")
    res = client.post("/hubs/scans", data={"scan_code": "AT_ORIGIN_HUB"}, follow_redirects=False)
    assert res.status_code in (302, 303)
    assert "/shipments/" in res.headers["Location"]
    client.post("/auth/logout", follow_redirects=True)

def test_shipment_scan_model_and_infrastructure_preserved():
    """Verify ShipmentScan and Hub models remain intact for the 55-table architecture."""
    assert hasattr(ShipmentScan, "__tablename__")
    assert ShipmentScan.__tablename__ == "shipment_scans"
    assert hasattr(Hub, "__tablename__")
    assert Hub.__tablename__ == "hubs"
