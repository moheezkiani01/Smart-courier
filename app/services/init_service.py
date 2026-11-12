import os
from datetime import date
from flask import current_app
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.auth import Role, Permission, RolePermission, User, UserRole
from app.models.organization import Branch, Hub, ServiceZone, BranchZone
from app.models.catalog import ServiceType, ParcelCategory, PackagingType, RateCard, RateCardRule
from app.models.support import AppSetting, NotificationTemplate

def init_production_catalog(admin_email: str = None, admin_password: str = None, admin_name: str = None) -> dict:
    """
    Idempotent, secure production initialization service.
    Guarantees that all 9 user roles, all 12 permissions, role-permission links,
    and the essential courier catalog exist in PostgreSQL.
    Preserves all existing records and does NOT seed public demo passwords.
    """
    stats = {
        "roles_created": 0,
        "permissions_created": 0,
        "role_permissions_created": 0,
        "branches_created": 0,
        "hubs_created": 0,
        "zones_created": 0,
        "branch_zones_created": 0,
        "services_created": 0,
        "categories_created": 0,
        "packaging_created": 0,
        "rate_cards_created": 0,
        "rate_rules_created": 0,
        "settings_created": 0,
        "templates_created": 0,
        "admin_bootstrapped": False,
    }

    # ==========================================
    # 1. NINE USER ROLES
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
            stats["roles_created"] += 1
        roles_dict[code] = r

    # ==========================================
    # 2. TWELVE SYSTEM PERMISSIONS
    # ==========================================
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
            stats["permissions_created"] += 1
        perms_dict[code] = p

    # ==========================================
    # 3. ROLE-PERMISSION MAPPINGS
    # ==========================================
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
                stats["role_permissions_created"] += 1

    # ==========================================
    # 4. ESSENTIAL BRANCHES & HUBS
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
            stats["branches_created"] += 1
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
            stats["hubs_created"] += 1
        hubs_dict[code] = h

    # ==========================================
    # 5. SERVICE ZONES & BRANCH COVERAGE
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
            stats["zones_created"] += 1
        zones_dict[code] = z

    branch_zone_links = [
        ("BR-LHR-01", "ZONE-LHR"),
        ("BR-KHI-01", "ZONE-KHI"),
        ("BR-ISB-01", "ZONE-ISB"),
        ("BR-ISB-01", "ZONE-RWP"),
    ]
    for b_code, z_code in branch_zone_links:
        bz = BranchZone.query.filter_by(branch_id=branches_dict[b_code].id, zone_id=zones_dict[z_code].id).first()
        if not bz:
            bz = BranchZone(branch_id=branches_dict[b_code].id, zone_id=zones_dict[z_code].id, pickup_enabled=True, delivery_enabled=True)
            db.session.add(bz)
            stats["branch_zones_created"] += 1

    # ==========================================
    # 6. SERVICE TYPES, CATEGORIES & PACKAGING
    # ==========================================
    services_data = [
        ("STANDARD", "Standard Surface Delivery", 3, "Economical road transit nationwide"),
        ("EXPRESS", "Express Air Courier", 1, "Next business day priority dispatch"),
        ("OVERNIGHT", "Overnight Priority", 1, "Guaranteed early morning arrival"),
        ("SAME_DAY", "Same Day City Metro", 0, "Intra-city express courier service"),
    ]
    st_dict = {}
    for code, name, days, desc in services_data:
        st = ServiceType.query.filter_by(code=code).first()
        if not st:
            st = ServiceType(code=code, name=name, target_days=days, description=desc)
            db.session.add(st)
            db.session.flush()
            stats["services_created"] += 1
        st_dict[code] = st

    categories_data = [
        ("DOC", "Documents & Contracts", False),
        ("ELECTRONICS", "Consumer Electronics", True),
        ("APPAREL", "Textiles & Garments", False),
        ("FRAGILE", "Glass & Delicate Items", True),
        ("GENERAL", "General Commercial Goods", False),
    ]
    for code, name, fragile in categories_data:
        cat = ParcelCategory.query.filter_by(code=code).first()
        if not cat:
            cat = ParcelCategory(code=code, name=name, is_fragile=fragile)
            db.session.add(cat)
            stats["categories_created"] += 1

    packaging_data = [
        ("FLYER_S", "Small Document Flyer", 5000, 1000),      # Rs. 50, 1kg
        ("FLYER_L", "Large Padded Flyer", 10000, 3000),       # Rs. 100, 3kg
        ("BOX_M", "Medium Carton Box", 25000, 10000),         # Rs. 250, 10kg
        ("BOX_L", "Heavy Corrugated Box", 50000, 30000),      # Rs. 500, 30kg
    ]
    for code, name, fee, max_w in packaging_data:
        pkg = PackagingType.query.filter_by(code=code).first()
        if not pkg:
            pkg = PackagingType(code=code, name=name, fee_paisa=fee, max_weight_grams=max_w)
            db.session.add(pkg)
            stats["packaging_created"] += 1

    # ==========================================
    # 7. COMPREHENSIVE RATE CARDS & RULES
    # ==========================================
    valid_from = date(2026, 1, 1)
    valid_until = date(2030, 12, 31)

    # Base pricing tariffs (paisa): (intra_base1, intra_extra1, intra_base2, intra_extra2, inter_base1, inter_extra1, inter_base2, inter_extra2)
    tariffs = {
        "STANDARD": (25000, 10000, 45000, 8000,  45000, 18000, 75000, 15000),
        "EXPRESS":  (35000, 15000, 60000, 12000, 55000, 20000, 95000, 18000),
        "OVERNIGHT":(40000, 18000, 70000, 15000, 65000, 25000, 110000, 20000),
        "SAME_DAY": (50000, 20000, 85000, 18000, 80000, 30000, 140000, 25000),
    }

    zone_keys = list(zones_dict.keys())
    for s_code, st_obj in st_dict.items():
        t = tariffs.get(s_code, tariffs["STANDARD"])
        for o_code in zone_keys:
            for d_code in zone_keys:
                is_intra = (o_code == d_code) or (o_code in ("ZONE-ISB", "ZONE-RWP") and d_code in ("ZONE-ISB", "ZONE-RWP"))
                base1 = t[0] if is_intra else t[4]
                extra1 = t[1] if is_intra else t[5]
                base2 = t[2] if is_intra else t[6]
                extra2 = t[3] if is_intra else t[7]

                rc = RateCard.query.filter_by(
                    service_type_id=st_obj.id,
                    origin_zone_id=zones_dict[o_code].id,
                    destination_zone_id=zones_dict[d_code].id,
                ).first()

                if not rc:
                    rc = RateCard(
                        service_type_id=st_obj.id,
                        origin_zone_id=zones_dict[o_code].id,
                        destination_zone_id=zones_dict[d_code].id,
                        valid_from=valid_from,
                        valid_until=valid_until,
                        currency="PKR",
                    )
                    db.session.add(rc)
                    db.session.flush()
                    stats["rate_cards_created"] += 1

                    rule1 = RateCardRule(
                        rate_card_id=rc.id,
                        min_weight_grams=0,
                        max_weight_grams=1000,
                        base_fee_paisa=base1,
                        extra_per_kg_paisa=extra1,
                    )
                    rule2 = RateCardRule(
                        rate_card_id=rc.id,
                        min_weight_grams=1001,
                        max_weight_grams=5000,
                        base_fee_paisa=base2,
                        extra_per_kg_paisa=extra2,
                    )
                    db.session.add(rule1)
                    db.session.add(rule2)
                    stats["rate_rules_created"] += 2

    # ==========================================
    # 8. APP SETTINGS & NOTIFICATION TEMPLATES
    # ==========================================
    if not AppSetting.query.filter_by(setting_key="COMPANY_NAME").first():
        db.session.add(AppSetting(
            setting_key="COMPANY_NAME",
            value_json='{"name": "Smart Courier Pakistan", "reg_no": "PK-SEC-99881"}',
            description="Official legal entity name"
        ))
        stats["settings_created"] += 1

    if not AppSetting.query.filter_by(setting_key="SALES_TAX_PERCENT").first():
        db.session.add(AppSetting(
            setting_key="SALES_TAX_PERCENT",
            value_json='{"rate_basis_points": 0}',
            description="General sales tax rate on courier freight services"
        ))
        stats["settings_created"] += 1

    templates_data = [
        ("SHIPMENT_DELIVERED", "IN_APP", "Parcel {tracking_number} has been delivered", "Your consignment with tracking code {tracking_number} was successfully delivered to {recipient}."),
        ("SHIPMENT_BOOKED", "IN_APP", "Parcel {tracking_number} booked successfully", "Your booking {tracking_number} has been registered and is being processed."),
        ("OUT_FOR_DELIVERY", "IN_APP", "Parcel {tracking_number} is out for delivery", "Your parcel {tracking_number} is out for delivery with courier driver."),
    ]
    for code, ch, subj, body in templates_data:
        nt = NotificationTemplate.query.filter_by(code=code).first()
        if not nt:
            nt = NotificationTemplate(code=code, channel=ch, subject_template=subj, body_template=body)
            db.session.add(nt)
            stats["templates_created"] += 1

    # ==========================================
    # 9. OPTIONAL SUPERADMIN BOOTSTRAP
    # ==========================================
    email = admin_email or os.environ.get("ADMIN_BOOTSTRAP_EMAIL")
    password = admin_password or os.environ.get("ADMIN_BOOTSTRAP_PASSWORD")
    name = admin_name or os.environ.get("ADMIN_BOOTSTRAP_NAME", "System Administrator")

    if email and password:
        email = email.strip().lower()
        admin_role = roles_dict["SUPER_ADMIN"]
        admin_user = User.query.filter_by(email=email, is_deleted=False).first()
        if not admin_user:
            admin_user = User(
                full_name=name.strip(),
                email=email,
                phone="+923000000000",
                password_hash=generate_password_hash(password),
                is_email_verified=True,
                status="ACTIVE",
            )
            db.session.add(admin_user)
            db.session.flush()
        else:
            admin_user.password_hash = generate_password_hash(password)
            admin_user.status = "ACTIVE"

        has_ur = UserRole.query.filter_by(user_id=admin_user.id, role_id=admin_role.id).first()
        if not has_ur:
            ur = UserRole(user_id=admin_user.id, role_id=admin_role.id)
            db.session.add(ur)

        stats["admin_bootstrapped"] = True

    db.session.commit()
    return stats
