from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.admin import admin_bp
from app.security.rbac import roles_required
from app.models.auth import User, Role, UserRole
from app.models.organization import Branch, Hub, Employee, ServiceZone
from app.models.support import AuditLog
from app.forms.admin_forms import BranchForm, HubForm, EmployeeForm, ServiceZoneForm
from app.services.audit_service import log_audit

@admin_bp.route("/branches", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER")
def branches():
    branch_list = Branch.query.filter_by(is_deleted=False).all()
    return render_template("admin/branches.html", branches=branch_list)

@admin_bp.route("/branches/new", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN")
def new_branch():
    form = BranchForm()
    if form.validate_on_submit():
        branch = Branch(
            code=form.code.data.strip().upper(),
            name=form.name.data.strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            city=form.city.data.strip(),
            address_line=form.address_line.data.strip(),
            created_by=current_user.id
        )
        db.session.add(branch)
        db.session.flush()
        log_audit("CREATE_BRANCH", "Branch", branch.id, after={"code": branch.code, "name": branch.name}, user_id=current_user.id)
        db.session.commit()
        flash(f"Branch '{branch.name}' created successfully.", "success")
        return redirect(url_for("admin.branches"))
    return render_template("admin/branch_form.html", form=form, title="Create Branch")

@admin_bp.route("/branches/<int:branch_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER")
def edit_branch(branch_id):
    branch = Branch.query.filter_by(id=branch_id, is_deleted=False).first_or_404()
    form = BranchForm(obj=branch)
    if form.validate_on_submit():
        before_state = {"name": branch.name, "city": branch.city, "phone": branch.phone}
        branch.name = form.name.data.strip()
        branch.phone = form.phone.data.strip() if form.phone.data else None
        branch.city = form.city.data.strip()
        branch.address_line = form.address_line.data.strip()
        branch.updated_at = datetime.utcnow()
        branch.updated_by = current_user.id
        log_audit("UPDATE_BRANCH", "Branch", branch.id, before=before_state, after={"name": branch.name, "city": branch.city}, user_id=current_user.id)
        db.session.commit()
        flash(f"Branch '{branch.name}' updated successfully.", "success")
        return redirect(url_for("admin.branches"))
    return render_template("admin/branch_form.html", form=form, title="Edit Branch", branch=branch)

@admin_bp.route("/branches/<int:branch_id>/deactivate", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN")
def deactivate_branch(branch_id):
    branch = Branch.query.filter_by(id=branch_id, is_deleted=False).first_or_404()
    branch.soft_delete(user_id=current_user.id)
    log_audit("DEACTIVATE_BRANCH", "Branch", branch.id, user_id=current_user.id)
    db.session.commit()
    flash(f"Branch '{branch.name}' deactivated.", "info")
    return redirect(url_for("admin.branches"))

# HUBS
@admin_bp.route("/hubs", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER")
def hubs():
    hub_list = Hub.query.filter_by(is_deleted=False).all()
    return render_template("admin/hubs.html", hubs=hub_list)

@admin_bp.route("/hubs/new", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER")
def new_hub():
    form = HubForm()
    branches = Branch.query.filter_by(is_deleted=False).all()
    form.branch_id.choices = [(b.id, f"{b.name} ({b.city})") for b in branches]
    if form.validate_on_submit():
        hub = Hub(
            branch_id=form.branch_id.data,
            code=form.code.data.strip().upper(),
            name=form.name.data.strip(),
            location_note=form.location_note.data.strip() if form.location_note.data else None,
            created_by=current_user.id
        )
        db.session.add(hub)
        db.session.flush()
        log_audit("CREATE_HUB", "Hub", hub.id, after={"code": hub.code, "name": hub.name}, user_id=current_user.id)
        db.session.commit()
        flash(f"Hub '{hub.name}' created successfully.", "success")
        return redirect(url_for("admin.hubs"))
    return render_template("admin/hub_form.html", form=form, title="Create Hub")

@admin_bp.route("/hubs/<int:hub_id>/deactivate", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN")
def deactivate_hub(hub_id):
    hub = Hub.query.filter_by(id=hub_id, is_deleted=False).first_or_404()
    hub.soft_delete(user_id=current_user.id)
    log_audit("DEACTIVATE_HUB", "Hub", hub.id, user_id=current_user.id)
    db.session.commit()
    flash(f"Hub '{hub.name}' deactivated.", "info")
    return redirect(url_for("admin.hubs"))

# USERS & STAFF
@admin_bp.route("/users", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER")
def users():
    if current_user.has_role("BRANCH_MANAGER") and not current_user.has_role("SUPER_ADMIN"):
        branch_id = current_user.employee.primary_branch_id if hasattr(current_user, "employee") and current_user.employee else None
        if branch_id:
            users_list = User.query.join(Employee, Employee.user_id == User.id).filter(
                Employee.primary_branch_id == branch_id,
                User.is_deleted == False
            ).all()
        else:
            users_list = [current_user]
    else:
        users_list = User.query.filter_by(is_deleted=False).all()
    return render_template("admin/users.html", users=users_list)

@admin_bp.route("/users/new", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN")
def new_user():
    form = EmployeeForm()
    branches = Branch.query.filter_by(is_deleted=False).all()
    roles = Role.query.filter_by(is_deleted=False).all()
    form.primary_branch_id.choices = [(b.id, b.name) for b in branches]
    form.role_code.choices = [(r.code, r.name) for r in roles]

    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            created_by=current_user.id
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        role = Role.query.filter_by(code=form.role_code.data).first()
        if role:
            ur = UserRole(user_id=user.id, role_id=role.id, assigned_by_user_id=current_user.id)
            db.session.add(ur)

        emp = Employee(
            user_id=user.id,
            primary_branch_id=form.primary_branch_id.data,
            employee_no=form.employee_no.data.strip().upper(),
            job_title=form.job_title.data.strip(),
            hired_on=form.hired_on.data or datetime.utcnow().date(),
            created_by=current_user.id
        )
        db.session.add(emp)
        db.session.flush()

        log_audit("CREATE_STAFF_USER", "User", user.id, after={"email": user.email, "role": form.role_code.data}, user_id=current_user.id)
        db.session.commit()
        flash(f"Staff member '{user.full_name}' registered.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, title="Register Staff Member")

@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN")
def deactivate_user(user_id):
    if user_id == current_user.id:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("admin.users"))
    user = User.query.filter_by(id=user_id, is_deleted=False).first_or_404()
    user.soft_delete(user_id=current_user.id)
    log_audit("DEACTIVATE_USER", "User", user.id, user_id=current_user.id)
    db.session.commit()
    flash(f"User '{user.full_name}' has been deactivated.", "info")
    return redirect(url_for("admin.users"))

# SERVICE ZONES
@admin_bp.route("/zones", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER")
def zones():
    zone_list = ServiceZone.query.filter_by(is_deleted=False).all()
    return render_template("admin/zones.html", zones=zone_list)

@admin_bp.route("/zones/new", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN")
def new_zone():
    form = ServiceZoneForm()
    if form.validate_on_submit():
        zone = ServiceZone(
            code=form.code.data.strip().upper(),
            name=form.name.data.strip(),
            city=form.city.data.strip(),
            region=form.region.data.strip(),
            postal_prefix=form.postal_prefix.data.strip() if form.postal_prefix.data else None,
            created_by=current_user.id
        )
        db.session.add(zone)
        db.session.flush()
        log_audit("CREATE_ZONE", "ServiceZone", zone.id, after={"code": zone.code, "name": zone.name}, user_id=current_user.id)
        db.session.commit()
        flash(f"Service Zone '{zone.name}' created.", "success")
        return redirect(url_for("admin.zones"))
    return render_template("admin/zone_form.html", form=form, title="Create Service Zone")

# AUDIT LOGS
@admin_bp.route("/audit-logs", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN")
def audit_logs():
    q = request.args.get("q", "").strip()
    query = AuditLog.query.order_by(AuditLog.occurred_at.desc())
    if q:
        query = query.filter((AuditLog.action.contains(q)) | (AuditLog.entity_type.contains(q)))
    logs = query.limit(100).all()
    return render_template("admin/audit_logs.html", logs=logs, q=q)
