"""Capture verification screenshots of the 55-table viva demonstration dataset using headless Chrome."""
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
from app.models.shipments import Shipment
from app.services.three_bookings_service import get_three_bookings
from app.services.viva_full_seed_service import seed_viva_full

ARTIFACT_DIR = r"C:\Users\hp\.gemini\antigravity-cli\brain\c8908832-e205-46a9-b8bd-7ad4af036158"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def run_capture():
    app = create_app("development")

    with app.app_context():
        # Ensure full 55-table demonstration dataset is seeded
        seed_viva_full(dry_run=False)
        entries = get_three_bookings()
        by_ref = {e["ref"]: e for e in entries}
        s1_id = by_ref["SC-DEMO-BOOK-01"]["shipment_id"] if "SC-DEMO-BOOK-01" in by_ref else 1
        s1_tn = by_ref["SC-DEMO-BOOK-01"]["tracking_number"] if "SC-DEMO-BOOK-01" in by_ref else "SC26111BD34E"

    @app.route("/test-login-admin")
    def test_login_admin():
        with app.app_context():
            admin = User.query.filter_by(email="admin@smartcourier.pk").first() or User.query.first()
            login_user(admin)
            return redirect(url_for("shipments.show", shipment_id=s1_id))

    @app.route("/test-login-cod")
    def test_login_cod():
        with app.app_context():
            admin = User.query.filter_by(email="admin@smartcourier.pk").first() or User.query.first()
            login_user(admin)
            return redirect(url_for("finance.cod_summary"))

    @app.route("/test-login-transfers")
    def test_login_transfers():
        with app.app_context():
            admin = User.query.filter_by(email="admin@smartcourier.pk").first() or User.query.first()
            login_user(admin)
            return redirect(url_for("hubs.transfers"))

    # Start Flask dev server on port 5062
    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=5062, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()
    time.sleep(2)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    targets = [
        {
            "name": "viva_55_tables_shipment_detail_desktop.png",
            "url": "http://127.0.0.1:5062/test-login-admin",
            "width": 1366,
            "height": 950,
            "user_data": "temp_chrome_detail_desk",
        },
        {
            "name": "viva_55_tables_cod_summary_desktop.png",
            "url": "http://127.0.0.1:5062/test-login-cod",
            "width": 1366,
            "height": 850,
            "user_data": "temp_chrome_cod_desk",
        },
        {
            "name": "viva_55_tables_hub_transfers_desktop.png",
            "url": "http://127.0.0.1:5062/test-login-transfers",
            "width": 1366,
            "height": 850,
            "user_data": "temp_chrome_transfers_desk",
        },
        {
            "name": "viva_55_tables_public_tracking_desktop.png",
            "url": f"http://127.0.0.1:5062/tracking/{s1_tn}",
            "width": 1366,
            "height": 900,
            "user_data": "temp_chrome_tracking_desk",
        },
    ]

    for t in targets:
        out_path = os.path.join(ARTIFACT_DIR, t["name"])
        data_dir = os.path.join(os.getcwd(), t["user_data"])
        cmd = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            f"--window-size={t['width']},{t['height']}",
            f"--user-data-dir={data_dir}",
            f"--screenshot={out_path}",
            t["url"],
        ]
        print(f"[*] Capturing {t['name']}...")
        try:
            subprocess.run(cmd, check=True, timeout=15)
            print(f"[+] Saved: {out_path} ({os.path.getsize(out_path)} bytes)")
        except Exception as e:
            print(f"[!] Error capturing {t['name']}: {e}")

if __name__ == "__main__":
    run_capture()
