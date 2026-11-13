from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.hubs import hubs_bp
from app.security.rbac import roles_required
from app.models.dispatch import ShipmentScan, HubTransfer
from app.models.organization import Hub
from app.models.shipments import Shipment
from app.forms.dispatch_forms import HubScanForm, HubTransferForm
from app.services.hub_service import HubService

@hubs_bp.route("/scans", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "HUB_OPERATOR", "DISPATCHER")
def scans():
    """Retired optional endpoint.

    Hub scan operations are consolidated into parcel tracking and status progression.
    Authorized staff are gracefully redirected to the active shipments module with an informative alert.
    """
    if request.method == "POST":
        flash("Direct barcode scan submission is retired. Use shipment workflows or transfers.", "warning")
        return redirect(url_for("shipments.index")), 303

    flash("Hub Scans has been consolidated into parcel tracking & dispatch.", "info")
    return redirect(url_for("shipments.index"))

@hubs_bp.route("/transfers", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "HUB_OPERATOR", "DISPATCHER")
def transfers():
    form = HubTransferForm()
    eligible_shipments = Shipment.query.filter(
        Shipment.shipment_status.in_(["AT_ORIGIN_HUB", "AT_DESTINATION_HUB"]),
        Shipment.is_deleted == False
    ).order_by(Shipment.booked_at.desc()).all()
    hubs = Hub.query.filter_by(is_deleted=False).all()
    if eligible_shipments:
        form.shipment_id.choices = [(s.id, f"{s.tracking_number} ({s.shipment_status})") for s in eligible_shipments]
    else:
        form.shipment_id.choices = [(0, "No parcels currently awaiting freight transfer")]
    form.from_hub_id.choices = [(h.id, f"{h.name} ({h.branch.name})") for h in hubs]
    form.to_hub_id.choices = [(h.id, f"{h.name} ({h.branch.name})") for h in hubs]

    if form.validate_on_submit():
        if form.shipment_id.data == 0:
            flash("No eligible parcel selected for transfer.", "warning")
            return redirect(url_for("hubs.transfers"))
        emp_id = current_user.employee.id if hasattr(current_user, "employee") and current_user.employee else None
        try:
            HubService.initiate_transfer(
                shipment_id=form.shipment_id.data,
                from_hub_id=form.from_hub_id.data,
                to_hub_id=form.to_hub_id.data,
                employee_id=emp_id,
                actor_user_id=current_user.id,
            )
            flash("Hub transfer initiated and freight dispatched.", "success")
            return redirect(url_for("hubs.transfers"))
        except Exception as e:
            db.session.rollback()
            flash(f"Transfer error: {str(e)}", "danger")

    recent_transfers = HubTransfer.query.order_by(HubTransfer.departed_at.desc()).limit(30).all()
    return render_template("hubs/transfers.html", form=form, transfers=recent_transfers)

@hubs_bp.route("/transfers/<int:transfer_id>/receive", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "HUB_OPERATOR")
def receive_transfer(transfer_id):
    emp_id = current_user.employee.id if hasattr(current_user, "employee") and current_user.employee else None
    try:
        HubService.receive_transfer(
            transfer_id=transfer_id,
            employee_id=emp_id,
            actor_user_id=current_user.id,
        )
        flash("Hub transfer received and logged.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error receiving transfer: {str(e)}", "danger")
    return redirect(url_for("hubs.transfers"))
