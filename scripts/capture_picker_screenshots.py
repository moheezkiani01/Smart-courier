"""Capture verification screenshots of the login page with and without the Viva Test Account dropdown."""
import os
import sys
import time
import threading
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.services.viva_demo_accounts_service import ensure_viva_demo_accounts

ARTIFACT_DIR = r"C:\Users\hp\.gemini\antigravity-cli\brain\c8908832-e205-46a9-b8bd-7ad4af036158"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def capture_for_app(app_instance, port, screenshots):
    server_thread = threading.Thread(
        target=lambda: app_instance.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()
    time.sleep(2)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    for s in screenshots:
        out_path = os.path.join(ARTIFACT_DIR, s["name"])
        data_dir = os.path.join(os.getcwd(), s["user_data"])
        cmd = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            f"--window-size={s['width']},{s['height']}",
            f"--user-data-dir={data_dir}",
            f"--screenshot={out_path}",
            s["url"],
        ]
        print(f"[*] Capturing {s['name']}...")
        try:
            subprocess.run(cmd, check=True, timeout=15)
            print(f"[+] Saved: {out_path} ({os.path.getsize(out_path)} bytes)")
        except Exception as e:
            print(f"[!] Error: {e}")

def main():
    # 1. Capture with picker OFF (default state)
    app_off = create_app("development")
    app_off.config["VIVA_LOGIN_PICKER_ENABLED"] = False

    targets_off = [
        {
            "name": "viva_login_picker_off_desktop_1366.png",
            "url": "http://127.0.0.1:5070/auth/login",
            "width": 1366,
            "height": 768,
            "user_data": "temp_chrome_p_off_desk",
        },
        {
            "name": "viva_login_picker_off_mobile_390.png",
            "url": "http://127.0.0.1:5070/auth/login",
            "width": 390,
            "height": 844,
            "user_data": "temp_chrome_p_off_mob",
        },
    ]
    capture_for_app(app_off, 5070, targets_off)

    # 2. Capture with picker ON (viva demonstration state)
    app_on = create_app("development")
    app_on.config["VIVA_LOGIN_PICKER_ENABLED"] = True

    with app_on.app_context():
        ensure_viva_demo_accounts(password="AdminPass@1234")

    targets_on = [
        {
            "name": "viva_login_picker_on_desktop_1366.png",
            "url": "http://127.0.0.1:5071/auth/login",
            "width": 1366,
            "height": 850,
            "user_data": "temp_chrome_p_on_desk",
        },
        {
            "name": "viva_login_picker_on_mobile_390.png",
            "url": "http://127.0.0.1:5071/auth/login",
            "width": 390,
            "height": 844,
            "user_data": "temp_chrome_p_on_mob",
        },
    ]
    capture_for_app(app_on, 5071, targets_on)

if __name__ == "__main__":
    main()
