import pytest
from flask import url_for
from app.models.auth import User
from app.models.support import AppSetting
from app.services.showcase_service import seed_showcase, get_showcase_entries, SCENARIOS

def login_as(client, email, password="AdminPass@1234"):
    client.post("/auth/logout", follow_redirects=True)
    res = client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)
    assert res.status_code == 200
    return res

def test_guest_root_redirects_to_login(client):
    """Guest visiting '/' must be redirected directly to '/auth/login' (HTTP 302 -> 200)."""
    client.post("/auth/logout", follow_redirects=True)
    res = client.get("/", follow_redirects=False)
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]

    # Following redirect renders login page without loop
    follow_res = client.get(res.headers["Location"])
    assert follow_res.status_code == 200
    assert "sc-login-wrap" in follow_res.data.decode("utf-8")

def test_authenticated_user_accesses_dashboard_without_redirect_loop(client):
    """Authenticated user visiting '/' renders dashboard directly."""
    login_as(client, "admin@smartcourier.pk")
    res = client.get("/", follow_redirects=False)
    assert res.status_code == 200
    assert "Operational Overview" in res.data.decode("utf-8")
    client.post("/auth/logout", follow_redirects=True)

def test_logout_redirects_to_login_with_flash(client):
    """POST /auth/logout must redirect directly to /auth/login with flash message."""
    login_as(client, "customer@smartcourier.pk")

    # Logout via POST
    res = client.post("/auth/logout", follow_redirects=False)
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]

    # Flash message present on login page
    login_page = client.get(res.headers["Location"])
    assert login_page.status_code == 200
    html = login_page.data.decode("utf-8")
    assert "signed out successfully" in html
    assert "sc-login-wrap" in html

def test_cache_control_headers_on_private_pages(client):
    """Authenticated responses must set Cache-Control: no-cache, no-store."""
    login_as(client, "customer@smartcourier.pk")
    res = client.get("/")
    assert res.status_code == 200
    cc = res.headers.get("Cache-Control", "")
    assert "no-store" in cc
    assert "no-cache" in cc
    client.post("/auth/logout", follow_redirects=True)

def test_showcase_seeder_idempotency_and_dry_run(client, app):
    """Showcase seeder must support dry-run and maintain idempotency across multiple executions."""
    with app.app_context():
        # 1. Test dry-run
        res_dry, count_dry = seed_showcase(dry_run=True)
        assert res_dry["status"] == "dry_run"
        assert count_dry == 0
        assert len(res_dry["entries"]) == 5

        # 2. Test actual seed
        res_seed, count_seed = seed_showcase(dry_run=False)
        assert res_seed["status"] in ("success", "already_seeded")
        assert len(res_seed["entries"]) == 5

        # 3. Test idempotency (rerun should not create duplicates)
        res_rerun, count_rerun = seed_showcase(dry_run=False)
        assert res_rerun["status"] == "already_seeded"
        assert count_rerun == 0
        assert len(res_rerun["entries"]) == 5

        # 4. Verify each of the 5 statuses is represented
        statuses = {e["status"] for e in res_rerun["entries"]}
        expected_statuses = {"BOOKED", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED", "DELIVERY_FAILED"}
        assert expected_statuses == statuses

def test_showcase_entries_render_on_demo_customer_dashboard(client, app):
    """Showcase demo customer sees the dedicated academic showcase panel."""
    with app.app_context():
        seed_showcase(dry_run=False)
        user = User.query.filter_by(email="demo.merchant@smartcourier.pk").first()
        assert user is not None
        user.set_password("DemoShowcasePass@123")
        from app.extensions import db
        db.session.commit()

    login_as(client, "demo.merchant@smartcourier.pk", "DemoShowcasePass@123")
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Academic Showcase Test Entries" in html
    assert "DEMO-DOC-01" in html
    assert "DEMO-GLASS-05" in html
    client.post("/auth/logout", follow_redirects=True)
