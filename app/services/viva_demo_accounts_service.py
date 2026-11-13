"""
app.services.viva_demo_accounts_service
---------------------------------------
Idempotent, secure management of the 9 dedicated demonstration accounts
for university viva examination across all 9 Smart Courier roles:

1. Super Admin
2. Branch Manager
3. Booking Agent
4. Hub Operator
5. Dispatcher
6. Driver
7. Finance Officer
8. Support Agent
9. Customer

Preserves all 55 database tables and existing user data.
"""

import os
import secrets
import string
from datetime import date, timedelta
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.auth import User, Role, UserRole
from app.models.organization import Employee, EmployeeBranch, Branch, ServiceZone
from app.models.dispatch import Driver
from app.models.catalog import Customer, CustomerAddress
from app.services.init_service import init_production_catalog


VIVA_DEMO_SPECS = [
    {
        "role_code": "SUPER_ADMIN",
        "role_name": "Super Admin",
        "email": "admin@smartcourier.pk",
        "full_name": "System Administrator",
        "phone": "+923001112233",
        "employee_no": None,
        "job_title": None,
        "is_driver": False,
        "is_customer": False,
        "dashboard_url": "/admin/branches",
        "dashboard_label": "Branch & User Management",
    },
    {
        "role_code": "BRANCH_MANAGER",
        "role_name": "Branch Manager",
        "email": "lahore.manager@smartcourier.pk",
        "full_name": "Tariq Mahmood",
        "phone": "+923002223344",
        "employee_no": "EMP-LHR-MGR",
        "job_title": "Branch Operations Manager",
        "is_driver": False,
        "is_customer": False,
        "dashboard_url": "/admin/branches",
        "dashboard_label": "Branch Operations & Fleet",
    },
    {
        "role_code": "BOOKING_AGENT",
        "role_name": "Booking Agent",
        "email": "booking.lahore@smartcourier.pk",
        "full_name": "Ayesha Khan",
        "phone": "+923003334455",
        "employee_no": "EMP-LHR-BKG",
        "job_title": "Senior Booking Agent",
        "is_driver": False,
        "is_customer": False,
        "dashboard_url": "/shipments/new",
        "dashboard_label": "Consignment Booking Counter",
    },
    {
        "role_code": "HUB_OPERATOR",
        "role_name": "Hub Operator",
        "email": "hub.lahore@smartcourier.pk",
        "full_name": "Bilal Ahmed",
        "phone": "+923004445566",
        "employee_no": "EMP-LHR-HUB",
        "job_title": "Hub Sorting Operator",
        "is_driver": False,
        "is_customer": False,
        "dashboard_url": "/hubs/transfers",
        "dashboard_label": "Inter-Hub Freight Transfers",
    },
    {
        "role_code": "DISPATCHER",
        "role_name": "Dispatcher",
        "email": "dispatcher.lahore@smartcourier.pk",
        "full_name": "Hamza Ali",
        "phone": "+923005556677",
        "employee_no": "EMP-LHR-DSP",
        "job_title": "Logistics Dispatcher",
        "is_driver": False,
        "is_customer": False,
        "dashboard_url": "/dispatch/routes",
        "dashboard_label": "Delivery Routes & Runsheets",
    },
    {
        "role_code": "DRIVER",
        "role_name": "Driver",
        "email": "driver1@smartcourier.pk",
        "full_name": "Kamran Akram",
        "phone": "+923006667788",
        "employee_no": "EMP-LHR-DRV",
        "job_title": "Courier Delivery Driver",
        "is_driver": True,
        "license_number": "PK-LHR-DRV-9988",
        "is_customer": False,
        "dashboard_url": "/driver/my-runs",
        "dashboard_label": "Driver Runsheet Workspace",
    },
    {
        "role_code": "FINANCE_OFFICER",
        "role_name": "Finance Officer",
        "email": "finance@smartcourier.pk",
        "full_name": "Saima Farooq",
        "phone": "+923007778899",
        "employee_no": "EMP-LHR-FIN",
        "job_title": "Finance & Settlement Officer",
        "is_driver": False,
        "is_customer": False,
        "dashboard_url": "/finance/invoices",
        "dashboard_label": "Invoices, Receivables & COD",
    },
    {
        "role_code": "SUPPORT_AGENT",
        "role_name": "Support Agent",
        "email": "support@smartcourier.pk",
        "full_name": "Zainab Bibi",
        "phone": "+923008889900",
        "employee_no": "EMP-LHR-SUP",
        "job_title": "Customer Support Specialist",
        "is_driver": False,
        "is_customer": False,
        "dashboard_url": "/support/tickets",
        "dashboard_label": "Customer Support Tickets",
    },
    {
        "role_code": "CUSTOMER",
        "role_name": "Customer",
        "email": "customer@smartcourier.pk",
        "fallback_emails": ["viva.merchant@smartcourier.pk", "demo.merchant@smartcourier.pk"],
        "full_name": "Apex Viva Merchant Ltd",
        "phone": "+923009990011",
        "employee_no": None,
        "job_title": None,
        "is_driver": False,
        "is_customer": True,
        "customer_code": "CUST-VIVA-01",
        "dashboard_url": "/shipments/",
        "dashboard_label": "Customer Consignments & Bookings",
    },
]


def generate_secure_password(length=16):
    """Generate a high-entropy, cryptographically secure password meeting corporate complexity policies."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(chars) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*" for c in pwd)
        ):
            return pwd


def ensure_viva_demo_accounts(
    password: str = None,
    reset_passwords: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Idempotently guarantees that active accounts exist for all 9 roles,
    with appropriate branch, employee, driver, and customer relationships.
    """
    # Step 1: Ensure underlying master catalog and roles exist
    init_production_catalog()

    branch = Branch.query.filter_by(code="BR-LHR-01").first() or Branch.query.first()
    if not branch and not dry_run:
        branch = Branch(
            code="BR-LHR-01",
            name="Lahore Central Branch",
            phone="+924235551122",
            address_line="88 Main Boulevard, Gulberg III",
            city="Lahore",
        )
        db.session.add(branch)
        db.session.flush()

    zone = ServiceZone.query.filter_by(code="ZONE-LHR").first() or ServiceZone.query.first()
    if not zone and not dry_run:
        zone = ServiceZone(
            code="ZONE-LHR",
            name="Lahore Metro Zone",
            city="Lahore",
            region="Punjab",
            postal_prefix="54000",
        )
        db.session.add(zone)
        db.session.flush()

    # Determine master or generated password
    env_pwd = os.environ.get("VIVA_DEMO_PASSWORD", "").strip()
    shared_password = password or env_pwd or generate_secure_password()

    results = []
    created_count = 0
    updated_count = 0

    for spec in VIVA_DEMO_SPECS:
        role_code = spec["role_code"]
        target_role = Role.query.filter_by(code=role_code).first()

        # Locate existing user by primary email or fallback emails
        user = User.query.filter_by(email=spec["email"], is_deleted=False).first()
        if not user and spec.get("fallback_emails"):
            for fb_email in spec["fallback_emails"]:
                user = User.query.filter_by(email=fb_email, is_deleted=False).first()
                if user:
                    break

        account_pwd = shared_password
        is_new = False

        if dry_run:
            results.append({
                "role_name": spec["role_name"],
                "role_code": role_code,
                "email": user.email if user else spec["email"],
                "full_name": user.full_name if user else spec["full_name"],
                "status": "EXISTS" if user else "TO_CREATE",
                "dashboard_url": spec["dashboard_url"],
                "password": "[DRY-RUN PROTECTED]",
            })
            continue

        if not user:
            is_new = True
            user = User(
                email=spec["email"],
                full_name=spec["full_name"],
                phone=spec["phone"],
                status="ACTIVE",
                is_email_verified=True,
            )
            user.set_password(account_pwd)
            db.session.add(user)
            db.session.flush()
            created_count += 1
        else:
            user.status = "ACTIVE"
            user.is_email_verified = True
            if reset_passwords or (not user.password_hash):
                user.set_password(account_pwd)
            updated_count += 1

        # Link role
        if target_role:
            ur = UserRole.query.filter_by(user_id=user.id, role_id=target_role.id).first()
            if not ur:
                ur = UserRole(user_id=user.id, role_id=target_role.id, is_deleted=False)
                db.session.add(ur)
            elif ur.is_deleted:
                ur.is_deleted = False

        # Link employee profile if applicable
        if spec.get("employee_no") and branch:
            emp = Employee.query.filter_by(user_id=user.id).first()
            if not emp:
                emp = Employee.query.filter_by(employee_no=spec["employee_no"]).first()
            if not emp:
                emp = Employee(
                    user_id=user.id,
                    primary_branch_id=branch.id,
                    employee_no=spec["employee_no"],
                    job_title=spec["job_title"],
                    hired_on=date(2024, 1, 1),
                )
                db.session.add(emp)
                db.session.flush()
            else:
                emp.user_id = user.id
                emp.primary_branch_id = branch.id
                emp.job_title = spec["job_title"]

            # EmployeeBranch junction
            eb = EmployeeBranch.query.filter_by(employee_id=emp.id, branch_id=branch.id).first()
            if not eb:
                eb = EmployeeBranch(
                    employee_id=emp.id,
                    branch_id=branch.id,
                    is_primary=True,
                    assigned_on=date(2024, 1, 1),
                )
                db.session.add(eb)

            # Driver profile if applicable
            if spec.get("is_driver"):
                drv = Driver.query.filter_by(employee_id=emp.id).first()
                if not drv:
                    drv = Driver(
                        employee_id=emp.id,
                        license_number=spec.get("license_number", "PK-LHR-DRV-9988"),
                        license_expires_on=date.today() + timedelta(days=365 * 3),
                    )
                    db.session.add(drv)

        # Link customer profile if applicable
        if spec.get("is_customer"):
            cust = Customer.query.filter_by(user_id=user.id).first()
            if not cust:
                cust = Customer.query.filter_by(email=user.email).first()
            if not cust:
                cust = Customer(
                    user_id=user.id,
                    customer_code=spec.get("customer_code", "CUST-VIVA-01"),
                    full_name=user.full_name,
                    phone=user.phone or "+923009990011",
                    email=user.email,
                )
                db.session.add(cust)
                db.session.flush()
            else:
                cust.user_id = user.id
                cust.full_name = user.full_name
                cust.phone = user.phone or cust.phone

            if zone and not CustomerAddress.query.filter_by(customer_id=cust.id).first():
                ca = CustomerAddress(
                    customer_id=cust.id,
                    zone_id=zone.id,
                    label="Main Office",
                    line1="88 Main Boulevard, Gulberg III",
                    city="Lahore",
                    postal_code="54000",
                )
                db.session.add(ca)

        results.append({
            "role_name": spec["role_name"],
            "role_code": role_code,
            "email": user.email,
            "full_name": user.full_name,
            "status": "ACTIVE",
            "is_new": is_new,
            "dashboard_url": spec["dashboard_url"],
            "password": account_pwd if (is_new or reset_passwords or password or env_pwd) else "[PRESERVED]",
        })

    if not dry_run:
        db.session.commit()

    return {
        "status": "success",
        "dry_run": dry_run,
        "created_count": created_count,
        "updated_count": updated_count,
        "total_accounts": len(results),
        "accounts": results,
        "shared_password": shared_password if (created_count > 0 or reset_passwords or password or env_pwd) else None,
    }


def deactivate_viva_demo_accounts(preserve_admin: bool = True, confirm: bool = False) -> dict:
    """
    Safely deactivate dedicated demonstration accounts after the viva examination.
    Leaves all 55 relational database tables, shipments, and customer records intact.
    """
    if not confirm:
        return {
            "status": "error",
            "message": "Explicit confirmation required (--confirm) to deactivate demonstration accounts.",
        }

    deactivated = []
    for spec in VIVA_DEMO_SPECS:
        if preserve_admin and spec["role_code"] == "SUPER_ADMIN":
            continue

        emails = [spec["email"]] + spec.get("fallback_emails", [])
        for em in emails:
            u = User.query.filter_by(email=em, is_deleted=False).first()
            if u and u.status != "DEACTIVE":
                u.status = "DEACTIVE"
                deactivated.append({"role": spec["role_name"], "email": u.email, "name": u.full_name})

    db.session.commit()
    return {
        "status": "success",
        "deactivated_count": len(deactivated),
        "deactivated_accounts": deactivated,
    }


def activate_viva_demo_accounts(confirm: bool = False) -> dict:
    """Reactivate demonstration accounts if needed for additional testing sessions."""
    if not confirm:
        return {
            "status": "error",
            "message": "Explicit confirmation required (--confirm) to activate demonstration accounts.",
        }

    activated = []
    for spec in VIVA_DEMO_SPECS:
        emails = [spec["email"]] + spec.get("fallback_emails", [])
        for em in emails:
            u = User.query.filter_by(email=em, is_deleted=False).first()
            if u and u.status != "ACTIVE":
                u.status = "ACTIVE"
                activated.append({"role": spec["role_name"], "email": u.email, "name": u.full_name})

    db.session.commit()
    return {
        "status": "success",
        "activated_count": len(activated),
        "activated_accounts": activated,
    }


def get_viva_demo_accounts_status() -> list:
    """Check the real database status of all 9 viva role accounts."""
    status_list = []
    for spec in VIVA_DEMO_SPECS:
        role_code = spec["role_code"]
        emails = [spec["email"]] + spec.get("fallback_emails", [])
        user = None
        for em in emails:
            u = User.query.filter_by(email=em, is_deleted=False).first()
            if u:
                user = u
                break

        has_role = user.has_role(role_code) if user else False
        status_list.append({
            "role_name": spec["role_name"],
            "role_code": role_code,
            "target_email": spec["email"],
            "actual_email": user.email if user else None,
            "full_name": user.full_name if user else None,
            "exists": user is not None,
            "status": user.status if user else "NOT_FOUND",
            "has_role": has_role,
            "dashboard_url": spec["dashboard_url"],
        })
    return status_list
