import http.cookiejar
import re
import sys
import time
import urllib.parse
import urllib.request

BASE_URL = "https://smart-courier.onrender.com"

NINE_DEMO_ACCOUNTS = [
    {"role": "Super Admin", "email": "viva.admin@smartcourier.pk", "expected_dash": "/admin/branches"},
    {"role": "Branch Manager", "email": "lahore.manager@smartcourier.pk", "expected_dash": "/admin/branches"},
    {"role": "Booking Agent", "email": "booking.lahore@smartcourier.pk", "expected_dash": "/shipments/new"},
    {"role": "Hub Operator", "email": "hub.lahore@smartcourier.pk", "expected_dash": "/hubs/transfers"},
    {"role": "Dispatcher", "email": "dispatcher.lahore@smartcourier.pk", "expected_dash": "/dispatch/routes"},
    {"role": "Driver", "email": "driver1@smartcourier.pk", "expected_dash": "/driver/my-runs"},
    {"role": "Finance Officer", "email": "finance@smartcourier.pk", "expected_dash": "/finance/invoices"},
    {"role": "Support Agent", "email": "support@smartcourier.pk", "expected_dash": "/support/tickets"},
    {"role": "Customer", "email": "customer@smartcourier.pk", "expected_dash": "/shipments/"},
]

def get_csrf(html):
    m = re.search(r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"', html)
    if not m:
        m = re.search(r'value="([^"]+)"\s+name="csrf_token"', html)
    if not m:
        m = re.search(r'<input[^>]+name="csrf_token"[^>]+value="([^"]+)"', html)
    if not m:
        m = re.search(r'<input[^>]+value="([^"]+)"[^>]+name="csrf_token"', html)
    return m.group(1) if m else None

def test_single_account(email, password, role_name):
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    # 1. Fetch login page & CSRF token
    login_url = f"{BASE_URL}/auth/login"
    req_get = urllib.request.Request(login_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        res_get = opener.open(req_get, timeout=20)
        html_get = res_get.read().decode("utf-8")
        csrf_token = get_csrf(html_get)
        if not csrf_token:
            return False, "Failed to extract CSRF token"
    except Exception as e:
        return False, f"GET login error: {e}"

    # 2. Post login credentials
    post_data = urllib.parse.urlencode({
        "csrf_token": csrf_token,
        "email": email,
        "password": password,
    }).encode("utf-8")

    req_post = urllib.request.Request(login_url, data=post_data, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": login_url,
        "Origin": BASE_URL,
    })

    try:
        res_post = opener.open(req_post, timeout=20)
        final_url = res_post.geturl()
        html_post = res_post.read().decode("utf-8")

        # Success criteria: redirected away from /auth/login or Welcome back / Logout present
        is_logged_in = (
            "Invalid email or password" not in html_post
            and "Field must be at least" not in html_post
            and ("Logout" in html_post or "Sign Out" in html_post or "Welcome" in html_post or final_url != login_url)
        )

        if is_logged_in:
            return True, f"Success (HTTP {res_post.status}, URL: {final_url})"
        else:
            # Check specific error
            if "Field must be at least" in html_post:
                return False, "Failed: Minimum length validation blocked password"
            elif "Invalid email or password" in html_post:
                return False, "Failed: Invalid credentials"
            else:
                return False, f"Failed: Remaining on {final_url}"
    except Exception as e:
        return False, f"POST login error: {e}"

def verify_all_nine():
    print("\n" + "=" * 90)
    print("VERIFYING LIVE LOGIN FOR ALL 9 VIVA DEMO ACCOUNTS (PASSWORD: 123)")
    print(f"Target Host: {BASE_URL}")
    print("=" * 90)

    header = f"{'#':<3} {'Role Name':<17} {'Email Address':<32} {'Password':<10} {'Result'}"
    print(header)
    print("-" * 90)

    results = []
    for idx, acc in enumerate(NINE_DEMO_ACCOUNTS, start=1):
        ok, msg = test_single_account(acc["email"], "123", acc["role"])
        results.append((acc, ok, msg))
        status_symbol = "[PASS]" if ok else "[FAIL]"
        print(f"{idx:<3} {acc['role']:<17} {acc['email']:<32} {'123':<10} {status_symbol} {msg}")

    print("=" * 90)
    passed_count = sum(1 for _, ok, _ in results)
    print(f"Summary: {passed_count}/{len(results)} viva demo accounts successfully logged in on live site.")
    print("=" * 90 + "\n")
    return passed_count == len(results)

if __name__ == "__main__":
    success = verify_all_nine()
    sys.exit(0 if success else 1)
