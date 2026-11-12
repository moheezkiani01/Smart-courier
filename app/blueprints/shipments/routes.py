from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.shipments import shipments_bp
from app.security.rbac import roles_required
from app.models.shipments import Shipment, ShipmentAddress, ShipmentItem, PickupRequest, PickupAssignment, ShipmentStatusHistory
from app.models.catalog import Customer, CustomerAddress, RecipientProfile, RecipientAddress, ServiceType, ParcelCategory, PackagingType
from app.models.organization import Branch, ServiceZone, BranchZone
from app.models.dispatch import Driver, Vehicle
from app.forms.shipment_forms import ShipmentBookingForm, TransitionForm, PickupAssignForm
from app.services.shipment_service import ShipmentService
from app.services.audit_service import log_audit

@shipments_bp.route("/", methods=["GET"])
@login_required
def index():
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    query = Shipment.query.filter_by(is_deleted=False)

    # Customer, Driver & Branch scope restriction
    if current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN"):
        if hasattr(current_user, "customer") and current_user.customer:
            query = query.filter_by(customer_id=current_user.customer.id)
        else:
            query = query.filter(Shipment.id == -1)
    elif current_user.has_role("DRIVER") and not current_user.has_role("SUPER_ADMIN"):
        driver = current_user.employee.driver_profile if (hasattr(current_user, "employee") and current_user.employee and current_user.employee.driver_profile) else None
        if driver:
            from app.models.dispatch import Route, RouteStop
            route_ship_ids = [s[0] for s in db.session.query(RouteStop.shipment_id).join(Route, RouteStop.route_id == Route.id).filter(Route.driver_id == driver.id, RouteStop.is_deleted == False).all()]
            pickup_ship_ids = [p[0] for p in db.session.query(PickupRequest.shipment_id).join(PickupAssignment, PickupAssignment.pickup_request_id == PickupRequest.id).filter(PickupAssignment.driver_id == driver.id, PickupAssignment.is_deleted == False).all()]
            all_ids = set(route_ship_ids + pickup_ship_ids)
            query = query.filter(Shipment.id.in_(all_ids) if all_ids else Shipment.id == -1)
        else:
            query = query.filter(Shipment.id == -1)
    elif current_user.has_role("BRANCH_MANAGER") and not current_user.has_role("SUPER_ADMIN"):
        branch_id = current_user.employee.primary_branch_id if hasattr(current_user, "employee") and current_user.employee else None
        if branch_id:
            query = query.filter((Shipment.origin_branch_id == branch_id) | (Shipment.destination_branch_id == branch_id))

    if q:
        query = query.filter(Shipment.tracking_number.contains(q))
    if status_filter:
        query = query.filter(Shipment.shipment_status == status_filter)

    shipments_list = query.order_by(Shipment.booked_at.desc()).all()
    return render_template("shipments/index.html", shipments=shipments_list, q=q, current_status=status_filter)

@shipments_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "BOOKING_AGENT", "CUSTOMER")
def new():
    form = ShipmentBookingForm()
    customers = Customer.query.filter_by(is_deleted=False).all()
    branches = Branch.query.filter_by(is_deleted=False).all()
    services = ServiceType.query.filter_by(is_deleted=False).all()
    categories = ParcelCategory.query.filter_by(is_deleted=False).all()
    packages = PackagingType.query.filter_by(is_deleted=False).all()
    zones = ServiceZone.query.filter_by(is_deleted=False).all()

    is_customer = current_user.has_role("CUSTOMER") and not (
        current_user.has_role("SUPER_ADMIN") or current_user.has_role("BRANCH_MANAGER") or current_user.has_role("BOOKING_AGENT")
    )

    # 1. Ensure customer profile exists if logged in as customer
    if is_customer:
        if not (hasattr(current_user, "customer") and current_user.customer):
            cust = Customer(
                user_id=current_user.id,
                customer_code=f"CUST-{current_user.id:04d}",
                full_name=current_user.full_name,
                phone=current_user.phone or "+923000000000",
                email=current_user.email,
                created_by=current_user.id,
            )
            db.session.add(cust)
            db.session.commit()

        # Choices for saved addresses and recipients
        saved_addrs = [(0, "-- Enter New Sender Address --")]
        for a in current_user.customer.addresses:
            if not a.is_deleted:
                saved_addrs.append((a.id, f"{a.label}: {a.line1}, {a.city}"))
        form.use_saved_sender_address.choices = saved_addrs

        saved_recips = [(0, "-- Enter New Recipient Details --")]
        for r in current_user.customer.recipient_profiles:
            if not r.is_deleted:
                saved_recips.append((r.id, f"{r.name} ({r.phone})"))
        form.use_saved_recipient.choices = saved_recips

        form.customer_id.choices = [(current_user.customer.id, current_user.customer.full_name)]
        if request.method == "GET":
            form.customer_id.data = current_user.customer.id
            if not form.sender_name.data:
                form.sender_name.data = current_user.full_name
            if not form.sender_phone.data:
                form.sender_phone.data = current_user.phone or ""
            if current_user.customer.addresses and not form.sender_line1.data:
                first_addr = [a for a in current_user.customer.addresses if not a.is_deleted]
                if first_addr:
                    form.sender_line1.data = first_addr[0].line1
                    form.sender_city.data = first_addr[0].city
                    form.sender_zone_id.data = first_addr[0].zone_id
                    form.sender_postal.data = first_addr[0].postal_code or ""
    else:
        form.customer_id.choices = [(c.id, f"{c.full_name} ({c.customer_code})") for c in customers]
        form.use_saved_sender_address.choices = [(0, "None")]
        form.use_saved_recipient.choices = [(0, "None")]

    form.origin_branch_id.choices = [(0, "-- Auto-assign from zone --")] + [(b.id, f"{b.name} ({b.city})") for b in branches]
    form.destination_branch_id.choices = [(0, "-- Auto-assign from zone --")] + [(b.id, f"{b.name} ({b.city})") for b in branches]
    form.service_type_id.choices = [(s.id, s.name) for s in services]
    form.parcel_category_id.choices = [(c.id, c.name) for c in categories]
    form.packaging_type_id.choices = [(p.id, f"{p.name} (+{p.fee_paisa // 100} PKR)") for p in packages]
    form.sender_zone_id.choices = [(z.id, f"{z.name} ({z.city})") for z in zones]
    form.recipient_zone_id.choices = [(z.id, f"{z.name} ({z.city})") for z in zones]

    if form.validate_on_submit():
        # Enforce Customer Identity Server-Side
        if is_customer:
            target_customer_id = current_user.customer.id
        else:
            target_customer_id = form.customer_id.data
            if not target_customer_id:
                flash("Please select a customer account.", "danger")
                return render_template("shipments/new.html", form=form, is_customer=is_customer)

        # Invert or use specified branches
        origin_branch_id = form.origin_branch_id.data if form.origin_branch_id.data and form.origin_branch_id.data > 0 else None
        if not origin_branch_id:
            bz = BranchZone.query.filter_by(zone_id=form.sender_zone_id.data, is_deleted=False).first()
            origin_branch_id = bz.branch_id if bz else 1

        dest_branch_id = form.destination_branch_id.data if form.destination_branch_id.data and form.destination_branch_id.data > 0 else None
        if not dest_branch_id:
            bz = BranchZone.query.filter_by(zone_id=form.recipient_zone_id.data, is_deleted=False).first()
            dest_branch_id = bz.branch_id if bz else 1

        # Financial values (support both PKR and paisa fields)
        if form.declared_value_pkr.data:
            declared_value_paisa = int(form.declared_value_pkr.data) * 100
        else:
            declared_value_paisa = int(form.declared_value_paisa.data or 0)

        if form.cod_due_pkr.data:
            cod_due_paisa = int(form.cod_due_pkr.data) * 100
        else:
            cod_due_paisa = int(form.cod_due_paisa.data or 0)

        # Pickup options
        schedule_pickup = (form.pickup_type.data == "PICKUP") if hasattr(form, "pickup_type") and form.pickup_type.data else form.schedule_pickup.data
        time_slot = form.pickup_time_slot.data if hasattr(form, "pickup_time_slot") else ""
        raw_notes = form.pickup_notes.data.strip() if form.pickup_notes.data else ""
        pickup_notes = f"[{time_slot}] {raw_notes}".strip() if time_slot and raw_notes else (raw_notes or time_slot or None)

        sender_data = {
            "name": form.sender_name.data.strip(),
            "phone": form.sender_phone.data.strip(),
            "zone_id": form.sender_zone_id.data,
            "line1": form.sender_line1.data.strip(),
            "city": form.sender_city.data.strip(),
            "postal_code": form.sender_postal.data.strip() if form.sender_postal.data else None,
        }
        recipient_data = {
            "name": form.recipient_name.data.strip(),
            "phone": form.recipient_phone.data.strip(),
            "zone_id": form.recipient_zone_id.data,
            "line1": form.recipient_line1.data.strip(),
            "city": form.recipient_city.data.strip(),
            "postal_code": form.recipient_postal.data.strip() if form.recipient_postal.data else None,
        }
        items_data = [{
            "description": form.item_description.data.strip(),
            "quantity": form.item_quantity.data,
            "weight_grams": form.weight_grams.data,
            "declared_value_paisa": declared_value_paisa,
        }]

        # Optional: Save sender address to Address Book
        if form.save_sender_address.data and is_customer and current_user.customer:
            try:
                new_addr = CustomerAddress(
                    customer_id=current_user.customer.id,
                    zone_id=form.sender_zone_id.data,
                    label="Saved Address",
                    line1=sender_data["line1"],
                    city=sender_data["city"],
                    postal_code=sender_data["postal_code"],
                    created_by=current_user.id,
                )
                db.session.add(new_addr)
            except Exception:
                pass

        # Optional: Save recipient to Address Book
        if form.save_recipient.data and is_customer and current_user.customer:
            try:
                recip_p = RecipientProfile(
                    customer_id=current_user.customer.id,
                    name=recipient_data["name"],
                    phone=recipient_data["phone"],
                    created_by=current_user.id,
                )
                db.session.add(recip_p)
                db.session.flush()
                recip_a = RecipientAddress(
                    recipient_id=recip_p.id,
                    zone_id=form.recipient_zone_id.data,
                    line1=recipient_data["line1"],
                    city=recipient_data["city"],
                    postal_code=recipient_data["postal_code"],
                    created_by=current_user.id,
                )
                db.session.add(recip_a)
            except Exception:
                pass

        try:
            shipment = ShipmentService.book_shipment(
                customer_id=target_customer_id,
                origin_branch_id=origin_branch_id,
                destination_branch_id=dest_branch_id,
                service_type_id=form.service_type_id.data,
                parcel_category_id=form.parcel_category_id.data,
                packaging_type_id=form.packaging_type_id.data,
                sender_data=sender_data,
                recipient_data=recipient_data,
                items_data=items_data,
                actor_user_id=current_user.id,
                declared_value_paisa=declared_value_paisa,
                cod_due_paisa=cod_due_paisa,
                discount_code=form.discount_code.data.strip() if form.discount_code.data else None,
                schedule_pickup=schedule_pickup,
                pickup_notes=pickup_notes,
            )
            flash(f"Shipment booked successfully! Tracking Number: {shipment.tracking_number}", "success")
            return redirect(url_for("shipments.show", shipment_id=shipment.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Booking Error: {str(e)}", "danger")

    return render_template("shipments/new.html", form=form, is_customer=is_customer)

@shipments_bp.route("/<int:shipment_id>", methods=["GET"], endpoint="show")
@shipments_bp.route("/<int:shipment_id>", methods=["GET"], endpoint="details")
@login_required
def show(shipment_id):
    shipment = Shipment.query.filter_by(id=shipment_id, is_deleted=False).first_or_404()

    # Customer, Driver & Branch scope isolation
    if current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN"):
        if not (current_user.customer and current_user.customer.id == shipment.customer_id):
            abort(403)
    elif current_user.has_role("DRIVER") and not current_user.has_role("SUPER_ADMIN"):
        driver = current_user.employee.driver_profile if (hasattr(current_user, "employee") and current_user.employee and current_user.employee.driver_profile) else None
        if not driver:
            abort(403)
        from app.models.dispatch import Route, RouteStop
        is_assigned = (
            db.session.query(RouteStop).join(Route, RouteStop.route_id == Route.id).filter(
                RouteStop.shipment_id == shipment.id,
                Route.driver_id == driver.id,
                RouteStop.is_deleted == False
            ).first() is not None or
            db.session.query(PickupAssignment).join(PickupRequest, PickupAssignment.pickup_request_id == PickupRequest.id).filter(
                PickupRequest.shipment_id == shipment.id,
                PickupAssignment.driver_id == driver.id,
                PickupAssignment.is_deleted == False
            ).first() is not None
        )
        if not is_assigned:
            abort(403)
    elif current_user.has_role("BRANCH_MANAGER") and not current_user.has_role("SUPER_ADMIN"):
        branch_id = current_user.employee.primary_branch_id if hasattr(current_user, "employee") and current_user.employee else None
        if branch_id and shipment.origin_branch_id != branch_id and shipment.destination_branch_id != branch_id:
            abort(403)

    transition_form = TransitionForm()
    allowed_next = ShipmentService.ALLOWED_TRANSITIONS.get(shipment.shipment_status, [])
    transition_form.target_status.choices = [(s, s) for s in allowed_next]

    pickup_form = PickupAssignForm()
    drivers = Driver.query.filter_by(is_deleted=False).all()
    vehicles = Vehicle.query.filter_by(is_deleted=False).all()
    pickup_form.driver_id.choices = [(d.id, f"{d.employee.user.full_name} ({d.license_number})") for d in drivers]
    pickup_form.vehicle_id.choices = [(0, "None")] + [(v.id, f"{v.plate_number} ({v.vehicle_type})") for v in vehicles]

    return render_template(
        "shipments/show.html",
        shipment=shipment,
        transition_form=transition_form,
        pickup_form=pickup_form,
        allowed_next=allowed_next,
    )

@shipments_bp.route("/<int:shipment_id>/transition", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "HUB_OPERATOR", "DISPATCHER", "DRIVER")
def transition(shipment_id):
    shipment = Shipment.query.filter_by(id=shipment_id, is_deleted=False).first_or_404()

    # Ownership and assignment checks
    if current_user.has_role("DRIVER") and not current_user.has_role("SUPER_ADMIN"):
        driver = current_user.employee.driver_profile if (hasattr(current_user, "employee") and current_user.employee and current_user.employee.driver_profile) else None
        if not driver:
            abort(403)
        from app.models.dispatch import Route, RouteStop
        is_assigned = (
            db.session.query(RouteStop).join(Route, RouteStop.route_id == Route.id).filter(
                RouteStop.shipment_id == shipment.id,
                Route.driver_id == driver.id,
                RouteStop.is_deleted == False
            ).first() is not None or
            db.session.query(PickupAssignment).join(PickupRequest, PickupAssignment.pickup_request_id == PickupRequest.id).filter(
                PickupRequest.shipment_id == shipment.id,
                PickupAssignment.driver_id == driver.id,
                PickupAssignment.is_deleted == False
            ).first() is not None
        )
        if not is_assigned:
            abort(403)
    elif current_user.has_role("BRANCH_MANAGER") and not current_user.has_role("SUPER_ADMIN"):
        branch_id = current_user.employee.primary_branch_id if hasattr(current_user, "employee") and current_user.employee else None
        if branch_id and shipment.origin_branch_id != branch_id and shipment.destination_branch_id != branch_id:
            abort(403)

    target_status = request.form.get("target_status")
    reason = request.form.get("reason", "").strip() or None

    try:
        ShipmentService.transition(
            shipment_id=shipment.id,
            target_status=target_status,
            actor_user_id=current_user.id,
            reason=reason,
        )
        flash(f"Shipment status transitioned to {target_status}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Transition Failed: {str(e)}", "danger")

    return redirect(url_for("shipments.show", shipment_id=shipment.id))

@shipments_bp.route("/<int:shipment_id>/pickup/assign", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER", "DISPATCHER")
def assign_pickup(shipment_id):
    shipment = Shipment.query.filter_by(id=shipment_id, is_deleted=False).first_or_404()
    if not shipment.pickup_requests:
        flash("No pickup request found on this shipment.", "warning")
        return redirect(url_for("shipments.show", shipment_id=shipment.id))

    if current_user.has_role("BRANCH_MANAGER") and not current_user.has_role("SUPER_ADMIN"):
        branch_id = current_user.employee.primary_branch_id if hasattr(current_user, "employee") and current_user.employee else None
        if branch_id and shipment.origin_branch_id != branch_id:
            abort(403)

    pickup_req = shipment.pickup_requests[0]
    try:
        driver_id = int(request.form.get("driver_id", 0))
        veh_val = int(request.form.get("vehicle_id", 0))
        vehicle_id = veh_val if veh_val > 0 else None
    except (ValueError, TypeError):
        flash("Invalid assignment inputs.", "danger")
        return redirect(url_for("shipments.show", shipment_id=shipment.id))

    driver = db.session.get(Driver, driver_id)
    if not driver:
        flash("Selected driver not found.", "danger")
        return redirect(url_for("shipments.show", shipment_id=shipment.id))

    try:
        assignment = PickupAssignment(
            pickup_request_id=pickup_req.id,
            employee_id=driver.employee_id,
            driver_id=driver.id,
            vehicle_id=vehicle_id,
            assigned_at=datetime.utcnow(),
            created_by=current_user.id,
        )
        db.session.add(assignment)

        ShipmentService.transition(
            shipment_id=shipment.id,
            target_status="PICKUP_ASSIGNED",
            actor_user_id=current_user.id,
            reason=f"Pickup assigned to driver {driver.employee.user.full_name}",
        )
        flash("Pickup assigned successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error assigning pickup: {str(e)}", "danger")

    return redirect(url_for("shipments.show", shipment_id=shipment.id))

@shipments_bp.route("/<int:shipment_id>/label", methods=["GET"])
@login_required
def label(shipment_id):
    shipment = Shipment.query.filter_by(id=shipment_id, is_deleted=False).first_or_404()

    # Access scoping
    if current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN"):
        if not (current_user.customer and current_user.customer.id == shipment.customer_id):
            abort(403)
    elif current_user.has_role("DRIVER") and not current_user.has_role("SUPER_ADMIN"):
        driver = current_user.employee.driver_profile if (hasattr(current_user, "employee") and current_user.employee and current_user.employee.driver_profile) else None
        if not driver:
            abort(403)
        from app.models.dispatch import Route, RouteStop
        is_assigned = (
            db.session.query(RouteStop).join(Route, RouteStop.route_id == Route.id).filter(
                RouteStop.shipment_id == shipment.id,
                Route.driver_id == driver.id,
                RouteStop.is_deleted == False
            ).first() is not None or
            db.session.query(PickupAssignment).join(PickupRequest, PickupAssignment.pickup_request_id == PickupRequest.id).filter(
                PickupRequest.shipment_id == shipment.id,
                PickupAssignment.driver_id == driver.id,
                PickupAssignment.is_deleted == False
            ).first() is not None
        )
        if not is_assigned:
            abort(403)
    elif current_user.has_role("BRANCH_MANAGER") and not current_user.has_role("SUPER_ADMIN"):
        branch_id = current_user.employee.primary_branch_id if hasattr(current_user, "employee") and current_user.employee else None
        if branch_id and shipment.origin_branch_id != branch_id and shipment.destination_branch_id != branch_id:
            abort(403)
            abort(403)

    return render_template("shipments/label.html", shipment=shipment)
