from datetime import datetime, date
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.dispatch import dispatch_bp
from app.security.rbac import roles_required
from app.models.dispatch import Route, RouteStop, Vehicle, Driver
from app.models.organization import Branch, Employee
from app.models.shipments import Shipment
from app.forms.dispatch_forms import RouteForm, RouteStopForm, VehicleForm, DriverForm
from app.services.dispatch_service import DispatchService
from app.services.audit_service import log_audit

@dispatch_bp.route("/routes", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "DISPATCHER")
def routes():
    routes_list = Route.query.filter_by(is_deleted=False).order_by(Route.route_date.desc()).all()
    return render_template("dispatch/routes.html", routes=routes_list)

@dispatch_bp.route("/routes/new", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "DISPATCHER")
def new_route():
    form = RouteForm()
    branches = Branch.query.filter_by(is_deleted=False).all()
    drivers = Driver.query.filter_by(is_deleted=False).all()
    vehicles = Vehicle.query.filter_by(is_deleted=False).all()

    form.branch_id.choices = [(b.id, b.name) for b in branches]
    form.driver_id.choices = [(d.id, f"{d.employee.user.full_name} ({d.license_number})") for d in drivers]
    form.vehicle_id.choices = [(v.id, f"{v.plate_number} ({v.vehicle_type})") for v in vehicles]

    if form.validate_on_submit():
        try:
            route = DispatchService.create_route(
                branch_id=form.branch_id.data,
                driver_id=form.driver_id.data,
                vehicle_id=form.vehicle_id.data,
                route_code=form.route_code.data.strip().upper(),
                route_date=form.route_date.data,
                actor_user_id=current_user.id,
            )
            flash(f"Delivery route '{route.route_code}' created successfully.", "success")
            return redirect(url_for("dispatch.route_detail", route_id=route.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating route: {str(e)}", "danger")

    return render_template("dispatch/new_route.html", form=form)

@dispatch_bp.route("/routes/<int:route_id>", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "DISPATCHER")
def route_detail(route_id):
    route = Route.query.filter_by(id=route_id, is_deleted=False).first_or_404()
    form = RouteStopForm()
    # Available undelivered shipments
    available_shipments = Shipment.query.filter(
        Shipment.shipment_status.in_(["BOOKED", "PICKED_UP", "AT_ORIGIN_HUB", "AT_DESTINATION_HUB", "DELIVERY_FAILED"]),
        Shipment.is_deleted == False,
    ).all()
    form.shipment_id.choices = [(s.id, f"{s.tracking_number} — {s.shipment_status}") for s in available_shipments]

    if form.validate_on_submit():
        try:
            DispatchService.add_route_stop(
                route_id=route.id,
                shipment_id=form.shipment_id.data,
                stop_sequence=form.stop_sequence.data,
                stop_type=form.stop_type.data,
                actor_user_id=current_user.id,
            )
            flash(f"Stop #{form.stop_sequence.data} added to route.", "success")
            return redirect(url_for("dispatch.route_detail", route_id=route.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Stop assignment failed: {str(e)}", "danger")

    return render_template("dispatch/route_detail.html", route=route, form=form)

@dispatch_bp.route("/vehicles", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "DISPATCHER")
def vehicles():
    form = VehicleForm()
    branches = Branch.query.filter_by(is_deleted=False).all()
    form.branch_id.choices = [(b.id, b.name) for b in branches]

    if form.validate_on_submit():
        v = Vehicle(
            branch_id=form.branch_id.data,
            plate_number=form.plate_number.data.strip().upper(),
            vehicle_type=form.vehicle_type.data,
            capacity_grams=form.capacity_grams.data,
            service_due_on=form.service_due_on.data,
            created_by=current_user.id,
        )
        db.session.add(v)
        db.session.commit()
        flash(f"Vehicle '{v.plate_number}' added.", "success")
        return redirect(url_for("dispatch.vehicles"))

    vehicle_list = Vehicle.query.filter_by(is_deleted=False).all()
    return render_template("dispatch/vehicles.html", form=form, vehicles=vehicle_list)

@dispatch_bp.route("/drivers", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "DISPATCHER")
def drivers():
    form = DriverForm()
    # Unlinked employees or staff
    employees = Employee.query.filter_by(is_deleted=False).all()
    form.employee_id.choices = [(e.id, f"{e.user.full_name} ({e.employee_no})") for e in employees]

    if form.validate_on_submit():
        d = Driver(
            employee_id=form.employee_id.data,
            license_number=form.license_number.data.strip().upper(),
            license_expires_on=form.license_expires_on.data,
            created_by=current_user.id,
        )
        db.session.add(d)
        db.session.commit()
        flash(f"Driver profile for '{d.employee.user.full_name}' created.", "success")
        return redirect(url_for("dispatch.drivers"))

    driver_list = Driver.query.filter_by(is_deleted=False).all()
    return render_template("dispatch/drivers.html", form=form, drivers=driver_list)
