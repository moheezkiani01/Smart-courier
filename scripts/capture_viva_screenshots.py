"""Script to capture viva verification screenshots using headless Chrome."""
import os
import sys
import time
import threading
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask_login import login_user
from flask import redirect, url_for
from app import create_app
from app.models.auth import User
from app.services.three_bookings_service import seed_three_bookings

ARTIFACT_DIR = r"C:\Users\hp\.gemini\antigravity-cli\brain\c8908832-e205-46a9-b8bd-7ad4af036158"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def run_capture():
    app = create_app("development")

    with app.app_context():
        # Ensure 3 demo bookings exist
        seed_three_bookings(dry_run=False)
        demo_user = User.query.filter_by(email="demo.merchant@smartcourier.pk").first()

    @app.route("/test-login-demo")
    def test_login_demo():
        with app.app_context():
            u = User.query.filter_by(email="demo.merchant@smartcourier.pk").first()
            login_user(u)
            return redirect(url_for("main.index"))

    # Start Flask dev server on port 5058
    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=5058, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()
    time.sleep(2)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    targets = [
        {
            "name": "viva_login_desktop_1366.png",
            "url": "http://127.0.0.1:5058/auth/login",
            "width": 1366,
            "height": 768,
            "user_data": "temp_chrome_login_desk",
        },
        {
            "name": "viva_login_mobile_390.png",
            "url": "http://127.0.0.1:5058/auth/login",
            "width": 390,
            "height": 844,
            "user_data": "temp_chrome_login_mob",
        },
        {
            "name": "viva_dashboard_desktop_1366.png",
            "url": "http://127.0.0.1:5058/test-login-demo",
            "width": 1366,
            "height": 850,
            "user_data": "temp_chrome_dash_desk",
        },
        {
            "name": "viva_dashboard_mobile_390.png",
            "url": "http://127.0.0.1:5058/test-login-demo",
            "width": 390,
            "height": 844,
            "user_data": "temp_chrome_dash_mob",
        },
    ]

    for t in targets:
        out_path = os.path.join(ARTIFACT_DIR, t["name"])
        temp_dir = os.path.join(os.environ.get("TEMP", "C:\\Temp"), t["user_data"])
        cmd = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={temp_dir}",
            f"--window-size={t['width']},{t['height']}",
            f"--screenshot={out_path}",
            t["url"],
        ]
        print(f"[*] Capturing {t['name']} ({t['width']}x{t['height']})...")
        res = subprocess.run(cmd, capture_output=True, timeout=20)
        if os.path.exists(out_path):
            print(f"[+] Saved: {out_path} ({os.path.getsize(out_path)} bytes)")
        else:
            print(f"[-] Failed to capture {t['name']}: {res.stderr.decode('utf-8', errors='ignore')}")

if __name__ == "__main__":
    run_capture()
