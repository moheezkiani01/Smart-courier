from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.customers import customers_bp
from app.security.rbac import roles_required
from app.models.catalog import (
    Customer,
    CustomerAddress,
    CustomerContact,
    RecipientProfile,
    RecipientAddress,
)
from app.models.organization import ServiceZone
from app.forms.customer_forms import (
    CustomerForm,
    CustomerAddressForm,
    CustomerContactForm,
    RecipientProfileForm,
)
from app.services.audit_service import log_audit
from app.utils.helpers import generate_customer_code

@customers_bp.route("/", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "BOOKING_AGENT", "SUPPORT_AGENT")
def index():
    q = request.args.get("q", "").strip()
    query = Customer.query.filter_by(is_deleted=False)
    if q:
        query = query.filter(
            (Customer.full_name.contains(q)) |
            (Customer.customer_code.contains(q)) |
            (Customer.phone.contains(q))
        )
    customers_list = query.order_by(Customer.created_at.desc()).all()
    return render_template("customers/index.html", customers=customers_list, q=q)

@customers_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "BOOKING_AGENT")
def new_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        code = form.customer_code.data.strip().upper() if form.customer_code.data else generate_customer_code()
        customer = Customer(
            customer_code=code,
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower() if form.email.data else None,
            phone=form.phone.data.strip(),
            created_by=current_user.id,
        )
        db.session.add(customer)
        db.session.flush()
        log_audit("CREATE_CUSTOMER", "Customer", customer.id, after={"code": customer.customer_code, "name": customer.full_name}, user_id=current_user.id)
        db.session.commit()
        flash(f"Customer '{customer.full_name}' ({customer.customer_code}) registered.", "success")
        return redirect(url_for("customers.show", customer_id=customer.id))
    return render_template("customers/form.html", form=form, title="Register New Customer")

@customers_bp.route("/<int:customer_id>", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "BOOKING_AGENT", "SUPPORT_AGENT", "CUSTOMER")
def show(customer_id):
    customer = Customer.query.filter_by(id=customer_id, is_deleted=False).first_or_404()
    if current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN"):
        if not (current_user.customer and current_user.customer.id == customer_id):
            abort(403)
    return render_template("customers/show.html", customer=customer)

@customers_bp.route("/<int:customer_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "BOOKING_AGENT")
def edit_customer(customer_id):
    customer = Customer.query.filter_by(id=customer_id, is_deleted=False).first_or_404()
    form = CustomerForm(obj=customer)
    if form.validate_on_submit():
        customer.full_name = form.full_name.data.strip()
        customer.email = form.email.data.strip().lower() if form.email.data else None
        customer.phone = form.phone.data.strip()
        customer.updated_at = datetime.utcnow()
        customer.updated_by = current_user.id
        log_audit("UPDATE_CUSTOMER", "Customer", customer.id, after={"name": customer.full_name, "phone": customer.phone}, user_id=current_user.id)
        db.session.commit()
        flash(f"Customer '{customer.full_name}' updated successfully.", "success")
        return redirect(url_for("customers.show", customer_id=customer.id))
    return render_template("customers/form.html", form=form, title="Edit Customer", customer=customer)

@customers_bp.route("/<int:customer_id>/deactivate", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER")
def deactivate(customer_id):
    customer = Customer.query.filter_by(id=customer_id, is_deleted=False).first_or_404()
    customer.soft_delete(user_id=current_user.id)
    log_audit("DEACTIVATE_CUSTOMER", "Customer", customer.id, user_id=current_user.id)
    db.session.commit()
    flash(f"Customer '{customer.full_name}' deactivated.", "info")
    return redirect(url_for("customers.index"))

@customers_bp.route("/<int:customer_id>/addresses/new", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "BOOKING_AGENT", "CUSTOMER")
def add_address(customer_id):
    customer = Customer.query.filter_by(id=customer_id, is_deleted=False).first_or_404()
    if current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN"):
        if not (current_user.customer and current_user.customer.id == customer_id):
            abort(403)
    form = CustomerAddressForm()
    zones = ServiceZone.query.filter_by(is_deleted=False).all()
    form.zone_id.choices = [(z.id, f"{z.name} ({z.city})") for z in zones]

    if form.validate_on_submit():
        addr = CustomerAddress(
            customer_id=customer.id,
            zone_id=form.zone_id.data,
            label=form.label.data.strip(),
            line1=form.line1.data.strip(),
            city=form.city.data.strip(),
            postal_code=form.postal_code.data.strip() if form.postal_code.data else None,
            created_by=current_user.id,
        )
        db.session.add(addr)
        db.session.commit()
        flash("Address saved successfully.", "success")
        return redirect(url_for("customers.show", customer_id=customer.id))
    return render_template("customers/address_form.html", form=form, customer=customer)

@customers_bp.route("/<int:customer_id>/recipients/new", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "BOOKING_AGENT", "CUSTOMER")
def add_recipient(customer_id):
    customer = Customer.query.filter_by(id=customer_id, is_deleted=False).first_or_404()
    if current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN"):
        if not (current_user.customer and current_user.customer.id == customer_id):
            abort(403)
    form = RecipientProfileForm()
    zones = ServiceZone.query.filter_by(is_deleted=False).all()
    form.zone_id.choices = [(z.id, f"{z.name} ({z.city})") for z in zones]

    if form.validate_on_submit():
        profile = RecipientProfile(
            customer_id=customer.id,
            name=form.name.data.strip(),
            phone=form.phone.data.strip(),
            email=form.email.data.strip().lower() if form.email.data else None,
            created_by=current_user.id,
        )
        db.session.add(profile)
        db.session.flush()

        addr = RecipientAddress(
            recipient_id=profile.id,
            zone_id=form.zone_id.data,
            line1=form.line1.data.strip(),
            city=form.city.data.strip(),
            postal_code=form.postal_code.data.strip() if form.postal_code.data else None,
            created_by=current_user.id,
        )
        db.session.add(addr)
        db.session.commit()
        flash(f"Recipient profile for '{profile.name}' saved.", "success")
        return redirect(url_for("customers.show", customer_id=customer.id))
    return render_template("customers/recipient_form.html", form=form, customer=customer)
