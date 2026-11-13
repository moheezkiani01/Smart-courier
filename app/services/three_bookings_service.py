"""Three Demo Bookings Service.

Provides an opt-in, idempotent workflow to seed exactly three realistic
sample courier bookings for university viva demonstration, testing, and evaluation.

Three Standard Viva Scenarios:
1. SC-DEMO-BOOK-01: Lahore -> Islamabad, Legal documents, 350g, BOOKED
   Demonstrates: Customer parcel booking form, dynamic quote engine, issued invoice,
   and public parcel tracking initialization.
2. SC-DEMO-BOOK-02: Lahore -> Karachi, Clothing parcel, 800g, IN_TRANSIT
   Demonstrates: Inter-city logistics linehaul transit, status transition history,
   operational visibility, and linked customer support inquiry.
3. SC-DEMO-BOOK-03: Lahore -> Lahore, Small electronic item, 500g, DELIVERED
   Demonstrates: Dispatch route stop, driver delivery run, electronic proof of delivery (EPOD),
   delivered tracking event, and settled invoice payment.

Safety & Governance:
- Idempotent: Subsequent runs verify existing demo bookings without duplicating.
- Dry-run mode: Preview the 3 prospective records with zero database writes.
- Clean cleanup: Explicitly confirmed cleanup removes only records created by this workflow.
- 55 Relational Tables: Strictly preserves all 55 business tables and foreign-key constraints.
"""
import os
import json
import uuid
from datetime import datetime, date, timedelta
from app.extensions import db
from app.models.auth import User, Role, UserRole
from app.models.organization import Branch, Hub, ServiceZone, Employee
from app.models.catalog import (
    Customer,
    ServiceType,
    ParcelCategory,
    PackagingType,
)
from app.models.shipments import (
    Shipment,
    ShipmentItem,
    ShipmentAddress,
    ShipmentService as ShipmentQuote,
    ShipmentStatusHistory,
    PickupRequest,
)
from app.models.dispatch import (
    Route,
    RouteStop,
    TrackingEvent,
    DeliveryAttempt,
    DeliveryProof,
    DeliveryException,
    Driver,
    Vehicle,
)
from app.models.finance import Invoice, InvoiceItem, Payment, ShipmentDiscount
from app.models.support import SupportTicket, TicketMessage, AppSetting
from app.services.shipment_service import ShipmentService
from app.services.pricing_service import PricingService
from app.utils.helpers import (
    generate_tracking_number,
    generate_invoice_number,
    generate_ticket_number,
    generate_customer_code,
)

THREE_BOOKINGS_SETTING_KEY = "THREE_DEMO_BOOKINGS_MAP"

THREE_SCENARIOS = [
    {
        "ref": "SC-DEMO-BOOK-01",
        "sender_name": "Apex Legal Chambers",
        "sender_phone": "+923001112233",
        "sender_addr": "Suite 4, Mall Road",
        "sender_city": "Lahore",
        "origin_city": "Lahore",
        "recipient_name": "High Court Registrar",
        "recipient_phone": "+923334445566",
        "recipient_addr": "Constitution Avenue, G-5",
        "recipient_city": "Islamabad",
        "dest_city": "Islamabad",
        "item_desc": "Legal documents",
        "weight_grams": 350,
        "service_code": "EXPRESS",
        "target_status": "BOOKED",
        "note": "Initial booking with dynamic quote, issued billing invoice, and public tracking.",
    },
    {
        "ref": "SC-DEMO-BOOK-02",
        "sender_name": "Sapphire Outfitters",
        "sender_phone": "+923002223344",
        "sender_addr": "Plot 12, Gulberg III",
        "sender_city": "Lahore",
        "origin_city": "Lahore",
        "recipient_name": "Zainab Market Boutique",
        "recipient_phone": "+923215556677",
        "recipient_addr": "Shop 45, Saddar Town",
        "recipient_city": "Karachi",
        "dest_city": "Karachi",
        "item_desc": "Clothing parcel",
        "weight_grams": 800,
        "service_code": "STANDARD",
        "target_status": "IN_TRANSIT",
        "note": "Inter-city linehaul transit with legal hub progression and linked customer support ticket.",
    },
    {
        "ref": "SC-DEMO-BOOK-03",
        "sender_name": "Hafeez Center Electronics",
        "sender_phone": "+923003334455",
        "sender_addr": "Main Boulevard, Gulberg",
        "sender_city": "Lahore",
        "origin_city": "Lahore",
        "recipient_name": "Gulberg Tech Lab",
        "recipient_phone": "+923456667788",
        "recipient_addr": "Block B2, MM Alam Road",
        "recipient_city": "Lahore",
        "dest_city": "Lahore",
        "item_desc": "Small electronic item",
        "weight_grams": 500,
        "service_code": "STANDARD",
        "target_status": "DELIVERED",
        "note": "Intra-city run completed with driver route stop, signed electronic delivery proof, and paid invoice.",
    },
]


def get_three_bookings():
    """Retrieve existing three demo bookings if seeded."""
    setting = AppSetting.query.filter_by(setting_key=THREE_BOOKINGS_SETTING_KEY, is_deleted=False).first()
    if not setting:
        return []
    try:
        mapping = json.loads(setting.value_json)
    except Exception:
        return []

    entries = []
    for sc in THREE_SCENARIOS:
        ref = sc["ref"]
        tn = mapping.get(ref)
        if not tn:
            continue
        shipment = Shipment.query.filter_by(tracking_number=tn, is_deleted=False).first()
        if shipment:
            invoice = Invoice.query.filter_by(shipment_id=shipment.id, is_deleted=False).first()
            route_stop = RouteStop.query.filter_by(shipment_id=shipment.id, is_deleted=False).first()
            entries.append({
                "ref": ref,
                "tracking_number": shipment.tracking_number,
                "item": sc["item_desc"],
                "weight_grams": shipment.weight_grams,
                "origin": sc["origin_city"],
                "destination": sc["dest_city"],
                "status": shipment.shipment_status,
                "total_charge_paisa": shipment.total_charge_paisa,
                "shipment_id": shipment.id,
                "invoice_id": invoice.id if invoice else None,
                "invoice_number": invoice.invoice_number if invoice else None,
                "invoice_status": invoice.invoice_status if invoice else "N/A",
                "route_code": route_stop.route.route_code if (route_stop and route_stop.route) else None,
                "note": sc["note"],
            })
    return entries


def seed_three_bookings(dry_run: bool = False, demo_email: str = "demo.merchant@smartcourier.pk"):
    """
    Idempotent seeder that creates exactly 3 realistic sample shipments
    using genuine ShipmentService and PricingService workflows.
    Returns (result_dict, created_count).
    """
    existing_entries = get_three_bookings()
    if len(existing_entries) == len(THREE_SCENARIOS):
        return {
            "status": "already_seeded",
            "message": "All 3 demo bookings already exist in this database.",
            "entries": existing_entries,
        }, 0

    if dry_run:
        simulated = []
        for s in THREE_SCENARIOS:
            simulated.append({
                "ref": s["ref"],
                "tracking_number": f"SC-SIMULATED-{s['ref']}",
                "item": s["item_desc"],
                "weight_grams": s["weight_grams"],
                "origin": s["origin_city"],
                "destination": s["dest_city"],
                "status": s["target_status"],
                "total_charge_paisa": 55000 if s["service_code"] == "EXPRESS" else 35000,
                "note": s["note"],
            })
        return {
            "status": "dry_run",
            "message": "Dry-run preview completed. No changes written to database.",
            "entries": simulated,
        }, 0

    # 1. Provision or locate dedicated demo customer user
    demo_user = User.query.filter_by(email=demo_email, is_deleted=False).first()
    cust_role = Role.query.filter_by(code="CUSTOMER").first()

    if not demo_user:
        raw_pwd = os.environ.get("DEMO_BOOKINGS_PASSWORD", f"DemoBookPass@{uuid.uuid4().hex[:6]}")
        demo_user = User(
            email=demo_email,
            full_name="Academic Demo Merchant",
            phone="+923001234567",
            status="ACTIVE",
        )
        demo_user.set_password(raw_pwd)
        db.session.add(demo_user)
        db.session.flush()

    if cust_role:
        ur = UserRole.query.filter_by(user_id=demo_user.id, role_id=cust_role.id, is_deleted=False).first()
        if not ur:
            db.session.add(UserRole(user_id=demo_user.id, role_id=cust_role.id, created_by=demo_user.id))
            db.session.flush()

    customer = Customer.query.filter_by(user_id=demo_user.id, is_deleted=False).first()
    if not customer:
        customer = Customer(
            user_id=demo_user.id,
            customer_code=generate_customer_code(),
            full_name="Academic Demo Merchant Ltd",
            phone="+923001234567",
            email=demo_email,
        )
        db.session.add(customer)
        db.session.flush()

    # 2. Locate staff & operations actors
    staff_user = User.query.join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id).filter(
        Role.code.in_(["SUPER_ADMIN", "BRANCH_MANAGER", "DISPATCHER"]),
        User.is_deleted == False,
    ).first()
    if not staff_user:
        staff_user = demo_user

    # 3. Locate catalog resources
    branches = {b.city: b for b in Branch.query.filter_by(is_deleted=False).all()}
    fallback_branch = Branch.query.filter_by(is_deleted=False).first()

    zones = {z.city: z for z in ServiceZone.query.filter_by(is_deleted=False).all()}
    fallback_zone = ServiceZone.query.filter_by(is_deleted=False).first()

    services = {s.code: s for s in ServiceType.query.filter_by(is_deleted=False).all()}
    fallback_service = ServiceType.query.filter_by(is_deleted=False).first()

    category = ParcelCategory.query.filter_by(is_deleted=False).first()
    packaging = PackagingType.query.filter_by(is_deleted=False).first()
    hub = Hub.query.filter_by(is_deleted=False).first()
    employee = Employee.query.filter_by(is_deleted=False).first()

    # Ensure driver and vehicle exist for last-mile demonstration
    driver = Driver.query.filter_by(is_deleted=False).first()
    if not driver:
        if not employee:
            employee = Employee(
                user_id=staff_user.id,
                employee_code="EMP-DEMO-01",
                job_title="Operations Specialist",
                primary_branch_id=fallback_branch.id if fallback_branch else 1,
            )
            db.session.add(employee)
            db.session.flush()
        driver = Driver(
            employee_id=employee.id,
            license_number="LIC-DEMO-2026",
            license_expires_on=date(2028, 12, 31),
        )
        db.session.add(driver)
        db.session.flush()

    vehicle = Vehicle.query.filter_by(is_deleted=False).first()
    if not vehicle and fallback_branch:
        vehicle = Vehicle(
            branch_id=fallback_branch.id,
            plate_number="LHR-DEMO-909",
            vehicle_type="Motorcycle",
            capacity_grams=35000,
        )
        db.session.add(vehicle)
        db.session.flush()

    # Driver user actor for transitions
    driver_user = driver.employee.user if (driver.employee and driver.employee.user) else staff_user

    # Mapping store
    setting = AppSetting.query.filter_by(setting_key=THREE_BOOKINGS_SETTING_KEY).first()
    mapping = {}
    if setting:
        try:
            mapping = json.loads(setting.value_json)
        except Exception:
            mapping = {}

    created_count = 0

    for sc in THREE_SCENARIOS:
        ref = sc["ref"]
        # Skip if already exists
        existing_tn = mapping.get(ref)
        if existing_tn:
            existing_shipment = Shipment.query.filter_by(tracking_number=existing_tn, is_deleted=False).first()
            if existing_shipment:
                continue

        origin_b = branches.get(sc["origin_city"], fallback_branch)
        dest_b = branches.get(sc["dest_city"], fallback_branch)
        origin_z = zones.get(sc["origin_city"], fallback_zone)
        dest_z = zones.get(sc["dest_city"], fallback_zone)
        service = services.get(sc["service_code"], fallback_service)

        postal_code_dest = "44000" if sc["dest_city"] == "Islamabad" else ("75500" if sc["dest_city"] == "Karachi" else "54000")

        # 4. Atomically book shipment through genuine ShipmentService
        shipment = ShipmentService.book_shipment(
            customer_id=customer.id,
            origin_branch_id=origin_b.id,
            destination_branch_id=dest_b.id,
            service_type_id=service.id,
            parcel_category_id=category.id if category else 1,
            packaging_type_id=packaging.id if packaging else 1,
            sender_data={
                "person_name": sc["sender_name"],
                "phone": sc["sender_phone"],
                "line1": sc["sender_addr"],
                "city": sc["origin_city"],
                "postal_code": "54000",
                "zone_id": origin_z.id,
            },
            recipient_data={
                "person_name": sc["recipient_name"],
                "phone": sc["recipient_phone"],
                "line1": sc["recipient_addr"],
                "city": sc["dest_city"],
                "postal_code": postal_code_dest,
                "zone_id": dest_z.id,
            },
            items_data=[{
                "description": f"[{ref}] {sc['item_desc']}",
                "quantity": 1,
                "weight_grams": sc["weight_grams"],
                "declared_value_paisa": 250000,
            }],
            actor_user_id=demo_user.id,
            declared_value_paisa=250000,
            cod_due_paisa=0,
        )

        tracking_num = shipment.tracking_number

        # 5. Handle workflow state transitions in legal state-machine order
        if sc["target_status"] == "BOOKED":
            # SC-DEMO-BOOK-01 remains BOOKED as per requirement
            pass

        elif sc["target_status"] == "IN_TRANSIT":
            # SC-DEMO-BOOK-02: Transition BOOKED -> AT_ORIGIN_HUB -> IN_TRANSIT
            ShipmentService.transition(
                shipment_id=shipment.id,
                target_status="AT_ORIGIN_HUB",
                actor_user_id=staff_user.id,
                hub_id=hub.id if hub else None,
                reason="Consignment received and scanned at Lahore Logistics Hub.",
            )
            ShipmentService.transition(
                shipment_id=shipment.id,
                target_status="IN_TRANSIT",
                actor_user_id=staff_user.id,
                reason=f"Dispatched via linehaul freight en route to {dest_b.city}.",
            )

            # Link a realistic customer support ticket to exercise the support section
            ticket = SupportTicket(
                ticket_number=generate_ticket_number(),
                customer_id=customer.id,
                shipment_id=shipment.id,
                assigned_employee_id=employee.id if employee else None,
                subject=f"Transit ETA inquiry for {ref} ({tracking_num})",
                priority="MEDIUM",
                ticket_status="OPEN",
                opened_at=datetime.utcnow() - timedelta(hours=2),
                created_by=demo_user.id,
            )
            db.session.add(ticket)
            db.session.flush()
            db.session.add(TicketMessage(
                ticket_id=ticket.id,
                sender_customer_id=customer.id,
                sender_user_id=demo_user.id,
                body=f"Hello, please confirm estimated delivery arrival for clothing parcel {tracking_num} at Karachi hub.",
                is_internal=False,
                posted_at=ticket.opened_at,
                created_by=demo_user.id,
            ))
            db.session.commit()

        elif sc["target_status"] == "DELIVERED":
            # SC-DEMO-BOOK-03: Transition BOOKED -> AT_ORIGIN_HUB -> IN_TRANSIT -> AT_DESTINATION_HUB
            ShipmentService.transition(
                shipment_id=shipment.id,
                target_status="AT_ORIGIN_HUB",
                actor_user_id=staff_user.id,
                hub_id=hub.id if hub else None,
                reason="Consignment received at Lahore Origin Hub.",
            )
            ShipmentService.transition(
                shipment_id=shipment.id,
                target_status="IN_TRANSIT",
                actor_user_id=staff_user.id,
                reason="Transferred to Lahore Local Distribution Depot.",
            )
            ShipmentService.transition(
                shipment_id=shipment.id,
                target_status="AT_DESTINATION_HUB",
                actor_user_id=staff_user.id,
                hub_id=hub.id if hub else None,
                reason="Arrived at Lahore Distribution Depot.",
            )

            # Dispatch assignment: Active driver route & route stop
            route = Route.query.filter_by(driver_id=driver.id, is_deleted=False).first()
            if not route:
                route = Route(
                    branch_id=dest_b.id,
                    driver_id=driver.id,
                    vehicle_id=vehicle.id if vehicle else 1,
                    route_code="ROUTE-DEMO-LHR-01",
                    route_date=date.today(),
                    route_status="IN_PROGRESS",
                    created_by=staff_user.id,
                )
                db.session.add(route)
                db.session.flush()

            # Sequence stop
            existing_stop = RouteStop.query.filter_by(route_id=route.id, shipment_id=shipment.id, is_deleted=False).first()
            if not existing_stop:
                seq = (db.session.query(db.func.max(RouteStop.stop_sequence)).filter_by(route_id=route.id).scalar() or 0) + 1
                stop = RouteStop(
                    route_id=route.id,
                    shipment_id=shipment.id,
                    stop_sequence=seq,
                    stop_type="DELIVERY",
                    created_by=staff_user.id,
                )
                db.session.add(stop)
                db.session.flush()
            else:
                stop = existing_stop

            # Transition to OUT_FOR_DELIVERY
            ShipmentService.transition(
                shipment_id=shipment.id,
                target_status="OUT_FOR_DELIVERY",
                actor_user_id=driver_user.id,
                reason="Out for delivery on rider runsheet.",
            )

            # Delivery attempt (SUCCESS) and Electronic Proof of Delivery
            attempt = DeliveryAttempt(
                shipment_id=shipment.id,
                route_stop_id=stop.id,
                driver_id=driver.id,
                attempted_at=datetime.utcnow() - timedelta(minutes=30),
                outcome="SUCCESS",
                created_by=driver_user.id,
            )
            db.session.add(attempt)
            db.session.flush()

            proof = DeliveryProof(
                shipment_id=shipment.id,
                delivery_attempt_id=attempt.id,
                received_by_name=sc["recipient_name"],
                delivered_at=attempt.attempted_at,
                signed_filename="PROOF-EPOD-E-SIGNED-VERIFIED",
                created_by=driver_user.id,
            )
            db.session.add(proof)
            db.session.flush()

            # Transition to DELIVERED
            ShipmentService.transition(
                shipment_id=shipment.id,
                target_status="DELIVERED",
                actor_user_id=driver_user.id,
                reason=f"Consignment delivered successfully. Handed to {sc['recipient_name']}.",
            )

            # Mark billing invoice paid and record settled payment
            invoice = Invoice.query.filter_by(shipment_id=shipment.id, is_deleted=False).first()
            if invoice:
                invoice.invoice_status = "PAID"
                payment = Payment(
                    invoice_id=invoice.id,
                    received_by_employee_id=employee.id if employee else None,
                    amount_paisa=invoice.total_paisa,
                    method="BANK_TRANSFER",
                    reference_code=f"PAY-{tracking_num}",
                    payment_status="SETTLED",
                    paid_at=attempt.attempted_at,
                    created_by=staff_user.id,
                )
                db.session.add(payment)
                db.session.commit()

        mapping[ref] = tracking_num
        created_count += 1

    # Save mapping in AppSetting
    if not setting:
        setting = AppSetting(
            setting_key=THREE_BOOKINGS_SETTING_KEY,
            value_json=json.dumps(mapping, indent=2),
            description="Reference mapping for the three academic viva demo bookings",
        )
        db.session.add(setting)
    else:
        setting.value_json = json.dumps(mapping, indent=2)
        setting.updated_at = datetime.utcnow()

    db.session.commit()

    return {
        "status": "success",
        "message": f"Successfully seeded {created_count} demo bookings.",
        "entries": get_three_bookings(),
    }, created_count


def cleanup_three_bookings(confirm: bool = False):
    """
    Scoped cleanup that deletes ONLY the three demo bookings created by this service,
    preserving non-demo shipments, customers, audit logs, and database schema integrity.
    """
    if not confirm:
        return {
            "status": "confirmation_required",
            "message": "Explicit confirmation (--confirm) is required to delete demo bookings.",
            "deleted_count": 0,
        }

    setting = AppSetting.query.filter_by(setting_key=THREE_BOOKINGS_SETTING_KEY).first()
    if not setting:
        return {
            "status": "not_found",
            "message": "No demo bookings are currently registered.",
            "deleted_count": 0,
        }

    try:
        mapping = json.loads(setting.value_json)
    except Exception:
        mapping = {}

    deleted_count = 0
    for ref, tn in mapping.items():
        shipment = Shipment.query.filter_by(tracking_number=tn).first()
        if not shipment:
            continue

        sid = shipment.id

        # 1. Support tickets and messages
        tickets = SupportTicket.query.filter_by(shipment_id=sid).all()
        for t in tickets:
            TicketMessage.query.filter_by(ticket_id=t.id).delete(synchronize_session=False)
            db.session.delete(t)

        # 2. Payments, invoice items, invoices
        invoices = Invoice.query.filter_by(shipment_id=sid).all()
        for inv in invoices:
            Payment.query.filter_by(invoice_id=inv.id).delete(synchronize_session=False)
            InvoiceItem.query.filter_by(invoice_id=inv.id).delete(synchronize_session=False)
            db.session.delete(inv)

        # 3. Delivery proofs, exceptions, attempts
        proofs = DeliveryProof.query.filter_by(shipment_id=sid).all()
        for p in proofs:
            db.session.delete(p)

        exceptions = DeliveryException.query.filter_by(shipment_id=sid).all()
        for exc in exceptions:
            db.session.delete(exc)

        attempts = DeliveryAttempt.query.filter_by(shipment_id=sid).all()
        for att in attempts:
            db.session.delete(att)

        # 4. Route stops
        RouteStop.query.filter_by(shipment_id=sid).delete(synchronize_session=False)

        # 5. Tracking events
        TrackingEvent.query.filter_by(shipment_id=sid).delete(synchronize_session=False)

        # 6. Status history
        ShipmentStatusHistory.query.filter_by(shipment_id=sid).delete(synchronize_session=False)

        # 7. Quotes & discounts
        ShipmentDiscount.query.filter_by(shipment_id=sid).delete(synchronize_session=False)
        ShipmentQuote.query.filter_by(shipment_id=sid).delete(synchronize_session=False)

        # 8. Items, addresses, pickup requests
        PickupRequest.query.filter_by(shipment_id=sid).delete(synchronize_session=False)
        ShipmentItem.query.filter_by(shipment_id=sid).delete(synchronize_session=False)
        ShipmentAddress.query.filter_by(shipment_id=sid).delete(synchronize_session=False)

        # 9. Shipment itself
        db.session.delete(shipment)
        deleted_count += 1

    # Remove the setting marker
    db.session.delete(setting)
    db.session.commit()

    return {
        "status": "success",
        "message": f"Successfully deleted {deleted_count} demo bookings and their associated operational records.",
        "deleted_count": deleted_count,
    }
