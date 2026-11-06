from flask import render_template, request, redirect, url_for, flash
from app.blueprints.tracking import tracking_bp
from app.models.shipments import Shipment
from app.models.dispatch import TrackingEvent

@tracking_bp.route("/search", methods=["GET"])
def search():
    code = request.args.get("tracking_number", "").strip().upper()
    if not code:
        flash("Please enter a valid tracking number.", "warning")
        return redirect(url_for("main.index"))
    return redirect(url_for("tracking.view", tracking_number=code))

@tracking_bp.route("/<tracking_number>", methods=["GET"])
def view(tracking_number):
    clean_code = tracking_number.strip().upper()
    shipment = Shipment.query.filter_by(tracking_number=clean_code, is_deleted=False).first()
    if not shipment:
        return render_template("tracking/not_found.html", tracking_number=clean_code), 404

    # Public visible timeline only (security rule: never expose recipient phone or payment detail)
    events = TrackingEvent.query.filter_by(
        shipment_id=shipment.id,
        visible_to_customer=True,
        is_deleted=False
    ).order_by(TrackingEvent.occurred_at.asc()).all()

    return render_template("tracking/view.html", shipment=shipment, events=events)
