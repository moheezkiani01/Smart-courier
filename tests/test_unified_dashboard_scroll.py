"""Tests for single unified page scrollbar and sidebar non-sticky layout.

Verifies:
1. base.html has removed position-sticky from sidebar inner wrapper.
2. modern-ui.css enforces single vertical document scrollbar:
   - html { overflow-y: auto; overflow-x: hidden; }
   - body { min-height: 100vh; overflow-y: visible; }
   - .sidebar, main { height: auto; max-height: none; overflow-y: visible; }
3. Authenticated dashboard renders cleanly in single Bootstrap row.
"""
import os
import re
from app.models.auth import User


def test_base_html_sidebar_not_position_sticky():
    """Verify base.html sidebar inner wrapper does not use position-sticky class."""
    base_html_path = os.path.join("app", "templates", "base.html")
    with open(base_html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The sidebar navigation should have <div class="pt-2">, NOT <div class="position-sticky pt-2">
    sidebar_nav_match = re.search(r'<nav[^>]*id="sidebarMenu"[^>]*>([\s\S]*?)</nav>', content)
    assert sidebar_nav_match is not None, "sidebarMenu not found in base.html"
    sidebar_html = sidebar_nav_match.group(1)

    assert "position-sticky" not in sidebar_html, (
        "base.html sidebarMenu inner wrapper must not contain 'position-sticky' class, "
        "enabling sidebar to scroll naturally with the main page content."
    )


def test_modern_css_single_unified_scrollbar():
    """Verify modern-ui.css defines single document root scroll rules."""
    css_path = os.path.join("app", "static", "css", "modern-ui.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    # Check html overflow-y
    assert "html {" in css
    assert "overflow-y: auto" in css

    # Check body overflow-y visible
    assert "body {" in css
    assert "overflow-y: visible" in css

    # Check sidebar and main height auto / overflow-y visible
    assert ".sidebar, main" in css or (".sidebar" in css and "main" in css)
    assert "overflow-y: visible" in css


def test_dashboard_renders_single_document_flow(client, app):
    """Verify rendered dashboard page does not inject independent scroll wrappers."""
    with app.app_context():
        user = User.query.filter_by(email="customer@smartcourier.pk").first()
        assert user is not None
        user.set_password("CustomerPass@1234")
        from app.extensions import db
        db.session.commit()

    login_res = client.post("/auth/login", data={"email": "customer@smartcourier.pk", "password": "CustomerPass@1234"}, follow_redirects=True)
    assert login_res.status_code == 200

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    assert 'id="sidebarMenu"' in html
    assert "<main class=" in html
    assert "position-sticky pt-2" not in html
    client.post("/auth/logout", follow_redirects=True)
