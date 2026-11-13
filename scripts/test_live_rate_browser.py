import sys
import os
import time
import subprocess
from playwright.sync_api import sync_playwright

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ARTIFACT_DIR = r"C:\Users\hp\.gemini\antigravity-cli\brain\c8908832-e205-46a9-b8bd-7ad4af036158"

def main():
    print("[*] Starting local Flask test server on port 5055...")
    env = os.environ.copy()
    env["FLASK_APP"] = "run.py"
    env["VIVA_LOGIN_PICKER_ENABLED"] = "true"
    
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "flask", "run", "--port", "5055", "--no-reload"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    time.sleep(3)

    try:
        with sync_playwright() as p:
            print("[*] Launching system Chrome browser...")
            browser = p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1366,768"]
            )
            context = browser.new_context(viewport={"width": 1366, "height": 768})
            page = context.new_page()

            # 1. Login as Admin
            print("[*] Navigating to login page...")
            page.goto("http://127.0.0.1:5055/auth/login")
            page.fill("input[name='email']", "admin@smartcourier.pk")
            page.fill("input[name='password']", "AdminPass@1234")
            page.click("input[type='submit']")
            page.wait_for_load_state("networkidle")
            print(f"[+] Logged in. Current URL: {page.url}")

            # 2. Navigate to New Shipment Booking
            print("[*] Navigating to /shipments/new...")
            page.goto("http://127.0.0.1:5055/shipments/new")
            page.wait_for_load_state("networkidle")

            # 3. Test Case A: Empty Coupon Calculation (Lahore -> Karachi, 500g)
            print("[*] Testing Empty Coupon (Lahore to Karachi, 500g)...")
            page.select_option("#senderZoneSelect", value="1")       # Lahore Metro
            page.select_option("#recipientZoneSelect", value="2")    # Karachi Central
            page.select_option("#serviceTypeSelect", value="1")      # Standard Surface
            page.fill("#weightGramsInput", "500")
            page.fill("#discountCodeInput", "")

            # Click Calculate Live Rate button
            page.click("#btnUpdateQuote")
            time.sleep(1)

            base_txt = page.text_content("#quoteBaseFee").strip()
            pkg_txt = page.text_content("#quotePkgFee").strip()
            disc_txt = page.text_content("#quoteDiscount").strip()
            total_txt = page.text_content("#quoteTotal").strip()
            print(f"    Base: {base_txt}, Pkg: {pkg_txt}, Disc: {disc_txt}, Total: {total_txt}")
            assert base_txt == "PKR 450.00", f"Expected PKR 450.00, got {base_txt}"
            assert pkg_txt == "PKR 50.00", f"Expected PKR 50.00, got {pkg_txt}"
            assert total_txt == "PKR 500.00", f"Expected PKR 500.00, got {total_txt}"
            assert disc_txt == "- PKR 0.00", f"Expected - PKR 0.00, got {disc_txt}"

            shot_empty = os.path.join(ARTIFACT_DIR, "live_rate_empty_coupon.png")
            page.screenshot(path=shot_empty, full_page=False)
            print(f"[+] Saved screenshot: {shot_empty}")

            # 4. Test Case B: Valid Coupon (EIDMUBARAK 10% discount)
            print("[*] Testing Valid Coupon (EIDMUBARAK 10% discount)...")
            page.fill("#discountCodeInput", "EIDMUBARAK")
            page.click("#btnUpdateQuote")
            time.sleep(1)

            base_txt = page.text_content("#quoteBaseFee").strip()
            pkg_txt = page.text_content("#quotePkgFee").strip()
            disc_txt = page.text_content("#quoteDiscount").strip()
            total_txt = page.text_content("#quoteTotal").strip()
            success_txt = page.text_content("#quoteSuccessText").strip()
            print(f"    Base: {base_txt}, Pkg: {pkg_txt}, Disc: {disc_txt}, Total: {total_txt}, Msg: {success_txt}")
            assert disc_txt == "- PKR 50.00", f"Expected - PKR 50.00, got {disc_txt}"
            assert total_txt == "PKR 450.00", f"Expected PKR 450.00, got {total_txt}"
            assert "applied successfully" in success_txt

            shot_valid = os.path.join(ARTIFACT_DIR, "live_rate_valid_coupon.png")
            page.screenshot(path=shot_valid, full_page=False)
            print(f"[+] Saved screenshot: {shot_valid}")

            # 5. Test Case C: Invalid Coupon
            print("[*] Testing Invalid Coupon (INVALID99)...")
            page.fill("#discountCodeInput", "INVALID99")
            page.click("#btnUpdateQuote")
            time.sleep(1)

            total_txt = page.text_content("#quoteTotal").strip()
            alert_txt = page.text_content("#quoteAlertText").strip()
            print(f"    Total: {total_txt}, Alert: {alert_txt}")
            assert total_txt == "PKR 500.00", f"Expected PKR 500.00, got {total_txt}"
            assert "Coupon 'INVALID99' is invalid" in alert_txt

            shot_invalid = os.path.join(ARTIFACT_DIR, "live_rate_invalid_coupon.png")
            page.screenshot(path=shot_invalid, full_page=False)
            print(f"[+] Saved screenshot: {shot_invalid}")

            # 6. Test Case D: Weight Tier 2kg (2000g)
            print("[*] Testing 2000g Parcel (Lahore to Karachi)...")
            page.fill("#discountCodeInput", "")
            page.fill("#weightGramsInput", "2000")
            page.click("#btnUpdateQuote")
            time.sleep(1)

            base_txt = page.text_content("#quoteBaseFee").strip()
            total_txt = page.text_content("#quoteTotal").strip()
            print(f"    Base: {base_txt}, Total for 2000g: {total_txt}")
            assert base_txt == "PKR 750.00", f"Expected PKR 750.00, got {base_txt}"
            assert total_txt == "PKR 800.00", f"Expected PKR 800.00, got {total_txt}"

            # 7. Test Case E: Intra-City (Lahore to Lahore, 500g)
            print("[*] Testing Intra-city (Lahore to Lahore, 500g)...")
            page.select_option("#recipientZoneSelect", value="1")  # Lahore
            page.fill("#weightGramsInput", "500")
            page.click("#btnUpdateQuote")
            time.sleep(1)

            base_txt = page.text_content("#quoteBaseFee").strip()
            total_txt = page.text_content("#quoteTotal").strip()
            print(f"    Base: {base_txt}, Total for Lahore-to-Lahore 500g: {total_txt}")
            assert base_txt == "PKR 250.00", f"Expected PKR 250.00, got {base_txt}"
            assert total_txt == "PKR 300.00", f"Expected PKR 300.00, got {total_txt}"

            shot_intra = os.path.join(ARTIFACT_DIR, "live_rate_lahore_intra.png")
            page.screenshot(path=shot_intra, full_page=False)
            print(f"[+] Saved screenshot: {shot_intra}")

            # 8. Test Case F: Helpful Error Validation
            print("[*] Testing Helpful Validation Message (0 weight)...")
            page.fill("#weightGramsInput", "0")
            page.click("#btnUpdateQuote")
            time.sleep(1)

            alert_txt = page.text_content("#quoteAlertText").strip()
            print(f"    Validation alert: {alert_txt}")
            assert "Parcel weight must be a positive number greater than 0 grams" in alert_txt

            shot_err = os.path.join(ARTIFACT_DIR, "live_rate_validation_error.png")
            page.screenshot(path=shot_err, full_page=False)
            print(f"[+] Saved screenshot: {shot_err}")

            browser.close()
            print("\n[+] ALL BROWSER BUTTON TESTS PASSED WITH 100% SUCCESS!")

    finally:
        server_proc.terminate()
        server_proc.wait()
        print("[*] Test server stopped.")

if __name__ == "__main__":
    main()
