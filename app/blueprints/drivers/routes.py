from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.drivers import drivers_bp
from app.security.rbac import roles_required
from app.models.dispatch import Driver, Route, RouteStop, DeliveryAttempt
from app.models.shipments import Shipment
from app.forms.dispatch_forms import DeliveryAttemptForm, DeliveryProofForm
from app.services.dispatch_service import DispatchService

@drivers_bp.route("/my-runs", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN", "DRIVER")
def my_runs():
    driver = None
    if hasattr(current_user, "employee") and current_user.employee and current_user.employee.driver_profile:
        driver = current_user.employee.driver_profile

    # For super admin viewing
    if not driver and current_user.has_role("SUPER_ADMIN"):
        driver = Driver.query.filter_by(is_deleted=False).first()

    if not driver:
        flash("No active driver profile associated with your user.", "warning")
        return render_template("drivers/my_runs.html", routes=[])

    routes = Route.query.filter_by(driver_id=driver.id, is_deleted=False).order_by(Route.route_date.desc()).all()
    attempt_form = DeliveryAttemptForm()
    proof_form = DeliveryProofForm()
    return render_template("drivers/my_runs.html", routes=routes, driver=driver, attempt_form=attempt_form, proof_form=proof_form)

@drivers_bp.route("/attempts", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN", "DRIVER")
def record_attempt():
    try:
        driver_id = int(request.form.get("driver_id", 0))
        shipment_id = int(request.form.get("shipment_id", 0))
        stop_id_str = request.form.get("route_stop_id")
        route_stop_id = int(stop_id_str) if stop_id_str and stop_id_str.isdigit() else None
    except (ValueError, TypeError):
        flash("Invalid request parameters for delivery attempt.", "danger")
        return redirect(url_for("drivers.my_runs"))

    if not driver_id or not shipment_id:
        flash("Driver ID and Shipment ID are required.", "danger")
        return redirect(url_for("drivers.my_runs"))

    # Verify driver ownership and shipment assignment
    if current_user.has_role("DRIVER") and not current_user.has_role("SUPER_ADMIN"):
        actual_driver = current_user.employee.driver_profile if (hasattr(current_user, "employee") and current_user.employee) else None
        if not actual_driver or actual_driver.id != driver_id:
            flash("Unauthorized: You may only record delivery attempts for your own runsheet.", "danger")
            abort(403)

        from app.models.shipments import PickupRequest, PickupAssignment
        is_assigned = (
            db.session.query(RouteStop).join(Route, RouteStop.route_id == Route.id).filter(
                RouteStop.shipment_id == shipment_id,
                Route.driver_id == actual_driver.id,
                RouteStop.is_deleted == False,
                Route.is_deleted == False,
            ).first() is not None or
            db.session.query(PickupAssignment).join(PickupRequest, PickupAssignment.pickup_request_id == PickupRequest.id).filter(
                PickupRequest.shipment_id == shipment_id,
                PickupAssignment.driver_id == actual_driver.id,
                PickupAssignment.is_deleted == False,
            ).first() is not None
        )
        if not is_assigned:
            flash("Unauthorized: This shipment is not assigned to your active runsheet.", "danger")
            abort(403)

    outcome = request.form.get("outcome")
    failure_reason = request.form.get("failure_reason", "").strip() or None

    try:
        attempt = DispatchService.record_attempt(
            shipment_id=shipment_id,
            driver_id=driver_id,
            outcome=outcome,
            actor_user_id=current_user.id,
            route_stop_id=route_stop_id,
            failure_reason=failure_reason,
        )
        flash(f"Delivery attempt '{outcome}' recorded.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error recording attempt: {str(e)}", "danger")

    return redirect(url_for("drivers.my_runs"))

@drivers_bp.route("/proofs", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN", "DRIVER")
def record_proof():
    try:
        attempt_id = int(request.form.get("attempt_id", 0))
    except (ValueError, TypeError):
        flash("Invalid attempt identifier.", "danger")
        return redirect(url_for("drivers.my_runs"))

    if not attempt_id:
        flash("Attempt ID is required.", "danger")
        return redirect(url_for("drivers.my_runs"))

    attempt = db.session.get(DeliveryAttempt, attempt_id)
    if not attempt or attempt.is_deleted:
        flash("Delivery attempt record not found.", "danger")
        return redirect(url_for("drivers.my_runs"))

    # Verify driver ownership
    if current_user.has_role("DRIVER") and not current_user.has_role("SUPER_ADMIN"):
        actual_driver = current_user.employee.driver_profile if (hasattr(current_user, "employee") and current_user.employee) else None
        if not actual_driver or actual_driver.id != attempt.driver_id:
            flash("Unauthorized: You may only confirm proof for your own delivery attempts.", "danger")
            abort(403)

    received_by = request.form.get("received_by_name", "").strip()
    if not received_by:
        flash("Receiver name is required for proof of delivery.", "danger")
        return redirect(url_for("drivers.my_runs"))

    try:
        DispatchService.record_delivery_proof(
            attempt_id=attempt_id,
            received_by_name=received_by,
            actor_user_id=current_user.id,
        )
        flash("Delivery proof confirmed and shipment marked DELIVERED!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error recording delivery proof: {str(e)}", "danger")

    return redirect(url_for("drivers.my_runs"))
