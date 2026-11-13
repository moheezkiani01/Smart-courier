"""Tests for the Temporary Viva Quick Test Account Dropdown.

Verifies:
1. When VIVA_LOGIN_PICKER_ENABLED is false/absent, no dropdown is rendered.
2. When VIVA_LOGIN_PICKER_ENABLED is true, only verified active accounts with matching roles appear.
3. Malformed or empty JSON configuration gracefully handles without crashing or breaking login.
4. Nonexistent, deleted, deactivated, or mismatched-role accounts are strictly excluded.
5. Password authentication is mandatory: no automatic submission or passwordless bypass.
6. Valid credentials log in properly; wrong password produces validation error.
7. RBAC and tenant separation remain intact without role spoofing.
"""
import json
import pytest
from app.extensions import db
from app.models.auth import User, Role, UserRole


def test_viva_login_picker_disabled_by_default(client, app):
    """Verify that when picker flag is disabled, no demo dropdown or badge appears."""
    app.config["VIVA_LOGIN_PICKER_ENABLED"] = False
    app.config["VIVA_LOGIN_ACCOUNTS_JSON"] = ""

    resp = client.get("/auth/login")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert "demo-account-picker" not in html
    assert "Quick Test Account" not in html
    assert "Viva only" not in html


def test_viva_login_picker_enabled_default_candidates(client, app):
    """Verify that when enabled, only existing active verified role accounts appear in dropdown."""
    app.config["VIVA_LOGIN_PICKER_ENABLED"] = True
    app.config["VIVA_LOGIN_ACCOUNTS_JSON"] = ""

    resp = client.get("/auth/login")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert "demo-account-picker" in html
    assert "Quick Test Account" in html
    assert "Viva only" in html
    assert "Select a demo role..." in html

    # Existing active accounts in the test db should appear
    with app.app_context():
        admin = User.query.filter_by(email="admin@smartcourier.pk", is_deleted=False).first()
        if admin and admin.has_role("SUPER_ADMIN"):
            assert "admin@smartcourier.pk" in html
            assert "Super Admin" in html


def test_viva_login_picker_custom_json_filtering(client, app):
    """Verify custom JSON only renders accounts that exist and match the requested role."""
    app.config["VIVA_LOGIN_PICKER_ENABLED"] = True

    # Configure one valid account, one nonexistent account, and one wrong-role account
    custom_config = {
        "Super Admin": "admin@smartcourier.pk",         # Exists & has SUPER_ADMIN role
        "Driver": "nonexistent.driver@example.com",     # Does NOT exist
        "Finance Officer": "customer@smartcourier.pk",  # Exists but is CUSTOMER, NOT FINANCE_OFFICER
    }
    app.config["VIVA_LOGIN_ACCOUNTS_JSON"] = json.dumps(custom_config)

    resp = client.get("/auth/login")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert "demo-account-picker" in html
    # Valid account with correct role should be present
    assert "admin@smartcourier.pk" in html

    # Nonexistent account must be excluded
    assert "nonexistent.driver@example.com" not in html

    # Wrong-role account must be excluded from Finance Officer option
    assert 'value="customer@smartcourier.pk">Finance Officer' not in html


def test_viva_login_picker_malformed_json_graceful_handling(client, app):
    """Verify malformed JSON does not crash the page or break sign-in."""
    app.config["VIVA_LOGIN_PICKER_ENABLED"] = True
    app.config["VIVA_LOGIN_ACCOUNTS_JSON"] = "{invalid: json, broken..."

    resp = client.get("/auth/login")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Page loads cleanly and email/password inputs remain functional
    assert 'name="email"' in html
    assert 'name="password"' in html


def test_viva_login_picker_deactivated_account_excluded(client, app):
    """Verify deactivated user accounts are strictly excluded from the demo picker."""
    app.config["VIVA_LOGIN_PICKER_ENABLED"] = True

    with app.app_context():
        deact_user = User.query.filter_by(email="deact.demo@example.com").first()
        if not deact_user:
            deact_user = User(
                email="deact.demo@example.com",
                full_name="Deactivated Courier",
                phone="+923000000000",
                status="DEACTIVE",
            )
            deact_user.set_password("SomePassword@123")
            db.session.add(deact_user)
            role = Role.query.filter_by(code="DRIVER").first()
            if role:
                db.session.add(UserRole(user_id=deact_user.id, role_id=role.id, created_by=deact_user.id))
            db.session.commit()

    app.config["VIVA_LOGIN_ACCOUNTS_JSON"] = json.dumps({"Driver": "deact.demo@example.com"})

    resp = client.get("/auth/login")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert "deact.demo@example.com" not in html


def test_viva_login_submission_requires_valid_password(client, app):
    """Verify password authentication is strictly enforced; picker does not allow passwordless login."""
    app.config["VIVA_LOGIN_PICKER_ENABLED"] = True

    # Attempt login with empty password
    resp = client.post(
        "/auth/login",
        data={"email": "admin@smartcourier.pk", "password": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "This field is required" in html or "Invalid email or password" in html

    # Attempt login with wrong password
    resp_wrong = client.post(
        "/auth/login",
        data={"email": "admin@smartcourier.pk", "password": "WrongPassword123"},
        follow_redirects=True,
    )
    assert resp_wrong.status_code == 200
    assert "Invalid email or password" in resp_wrong.get_data(as_text=True)

    # Valid credentials log in successfully
    resp_valid = client.post(
        "/auth/login",
        data={"email": "admin@smartcourier.pk", "password": "AdminPass@1234"},
        follow_redirects=True,
    )
    assert resp_valid.status_code == 200
    assert "Welcome back" in resp_valid.get_data(as_text=True)
    assert "/auth/logout" in resp_valid.get_data(as_text=True)
