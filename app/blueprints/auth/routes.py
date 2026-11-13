import hashlib
import json
import os
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.blueprints.auth import auth_bp
from app.forms.auth_forms import LoginForm, ChangePasswordForm, ProfileForm, RegisterForm
from app.models.auth import User, Role, UserRole, LoginSession
from app.models.catalog import Customer

VIVA_ROLE_CODE_MAP = {
    "super admin": "SUPER_ADMIN",
    "super_admin": "SUPER_ADMIN",
    "branch manager": "BRANCH_MANAGER",
    "branch_manager": "BRANCH_MANAGER",
    "booking agent": "BOOKING_AGENT",
    "booking_agent": "BOOKING_AGENT",
    "hub operator": "HUB_OPERATOR",
    "hub_operator": "HUB_OPERATOR",
    "dispatcher": "DISPATCHER",
    "driver": "DRIVER",
    "finance officer": "FINANCE_OFFICER",
    "finance_officer": "FINANCE_OFFICER",
    "support agent": "SUPPORT_AGENT",
    "support_agent": "SUPPORT_AGENT",
    "customer": "CUSTOMER",
    "customer (secondary)": "CUSTOMER",
}

DEFAULT_VIVA_DEMO_ACCOUNTS = [
    {
        "role": "Super Admin",
        "role_code": "SUPER_ADMIN",
        "email": "viva.admin@smartcourier.pk",
        "fallback_emails": ["admin@smartcourier.pk"],
        "label": "Viva Administrator",
    },
    {
        "role": "Branch Manager",
        "role_code": "BRANCH_MANAGER",
        "email": "lahore.manager@smartcourier.pk",
        "fallback_emails": [],
        "label": "Tariq Mahmood",
    },
    {
        "role": "Booking Agent",
        "role_code": "BOOKING_AGENT",
        "email": "booking.lahore@smartcourier.pk",
        "fallback_emails": [],
        "label": "Ayesha Khan",
    },
    {
        "role": "Hub Operator",
        "role_code": "HUB_OPERATOR",
        "email": "hub.lahore@smartcourier.pk",
        "fallback_emails": [],
        "label": "Bilal Ahmed",
    },
    {
        "role": "Dispatcher",
        "role_code": "DISPATCHER",
        "email": "dispatcher.lahore@smartcourier.pk",
        "fallback_emails": [],
        "label": "Hamza Ali",
    },
    {
        "role": "Driver",
        "role_code": "DRIVER",
        "email": "driver1@smartcourier.pk",
        "fallback_emails": [],
        "label": "Kamran Akram",
    },
    {
        "role": "Finance Officer",
        "role_code": "FINANCE_OFFICER",
        "email": "finance@smartcourier.pk",
        "fallback_emails": [],
        "label": "Saima Farooq",
    },
    {
        "role": "Support Agent",
        "role_code": "SUPPORT_AGENT",
        "email": "support@smartcourier.pk",
        "fallback_emails": [],
        "label": "Zainab Bibi",
    },
    {
        "role": "Customer",
        "role_code": "CUSTOMER",
        "email": "customer@smartcourier.pk",
        "fallback_emails": ["viva.merchant@smartcourier.pk", "demo.merchant@smartcourier.pk"],
        "label": "Apex Viva Merchant",
    },
]

def get_viva_demo_accounts():
    """Retrieve and strictly validate active demonstration accounts for the viva login picker."""
    if not current_app.config.get("VIVA_LOGIN_PICKER_ENABLED", False):
        return []

    custom_json = current_app.config.get("VIVA_LOGIN_ACCOUNTS_JSON", "")
    candidates = []
    if custom_json and custom_json.strip():
        try:
            parsed = json.loads(custom_json.strip())
            if isinstance(parsed, dict):
                for role_label, email in parsed.items():
                    role_code = VIVA_ROLE_CODE_MAP.get(role_label.strip().lower(), role_label.strip().upper().replace(" ", "_"))
                    candidates.append({
                        "role": role_label.strip(),
                        "role_code": role_code,
                        "email": str(email).strip().lower(),
                        "label": "",
                    })
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "email" in item:
                        r_label = item.get("role", "Demo User")
                        r_code = item.get("role_code") or VIVA_ROLE_CODE_MAP.get(r_label.strip().lower(), r_label.strip().upper().replace(" ", "_"))
                        candidates.append({
                            "role": r_label,
                            "role_code": r_code,
                            "email": str(item["email"]).strip().lower(),
                            "label": item.get("label", ""),
                        })
        except Exception:
            candidates = []

    if not candidates:
        candidates = DEFAULT_VIVA_DEMO_ACCOUNTS

    verified = []
    for c in candidates:
        req_role = c.get("role_code")
        candidate_emails = []
        if c.get("email"):
            candidate_emails.append(c["email"].strip().lower())
        for fb in c.get("fallback_emails", []):
            if fb and fb.strip().lower() not in candidate_emails:
                candidate_emails.append(fb.strip().lower())

        user = None
        for em in candidate_emails:
            u = User.query.filter_by(email=em, is_deleted=False).first()
            if u and u.status == "ACTIVE" and (not req_role or u.has_role(req_role)):
                user = u
                break

        # Fallback for Super Admin: find any active SUPER_ADMIN user if target email was not found
        if not user and req_role == "SUPER_ADMIN":
            admin_role = Role.query.filter_by(code="SUPER_ADMIN").first()
            if admin_role:
                active_ur = (
                    UserRole.query.filter_by(role_id=admin_role.id, is_deleted=False)
                    .join(User, UserRole.user_id == User.id)
                    .filter(User.status == "ACTIVE", User.is_deleted == False)
                    .first()
                )
                if active_ur and active_ur.user:
                    user = active_ur.user

        if not user or user.status != "ACTIVE":
            continue
        if req_role and not user.has_role(req_role):
            continue

        verified.append({
            "role": c.get("role", req_role or "Demo User"),
            "email": user.email,
            "label": user.full_name or c.get("label", ""),
        })

    return verified

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    demo_accounts = get_viva_demo_accounts()
    form = LoginForm()
    if form.validate_on_submit():
        norm_email = form.email.data.strip().lower()
        user = User.query.filter_by(email=norm_email, is_deleted=False).first()

        # Dynamic synchronization for dedicated viva demo accounts with password "123"
        viva_enabled = (
            current_app.config.get("VIVA_TESTING_ENABLED", False)
            or current_app.config.get("VIVA_LOGIN_PICKER_ENABLED", False)
            or os.environ.get("VIVA_TESTING_ENABLED", "").lower() in ("true", "1", "yes")
            or os.environ.get("VIVA_LOGIN_PICKER_ENABLED", "").lower() in ("true", "1", "yes")
        )
        from app.services.viva_demo_accounts_service import is_viva_demo_email
        if user and viva_enabled and is_viva_demo_email(norm_email) and form.password.data == "123":
            if not user.check_password("123"):
                user.set_password("123")
                db.session.commit()

        if user and user.check_password(form.password.data):
            if user.status == "DEACTIVE":
                flash("Your account has been deactivated. Please contact support.", "danger")
                return render_template("auth/login.html", form=form, demo_accounts=demo_accounts)

            login_user(user, remember=form.remember_me.data)
            user.last_login_at = datetime.utcnow()

            # Record login session security audit
            raw_token = f"{user.id}:{datetime.utcnow().isoformat()}:{os.urandom(16).hex()}"
            session_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            session_entry = LoginSession(
                user_id=user.id,
                session_hash=session_hash,
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7 if form.remember_me.data else 1),
                ip_hint=request.remote_addr,
                created_by=user.id,
            )
            db.session.add(session_entry)
            db.session.commit()

            flash(f"Welcome back, {user.full_name}!", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("main.index"))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("auth/login.html", form=form, demo_accounts=demo_accounts)



@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        norm_email = form.email.data.strip().lower()
        existing = User.query.filter_by(email=norm_email).first()
        if existing:
            flash("An account with this email address already exists. Please sign in.", "warning")
            return render_template("auth/register.html", form=form)

        try:
            # 1. Create User
            user = User(
                email=norm_email,
                full_name=form.full_name.data.strip(),
                phone=form.phone.data.strip(),
                is_email_verified=True,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()

            # 2. Attach CUSTOMER role
            cust_role = Role.query.filter_by(code="CUSTOMER").first()
            if not cust_role:
                cust_role = Role(code="CUSTOMER", name="Registered Customer", description="Self-service booking, tracking & support")
                db.session.add(cust_role)
                db.session.flush()
            ur = UserRole(user_id=user.id, role_id=cust_role.id, created_by=user.id)
            db.session.add(ur)

            # 3. Create linked Customer profile
            cust_code = f"CUST-{user.id:04d}"
            cust_profile = Customer(
                user_id=user.id,
                customer_code=cust_code,
                full_name=user.full_name,
                phone=user.phone,
                email=user.email,
                created_by=user.id,
            )
            db.session.add(cust_profile)
            db.session.commit()

            # 4. Auto-login newly registered customer
            login_user(user)
            flash(f"Welcome to Smart Courier, {user.full_name}! Your customer account is ready.", "success")
            return redirect(url_for("main.index"))
        except Exception as e:
            db.session.rollback()
            flash(f"Registration error: {str(e)}", "danger")

    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    profile_form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()

    if "submit_profile" in request.form and profile_form.validate_on_submit():
        current_user.full_name = profile_form.full_name.data.strip()
        current_user.phone = profile_form.phone.data.strip() if profile_form.phone.data else None
        current_user.updated_at = datetime.utcnow()
        current_user.updated_by = current_user.id
        db.session.commit()
        flash("Your profile details have been updated.", "success")
        return redirect(url_for("auth.profile"))

    if "submit_password" in request.form and password_form.validate_on_submit():
        if current_user.check_password(password_form.old_password.data):
            current_user.set_password(password_form.new_password.data)
            current_user.updated_at = datetime.utcnow()
            current_user.updated_by = current_user.id
            db.session.commit()
            flash("Your password has been changed successfully.", "success")
            return redirect(url_for("auth.profile"))
        else:
            flash("Current password was incorrect.", "danger")

    return render_template("auth/profile.html", profile_form=profile_form, password_form=password_form)
