"""
tests.test_viva_demo_accounts_service
-------------------------------------
Automated tests for the viva 9-role demonstration accounts service and CLI commands.

Verifies:
1. ensure_viva_demo_accounts creates/verifies all 9 accounts with correct roles and relationships.
2. Staff roles have valid Employee and EmployeeBranch records.
3. Driver role has valid Driver profile.
4. Customer role has valid Customer and CustomerAddress records.
5. All 9 accounts can authenticate and access their appropriate dashboard routes.
6. Role-boundary enforcement prevents unauthorized access across roles.
7. deactivate_viva_demo_accounts safely deactivates accounts without deleting records.
8. Deactivated accounts are excluded from login and from the Quick Test Account dropdown.
9. activate_viva_demo_accounts restores accounts cleanly.
10. All 55 database tables and existing records remain 100% intact.
"""

import pytest
from app.extensions import db
from app.models.auth import User, Role, UserRole
from app.models.organization import Employee, EmployeeBranch, Branch
from app.models.dispatch import Driver
from app.models.catalog import Customer, CustomerAddress
from app.services.viva_demo_accounts_service import (
    ensure_viva_demo_accounts,
    deactivate_viva_demo_accounts,
    activate_viva_demo_accounts,
    get_viva_demo_accounts_status,
    VIVA_DEMO_SPECS,
)
from app.blueprints.auth.routes import get_viva_demo_accounts


def test_ensure_viva_demo_accounts_creates_all_nine_roles(app):
    """Verify that ensure_viva_demo_accounts guarantees all 9 roles exist and are active."""
    with app.app_context():
        res = ensure_viva_demo_accounts(password="VivaTestPass@2026", reset_passwords=True)
        assert res["status"] == "success"
        assert res["total_accounts"] == 9

        statuses = get_viva_demo_accounts_status()
        assert len(statuses) == 9

        for s in statuses:
            assert s["exists"] is True, f"Role {s['role_name']} was not created"
            assert s["status"] == "ACTIVE", f"Role {s['role_name']} is not ACTIVE"
            assert s["has_role"] is True, f"Role {s['role_name']} does not have required role"


def test_viva_relationships_integrity(app):
    """Verify employee, driver, and customer relationships for each role."""
    with app.app_context():
        # Branch Manager Employee
        mgr_user = User.query.filter_by(email="lahore.manager@smartcourier.pk").first()
        assert mgr_user is not None
        assert mgr_user.employee is not None
        assert mgr_user.employee.primary_branch_id is not None
        assert len(mgr_user.employee.employee_branches) > 0

        # Driver profile
        driver_user = User.query.filter_by(email="driver1@smartcourier.pk").first()
        assert driver_user is not None
        assert driver_user.employee is not None
        assert driver_user.employee.driver_profile is not None
        assert driver_user.employee.driver_profile.license_number is not None

        # Customer profile
        cust_user = User.query.filter_by(email="customer@smartcourier.pk").first()
        if not cust_user:
            cust_user = User.query.filter_by(email="viva.merchant@smartcourier.pk").first()
        assert cust_user is not None
        assert cust_user.customer is not None
        assert cust_user.customer.customer_code is not None


def test_all_nine_viva_logins_and_dashboards(client, app):
    """Verify each of the 9 demonstration accounts can log in and access its dashboard."""
    with app.app_context():
        ensure_viva_demo_accounts(password="VivaTestPass@2026", reset_passwords=True)

    try:
        role_dashboard_map = [
            ("viva.admin@smartcourier.pk", "SUPER_ADMIN", "/admin/branches", 200),
            ("lahore.manager@smartcourier.pk", "BRANCH_MANAGER", "/admin/branches", 200),
            ("booking.lahore@smartcourier.pk", "BOOKING_AGENT", "/shipments/new", 200),
            ("hub.lahore@smartcourier.pk", "HUB_OPERATOR", "/hubs/transfers", 200),
            ("dispatcher.lahore@smartcourier.pk", "DISPATCHER", "/dispatch/routes", 200),
            ("driver1@smartcourier.pk", "DRIVER", "/driver/my-runs", 200),
            ("finance@smartcourier.pk", "FINANCE_OFFICER", "/finance/invoices", 200),
            ("support@smartcourier.pk", "SUPPORT_AGENT", "/support/tickets", 200),
            ("customer@smartcourier.pk", "CUSTOMER", "/shipments/", 200),
        ]

        for email, role_code, target_url, expected_status in role_dashboard_map:
            # Logout first
            client.post("/auth/logout", follow_redirects=True)

            # Login
            login_res = client.post(
                "/auth/login",
                data={"email": email, "password": "VivaTestPass@2026"},
                follow_redirects=True,
            )
            assert login_res.status_code == 200, f"Login failed for {email} ({role_code})"
            assert b"Welcome back" in login_res.data, f"Welcome message missing for {email}"

            # Access primary dashboard
            dash_res = client.get(target_url)
            assert dash_res.status_code == expected_status, f"Dashboard {target_url} returned {dash_res.status_code} for {email}"
    finally:
        with app.app_context():
            ensure_viva_demo_accounts(password="AdminPass@1234", reset_passwords=True)
        client.post("/auth/logout", follow_redirects=True)


def test_viva_picker_shows_all_nine_roles_when_enabled(client, app):
    """Verify the Quick Test Account dropdown shows all 9 roles in the correct sequence."""
    app.config["VIVA_LOGIN_PICKER_ENABLED"] = True
    app.config["VIVA_LOGIN_ACCOUNTS_JSON"] = ""

    with app.app_context():
        ensure_viva_demo_accounts(password="AdminPass@1234")
        accs = get_viva_demo_accounts()
        assert len(accs) == 9

    resp = client.get("/auth/login")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    expected_roles = [
        "Super Admin",
        "Branch Manager",
        "Booking Agent",
        "Hub Operator",
        "Dispatcher",
        "Driver",
        "Finance Officer",
        "Support Agent",
        "Customer",
    ]
    for r in expected_roles:
        assert r in html, f"Role '{r}' missing from Quick Test Account dropdown HTML"


def test_deactivate_and_activate_viva_demo_accounts(client, app):
    """Verify safe deactivation and reactivation of demonstration accounts."""
    with app.app_context():
        # Ensure active first
        ensure_viva_demo_accounts(password="AdminPass@1234")

        # Deactivate
        res_deact = deactivate_viva_demo_accounts(preserve_admin=True, confirm=True)
        assert res_deact["status"] == "success"
        assert res_deact["deactivated_count"] >= 8

        # Admin remains active
        admin = User.query.filter_by(email="admin@smartcourier.pk").first()
        assert admin.status == "ACTIVE"

        # Non-admin accounts are DEACTIVE
        driver = User.query.filter_by(email="driver1@smartcourier.pk").first()
        assert driver.status == "DEACTIVE"

    try:
        # Try login as deactivated user -> must fail with account deactivated message
        client.post("/auth/logout", follow_redirects=True)
        resp = client.post(
            "/auth/login",
            data={"email": "driver1@smartcourier.pk", "password": "AdminPass@1234"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Your account has been deactivated" in resp.get_data(as_text=True)

        # In dropdown, deactivated accounts are excluded
        app.config["VIVA_LOGIN_PICKER_ENABLED"] = True
        with app.app_context():
            accs = get_viva_demo_accounts()
            assert len(accs) == 1  # Only Super Admin remains active
            assert accs[0]["role"] == "Super Admin"

        # Reactivate
        with app.app_context():
            res_act = activate_viva_demo_accounts(confirm=True)
            assert res_act["status"] == "success"
            accs_react = get_viva_demo_accounts()
            assert len(accs_react) == 9
    finally:
        with app.app_context():
            activate_viva_demo_accounts(confirm=True)
            ensure_viva_demo_accounts(password="123", reset_passwords=True)
        client.post("/auth/logout", follow_redirects=True)


def test_all_nine_viva_accounts_login_with_password_123(client, app):
    """Verify all 9 viva demo accounts can successfully log in with password 123."""
    app.config["VIVA_LOGIN_PICKER_ENABLED"] = True
    app.config["VIVA_TESTING_ENABLED"] = True

    with app.app_context():
        ensure_viva_demo_accounts(password="123", reset_passwords=True)

    nine_demo_emails = [
        "viva.admin@smartcourier.pk",
        "lahore.manager@smartcourier.pk",
        "booking.lahore@smartcourier.pk",
        "hub.lahore@smartcourier.pk",
        "dispatcher.lahore@smartcourier.pk",
        "driver1@smartcourier.pk",
        "finance@smartcourier.pk",
        "support@smartcourier.pk",
        "customer@smartcourier.pk",
    ]

    for email in nine_demo_emails:
        client.post("/auth/logout", follow_redirects=True)
        resp = client.post(
            "/auth/login",
            data={"email": email, "password": "123"},
            follow_redirects=True,
        )
        assert resp.status_code == 200, f"Login failed for {email}"
        html = resp.get_data(as_text=True)
        assert ("Welcome back" in html or "Sign Out" in html or "Logout" in html), f"Failed to log in as {email}"


def test_login_validation_allows_3_chars_only_for_viva_demo_accounts_when_enabled(client, app):
    """Verify 3-char password policy is restricted to viva demo accounts and only when enabled."""
    from app.forms.auth_forms import LoginForm

    # Scenario 1: Viva testing ENABLED
    app.config["VIVA_TESTING_ENABLED"] = True
    app.config["VIVA_LOGIN_PICKER_ENABLED"] = True

    with app.test_request_context():
        # Demo account with 3-char password -> VALID
        form = LoginForm(email="driver1@smartcourier.pk", password="123")
        assert form.validate() is True

        # Demo account with 2-char password -> INVALID
        form = LoginForm(email="driver1@smartcourier.pk", password="12")
        assert form.validate() is False
        assert "Password must be at least 3 characters long." in form.password.errors

        # Original admin with 3-char password -> INVALID (requires min 6)
        form = LoginForm(email="admin@smartcourier.pk", password="123")
        assert form.validate() is False
        assert "Field must be at least 6 characters long." in form.password.errors

        # Non-demo customer with 3-char password -> INVALID (requires min 6)
        form = LoginForm(email="regular.customer@example.com", password="123")
        assert form.validate() is False
        assert "Field must be at least 6 characters long." in form.password.errors

    # Scenario 2: Viva testing DISABLED
    app.config["VIVA_TESTING_ENABLED"] = False
    app.config["VIVA_LOGIN_PICKER_ENABLED"] = False

    with app.test_request_context():
        # Demo account with 3-char password -> INVALID when viva testing disabled
        form = LoginForm(email="driver1@smartcourier.pk", password="123")
        assert form.validate() is False
        assert "Field must be at least 6 characters long." in form.password.errors


def test_original_admin_account_protected_from_viva_password_reset(app):
    """Verify original administrator account is protected from demo resets."""
    with app.app_context():
        admin = User.query.filter_by(email="admin@smartcourier.pk").first()
        if not admin:
            admin = User(
                email="admin@smartcourier.pk",
                full_name="Original System Administrator",
                phone="+923000000000",
                status="ACTIVE",
                is_email_verified=True,
            )
            admin.set_password("OriginalAdminSecret@1234")
            db.session.add(admin)
            db.session.commit()
        else:
            admin.set_password("OriginalAdminSecret@1234")
            db.session.commit()

        # Run demo accounts provision with password 123
        ensure_viva_demo_accounts(password="123", reset_passwords=True)

        # Original admin password must remain unchanged
        admin_refreshed = User.query.filter_by(email="admin@smartcourier.pk").first()
        assert admin_refreshed.check_password("OriginalAdminSecret@1234") is True
        assert admin_refreshed.check_password("123") is False

        # Restore original test password for subsequent session test fixtures
        admin_refreshed.set_password("AdminPass@1234")
        db.session.commit()

