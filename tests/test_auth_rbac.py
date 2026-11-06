from app.models.auth import User

def test_password_hashing(app):
    """Verify passwords are secure hashed and not stored in plaintext."""
    with app.app_context():
        user = User.query.filter_by(email="admin@smartcourier.pk").first()
        assert user is not None
        assert user.password_hash != "AdminPass@1234"
        assert user.check_password("AdminPass@1234") is True
        assert user.check_password("WrongPassword") is False

def test_unauthenticated_access_redirects(client):
    """Ensure protected routes redirect anonymous visitors to login."""
    client.post("/auth/logout", follow_redirects=True)
    res = client.get("/admin/branches")
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]

def test_admin_has_full_access(authenticated_admin):
    """Verify Super Admin can access admin modules."""
    res = authenticated_admin.get("/admin/branches")
    assert res.status_code == 200
    assert b"Branch Management" in res.data

def test_customer_denied_admin_access(authenticated_customer):
    """Verify customer role cannot access staff administrative routes."""
    res = authenticated_customer.get("/admin/branches")
    assert res.status_code == 403

def test_driver_workspace_access(authenticated_driver):
    """Verify driver can access driver runsheet workspace."""
    res = authenticated_driver.get("/driver/my-runs")
    assert res.status_code == 200
    assert b"Driver Runsheet Workspace" in res.data
