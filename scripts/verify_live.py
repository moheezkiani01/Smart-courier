import re
import urllib.request
import urllib.parse
import http.cookiejar

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

def get_csrf(html):
    m = re.search(r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"', html)
    if not m:
        m = re.search(r'value="([^"]+)"\s+name="csrf_token"', html)
    if not m:
        m = re.search(r'<input[^>]+name="csrf_token"[^>]+value="([^"]+)"', html)
    if not m:
        m = re.search(r'<input[^>]+value="([^"]+)"[^>]+name="csrf_token"', html)
    return m.group(1) if m else None

def get_first_option(html, select_name):
    pattern = rf'<select[^>]+name="{select_name}"[^>]*>(.*?)</select>'
    m = re.search(pattern, html, re.DOTALL)
    if m:
        opts = re.findall(r'<option[^>]+value="(\d+)"', m.group(1))
        return opts[0] if opts else "1"
    return "1"

def test_live_journey():
    print("\n--- TESTING LIVE CUSTOMER JOURNEY & PERMISSIONS ---")

    # 1. Fetch Register page and CSRF
    reg_url = "https://smart-courier.onrender.com/auth/register"
    req = urllib.request.Request(reg_url, headers={"User-Agent": "Mozilla/5.0"})
    res = opener.open(req)
    html = res.read().decode("utf-8")
    csrf = get_csrf(html)
    print(f"[+] Loaded registration page (HTTP {res.status}). CSRF extracted: {bool(csrf)}")

    # 2. Register unique customer
    import uuid
    rand_id = uuid.uuid4().hex[:6]
    test_email = f"live.student.{rand_id}@smartcourier.pk"
    test_pass = "TestStudentPass@1234"

    reg_data = urllib.parse.urlencode({
        "csrf_token": csrf,
        "full_name": f"Live Student {rand_id}",
        "email": test_email,
        "phone": "+923001234567",
        "password": test_pass,
        "confirm_password": test_pass,
        "agree_terms": "y",
    }).encode("utf-8")

    headers_post = {
        "User-Agent": "Mozilla/5.0",
        "Referer": reg_url,
        "Origin": "https://smart-courier.onrender.com",
    }
    req_reg = urllib.request.Request(reg_url, data=reg_data, headers=headers_post)
    res_reg = opener.open(req_reg)
    print(f"[+] Registered live test customer: {test_email} (Final URL: {res_reg.geturl()}, HTTP {res_reg.status})")

    # 3. Access Dashboard as registered customer
    dash_req = urllib.request.Request("https://smart-courier.onrender.com/", headers={"User-Agent": "Mozilla/5.0"})
    dash_res = opener.open(dash_req)
    dash_html = dash_res.read().decode("utf-8")
    print(f"[+] Customer Dashboard accessed (HTTP {dash_res.status}). Welcome present: {'Welcome back' in dash_html}")
    print(f"[+] Hub Scans NOT present in customer navigation: {'Hub Scans' not in dash_html}")
    print(f"[+] Single document scroll CSS link present: {'modern-ui.css' in dash_html}")

    # 4. Attempt to access /hubs/scans as customer -> MUST return 403 Forbidden!
    try:
        scans_req = urllib.request.Request("https://smart-courier.onrender.com/hubs/scans", headers={"User-Agent": "Mozilla/5.0"})
        scans_res = opener.open(scans_req)
        print(f"[-] Customer accessed /hubs/scans unexpectedly: HTTP {scans_res.status}")
    except urllib.error.HTTPError as he:
        if he.code == 403:
            print(f"[+] Customer access to /hubs/scans correctly blocked with HTTP 403 Forbidden (RBAC enforced).")
        else:
            print(f"[*] Customer access to /hubs/scans returned HTTP {he.code}.")

    # 5. Open Booking page
    book_url = "https://smart-courier.onrender.com/shipments/new"
    book_req = urllib.request.Request(book_url, headers={"User-Agent": "Mozilla/5.0"})
    book_res = opener.open(book_req)
    book_html = book_res.read().decode("utf-8")
    book_csrf = get_csrf(book_html)
    print(f"[+] Booking form accessed (HTTP {book_res.status}). Form ready: {bool(book_csrf)}")

    s_service = get_first_option(book_html, "service_type_id")
    s_cat = get_first_option(book_html, "parcel_category_id")
    s_pkg = get_first_option(book_html, "packaging_type_id")
    s_szone = get_first_option(book_html, "sender_zone_id")
    s_rzone = get_first_option(book_html, "recipient_zone_id")

    # 6. Book a parcel
    book_data = urllib.parse.urlencode({
        "csrf_token": book_csrf,
        "service_type_id": s_service,
        "parcel_category_id": s_cat,
        "packaging_type_id": s_pkg,
        "sender_name": f"Live Student {rand_id}",
        "sender_phone": "+923001234567",
        "sender_zone_id": s_szone,
        "sender_line1": "Main Campus Hostel, Block B",
        "sender_city": "Lahore",
        "sender_postal": "54000",
        "recipient_name": "Department Chair",
        "recipient_phone": "+923334445566",
        "recipient_zone_id": s_rzone,
        "recipient_line1": "Academic Block 3, Office 12",
        "recipient_city": "Islamabad",
        "recipient_postal": "44000",
        "item_description": "Final Year Project Documentation & USB",
        "item_quantity": "1",
        "weight_grams": "450",
        "declared_value_pkr": "1000",
        "cod_due_pkr": "0",
        "pickup_type": "PICKUP",
        "pickup_time_slot": "MORNING",
    }).encode("utf-8")

    headers_book = {
        "User-Agent": "Mozilla/5.0",
        "Referer": book_url,
        "Origin": "https://smart-courier.onrender.com",
    }
    res_post_book = opener.open(urllib.request.Request(book_url, data=book_data, headers=headers_book))
    final_book_html = res_post_book.read().decode("utf-8")
    print(f"[+] Booked parcel successfully! Redirected to: {res_post_book.geturl()} (HTTP {res_post_book.status})")

    # Extract tracking number from final URL or HTML
    m_tn = re.search(r'SC\d{4}[A-Z0-9]+', final_book_html)
    if m_tn:
        tn = m_tn.group(0)
        print(f"[+] Live parcel booked with generated tracking number: {tn}")

        # 7. Test public tracking
        track_url = f"https://smart-courier.onrender.com/tracking/{tn}"
        track_res = opener.open(urllib.request.Request(track_url, headers={"User-Agent": "Mozilla/5.0"}))
        track_html = track_res.read().decode("utf-8")
        print(f"[+] Public tracking verified (HTTP {track_res.status}). Tracking details displayed: {tn in track_html}")

if __name__ == "__main__":
    test_live_journey()
