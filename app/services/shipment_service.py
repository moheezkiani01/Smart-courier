from datetime import datetime, timedelta
from app.extensions import db
from app.models.auth import User
from app.models.catalog import Customer
from app.models.shipments import (
    Shipment,
    ShipmentItem,
    ShipmentAddress,
    ShipmentService as ShipmentQuote,
    ShipmentStatusHistory,
    PickupRequest,
)
from app.models.dispatch import TrackingEvent
from app.models.finance import Invoice, InvoiceItem, ShipmentDiscount
from app.services.pricing_service import PricingService
from app.services.audit_service import log_audit
from app.utils.helpers import generate_tracking_number, generate_invoice_number

class ShipmentService:
    ALLOWED_TRANSITIONS = {
        "DRAFT": ["BOOKED"],
        "BOOKED": ["PICKUP_ASSIGNED", "AT_ORIGIN_HUB", "CANCELLED"],
        "PICKUP_ASSIGNED": ["PICKED_UP", "CANCELLED"],
        "PICKED_UP": ["AT_ORIGIN_HUB"],
        "AT_ORIGIN_HUB": ["IN_TRANSIT"],
        "IN_TRANSIT": ["AT_DESTINATION_HUB"],
        "AT_DESTINATION_HUB": ["OUT_FOR_DELIVERY"],
        "OUT_FOR_DELIVERY": ["DELIVERED", "DELIVERY_FAILED"],
        "DELIVERY_FAILED": ["OUT_FOR_DELIVERY", "RETURN_INITIATED"],
        "RETURN_INITIATED": ["RETURNED_TO_SENDER"],
    }

    STATUS_MESSAGES = {
        "BOOKED": "Shipment has been registered and booked into the system.",
        "PICKUP_ASSIGNED": "Pickup courier has been assigned to collect the parcel.",
        "PICKED_UP": "Parcel has been picked up from sender.",
        "AT_ORIGIN_HUB": "Parcel received and scanned at origin sorting hub.",
        "IN_TRANSIT": "Parcel is in transit between logistics hubs.",
        "AT_DESTINATION_HUB": "Parcel received at destination sorting hub.",
        "OUT_FOR_DELIVERY": "Parcel is out for delivery with courier driver.",
        "DELIVERED": "Parcel has been successfully delivered to the recipient.",
        "DELIVERY_FAILED": "Delivery attempt failed. Awaiting reschedule or instruction.",
        "CANCELLED": "Consignment has been cancelled.",
        "RETURN_INITIATED": "Return process initiated back to origin sender.",
        "RETURNED_TO_SENDER": "Parcel has been returned to sender.",
    }

    @staticmethod
    def book_shipment(
        customer_id: int,
        origin_branch_id: int,
        destination_branch_id: int,
        service_type_id: int,
        parcel_category_id: int,
        packaging_type_id: int,
        sender_data: dict,
        recipient_data: dict,
        items_data: list,
        actor_user_id: int,
        declared_value_paisa: int = 0,
        cod_due_paisa: int = 0,
        discount_code: str = None,
        schedule_pickup: bool = False,
        pickup_notes: str = None,
    ) -> Shipment:
        """
        Atomically book a new shipment, snapshotting addresses, pricing quote,
        generating invoice, and opening status history.
        """
        # Verify actor user & customer authorization
        actor_user = db.session.get(User, actor_user_id)
        if not actor_user:
            raise ValueError("Actor user not found.")

        is_admin_or_staff = (
            actor_user.has_role("SUPER_ADMIN")
            or actor_user.has_role("BRANCH_MANAGER")
            or actor_user.has_role("BOOKING_AGENT")
        )
        is_customer = actor_user.has_role("CUSTOMER")

        if not (is_admin_or_staff or is_customer):
            raise PermissionError("User is not authorized to book shipments.")

        if is_customer and not is_admin_or_staff:
            if not (actor_user.customer and actor_user.customer.id == customer_id):
                raise PermissionError("Customers can only book shipments for their own customer account.")

        customer = Customer.query.filter_by(id=customer_id, is_deleted=False).first()
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist or has been deactivated.")

        # Calculate total weight
        total_weight_grams = sum(item.get("weight_grams", 1) * item.get("quantity", 1) for item in items_data)
        if total_weight_grams <= 0:
            total_weight_grams = 500  # Default 500g

        # Quote pricing
        quote = PricingService.calculate_quote(
            service_type_id=service_type_id,
            origin_zone_id=sender_data["zone_id"],
            destination_zone_id=recipient_data["zone_id"],
            weight_grams=total_weight_grams,
            packaging_type_id=packaging_type_id,
            discount_code=discount_code,
        )

        tracking_num = generate_tracking_number()

        # 1. Create Shipment
        shipment = Shipment(
            tracking_number=tracking_num,
            customer_id=customer_id,
            origin_branch_id=origin_branch_id,
            destination_branch_id=destination_branch_id,
            service_type_id=service_type_id,
            parcel_category_id=parcel_category_id,
            packaging_type_id=packaging_type_id,
            weight_grams=total_weight_grams,
            declared_value_paisa=declared_value_paisa,
            cod_due_paisa=cod_due_paisa,
            booked_at=datetime.utcnow(),
            shipment_status="BOOKED",
            total_charge_paisa=quote["total_paisa"],
            created_by=actor_user_id,
        )
        db.session.add(shipment)
        db.session.flush()

        # 2. Add Items
        for it in items_data:
            item_entry = ShipmentItem(
                shipment_id=shipment.id,
                description=it.get("description", "Standard Item"),
                quantity=it.get("quantity", 1),
                weight_grams=it.get("weight_grams", 1),
                declared_value_paisa=it.get("declared_value_paisa", 0),
                created_by=actor_user_id,
            )
            db.session.add(item_entry)

        # 3. Add Sender and Recipient Address Snapshots
        sender_addr = ShipmentAddress(
            shipment_id=shipment.id,
            address_role="SENDER",
            person_name=sender_data.get("person_name") or sender_data.get("name", "Sender"),
            phone=sender_data["phone"],
            line1=sender_data["line1"],
            city=sender_data["city"],
            postal_code=sender_data.get("postal_code"),
            zone_id=sender_data["zone_id"],
            created_by=actor_user_id,
        )
        recipient_addr = ShipmentAddress(
            shipment_id=shipment.id,
            address_role="RECIPIENT",
            person_name=recipient_data.get("person_name") or recipient_data.get("name", "Recipient"),
            phone=recipient_data["phone"],
            line1=recipient_data["line1"],
            city=recipient_data["city"],
            postal_code=recipient_data.get("postal_code"),
            zone_id=recipient_data["zone_id"],
            created_by=actor_user_id,
        )
        db.session.add(sender_addr)
        db.session.add(recipient_addr)
        db.session.flush()

        # 4. Save Quote Snapshot
        quote_snapshot = ShipmentQuote(
            shipment_id=shipment.id,
            service_type_id=service_type_id,
            quoted_rate_card_id=quote["rate_card_id"],
            quoted_rule_id=quote["rule_id"],
            base_fee_paisa=quote["base_fee_paisa"],
            packaging_fee_paisa=quote["packaging_fee_paisa"],
            discount_paisa=quote["discount_paisa"],
            tax_paisa=quote["tax_paisa"],
            total_paisa=quote["total_paisa"],
            currency=quote["currency"],
            created_by=actor_user_id,
        )
        db.session.add(quote_snapshot)

        # 5. Save Discount link if applied
        if quote.get("discount_id"):
            shipment_discount = ShipmentDiscount(
                shipment_id=shipment.id,
                discount_id=quote["discount_id"],
                applied_amount_paisa=quote["discount_paisa"],
                created_by=actor_user_id,
            )
            db.session.add(shipment_discount)

        # 6. Status History & Tracking Event
        history = ShipmentStatusHistory(
            shipment_id=shipment.id,
            previous_status="DRAFT",
            new_status="BOOKED",
            changed_at=datetime.utcnow(),
            actor_user_id=actor_user_id,
            reason="Initial booking",
            created_by=actor_user_id,
        )
        db.session.add(history)
        db.session.flush()

        tracking_event = TrackingEvent(
            shipment_id=shipment.id,
            status_history_id=history.id,
            event_code="BOOKED",
            public_message=ShipmentService.STATUS_MESSAGES["BOOKED"],
            occurred_at=datetime.utcnow(),
            actor_user_id=actor_user_id,
            visible_to_customer=True,
            created_by=actor_user_id,
        )
        db.session.add(tracking_event)

        # 7. Optional Pickup Request
        if schedule_pickup:
            pickup_req = PickupRequest(
                shipment_id=shipment.id,
                pickup_address_id=sender_addr.id,
                requested_start=datetime.utcnow(),
                requested_end=datetime.utcnow() + timedelta(hours=4),
                pickup_status="PENDING",
                notes=pickup_notes,
                created_by=actor_user_id,
            )
            db.session.add(pickup_req)

        # 8. Create Billing Invoice
        invoice = Invoice(
            shipment_id=shipment.id,
            customer_id=customer_id,
            invoice_number=generate_invoice_number(),
            subtotal_paisa=quote["base_fee_paisa"] + quote["packaging_fee_paisa"],
            discount_paisa=quote["discount_paisa"],
            tax_paisa=quote["tax_paisa"],
            total_paisa=quote["total_paisa"],
            currency=quote["currency"],
            invoice_status="ISSUED",
            issued_at=datetime.utcnow(),
            due_at=datetime.utcnow() + timedelta(days=7),
            created_by=actor_user_id,
        )
        db.session.add(invoice)
        db.session.flush()

        # Add invoice line item
        inv_item = InvoiceItem(
            invoice_id=invoice.id,
            shipment_service_id=quote_snapshot.id,
            description=f"Freight charge ({tracking_num})",
            quantity=1,
            unit_price_paisa=invoice.subtotal_paisa,
            line_total_paisa=invoice.subtotal_paisa,
            created_by=actor_user_id,
        )
        db.session.add(inv_item)

        log_audit(
            action="CREATE",
            entity_type="Shipment",
            entity_id=shipment.id,
            after={"tracking_number": tracking_num, "total_paisa": quote["total_paisa"]},
            branch_id=origin_branch_id,
            user_id=actor_user_id,
        )

        db.session.commit()
        return shipment

    @staticmethod
    def transition(shipment_id: int, target_status: str, actor_user_id: int, reason: str = None, hub_id: int = None) -> Shipment:
        """
        Validate and perform a state machine transition on a shipment.
        """
        shipment = Shipment.query.filter_by(id=shipment_id, is_deleted=False).with_for_update().first()
        if not shipment:
            raise ValueError("Shipment not found.")

        current = shipment.shipment_status
        allowed = ShipmentService.ALLOWED_TRANSITIONS.get(current, [])

        if target_status not in allowed:
            raise ValueError(f"Invalid transition from '{current}' to '{target_status}'. Allowed targets: {allowed}")

        # Update status
        shipment.shipment_status = target_status
        if hub_id:
            shipment.current_hub_id = hub_id
        shipment.updated_at = datetime.utcnow()
        shipment.updated_by = actor_user_id

        # Write status history
        history = ShipmentStatusHistory(
            shipment_id=shipment.id,
            previous_status=current,
            new_status=target_status,
            changed_at=datetime.utcnow(),
            actor_user_id=actor_user_id,
            reason=reason or f"Status changed to {target_status}",
            created_by=actor_user_id,
        )
        db.session.add(history)
        db.session.flush()

        # Public tracking event
        msg = ShipmentService.STATUS_MESSAGES.get(target_status, f"Shipment status is now {target_status}.")
        tracking_event = TrackingEvent(
            shipment_id=shipment.id,
            status_history_id=history.id,
            event_code=target_status,
            public_message=msg,
            occurred_at=datetime.utcnow(),
            hub_id=hub_id or shipment.current_hub_id,
            actor_user_id=actor_user_id,
            visible_to_customer=True,
            created_by=actor_user_id,
        )
        db.session.add(tracking_event)

        log_audit(
            action="UPDATE_STATUS",
            entity_type="Shipment",
            entity_id=shipment.id,
            before={"status": current},
            after={"status": target_status, "reason": reason},
            branch_id=shipment.origin_branch_id,
            user_id=actor_user_id,
        )

        db.session.commit()
        return shipment
