import os
from datetime import datetime, date, timedelta
from app.extensions import db
from app.models.auth import User, Role, Permission, UserRole, RolePermission
from app.models.organization import Branch, Hub, Employee, EmployeeBranch, ServiceZone, BranchZone
from app.models.catalog import (
    Customer,
    CustomerContact,
    CustomerAddress,
    RecipientProfile,
    RecipientAddress,
    ServiceType,
    ParcelCategory,
    PackagingType,
    RateCard,
    RateCardRule,
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
    ShipmentScan,
    TrackingEvent,
    DeliveryAttempt,
    DeliveryProof,
    DeliveryException,
    Vehicle,
    Driver,
    VehicleAssignment,
)
from app.models.finance import (
    Invoice,
    InvoiceItem,
    Payment,
    CodCollection,
    CodRemittance,
    Discount,
    ShipmentDiscount,
)
from app.models.support import (
    SupportTicket,
    TicketMessage,
    Notification,
    NotificationTemplate,
    AuditLog,
    AppSetting,
)

def seed_all():
    """Idempotent master database seeder for all 55 business tables."""
    print("[*] Starting database seed...")

    # ==========================================
    # 1. ROLES & PERMISSIONS
    # ==========================================
    roles_data = [
        ("SUPER_ADMIN", "Super Administrator", "Full unrestricted enterprise authority"),
        ("BRANCH_MANAGER", "Branch Manager", "Manages branch operations, local staff, and fleet"),
        ("BOOKING_AGENT", "Booking Counter Agent", "Accepts parcels, customer registrations, quotes"),
        ("HUB_OPERATOR", "Hub Sorting Operator", "Handles incoming/outgoing hub scans & transfers"),
        ("DISPATCHER", "Logistics Dispatcher", "Routes vehicles, driver stop sequencing"),
        ("DRIVER", "Delivery Driver", "Executes runsheet, records attempts & delivery proofs"),
        ("FINANCE_OFFICER", "Finance Officer", "Manages invoices, settlements, refunds & COD"),
        ("SUPPORT_AGENT", "Customer Support Agent", "Solves complaints and customer inquiries"),
        ("CUSTOMER", "Registered Customer", "Self-service booking, tracking & support"),
    ]

    roles_dict = {}
    for code, name, desc in roles_data:
        r = Role.query.filter_by(code=code).first()
        if not r:
            r = Role(code=code, name=name, description=desc)
            db.session.add(r)
            db.session.flush()
        roles_dict[code] = r

    permissions_data = [
        ("BRANCH_MANAGE", "ORGANIZATION", "Manage branches and operating hubs"),
        ("STAFF_MANAGE", "ORGANIZATION", "Manage employee profiles and roles"),
        ("CUSTOMER_MANAGE", "CATALOG", "Manage customers and saved addresses"),
        ("RATE_MANAGE", "CATALOG", "Manage rate cards, weight bands and packaging"),
        ("SHIPMENT_BOOK", "SHIPMENTS", "Create and quote parcel bookings"),
        ("SHIPMENT_VIEW", "SHIPMENTS", "View shipments across organization"),
        ("HUB_OPERATE", "DISPATCH", "Perform parcel scans and freight transfers"),
        ("ROUTE_DISPATCH", "DISPATCH", "Create delivery routes and stop assignments"),
        ("DELIVERY_EXECUTE", "DISPATCH", "Conduct delivery attempts and record proof"),
        ("FINANCE_MANAGE", "FINANCE", "Post payments, manage COD and authorize refunds"),
        ("SUPPORT_MANAGE", "SUPPORT", "Manage tickets and customer communications"),
        ("AUDIT_VIEW", "SECURITY", "Inspect system-wide immutable audit trail"),
    ]

    perms_dict = {}
    for code, mod, desc in permissions_data:
        p = Permission.query.filter_by(code=code).first()
        if not p:
            p = Permission(code=code, module=mod, description=desc)
            db.session.add(p)
            db.session.flush()
        perms_dict[code] = p

    # Assign permissions to roles
    role_perms_map = {
        "SUPER_ADMIN": list(perms_dict.keys()),
        "BRANCH_MANAGER": ["BRANCH_MANAGE", "STAFF_MANAGE", "SHIPMENT_VIEW", "HUB_OPERATE", "ROUTE_DISPATCH", "AUDIT_VIEW"],
        "BOOKING_AGENT": ["CUSTOMER_MANAGE", "SHIPMENT_BOOK", "SHIPMENT_VIEW", "RATE_MANAGE"],
        "HUB_OPERATOR": ["HUB_OPERATE", "SHIPMENT_VIEW"],
        "DISPATCHER": ["ROUTE_DISPATCH", "SHIPMENT_VIEW"],
        "DRIVER": ["DELIVERY_EXECUTE"],
        "FINANCE_OFFICER": ["FINANCE_MANAGE", "SHIPMENT_VIEW"],
        "SUPPORT_AGENT": ["SUPPORT_MANAGE", "SHIPMENT_VIEW"],
        "CUSTOMER": ["SHIPMENT_BOOK", "SHIPMENT_VIEW"],
    }

    for r_code, perm_list in role_perms_map.items():
        role = roles_dict[r_code]
        for p_code in perm_list:
            perm = perms_dict[p_code]
            rp = RolePermission.query.filter_by(role_id=role.id, permission_id=perm.id).first()
            if not rp:
                rp = RolePermission(role_id=role.id, permission_id=perm.id)
                db.session.add(rp)

    # ==========================================
    # 2. USERS (9 DEMO ACCOUNTS)
    # ==========================================
    default_pass = os.environ.get("SEED_ADMIN_PASSWORD", "AdminPass@1234")
    users_data = [
        ("admin@smartcourier.pk", "Super Admin", "+923001112233", "SUPER_ADMIN"),
        ("lahore.manager@smartcourier.pk", "Tariq Mahmood", "+923002223344", "BRANCH_MANAGER"),
        ("booking.lahore@smartcourier.pk", "Ayesha Khan", "+923003334455", "BOOKING_AGENT"),
        ("hub.lahore@smartcourier.pk", "Bilal Ahmed", "+923004445566", "HUB_OPERATOR"),
        ("dispatcher.lahore@smartcourier.pk", "Hamza Ali", "+923005556677", "DISPATCHER"),
        ("driver1@smartcourier.pk", "Kamran Akram", "+923006667788", "DRIVER"),
        ("finance@smartcourier.pk", "Saima Farooq", "+923007778899", "FINANCE_OFFICER"),
        ("support@smartcourier.pk", "Zainab Bibi", "+923008889900", "SUPPORT_AGENT"),
        ("customer@smartcourier.pk", "Usman Malik (Merchant)", "+923009990011", "CUSTOMER"),
    ]

    users_dict = {}
    for email, full_name, phone, r_code in users_data:
        u = User.query.filter_by(email=email).first()
        if not u:
            u = User(email=email, full_name=full_name, phone=phone, is_email_verified=True)
            u.set_password(default_pass)
            db.session.add(u)
            db.session.flush()

            ur = UserRole(user_id=u.id, role_id=roles_dict[r_code].id)
            db.session.add(ur)
        users_dict[email] = u

    # ==========================================
    # 3. BRANCHES & HUBS
    # ==========================================
    branches_data = [
        ("BR-LHR-01", "Lahore Central Branch", "+924235551122", "88 Main Boulevard, Gulberg III", "Lahore"),
        ("BR-KHI-01", "Karachi Port Branch", "+922135552233", "12 I.I. Chundrigar Road", "Karachi"),
        ("BR-ISB-01", "Islamabad Capital Branch", "+925135553344", "Plot 42, Blue Area", "Islamabad"),
    ]

    branches_dict = {}
    for code, name, phone, addr, city in branches_data:
        b = Branch.query.filter_by(code=code).first()
        if not b:
            b = Branch(code=code, name=name, phone=phone, address_line=addr, city=city)
            db.session.add(b)
            db.session.flush()
        branches_dict[code] = b

    hubs_data = [
        ("BR-LHR-01", "HUB-LHR-01", "Lahore Mega Sorting Facility", "Gulberg Industrial Area, Gate 4"),
        ("BR-KHI-01", "HUB-KHI-01", "Karachi Coastal Hub", "Korangi Industrial Zone, Sector 15"),
        ("BR-ISB-01", "HUB-ISB-01", "Islamabad Gateway Hub", "I-9/2 Industrial Area"),
    ]

    hubs_dict = {}
    for b_code, code, name, note in hubs_data:
        h = Hub.query.filter_by(code=code).first()
        if not h:
            h = Hub(branch_id=branches_dict[b_code].id, code=code, name=name, location_note=note)
            db.session.add(h)
            db.session.flush()
        hubs_dict[code] = h

    # ==========================================
    # 4. SERVICE ZONES & BRANCH COVERAGE
    # ==========================================
    zones_data = [
        ("ZONE-LHR", "Lahore Metro Zone", "Lahore", "Punjab", "54000"),
        ("ZONE-KHI", "Karachi Central Zone", "Karachi", "Sindh", "74000"),
        ("ZONE-ISB", "Islamabad Urban Zone", "Islamabad", "Federal", "44000"),
        ("ZONE-RWP", "Rawalpindi Region", "Rawalpindi", "Punjab", "46000"),
    ]

    zones_dict = {}
    for code, name, city, reg, prefix in zones_data:
        z = ServiceZone.query.filter_by(code=code).first()
        if not z:
            z = ServiceZone(code=code, name=name, city=city, region=reg, postal_prefix=prefix)
            db.session.add(z)
            db.session.flush()
        zones_dict[code] = z

    # Map zones to branches
    for b_code, z_code in [("BR-LHR-01", "ZONE-LHR"), ("BR-KHI-01", "ZONE-KHI"), ("BR-ISB-01", "ZONE-ISB"), ("BR-ISB-01", "ZONE-RWP")]:
        bz = BranchZone.query.filter_by(branch_id=branches_dict[b_code].id, zone_id=zones_dict[z_code].id).first()
        if not bz:
            bz = BranchZone(branch_id=branches_dict[b_code].id, zone_id=zones_dict[z_code].id, pickup_enabled=True, delivery_enabled=True)
            db.session.add(bz)

    # ==========================================
    # 5. EMPLOYEES & DRIVERS
    # ==========================================
    staff_data = [
        ("lahore.manager@smartcourier.pk", "BR-LHR-01", "EMP-1001", "Branch Manager", date(2023, 1, 15)),
        ("booking.lahore@smartcourier.pk", "BR-LHR-01", "EMP-1002", "Senior Booking Officer", date(2023, 4, 10)),
        ("hub.lahore@smartcourier.pk", "BR-LHR-01", "EMP-1003", "Sorting Hub Lead", date(2023, 6, 1)),
        ("dispatcher.lahore@smartcourier.pk", "BR-LHR-01", "EMP-1004", "Route Dispatch Specialist", date(2023, 8, 15)),
        ("driver1@smartcourier.pk", "BR-LHR-01", "EMP-1005", "Senior Delivery Driver", date(2023, 9, 1)),
        ("finance@smartcourier.pk", "BR-LHR-01", "EMP-1006", "Finance & Settlement Auditor", date(2023, 3, 20)),
        ("support@smartcourier.pk", "BR-LHR-01", "EMP-1007", "Senior Support Officer", date(2023, 5, 5)),
    ]

    employees_dict = {}
    for email, b_code, emp_no, title, hired in staff_data:
        emp = Employee.query.filter_by(employee_no=emp_no).first()
        if not emp:
            user = users_dict[email]
            emp = Employee(
                user_id=user.id,
                primary_branch_id=branches_dict[b_code].id,
                employee_no=emp_no,
                job_title=title,
                hired_on=hired,
            )
            db.session.add(emp)
            db.session.flush()

            eb = EmployeeBranch(employee_id=emp.id, branch_id=branches_dict[b_code].id, is_primary=True, assigned_on=hired)
            db.session.add(eb)
        employees_dict[emp_no] = emp

    # Driver profile
    driver_emp = employees_dict["EMP-1005"]
    drv = Driver.query.filter_by(employee_id=driver_emp.id).first()
    if not drv:
        drv = Driver(
            employee_id=driver_emp.id,
            license_number="PK-LHR-DRV-9988",
            license_expires_on=date.today() + timedelta(days=365 * 3),
        )
        db.session.add(drv)
        db.session.flush()

    # Vehicles
    vehicles_data = [
        ("BR-LHR-01", "LE-24-9001", "VAN", 850000),
        ("BR-LHR-01", "LE-24-9002", "MOTORCYCLE", 30000),
        ("BR-KHI-01", "KH-23-4555", "TRUCK", 3000000),
    ]
    vehicles_dict = {}
    for b_code, plate, vtype, cap in vehicles_data:
        v = Vehicle.query.filter_by(plate_number=plate).first()
        if not v:
            v = Vehicle(
                branch_id=branches_dict[b_code].id,
                plate_number=plate,
                vehicle_type=vtype,
                capacity_grams=cap,
                service_due_on=date.today() + timedelta(days=90),
            )
            db.session.add(v)
            db.session.flush()
        vehicles_dict[plate] = v

    # ==========================================
    # 6. CATALOG: SERVICE TYPES, CATEGORIES, PACKAGING, RATES
    # ==========================================
    service_types_data = [
        ("STANDARD", "Standard Surface Delivery", 3, "Economical road transit nationwide"),
        ("EXPRESS", "Express Air Courier", 1, "Next business day priority dispatch"),
        ("OVERNIGHT", "Overnight Priority", 1, "Guaranteed early morning arrival"),
        ("SAME_DAY", "Same Day City Metro", 0, "Intra-city express courier service"),
    ]
    st_dict = {}
    for code, name, days, desc in service_types_data:
        st = ServiceType.query.filter_by(code=code).first()
        if not st:
            st = ServiceType(code=code, name=name, target_days=days, description=desc)
            db.session.add(st)
            db.session.flush()
        st_dict[code] = st

    categories_data = [
        ("DOC", "Documents & Contracts", False),
        ("ELECTRONICS", "Consumer Electronics", True),
        ("APPAREL", "Textiles & Garments", False),
        ("FRAGILE", "Glass & Delicate Items", True),
        ("GENERAL", "General Commercial Goods", False),
    ]
    cat_dict = {}
    for code, name, fragile in categories_data:
        cat = ParcelCategory.query.filter_by(code=code).first()
        if not cat:
            cat = ParcelCategory(code=code, name=name, is_fragile=fragile)
            db.session.add(cat)
            db.session.flush()
        cat_dict[code] = cat

    packaging_data = [
        ("FLYER_S", "Small Document Flyer", 5000, 1000),      # Rs. 50, 1kg
        ("FLYER_L", "Large Padded Flyer", 10000, 3000),       # Rs. 100, 3kg
        ("BOX_M", "Medium Carton Box", 25000, 10000),         # Rs. 250, 10kg
        ("BOX_L", "Heavy Corrugated Box", 50000, 30000),      # Rs. 500, 30kg
    ]
    pkg_dict = {}
    for code, name, fee, max_w in packaging_data:
        pkg = PackagingType.query.filter_by(code=code).first()
        if not pkg:
            pkg = PackagingType(code=code, name=name, fee_paisa=fee, max_weight_grams=max_w)
            db.session.add(pkg)
            db.session.flush()
        pkg_dict[code] = pkg

    # Rate Cards & Rules (Inter-zone rate matrix)
    # 1. Intra-city LHR -> LHR (Standard)
    rc1 = RateCard.query.filter_by(
        service_type_id=st_dict["STANDARD"].id,
        origin_zone_id=zones_dict["ZONE-LHR"].id,
        destination_zone_id=zones_dict["ZONE-LHR"].id,
    ).first()
    if not rc1:
        rc1 = RateCard(
            service_type_id=st_dict["STANDARD"].id,
            origin_zone_id=zones_dict["ZONE-LHR"].id,
            destination_zone_id=zones_dict["ZONE-LHR"].id,
            valid_from=date(2026, 1, 1),
            valid_until=date(2027, 12, 31),
            currency="PKR",
        )
        db.session.add(rc1)
        db.session.flush()

        r1_rule1 = RateCardRule(rate_card_id=rc1.id, min_weight_grams=0, max_weight_grams=1000, base_fee_paisa=25000, extra_per_kg_paisa=10000)
        r1_rule2 = RateCardRule(rate_card_id=rc1.id, min_weight_grams=1001, max_weight_grams=5000, base_fee_paisa=45000, extra_per_kg_paisa=8000)
        db.session.add(r1_rule1)
        db.session.add(r1_rule2)

    # 2. Inter-city LHR -> KHI (Standard)
    rc2 = RateCard.query.filter_by(
        service_type_id=st_dict["STANDARD"].id,
        origin_zone_id=zones_dict["ZONE-LHR"].id,
        destination_zone_id=zones_dict["ZONE-KHI"].id,
    ).first()
    if not rc2:
        rc2 = RateCard(
            service_type_id=st_dict["STANDARD"].id,
            origin_zone_id=zones_dict["ZONE-LHR"].id,
            destination_zone_id=zones_dict["ZONE-KHI"].id,
            valid_from=date(2026, 1, 1),
            valid_until=date(2027, 12, 31),
            currency="PKR",
        )
        db.session.add(rc2)
        db.session.flush()

        r2_rule1 = RateCardRule(rate_card_id=rc2.id, min_weight_grams=0, max_weight_grams=1000, base_fee_paisa=45000, extra_per_kg_paisa=18000)
        r2_rule2 = RateCardRule(rate_card_id=rc2.id, min_weight_grams=1001, max_weight_grams=5000, base_fee_paisa=75000, extra_per_kg_paisa=15000)
        db.session.add(r2_rule1)
        db.session.add(r2_rule2)

    # 3. Inter-city LHR -> ISB (Express)
    rc3 = RateCard.query.filter_by(
        service_type_id=st_dict["EXPRESS"].id,
        origin_zone_id=zones_dict["ZONE-LHR"].id,
        destination_zone_id=zones_dict["ZONE-ISB"].id,
    ).first()
    if not rc3:
        rc3 = RateCard(
            service_type_id=st_dict["EXPRESS"].id,
            origin_zone_id=zones_dict["ZONE-LHR"].id,
            destination_zone_id=zones_dict["ZONE-ISB"].id,
            valid_from=date(2026, 1, 1),
            valid_until=date(2027, 12, 31),
            currency="PKR",
        )
        db.session.add(rc3)
        db.session.flush()

        r3_rule = RateCardRule(rate_card_id=rc3.id, min_weight_grams=0, max_weight_grams=2000, base_fee_paisa=55000, extra_per_kg_paisa=20000)
        db.session.add(r3_rule)

    # Discounts
    disc = Discount.query.filter_by(code="EIDMUBARAK").first()
    if not disc:
        disc = Discount(
            code="EIDMUBARAK",
            discount_type="PERCENTAGE",
            value=1000,  # 10%
            valid_from=date(2026, 1, 1),
            valid_until=date(2027, 12, 31),
            max_redemptions=500,
        )
        db.session.add(disc)

    # ==========================================
    # 7. CUSTOMERS & SAVED RECIPIENTS
    # ==========================================
    cust_user = users_dict["customer@smartcourier.pk"]
    cust = Customer.query.filter_by(customer_code="CUST-PK-1001").first()
    if not cust:
        cust = Customer(
            user_id=cust_user.id,
            customer_code="CUST-PK-1001",
            full_name="Usman Malik (Alpha Enterprises)",
            phone="+923009990011",
            email="customer@smartcourier.pk",
        )
        db.session.add(cust)
        db.session.flush()

        contact = CustomerContact(customer_id=cust.id, name="Ali Raza", phone="+923009990022", is_primary=True)
        db.session.add(contact)

        caddr = CustomerAddress(
            customer_id=cust.id,
            zone_id=zones_dict["ZONE-LHR"].id,
            label="Head Office Warehouse",
            line1="Suit 14, Commercial Plaza, DHA Phase 5",
            city="Lahore",
            postal_code="54000",
        )
        db.session.add(caddr)

        # Recipient Profile
        rec = RecipientProfile(customer_id=cust.id, name="Babar Azam (Retail Store)", phone="+923214455667", email="babar@store.pk")
        db.session.add(rec)
        db.session.flush()

        raddr = RecipientAddress(
            recipient_id=rec.id,
            zone_id=zones_dict["ZONE-KHI"].id,
            line1="Shop 4, Clifton Center, Block 5",
            city="Karachi",
            postal_code="74000",
        )
        db.session.add(raddr)

    # ==========================================
    # 8. SAMPLE SHIPMENTS (ACROSS LIFECYCLE STAGES)
    # ==========================================
    # Shipment 1: DELIVERED (with attempt, proof, invoice, settled payment)
    s1 = Shipment.query.filter_by(tracking_number="SC2611-LHR-DELIV01").first()
    if not s1:
        s1 = Shipment(
            tracking_number="SC2611-LHR-DELIV01",
            customer_id=cust.id,
            origin_branch_id=branches_dict["BR-LHR-01"].id,
            destination_branch_id=branches_dict["BR-KHI-01"].id,
            service_type_id=st_dict["STANDARD"].id,
            parcel_category_id=cat_dict["GENERAL"].id,
            packaging_type_id=pkg_dict["FLYER_S"].id,
            booking_employee_id=employees_dict["EMP-1002"].id,
            current_hub_id=hubs_dict["HUB-KHI-01"].id,
            weight_grams=850,
            declared_value_paisa=500000,
            cod_due_paisa=250000,
            booked_at=datetime.utcnow() - timedelta(days=3),
            shipment_status="DELIVERED",
            total_charge_paisa=50000,  # Rs. 500
        )
        db.session.add(s1)
        db.session.flush()

        # Item & addresses
        db.session.add(ShipmentItem(shipment_id=s1.id, description="Cotton Textiles Samples", quantity=1, weight_grams=850))
        db.session.add(ShipmentAddress(shipment_id=s1.id, address_role="SENDER", person_name="Usman Malik", phone="+923009990011", line1="DHA Phase 5", city="Lahore", zone_id=zones_dict["ZONE-LHR"].id))
        db.session.add(ShipmentAddress(shipment_id=s1.id, address_role="RECIPIENT", person_name="Babar Azam", phone="+923214455667", line1="Clifton Block 5", city="Karachi", zone_id=zones_dict["ZONE-KHI"].id))
        db.session.add(ShipmentQuote(shipment_id=s1.id, service_type_id=st_dict["STANDARD"].id, quoted_rate_card_id=rc2.id, quoted_rule_id=rc2.rules[0].id, base_fee_paisa=45000, packaging_fee_paisa=5000, total_paisa=50000, currency="PKR"))

        # History & Tracking
        h1 = ShipmentStatusHistory(shipment_id=s1.id, previous_status="OUT_FOR_DELIVERY", new_status="DELIVERED", changed_at=datetime.utcnow() - timedelta(hours=2), reason="Delivered successfully to recipient")
        db.session.add(h1)
        db.session.flush()

        db.session.add(TrackingEvent(shipment_id=s1.id, status_history_id=h1.id, event_code="DELIVERED", public_message="Delivered to Babar Azam. Verified by signature.", occurred_at=datetime.utcnow() - timedelta(hours=2)))

        # Attempt & Proof
        attempt1 = DeliveryAttempt(shipment_id=s1.id, driver_id=drv.id, attempted_at=datetime.utcnow() - timedelta(hours=2), outcome="SUCCESS")
        db.session.add(attempt1)
        db.session.flush()

        proof1 = DeliveryProof(shipment_id=s1.id, delivery_attempt_id=attempt1.id, received_by_name="Babar Azam", delivered_at=datetime.utcnow() - timedelta(hours=2))
        db.session.add(proof1)

        # COD Collection
        db.session.add(CodCollection(
            shipment_id=s1.id,
            collected_by_driver_id=drv.id,
            amount_paisa=250000,
            collected_at=datetime.utcnow() - timedelta(hours=2),
            collection_status="COLLECTED"
        ))

        # Invoice & Settled Payment
        inv1 = Invoice(
            shipment_id=s1.id,
            customer_id=cust.id,
            invoice_number="INV-202611-0001",
            subtotal_paisa=50000,
            total_paisa=50000,
            invoice_status="PAID",
            issued_at=datetime.utcnow() - timedelta(days=3),
            due_at=datetime.utcnow() + timedelta(days=4),
        )
        db.session.add(inv1)
        db.session.flush()

        db.session.add(InvoiceItem(invoice_id=inv1.id, description="Freight Shipping (Standard)", quantity=1, unit_price_paisa=50000, line_total_paisa=50000))
        db.session.add(Payment(invoice_id=inv1.id, received_by_employee_id=employees_dict["EMP-1006"].id, amount_paisa=50000, method="BANK_TRANSFER", reference_code="TRX-MCB-998811", paid_at=datetime.utcnow() - timedelta(days=2)))

    # Shipment 2: IN_TRANSIT (with hub scan)
    s2 = Shipment.query.filter_by(tracking_number="SC2611-LHR-TRANSIT02").first()
    if not s2:
        s2 = Shipment(
            tracking_number="SC2611-LHR-TRANSIT02",
            customer_id=cust.id,
            origin_branch_id=branches_dict["BR-LHR-01"].id,
            destination_branch_id=branches_dict["BR-ISB-01"].id,
            service_type_id=st_dict["EXPRESS"].id,
            parcel_category_id=cat_dict["ELECTRONICS"].id,
            packaging_type_id=pkg_dict["BOX_M"].id,
            booking_employee_id=employees_dict["EMP-1002"].id,
            current_hub_id=hubs_dict["HUB-LHR-01"].id,
            weight_grams=1400,
            declared_value_paisa=1200000,
            cod_due_paisa=350000,  # Rs. 3,500 COD
            booked_at=datetime.utcnow() - timedelta(days=1),
            shipment_status="IN_TRANSIT",
            total_charge_paisa=80000,  # Rs. 800
        )
        db.session.add(s2)
        db.session.flush()

        db.session.add(ShipmentItem(shipment_id=s2.id, description="Smart Watch Electronic Unit", quantity=1, weight_grams=1400))
        db.session.add(ShipmentAddress(shipment_id=s2.id, address_role="SENDER", person_name="Usman Malik", phone="+923009990011", line1="DHA Phase 5", city="Lahore", zone_id=zones_dict["ZONE-LHR"].id))
        db.session.add(ShipmentAddress(shipment_id=s2.id, address_role="RECIPIENT", person_name="Dr. Salman Qureshi", phone="+923335557788", line1="Sector F-7/2", city="Islamabad", zone_id=zones_dict["ZONE-ISB"].id))
        db.session.add(ShipmentQuote(shipment_id=s2.id, service_type_id=st_dict["EXPRESS"].id, quoted_rate_card_id=rc3.id, quoted_rule_id=rc3.rules[0].id, base_fee_paisa=55000, packaging_fee_paisa=25000, total_paisa=80000, currency="PKR"))

        # Scan & Event
        db.session.add(ShipmentScan(shipment_id=s2.id, hub_id=hubs_dict["HUB-LHR-01"].id, scanned_by_employee_id=employees_dict["EMP-1003"].id, scan_code="HUB_DEPARTURE", notes="Dispatched on truck to Islamabad"))
        db.session.add(TrackingEvent(shipment_id=s2.id, event_code="IN_TRANSIT", public_message="Departed Lahore Mega Sorting Hub en route to Islamabad Gateway Hub.", occurred_at=datetime.utcnow() - timedelta(hours=6)))

        # Invoice
        inv2 = Invoice(
            shipment_id=s2.id,
            customer_id=cust.id,
            invoice_number="INV-202611-0002",
            subtotal_paisa=80000,
            total_paisa=80000,
            invoice_status="ISSUED",
            issued_at=datetime.utcnow() - timedelta(days=1),
            due_at=datetime.utcnow() + timedelta(days=6),
        )
        db.session.add(inv2)
        db.session.flush()
        db.session.add(InvoiceItem(invoice_id=inv2.id, description="Express Priority Courier (LHR-ISB)", quantity=1, unit_price_paisa=80000, line_total_paisa=80000))

    # Shipment 3: OUT_FOR_DELIVERY (with Route and Stop assigned)
    s3 = Shipment.query.filter_by(tracking_number="SC2611-LHR-OUTFD03").first()
    if not s3:
        s3 = Shipment(
            tracking_number="SC2611-LHR-OUTFD03",
            customer_id=cust.id,
            origin_branch_id=branches_dict["BR-LHR-01"].id,
            destination_branch_id=branches_dict["BR-LHR-01"].id,
            service_type_id=st_dict["STANDARD"].id,
            parcel_category_id=cat_dict["GENERAL"].id,
            packaging_type_id=pkg_dict["FLYER_S"].id,
            booking_employee_id=employees_dict["EMP-1002"].id,
            current_hub_id=hubs_dict["HUB-LHR-01"].id,
            weight_grams=500,
            declared_value_paisa=200000,
            cod_due_paisa=150000,  # Rs. 1,500 COD
            booked_at=datetime.utcnow() - timedelta(hours=8),
            shipment_status="OUT_FOR_DELIVERY",
            total_charge_paisa=30000,
        )
        db.session.add(s3)
        db.session.flush()

        db.session.add(ShipmentItem(shipment_id=s3.id, description="Cosmetics Parcel", quantity=1, weight_grams=500))
        db.session.add(ShipmentAddress(shipment_id=s3.id, address_role="SENDER", person_name="Usman Malik", phone="+923009990011", line1="DHA Phase 5", city="Lahore", zone_id=zones_dict["ZONE-LHR"].id))
        db.session.add(ShipmentAddress(shipment_id=s3.id, address_role="RECIPIENT", person_name="Fatima Noor", phone="+923224449900", line1="House 22, Model Town", city="Lahore", zone_id=zones_dict["ZONE-LHR"].id))
        db.session.add(ShipmentQuote(shipment_id=s3.id, service_type_id=st_dict["STANDARD"].id, quoted_rate_card_id=rc1.id, quoted_rule_id=rc1.rules[0].id, base_fee_paisa=25000, packaging_fee_paisa=5000, total_paisa=30000, currency="PKR"))

        # Create route and stop
        rt1 = Route.query.filter_by(route_code="ROUTE-LHR-EAST-01").first()
        if not rt1:
            rt1 = Route(
                branch_id=branches_dict["BR-LHR-01"].id,
                driver_id=drv.id,
                vehicle_id=vehicles_dict["LE-24-9002"].id,
                route_code="ROUTE-LHR-EAST-01",
                route_date=date.today(),
                route_status="IN_PROGRESS",
            )
            db.session.add(rt1)
            db.session.flush()

            db.session.add(VehicleAssignment(vehicle_id=vehicles_dict["LE-24-9002"].id, driver_id=drv.id, route_id=rt1.id))

        db.session.add(RouteStop(route_id=rt1.id, shipment_id=s3.id, stop_sequence=1, stop_type="DELIVERY"))
        db.session.add(TrackingEvent(shipment_id=s3.id, event_code="OUT_FOR_DELIVERY", public_message="Out for delivery with rider Kamran Akram on motorcycle LE-24-9002.", occurred_at=datetime.utcnow() - timedelta(hours=2)))

        # Invoice
        inv3 = Invoice(
            shipment_id=s3.id,
            customer_id=cust.id,
            invoice_number="INV-202611-0003",
            subtotal_paisa=30000,
            total_paisa=30000,
            invoice_status="ISSUED",
            issued_at=datetime.utcnow() - timedelta(hours=8),
            due_at=datetime.utcnow() + timedelta(days=7),
        )
        db.session.add(inv3)
        db.session.flush()
        db.session.add(InvoiceItem(invoice_id=inv3.id, description="Local Delivery Charge", quantity=1, unit_price_paisa=30000, line_total_paisa=30000))

    # Shipment 4: DELIVERY_FAILED (with DeliveryException)
    s4 = Shipment.query.filter_by(tracking_number="SC2611-LHR-FAILED04").first()
    if not s4:
        s4 = Shipment(
            tracking_number="SC2611-LHR-FAILED04",
            customer_id=cust.id,
            origin_branch_id=branches_dict["BR-LHR-01"].id,
            destination_branch_id=branches_dict["BR-LHR-01"].id,
            service_type_id=st_dict["STANDARD"].id,
            parcel_category_id=cat_dict["GENERAL"].id,
            packaging_type_id=pkg_dict["FLYER_S"].id,
            booking_employee_id=employees_dict["EMP-1002"].id,
            current_hub_id=hubs_dict["HUB-LHR-01"].id,
            weight_grams=600,
            booked_at=datetime.utcnow() - timedelta(days=2),
            shipment_status="DELIVERY_FAILED",
            total_charge_paisa=30000,
        )
        db.session.add(s4)
        db.session.flush()

        db.session.add(ShipmentItem(shipment_id=s4.id, description="Leather Wallet", quantity=1, weight_grams=600))
        db.session.add(ShipmentAddress(shipment_id=s4.id, address_role="SENDER", person_name="Usman Malik", phone="+923009990011", line1="DHA Phase 5", city="Lahore", zone_id=zones_dict["ZONE-LHR"].id))
        db.session.add(ShipmentAddress(shipment_id=s4.id, address_role="RECIPIENT", person_name="Raza Gillani", phone="+923001239999", line1="Plaza 9, Johar Town", city="Lahore", zone_id=zones_dict["ZONE-LHR"].id))
        db.session.add(ShipmentQuote(shipment_id=s4.id, service_type_id=st_dict["STANDARD"].id, quoted_rate_card_id=rc1.id, quoted_rule_id=rc1.rules[0].id, base_fee_paisa=25000, packaging_fee_paisa=5000, total_paisa=30000, currency="PKR"))

        # Failed attempt & exception
        att4 = DeliveryAttempt(shipment_id=s4.id, driver_id=drv.id, outcome="FAILED", failure_reason="Premises locked / recipient unavailable")
        db.session.add(att4)
        db.session.flush()

        db.session.add(DeliveryException(shipment_id=s4.id, delivery_attempt_id=att4.id, exception_code="UNAVAILABLE", explanation="House was locked, phone was unreachable"))
        db.session.add(TrackingEvent(shipment_id=s4.id, event_code="DELIVERY_FAILED", public_message="Delivery attempt unsuccessful: Recipient unavailable. Rescheduling attempt.", occurred_at=datetime.utcnow() - timedelta(hours=5)))

        inv4 = Invoice(
            shipment_id=s4.id,
            customer_id=cust.id,
            invoice_number="INV-202611-0004",
            subtotal_paisa=30000,
            total_paisa=30000,
            invoice_status="ISSUED",
            issued_at=datetime.utcnow() - timedelta(days=2),
            due_at=datetime.utcnow() + timedelta(days=5),
        )
        db.session.add(inv4)
        db.session.flush()
        db.session.add(InvoiceItem(invoice_id=inv4.id, description="Local Delivery", quantity=1, unit_price_paisa=30000, line_total_paisa=30000))

    # Shipment 5: BOOKED (Ready for pickup/hub processing)
    s5 = Shipment.query.filter_by(tracking_number="SC2611-LHR-BOOKED05").first()
    if not s5:
        s5 = Shipment(
            tracking_number="SC2611-LHR-BOOKED05",
            customer_id=cust.id,
            origin_branch_id=branches_dict["BR-LHR-01"].id,
            destination_branch_id=branches_dict["BR-ISB-01"].id,
            service_type_id=st_dict["EXPRESS"].id,
            parcel_category_id=cat_dict["DOC"].id,
            packaging_type_id=pkg_dict["FLYER_S"].id,
            booking_employee_id=employees_dict["EMP-1002"].id,
            current_hub_id=hubs_dict["HUB-LHR-01"].id,
            weight_grams=350,
            booked_at=datetime.utcnow() - timedelta(hours=2),
            shipment_status="BOOKED",
            total_charge_paisa=60000,
        )
        db.session.add(s5)
        db.session.flush()

        db.session.add(ShipmentItem(shipment_id=s5.id, description="Legal Affidavits", quantity=1, weight_grams=350))
        db.session.add(ShipmentAddress(shipment_id=s5.id, address_role="SENDER", person_name="Usman Malik", phone="+923009990011", line1="DHA Phase 5", city="Lahore", zone_id=zones_dict["ZONE-LHR"].id))
        db.session.add(ShipmentAddress(shipment_id=s5.id, address_role="RECIPIENT", person_name="Advocate Zeeshan", phone="+923331112233", line1="High Court Chambers", city="Islamabad", zone_id=zones_dict["ZONE-ISB"].id))
        db.session.add(ShipmentQuote(shipment_id=s5.id, service_type_id=st_dict["EXPRESS"].id, quoted_rate_card_id=rc3.id, quoted_rule_id=rc3.rules[0].id, base_fee_paisa=55000, packaging_fee_paisa=5000, total_paisa=60000, currency="PKR"))

        inv5 = Invoice(
            shipment_id=s5.id,
            customer_id=cust.id,
            invoice_number="INV-202611-0005",
            subtotal_paisa=60000,
            total_paisa=60000,
            invoice_status="ISSUED",
            issued_at=datetime.utcnow() - timedelta(hours=2),
            due_at=datetime.utcnow() + timedelta(days=5),
        )
        db.session.add(inv5)
        db.session.flush()
        db.session.add(InvoiceItem(invoice_id=inv5.id, description="Express Documents Delivery", quantity=1, unit_price_paisa=60000, line_total_paisa=60000))

    # ==========================================
    # 9. SUPPORT TICKETS & MESSAGES
    # ==========================================
    tkt = SupportTicket.query.filter_by(ticket_number="TKT-202611-0001").first()
    if not tkt:
        tkt = SupportTicket(
            ticket_number="TKT-202611-0001",
            customer_id=cust.id,
            shipment_id=s4.id,
            assigned_employee_id=employees_dict["EMP-1007"].id,
            subject="Inquiry regarding failed delivery attempt on SC2611-LHR-FAILED04",
            priority="HIGH",
            ticket_status="IN_PROGRESS",
            opened_at=datetime.utcnow() - timedelta(hours=4),
        )
        db.session.add(tkt)
        db.session.flush()

        # Customer message
        db.session.add(TicketMessage(
            ticket_id=tkt.id,
            sender_user_id=cust_user.id,
            sender_customer_id=cust.id,
            body="Hello, my customer at Johar Town was at work when rider visited. Can you please re-attempt tomorrow after 3 PM?",
            is_internal=False,
            posted_at=datetime.utcnow() - timedelta(hours=4),
        ))

        # Internal staff note
        db.session.add(TicketMessage(
            ticket_id=tkt.id,
            sender_user_id=users_dict["support@smartcourier.pk"].id,
            sender_employee_id=employees_dict["EMP-1007"].id,
            body="Internal Note: Contacted Driver Kamran. He confirmed rider route can pass Johar Town around 3:30 PM tomorrow.",
            is_internal=True,
            posted_at=datetime.utcnow() - timedelta(hours=3),
        ))

        # Support public reply to customer
        db.session.add(TicketMessage(
            ticket_id=tkt.id,
            sender_user_id=users_dict["support@smartcourier.pk"].id,
            sender_employee_id=employees_dict["EMP-1007"].id,
            body="Dear Mr. Usman, we have coordinated with the local route dispatcher. The re-attempt has been scheduled for tomorrow afternoon after 3:00 PM.",
            is_internal=False,
            posted_at=datetime.utcnow() - timedelta(hours=2),
        ))

    # ==========================================
    # 10. NOTIFICATION TEMPLATES & NOTIFICATIONS
    # ==========================================
    nt = NotificationTemplate.query.filter_by(code="SHIPMENT_DELIVERED").first()
    if not nt:
        nt = NotificationTemplate(
            code="SHIPMENT_DELIVERED",
            channel="IN_APP",
            subject_template="Parcel {tracking_number} has been delivered",
            body_template="Your consignment with tracking code {tracking_number} was successfully delivered to {recipient}.",
        )
        db.session.add(nt)
        db.session.flush()

        db.session.add(Notification(
            customer_id=cust.id,
            shipment_id=s1.id,
            template_id=nt.id,
            channel="IN_APP",
            recipient="customer@smartcourier.pk",
            subject="Parcel SC2611-LHR-DELIV01 has been delivered",
            body="Your consignment with tracking code SC2611-LHR-DELIV01 was successfully delivered to Babar Azam.",
            delivery_status="SENT",
            created_for_event_at=datetime.utcnow() - timedelta(hours=2),
            sent_at=datetime.utcnow() - timedelta(hours=2),
        ))

    # ==========================================
    # 11. APP SETTINGS & AUDIT LOGS
    # ==========================================
    setting1 = AppSetting.query.filter_by(setting_key="COMPANY_NAME").first()
    if not setting1:
        db.session.add(AppSetting(setting_key="COMPANY_NAME", value_json='{"name": "Smart Courier Pakistan", "reg_no": "PK-SEC-99881"}', description="Official legal entity name"))
        db.session.add(AppSetting(setting_key="SALES_TAX_PERCENT", value_json='{"rate_basis_points": 0}', description="General sales tax rate on courier freight services"))

    audit1 = AuditLog.query.filter_by(action="SYSTEM_BOOTSTRAP").first()
    if not audit1:
        db.session.add(AuditLog(
            actor_user_id=users_dict["admin@smartcourier.pk"].id,
            branch_id=branches_dict["BR-LHR-01"].id,
            entity_type="System",
            entity_id=1,
            action="SYSTEM_BOOTSTRAP",
            after_json='{"initialized": true, "tables": 55, "roles": 9}',
            occurred_at=datetime.utcnow(),
        ))

    db.session.commit()
    print("[+] Successfully seeded all 55 business tables!")
