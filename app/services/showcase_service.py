"""Academic Showcase / Demo Dataset Service.

Provides a dedicated, safe, opt-in workflow to seed five clearly labeled
sample courier entries for university viva demonstrations and testing.

Illustrative Scenarios:
1. DEMO-DOC-01: Lahore -> Islamabad, Legal documents, 350g (BOOKED)
2. DEMO-CLOTH-02: Lahore -> Karachi, Clothing parcel, 800g (IN_TRANSIT)
3. DEMO-ELEC-03: Lahore -> Lahore, Small electronic item, 500g (OUT_FOR_DELIVERY)
4. DEMO-SHOE-04: Karachi -> Lahore, Shoes, 900g (DELIVERED)
5. DEMO-GLASS-05: Islamabad -> Lahore, Fragile household item, 700g (DELIVERY_FAILED)

Safety & Governance:
- Disabled by default in production. Requires explicit ALLOW_SHOWCASE_SEED=true or --confirm flag.
- Idempotent: Rerunning retrieves existing demo records without duplicating.
- Uses real rate cards calculated by PricingService, never hardcoded fake revenue.
- Generates valid unique tracking codes using generate_tracking_number().
- Preserves all 55 relational tables without schema changes; stores label mapping in AppSetting.
"""
import os
import json
import uuid
from datetime import datetime, timedelta
from app.extensions import db
from app.models.auth import User, Role, UserRole
from app.models.organization import Branch, Hub, ServiceZone, Employee
from app.models.catalog import (
    Customer,
    CustomerContact,
    CustomerAddress,
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
from app.models.finance import Invoice, Payment
from app.models.support import SupportTicket, TicketMessage, AppSetting
from app.services.pricing_service import PricingService
from app.utils.helpers import (
    generate_tracking_number,
    generate_invoice_number,
    generate_ticket_number,
    generate_customer_code,
)

SHOWCASE_SETTING_KEY = "SHOWCASE_DEMO_TRACKING_MAP"

SCENARIOS = [
    {
        "ref": "DEMO-DOC-01",
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
        "note": "Initial booking with active invoice and public tracking initialized.",
    },
    {
        "ref": "DEMO-CLOTH-02",
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
        "note": "Sorted at Lahore origin hub and dispatched on transit linehaul.",
    },
    {
        "ref": "DEMO-ELEC-03",
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
        "target_status": "OUT_FOR_DELIVERY",
        "note": "Loaded onto courier delivery runsheet with assigned driver route stop.",
    },
    {
        "ref": "DEMO-SHOE-04",
        "sender_name": "Metro Leather Works",
        "sender_phone": "+923217778899",
        "sender_addr": "Tariq Road Industrial Area",
        "sender_city": "Karachi",
        "origin_city": "Karachi",
        "recipient_name": "DHA Retail Boutique",
        "recipient_phone": "+923008889900",
        "recipient_addr": "Sector Y, Phase 3 DHA",
        "recipient_city": "Lahore",
        "dest_city": "Lahore",
        "item_desc": "Shoes",
        "weight_grams": 900,
        "service_code": "STANDARD",
        "target_status": "DELIVERED",
        "note": "Successful delivery verified with recipient electronic delivery proof.",
    },
    {
        "ref": "DEMO-GLASS-05",
        "sender_name": "Federal Crafts Center",
        "sender_phone": "+923339990011",
        "sender_addr": "Blue Area Business Center",
        "sender_city": "Islamabad",
        "origin_city": "Islamabad",
        "recipient_name": "Mall of Lahore Gallery",
        "recipient_phone": "+923001239876",
        "recipient_addr": "Park Towers, Cantt",
        "recipient_city": "Lahore",
        "dest_city": "Lahore",
        "item_desc": "Fragile household item",
        "weight_grams": 700,
        "service_code": "EXPRESS",
        "target_status": "DELIVERY_FAILED",
        "note": "Failed delivery attempt recorded with active support ticket for investigation.",
    },
]


def get_showcase_entries():
    """Retrieve existing showcase demo entries if seeded."""
    setting = AppSetting.query.filter_by(setting_key=SHOWCASE_SETTING_KEY, is_deleted=False).first()
    if not setting:
        return []
    try:
        mapping = json.loads(setting.value_json)
    except Exception:
        return []

    entries = []
    for scenario in SCENARIOS:
        ref = scenario["ref"]
        tn = mapping.get(ref)
        if not tn:
            continue
        shipment = Shipment.query.filter_by(tracking_number=tn, is_deleted=False).first()
        if shipment:
            entries.append({
                "ref": ref,
                "tracking_number": shipment.tracking_number,
                "item": scenario["item_desc"],
                "weight_grams": shipment.weight_grams,
                "origin": scenario["origin_city"],
                "destination": scenario["dest_city"],
                "status": shipment.shipment_status,
                "total_charge_paisa": shipment.total_charge_paisa,
                "shipment_id": shipment.id,
                "note": scenario["note"],
            })
    return entries


def seed_showcase(dry_run: bool = False, demo_email: str = "demo.merchant@smartcourier.pk"):
    """
    Idempotent showcase seeder that creates 5 realistic sample shipments.
    Returns (status_dict, created_count).
    """
    existing_entries = get_showcase_entries()
    if len(existing_entries) == len(SCENARIOS):
        return {
            "status": "already_seeded",
            "message": "All 5 showcase demo entries already exist.",
            "entries": existing_entries,
        }, 0

    if dry_run:
        simulated = []
        for s in SCENARIOS:
            simulated.append({
                "ref": s["ref"],
                "tracking_number": f"SC-SIMULATED-{s['ref']}",
                "item": s["item_desc"],
                "weight_grams": s["weight_grams"],
                "origin": s["origin_city"],
                "destination": s["dest_city"],
                "status": s["target_status"],
                "note": s["note"],
            })
        return {
            "status": "dry_run",
            "message": "Dry-run preview completed. No changes written to database.",
            "entries": simulated,
        }, 0

    # 1. Lookup or create showcase demo user & customer
    demo_user = User.query.filter_by(email=demo_email, is_deleted=False).first()
    cust_role = Role.query.filter_by(code="CUSTOMER").first()

    if not demo_user:
        raw_pwd = os.environ.get("SHOWCASE_DEMO_PASSWORD", f"ShowcaseDemoPass@{uuid.uuid4().hex[:6]}")
        demo_user = User(
            email=demo_email,
            full_name="Academic Showcase Merchant",
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
            full_name="Apex Academic Showcase Ltd",
            phone="+923001234567",
            email=demo_email,
        )
        db.session.add(customer)
        db.session.flush()

    # 2. Lookup catalog resources
    branches = {b.city: b for b in Branch.query.filter_by(is_deleted=False).all()}
    fallback_branch = Branch.query.filter_by(is_deleted=False).first()

    zones = {z.city: z for z in ServiceZone.query.filter_by(is_deleted=False).all()}
    fallback_zone = ServiceZone.query.filter_by(is_deleted=False).first()

    services = {s.code: s for s in ServiceType.query.filter_by(is_deleted=False).all()}
    fallback_service = ServiceType.query.filter_by(is_deleted=False).first()

    category = ParcelCategory.query.filter_by(is_deleted=False).first()
    packaging = PackagingType.query.filter_by(is_deleted=False).first()
    driver = Driver.query.filter_by(is_deleted=False).first()
    hub = Hub.query.filter_by(is_deleted=False).first()
    employee = Employee.query.filter_by(is_deleted=False).first()

    # App setting lookup mapping
    setting = AppSetting.query.filter_by(setting_key=SHOWCASE_SETTING_KEY).first()
    mapping = {}
    if setting:
        try:
            mapping = json.loads(setting.value_json)
        except Exception:
            mapping = {}

    created_count = 0
    now = datetime.utcnow()

    for idx, sc in enumerate(SCENARIOS):
        ref = sc["ref"]
        # If already exists for this ref, skip
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

        # Calculate genuine rate quote via PricingService
        quote = PricingService.calculate_quote(
            service_type_id=service.id,
            origin_zone_id=origin_z.id,
            destination_zone_id=dest_z.id,
            weight_grams=sc["weight_grams"],
            packaging_type_id=packaging.id if packaging else None,
        )

        tracking_num = generate_tracking_number()

        # Create Shipment
        shipment = Shipment(
            tracking_number=tracking_num,
            customer_id=customer.id,
            origin_branch_id=origin_b.id,
            destination_branch_id=dest_b.id,
            service_type_id=service.id,
            parcel_category_id=category.id if category else 1,
            packaging_type_id=packaging.id if packaging else 1,
            booking_employee_id=employee.id if employee else None,
            current_hub_id=hub.id if hub else None,
            weight_grams=sc["weight_grams"],
            declared_value_paisa=500000,
            cod_due_paisa=0,
            booked_at=now - timedelta(days=idx + 1),
            shipment_status=sc["target_status"],
            total_charge_paisa=quote["total_paisa"],
        )
        db.session.add(shipment)
        db.session.flush()

        # Item
        db.session.add(ShipmentItem(
            shipment_id=shipment.id,
            description=f"[{ref}] {sc['item_desc']}",
            quantity=1,
            weight_grams=sc["weight_grams"],
            declared_value_paisa=500000,
        ))

        # Addresses
        db.session.add(ShipmentAddress(
            shipment_id=shipment.id,
            address_role="SENDER",
            person_name=sc["sender_name"],
            phone=sc["sender_phone"],
            line1=sc["sender_addr"],
            city=sc["sender_city"],
            postal_code="54000",
            zone_id=origin_z.id,
        ))
        db.session.add(ShipmentAddress(
            shipment_id=shipment.id,
            address_role="RECIPIENT",
            person_name=sc["recipient_name"],
            phone=sc["recipient_phone"],
            line1=sc["recipient_addr"],
            city=sc["recipient_city"],
            postal_code="75500",
            zone_id=dest_z.id,
        ))

        # Frozen Quote breakdown
        db.session.add(ShipmentQuote(
            shipment_id=shipment.id,
            service_type_id=service.id,
            quoted_rate_card_id=quote["rate_card_id"],
            quoted_rule_id=quote["rule_id"],
            base_fee_paisa=quote["base_fee_paisa"],
            packaging_fee_paisa=quote["packaging_fee_paisa"],
            discount_paisa=quote["discount_paisa"],
            tax_paisa=quote["tax_paisa"],
            total_paisa=quote["total_paisa"],
            currency=quote.get("currency", "PKR"),
        ))

        # Invoice
        inv = Invoice(
            shipment_id=shipment.id,
            customer_id=customer.id,
            invoice_number=generate_invoice_number(),
            subtotal_paisa=quote["base_fee_paisa"],
            tax_paisa=quote["tax_paisa"],
            total_paisa=quote["total_paisa"],
            invoice_status="PAID" if sc["target_status"] == "DELIVERED" else "ISSUED",
            issued_at=shipment.booked_at,
            due_at=shipment.booked_at + timedelta(days=7),
        )
        db.session.add(inv)
        db.session.flush()

        if sc["target_status"] == "DELIVERED":
            db.session.add(Payment(
                invoice_id=inv.id,
                received_by_employee_id=employee.id if employee else None,
                amount_paisa=quote["total_paisa"],
                method="BANK_TRANSFER",
                reference_code=f"PAY-{tracking_num}",
                payment_status="SETTLED",
                paid_at=shipment.booked_at + timedelta(hours=16),
            ))

        # Tracking events sequence
        t_base = shipment.booked_at
        db.session.add(TrackingEvent(
            shipment_id=shipment.id,
            event_code="BOOKED",
            public_message=f"Consignment booked at {origin_b.name}.",
            occurred_at=t_base,
        ))

        if sc["target_status"] in ["IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED", "DELIVERY_FAILED"]:
            db.session.add(TrackingEvent(
                shipment_id=shipment.id,
                event_code="AT_ORIGIN_HUB",
                public_message="Processed through origin sorting hub scanning station.",
                occurred_at=t_base + timedelta(hours=3),
            ))
            db.session.add(TrackingEvent(
                shipment_id=shipment.id,
                event_code="IN_TRANSIT",
                public_message=f"Departed on linehaul transit to {dest_b.city}.",
                occurred_at=t_base + timedelta(hours=6),
            ))

        if sc["target_status"] in ["OUT_FOR_DELIVERY", "DELIVERED", "DELIVERY_FAILED"]:
            # Route and Stop assignment
            active_route = Route.query.filter_by(driver_id=driver.id, is_deleted=False).first() if driver else None
            if not active_route and driver:
                veh = Vehicle.query.filter_by(is_deleted=False).first()
                active_route = Route(
                    route_code=f"RT-SHOWCASE-{idx+1}",
                    branch_id=dest_b.id,
                    driver_id=driver.id,
                    vehicle_id=veh.id if veh else None,
                    route_type="DELIVERY",
                    route_status="IN_PROGRESS",
                    route_date=datetime.utcnow().date(),
                )
                db.session.add(active_route)
                db.session.flush()

            if active_route:
                db.session.add(RouteStop(
                    route_id=active_route.id,
                    shipment_id=shipment.id,
                    stop_sequence=idx + 1,
                    stop_type="DELIVERY",
                ))

            db.session.add(TrackingEvent(
                shipment_id=shipment.id,
                event_code="OUT_FOR_DELIVERY",
                public_message="Out for delivery with designated courier dispatch rider.",
                occurred_at=t_base + timedelta(hours=14),
            ))

        if sc["target_status"] == "DELIVERED":
            attempt = DeliveryAttempt(
                shipment_id=shipment.id,
                driver_id=driver.id if driver else None,
                attempted_at=t_base + timedelta(hours=16),
                outcome="SUCCESS",
            )
            db.session.add(attempt)
            db.session.flush()

            db.session.add(DeliveryProof(
                shipment_id=shipment.id,
                delivery_attempt_id=attempt.id,
                received_by_name=sc["recipient_name"],
                delivered_at=attempt.attempted_at,
            ))
            db.session.add(TrackingEvent(
                shipment_id=shipment.id,
                event_code="DELIVERED",
                public_message=f"Delivered successfully. Received by {sc['recipient_name']}.",
                occurred_at=attempt.attempted_at,
            ))

        if sc["target_status"] == "DELIVERY_FAILED":
            attempt = DeliveryAttempt(
                shipment_id=shipment.id,
                driver_id=driver.id if driver else None,
                attempted_at=t_base + timedelta(hours=16),
                outcome="FAILED",
                failure_reason="Customer unavailable / Premises locked upon arrival",
            )
            db.session.add(attempt)
            db.session.flush()

            db.session.add(DeliveryException(
                shipment_id=shipment.id,
                delivery_attempt_id=attempt.id,
                exception_code="UNAVAILABLE",
                explanation="Delivery rider arrived at location; recipient did not answer call.",
            ))
            db.session.add(TrackingEvent(
                shipment_id=shipment.id,
                event_code="DELIVERY_FAILED",
                public_message="Delivery attempt unsuccessful: Recipient unavailable.",
                occurred_at=attempt.attempted_at,
            ))

            # Linked support ticket
            ticket = SupportTicket(
                ticket_number=generate_ticket_number(),
                customer_id=customer.id,
                shipment_id=shipment.id,
                assigned_employee_id=employee.id if employee else None,
                subject=f"Delivery exception investigation: {ref}",
                priority="HIGH",
                ticket_status="OPEN",
                opened_at=attempt.attempted_at,
            )
            db.session.add(ticket)
            db.session.flush()
            db.session.add(TicketMessage(
                ticket_id=ticket.id,
                sender_employee_id=employee.id if employee else None,
                body=f"Automated alert: delivery attempt for {ref} ({tracking_num}) failed due to unavailable recipient.",
                is_internal=True,
                posted_at=attempt.attempted_at,
            ))

        mapping[ref] = tracking_num
        created_count += 1

    # Update or create AppSetting marker
    if not setting:
        setting = AppSetting(
            setting_key=SHOWCASE_SETTING_KEY,
            value_json=json.dumps(mapping, indent=2),
            description="Mapping of academic showcase demo labels to generated tracking numbers",
        )
        db.session.add(setting)
    else:
        setting.value_json = json.dumps(mapping, indent=2)
        setting.updated_at = datetime.utcnow()

    db.session.commit()
    return {
        "status": "success",
        "message": f"Successfully seeded {created_count} showcase demo entries.",
        "entries": get_showcase_entries(),
    }, created_count
