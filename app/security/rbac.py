from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def roles_required(*allowed_roles):
    """Ensure authenticated user holds at least one of the specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.has_role("SUPER_ADMIN"):
                return f(*args, **kwargs)
            if not any(current_user.has_role(role) for role in allowed_roles):
                flash("Access denied: You do not have permission to view this resource.", "danger")
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission_code):
    """Ensure authenticated user possesses the specified permission."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if not current_user.has_permission(permission_code):
                flash(f"Access denied: Missing permission '{permission_code}'.", "danger")
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def verify_branch_access(branch_id: int) -> bool:
    """Check if the current user has operational authority for a branch."""
    if not current_user.is_authenticated:
        return False
    if current_user.has_role("SUPER_ADMIN"):
        return True
    if hasattr(current_user, "employee") and current_user.employee:
        if current_user.employee.primary_branch_id == branch_id:
            return True
        for eb in current_user.employee.employee_branches:
            if eb.branch_id == branch_id and not eb.is_deleted:
                return True
    return False

def get_user_capabilities(user):
    """Return dictionary of boolean permissions for the user to power UI gates."""
    if not user or not user.is_authenticated:
        return {}

    is_super = user.has_role("SUPER_ADMIN")
    is_bm = user.has_role("BRANCH_MANAGER")
    is_ba = user.has_role("BOOKING_AGENT")
    is_hub = user.has_role("HUB_OPERATOR")
    is_disp = user.has_role("DISPATCHER")
    is_driver = user.has_role("DRIVER")
    is_fin = user.has_role("FINANCE_OFFICER")
    is_supp = user.has_role("SUPPORT_AGENT")
    is_cust = user.has_role("CUSTOMER")

    caps = {
        # Navigation & Views
        "can_view_dashboard": True,
        "can_view_shipments": is_super or is_bm or is_ba or is_hub or is_disp or is_fin or is_supp or is_cust,
        "can_book_shipment": is_super or is_bm or is_ba or is_cust,
        "can_view_customers": is_super or is_bm or is_ba or is_supp,
        "can_manage_customers": is_super or is_bm or is_ba,
        "can_view_hubs": is_super or is_bm or is_hub,
        "can_scan_hubs": is_super or is_bm or is_hub,
        "can_transfer_hubs": is_super or is_bm or is_hub,
        "can_view_dispatch": is_super or is_bm or is_disp,
        "can_manage_routes": is_super or is_bm or is_disp,
        "can_view_driver_workspace": is_super or is_driver,
        "can_view_invoices": is_super or is_bm or is_fin or is_cust,
        "can_settle_payments": is_super or is_fin or is_ba,
        "can_process_refunds": is_super or is_fin,
        "can_view_cod": is_super or is_fin,
        "can_manage_cod": is_super or is_fin,
        "can_view_rates": is_super or is_bm or is_ba,
        "can_manage_rates": is_super or is_bm,
        "can_view_branches": is_super or is_bm,
        "can_manage_branches": is_super,
        "can_view_staff": is_super or is_bm,
        "can_manage_staff": is_super,
        "can_view_audit_logs": is_super,
        "can_view_tickets": True,
        "can_manage_tickets": is_super or is_supp or is_bm,
        "can_assign_pickup": is_super or is_bm or is_disp,
        "can_change_status": is_super or is_bm or is_ba or is_hub or is_disp,
    }

    # Role indicators
    caps["is_customer"] = is_cust and not is_super
    caps["is_driver"] = is_driver and not is_super
    caps["is_staff"] = not caps["is_customer"]

    # Group visibility
    if caps["is_customer"]:
        caps["show_customer_section"] = True
        caps["show_desk_section"] = False
        caps["show_ops_section"] = False
        caps["show_finance_section"] = False
        caps["show_admin_section"] = False
    else:
        caps["show_customer_section"] = False
        caps["show_desk_section"] = caps["can_view_shipments"] or caps["can_book_shipment"] or caps["can_view_customers"]
        caps["show_ops_section"] = caps["can_scan_hubs"] or caps["can_transfer_hubs"] or caps["can_view_dispatch"] or caps["can_view_driver_workspace"]
        caps["show_finance_section"] = caps["can_view_invoices"] or caps["can_view_cod"]
        caps["show_admin_section"] = caps["can_view_branches"] or caps["can_view_staff"] or caps["can_view_audit_logs"] or caps["can_view_rates"] or (caps["can_view_tickets"] and not caps["is_customer"])

    return caps
