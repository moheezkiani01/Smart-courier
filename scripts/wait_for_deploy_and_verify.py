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

def test_login_attempt(email, password):
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    login_url = f"{BASE_URL}/auth/login"

    try:
        req_get = urllib.request.Request(login_url, headers={"User-Agent": "Mozilla/5.0"})
        res_get = opener.open(req_get, timeout=15)
        html_get = res_get.read().decode("utf-8")
        csrf_token = get_csrf(html_get)
        if not csrf_token:
            return False, "NO_CSRF", html_get
    except Exception as e:
        return False, f"GET_ERROR: {e}", ""

    post_data = urllib.parse.urlencode({
        "csrf_token": csrf_token,
        "email": email,
        "password": password,
    }).encode("utf-8")

    req_post = urllib.request.Request(login_url, data=post_data, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": login_url,
        "Origin": BASE_URL,
    })

    try:
        res_post = opener.open(req_post, timeout=15)
        final_url = res_post.geturl()
        html_post = res_post.read().decode("utf-8")

        if "Field must be at least" in html_post:
            return False, "MIN_LENGTH_BLOCKED", html_post
        if "Invalid email or password" in html_post:
            return False, "INVALID_CREDENTIALS", html_post
        if "Logout" in html_post or "Sign Out" in html_post or "Welcome" in html_post or final_url != login_url:
            return True, f"SUCCESS (URL: {final_url})", html_post

        return False, f"UNKNOWN (URL: {final_url})", html_post
    except Exception as e:
        return False, f"POST_ERROR: {e}", ""

def wait_for_new_deploy(max_wait_seconds=300):
    print(f"[*] Waiting for Render to build and deploy latest commit (timeout: {max_wait_seconds}s)...")
    start = time.time()
    attempt = 1
    while time.time() - start < max_wait_seconds:
        elapsed = int(time.time() - start)
        ok, reason, _ = test_login_attempt("viva.admin@smartcourier.pk", "123")
        if ok:
            print(f"\n[+] New deployment is ACTIVE and accepting 3-character password! (Detected in {elapsed}s)")
            return True
        elif reason == "MIN_LENGTH_BLOCKED":
            print(f"[{elapsed:3d}s] Attempt #{attempt}: Render still serving previous version (min length 6 active). Waiting 10s...", flush=True)
        else:
            print(f"[{elapsed:3d}s] Attempt #{attempt}: Status: {reason}. Waiting 10s...", flush=True)

        attempt += 1
        time.sleep(10)

    print("\n[-] Timed out waiting for deployment.")
    return False

def verify_all_nine():
    print("\n" + "=" * 95)
    print("SMART COURIER — LIVE PRODUCTION VIVA DEMO ACCOUNTS VERIFICATION")
    print(f"Target URL: {BASE_URL}")
    print("=" * 95)
    header = f"{'#':<3} {'Role Name':<17} {'Email Address':<32} {'Password':<10} {'Result':<10} {'Details'}"
    print(header)
    print("-" * 95)

    all_passed = True
    for idx, acc in enumerate(NINE_DEMO_ACCOUNTS, start=1):
        ok, reason, html = test_login_attempt(acc["email"], "123")
        status_tag = "[PASS]" if ok else "[FAIL]"
        if not ok:
            all_passed = False
        print(f"{idx:<3} {acc['role']:<17} {acc['email']:<32} {'123':<10} {status_tag:<10} {reason}")

    print("=" * 95)

    # Security boundary verification: non-viva accounts MUST NOT be allowed with 3-char password
    print("\n[*] Verifying Security Boundaries (RBAC & Length Policy Protection)...")
    admin_ok, admin_reason, _ = test_login_attempt("admin@smartcourier.pk", "123")
    print(f"    - Original Admin ('admin@smartcourier.pk') with 3-char password: {admin_reason} (BLOCKED as expected: {not admin_ok})")

    cust_ok, cust_reason, _ = test_login_attempt("regular.user@example.com", "123")
    print(f"    - Regular Customer ('regular.user@example.com') with 3-char password: {cust_reason} (BLOCKED as expected: {not cust_ok})")

    if not admin_ok and not cust_ok and all_passed:
        print("\n[+] ALL 9 VIVA DEMO ACCOUNTS AND SECURITY BOUNDARIES VERIFIED SUCCESSFULLY ON LIVE WEBSITE!\n")
        return True
    else:
        print("\n[-] Verification failed or security checks did not meet expectations.\n")
        return False

if __name__ == "__main__":
    ready = wait_for_new_deploy(max_wait_seconds=300)
    if not ready:
        sys.exit(1)

    success = verify_all_nine()
    sys.exit(0 if success else 1)
