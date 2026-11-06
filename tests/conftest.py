import os
import pytest
from app import create_app
from app.extensions import db
from app.services.seed_service import seed_all
from app.models.auth import User

@pytest.fixture(scope="session")
def app():
    """Create and configure a testing Flask app instance."""
    os.environ["FLASK_ENV"] = "testing"
    test_app = create_app("testing")

    with test_app.app_context():
        db.create_all()
        seed_all()
        yield test_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Test client for HTTP requests with isolated cookies."""
    c = app.test_client()
    if hasattr(c, "cookie_jar") and c.cookie_jar:
        c.cookie_jar.clear()
    yield c
    if hasattr(c, "cookie_jar") and c.cookie_jar:
        c.cookie_jar.clear()

@pytest.fixture
def runner(app):
    """CLI test runner."""
    return app.test_cli_runner()

@pytest.fixture
def admin_user(app):
    with app.app_context():
        return User.query.filter_by(email="admin@smartcourier.pk").first()

@pytest.fixture
def driver_user(app):
    with app.app_context():
        return User.query.filter_by(email="driver1@smartcourier.pk").first()

@pytest.fixture
def customer_user(app):
    with app.app_context():
        return User.query.filter_by(email="customer@smartcourier.pk").first()

@pytest.fixture
def authenticated_admin(client, admin_user):
    client.post("/auth/logout", follow_redirects=True)
    client.post("/auth/login", data={"email": admin_user.email, "password": "AdminPass@1234"}, follow_redirects=True)
    return client

@pytest.fixture
def authenticated_driver(client, driver_user):
    client.post("/auth/logout", follow_redirects=True)
    client.post("/auth/login", data={"email": driver_user.email, "password": "AdminPass@1234"}, follow_redirects=True)
    return client

@pytest.fixture
def authenticated_customer(client, customer_user):
    client.post("/auth/logout", follow_redirects=True)
    client.post("/auth/login", data={"email": customer_user.email, "password": "AdminPass@1234"}, follow_redirects=True)
    return client
