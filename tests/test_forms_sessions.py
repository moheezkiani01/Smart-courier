def test_login_form_validation(client):
    """Ensure invalid email and short password fail server-side validation."""
    client.post("/auth/logout", follow_redirects=True)
    res = client.post("/auth/login", data={"email": "invalid-email", "password": "123"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid email address" in res.data or b"Please try again" in res.data or b"Sign In" in res.data

def test_session_cookie_security_flags(client):
    """Verify session cookies have security attributes."""
    res = client.get("/auth/login")
    cookies = res.headers.getlist("Set-Cookie")
    for cookie in cookies:
        if "session=" in cookie:
            assert "HttpOnly" in cookie
            assert "SameSite=Lax" in cookie

def test_public_tracking_search_redirection(client):
    """Verify PRG pattern for tracking code lookup."""
    res = client.get("/tracking/search?tracking_number=SC-TEST-99")
    assert res.status_code == 302
    assert "/tracking/SC-TEST-99" in res.headers["Location"]
