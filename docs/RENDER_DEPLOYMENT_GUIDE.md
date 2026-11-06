# Smart Courier — Render & PostgreSQL Production Deployment Guide

This guide provides complete, step-by-step instructions for deploying the **Smart Courier & Parcel Delivery Management System** to Render with a persistent external PostgreSQL database (Supabase Free Postgres), zero cost, and zero data loss across container restarts.

---

## 1. Architecture Overview

```text
Local Workstation (Windows):
Browser  --->  Flask Dev Server  --->  instance/courier.sqlite3 (PRAGMA foreign_keys=ON)

Production Cloud (Render Free Web Service):
Browser  --->  Render Reverse Proxy (HTTPS)  --->  Gunicorn / Flask  --->  Persistent PostgreSQL (Supabase)
                                                    ^
                                                    | (Ephemeral disk)
```

> [!IMPORTANT]
> **Ephemeral Disk Warning:** Render Free Web Services use ephemeral disks. Any file saved to the local container disk is destroyed when the service spins down, restarts, or redeploys. Therefore, **all state must be saved in persistent PostgreSQL**. SQLite must never be used in production.

---

## 2. Step 1: Provision Persistent PostgreSQL (Supabase Free)

Render's native Free PostgreSQL database expires after **30 days**. To ensure a long-term, free demonstration database, provision a **Supabase Free Postgres** instance:

1. Sign up or log in at [supabase.com](https://supabase.com/).
2. Click **New project**.
3. Choose an organization, enter a name (e.g. `smart-courier-db`), set a strong database password, and choose a region close to your Render region (e.g., Frankfurt or Singapore).
4. Wait ~2 minutes for the database to provision.
5. In the Supabase project dashboard, navigate to **Project Settings** (gear icon) -> **Database**.
6. Under **Connection string**, select **URI** (or **Session Pooler**).
7. Copy the connection string. It will look like:
   ```text
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
   ```
8. Replace `[YOUR-PASSWORD]` with the database password you chose in Step 3.
   > **Note:** The Smart Courier app automatically converts `postgres://` or `postgresql://` into `postgresql+psycopg://` at runtime.

---

## 3. Step 2: Push Code to GitHub

The complete source code is synchronized with your GitHub repository:
- **Repository:** `https://github.com/moheezkiani01/Smart-courier`
- **Branch:** `main`

Ensure your changes on `main` are pushed before proceeding to Render.

---

## 4. Step 3: Create Render Web Service

1. Log in to [render.com](https://dashboard.render.com/).
2. In the top navigation bar, click **New +** and select **Web Service**.
3. Connect your GitHub account and choose the repository: **`moheezkiani01/Smart-courier`**.
4. Configure the Web Service settings:
   - **Name:** `smart-courier` (or a name of your choice)
   - **Region:** Choose a region matching or close to your database
   - **Branch:** `main`
   - **Root Directory:** *(leave blank for root)*
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `bash ./start.sh`
   - **Instance Type:** `Free` (0.1 CPU, 512 MB RAM)

---

## 5. Step 4: Configure Environment Variables on Render

In the **Environment** section of your new Web Service, add the following variables:

| Key | Value / Source | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Enables `ProductionConfig`, secure cookies & ProxyFix |
| `FLASK_ENV` | `production` | Enforces production runtime guards |
| `SECRET_KEY` | *(Click "Generate" or enter a 64-char random string)* | Cryptographic key for sessions and CSRF tokens |
| `DATABASE_URL` | `postgresql://...` *(from Step 1)* | Persistent PostgreSQL connection URI |
| `ADMIN_BOOTSTRAP_EMAIL` | `admin@smartcourier.pk` *(or your email)* | Superadmin initial login email |
| `ADMIN_BOOTSTRAP_PASSWORD` | *(Set your chosen strong password)* | Initial superadmin password |
| `ADMIN_BOOTSTRAP_NAME` | `System Administrator` | Superadmin display name |

Click **Save Changes**.

---

## 6. Step 5: Configure Health Check Path

1. In the Web Service settings, scroll down to **Advanced**.
2. Set **Health Check Path** to:
   ```text
   /healthz
   ```
3. Set **Auto-Deploy** to `Yes` (Render will automatically rebuild and deploy when you push new commits to `main`).

---

## 7. Step 6: Deploy and Monitor Startup

1. Click **Create Web Service** (or **Manual Deploy** -> **Deploy latest commit**).
2. Monitor the **Logs** tab:
   - Dependency installation (`pip install -r requirements.txt`)
   - Database migration (`Applying database migrations to latest head...`)
   - Superadmin initialization (`Superadmin bootstrapped successfully!`)
   - Gunicorn worker initialization (`[INFO] Starting gunicorn...`)
   - Health check probe (`GET /healthz HTTP/1.1 200`)
3. When the status displays a green checkmark and **Live**, click the public URL provided at the top of the Render dashboard (e.g. `https://smart-courier.onrender.com`).

---

## 8. Step 7: Post-Deployment Smoke Verification

1. **Health Check:** Visit `https://<your-app>.onrender.com/healthz` — verify it returns:
   ```json
   {"status": "healthy", "service": "smart-courier"}
   ```
2. **Public Home:** Verify the landing page loads cleanly with CSS and JS assets.
3. **Superadmin Login:** Log in using the `ADMIN_BOOTSTRAP_EMAIL` and `ADMIN_BOOTSTRAP_PASSWORD` configured in Step 4.
4. **Customer Registration & Booking:**
   - Register a new customer account.
   - Book a test shipment.
   - Record the tracking number (e.g. `SC-XXXXXXXX`).
5. **Data Persistence Verification:**
   - In Render Dashboard, click **Manual Deploy** -> **Clear build cache & deploy** (or restart the service).
   - Once restarted, search the test tracking number at `/tracking/search`.
   - Confirm the shipment and its journey history remain intact in PostgreSQL.

---

## 9. Render Free Tier Operational Notes

- **Spin-Down on Idle:** Render Free Web Services sleep after 15 minutes of inactivity. The first request after sleeping may take 45–60 seconds to wake up the service.
- **Supabase Inactivity Policy:** Supabase Free databases pause after 7 days of zero queries. To resume, simply open the Supabase dashboard and click "Restore project".
- **Zero Cost:** Both Render Free and Supabase Free require no credit card and incur $0 charges.
