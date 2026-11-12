import pytest
from app.models.auth import User

def login_as(client, email, password="AdminPass@1234"):
    client.post("/auth/logout", follow_redirects=True)
    res = client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)
    assert res.status_code == 200
    return res

def test_modern_login_page_renders_split_layout(client):
    """Verify modern login page renders with split hero and form layout."""
    client.post("/auth/logout", follow_redirects=True)
    res = client.get("/auth/login")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "sc-login-wrap" in html
    assert "sc-login-layout" in html
    assert "sc-login-hero" in html
    assert "Smarter delivery" in html
    assert "Welcome back" in html
    assert "name=\"email\"" in html or "id=\"email\"" in html
    assert "name=\"password\"" in html or "id=\"password\"" in html
    assert "modern-ui.css" in html

def test_customer_dashboard_renders_modern_charts(client):
    """Verify customer dashboard renders weekly bar chart, donut status chart, and quick actions."""
    login_as(client, "customer@smartcourier.pk")
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "sc-dashboard" in html
    assert "My Parcel Dashboard" in html
    assert "sc-week-chart" in html
    assert "sc-donut" in html
    assert "Outstanding Balance Due" in html
    assert "My Support Tickets" in html
    assert "Book a Parcel" in html
    client.post("/auth/logout", follow_redirects=True)

def test_admin_dashboard_renders_operational_charts(client):
    """Verify admin dashboard renders operational overview with all stat cards and activity."""
    login_as(client, "admin@smartcourier.pk")
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Operational Overview" in html
    assert "Total Bookings" in html
    assert "In Transit" in html
    assert "Delivered" in html
    assert "Delivery Failed" in html
    assert "sc-week-chart" in html
    assert "sc-donut" in html
    assert "Paid Invoice Revenue" in html
    client.post("/auth/logout", follow_redirects=True)
