from datetime import datetime
from app.extensions import db
from app.models.base import AuditMixin

class Shipment(AuditMixin, db.Model):
    """23. shipments — Core parcel/consignment record."""
    __tablename__ = "shipments"
    __table_args__ = (
        db.CheckConstraint("weight_grams > 0", name="chk_shipment_weight_pos"),
        db.CheckConstraint("declared_value_paisa >= 0", name="chk_shipment_value_nonneg"),
        db.CheckConstraint("cod_due_paisa >= 0", name="chk_shipment_cod_nonneg"),
        db.CheckConstraint("total_charge_paisa >= 0", name="chk_shipment_total_nonneg"),
    )

    tracking_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    origin_branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    destination_branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True)
    service_type_id = db.Column(db.Integer, db.ForeignKey("service_types.id", ondelete="RESTRICT"), nullable=False)
    parcel_category_id = db.Column(db.Integer, db.ForeignKey("parcel_categories.id", ondelete="RESTRICT"), nullable=False)
    packaging_type_id = db.Column(db.Integer, db.ForeignKey("packaging_types.id", ondelete="RESTRICT"), nullable=False)
    booking_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    current_hub_id = db.Column(db.Integer, db.ForeignKey("hubs.id", ondelete="SET NULL"), nullable=True)

    weight_grams = db.Column(db.Integer, nullable=False)
    declared_value_paisa = db.Column(db.Integer, default=0, nullable=False)
    cod_due_paisa = db.Column(db.Integer, default=0, nullable=False)
    booked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    shipment_status = db.Column(db.String(40), default="BOOKED", nullable=False, index=True)
    total_charge_paisa = db.Column(db.Integer, default=0, nullable=False)

    # Relationships
    customer = db.relationship("Customer", foreign_keys=[customer_id], back_populates="shipments")
    origin_branch = db.relationship("Branch", foreign_keys=[origin_branch_id])
    destination_branch = db.relationship("Branch", foreign_keys=[destination_branch_id])
    service_type = db.relationship("ServiceType", foreign_keys=[service_type_id])
    parcel_category = db.relationship("ParcelCategory", foreign_keys=[parcel_category_id])
    packaging_type = db.relationship("PackagingType", foreign_keys=[packaging_type_id])
    booking_employee = db.relationship("Employee", foreign_keys=[booking_employee_id])
    current_hub = db.relationship("Hub", foreign_keys=[current_hub_id])

    items = db.relationship("ShipmentItem", foreign_keys="ShipmentItem.shipment_id", back_populates="shipment", cascade="all, delete-orphan")
    addresses = db.relationship("ShipmentAddress", foreign_keys="ShipmentAddress.shipment_id", back_populates="shipment", cascade="all, delete-orphan")
    service_quote = db.relationship("ShipmentService", foreign_keys="ShipmentService.shipment_id", back_populates="shipment", uselist=False, cascade="all, delete-orphan")
    documents = db.relationship("ShipmentDocument", foreign_keys="ShipmentDocument.shipment_id", back_populates="shipment", cascade="all, delete-orphan")
    pickup_requests = db.relationship("PickupRequest", foreign_keys="PickupRequest.shipment_id", back_populates="shipment", cascade="all, delete-orphan")
    status_history = db.relationship("ShipmentStatusHistory", foreign_keys="ShipmentStatusHistory.shipment_id", back_populates="shipment", cascade="all, delete-orphan")

    invoice = db.relationship("Invoice", foreign_keys="Invoice.shipment_id", back_populates="shipment", uselist=False)
    cod_collection = db.relationship("CodCollection", foreign_keys="CodCollection.shipment_id", back_populates="shipment", uselist=False)
    scans = db.relationship("ShipmentScan", foreign_keys="ShipmentScan.shipment_id", back_populates="shipment", cascade="all, delete-orphan")
    tracking_events = db.relationship("TrackingEvent", foreign_keys="TrackingEvent.shipment_id", back_populates="shipment", cascade="all, delete-orphan")
    route_stops = db.relationship("RouteStop", foreign_keys="RouteStop.shipment_id", back_populates="shipment")
    delivery_attempts = db.relationship("DeliveryAttempt", foreign_keys="DeliveryAttempt.shipment_id", back_populates="shipment", cascade="all, delete-orphan")
    delivery_proof = db.relationship("DeliveryProof", foreign_keys="DeliveryProof.shipment_id", back_populates="shipment", uselist=False, cascade="all, delete-orphan")
    delivery_exceptions = db.relationship("DeliveryException", foreign_keys="DeliveryException.shipment_id", back_populates="shipment", cascade="all, delete-orphan")

    @property
    def sender_address(self):
        for addr in self.addresses:
            if addr.address_role == "SENDER":
                return addr
        return None

    @property
    def recipient_address(self):
        for addr in self.addresses:
            if addr.address_role == "RECIPIENT":
                return addr
        return None

    def __repr__(self):
        return f"<Shipment tracking='{self.tracking_number}' status='{self.shipment_status}'>"


class ShipmentItem(AuditMixin, db.Model):
    """24. shipment_items — Items enclosed within a parcel."""
    __tablename__ = "shipment_items"
    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="chk_item_quantity_pos"),
        db.CheckConstraint("weight_grams > 0", name="chk_item_weight_pos"),
        db.CheckConstraint("declared_value_paisa >= 0", name="chk_item_value_nonneg"),
    )

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    weight_grams = db.Column(db.Integer, default=1, nullable=False)
    declared_value_paisa = db.Column(db.Integer, default=0, nullable=False)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="items")


class ShipmentAddress(AuditMixin, db.Model):
    """25. shipment_addresses — Immutable snapshot of sender/recipient at booking."""
    __tablename__ = "shipment_addresses"
    __table_args__ = (
        db.UniqueConstraint("shipment_id", "address_role", name="uq_shipment_role_addr"),
        db.CheckConstraint("address_role IN ('SENDER', 'RECIPIENT')", name="chk_address_role_valid"),
    )

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    address_role = db.Column(db.String(20), nullable=False)  # SENDER or RECIPIENT
    person_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    line1 = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=True)
    zone_id = db.Column(db.Integer, db.ForeignKey("service_zones.id", ondelete="RESTRICT"), nullable=False)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="addresses")
    zone = db.relationship("ServiceZone", foreign_keys=[zone_id])


class ShipmentService(AuditMixin, db.Model):
    """26. shipment_services — Frozen price quote breakdown for a shipment."""
    __tablename__ = "shipment_services"
    __table_args__ = (
        db.CheckConstraint("base_fee_paisa >= 0", name="chk_quote_base_fee_nonneg"),
        db.CheckConstraint("packaging_fee_paisa >= 0", name="chk_quote_pkg_fee_nonneg"),
        db.CheckConstraint("discount_paisa >= 0", name="chk_quote_discount_nonneg"),
        db.CheckConstraint("tax_paisa >= 0", name="chk_quote_tax_nonneg"),
        db.CheckConstraint("total_paisa >= 0", name="chk_quote_total_nonneg"),
    )

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), unique=True, nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey("service_types.id", ondelete="RESTRICT"), nullable=False)
    quoted_rate_card_id = db.Column(db.Integer, db.ForeignKey("rate_cards.id", ondelete="RESTRICT"), nullable=False)
    quoted_rule_id = db.Column(db.Integer, db.ForeignKey("rate_card_rules.id", ondelete="RESTRICT"), nullable=False)

    base_fee_paisa = db.Column(db.Integer, nullable=False)
    packaging_fee_paisa = db.Column(db.Integer, default=0, nullable=False)
    discount_paisa = db.Column(db.Integer, default=0, nullable=False)
    tax_paisa = db.Column(db.Integer, default=0, nullable=False)
    total_paisa = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), default="PKR", nullable=False)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="service_quote")
    service_type = db.relationship("ServiceType", foreign_keys=[service_type_id])
    rate_card = db.relationship("RateCard", foreign_keys=[quoted_rate_card_id])
    rate_card_rule = db.relationship("RateCardRule", foreign_keys=[quoted_rule_id])


class ShipmentDocument(AuditMixin, db.Model):
    """27. shipment_documents — Attachments/customs declarations/waybills."""
    __tablename__ = "shipment_documents"

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="documents")
    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_user_id])


class PickupRequest(AuditMixin, db.Model):
    """28. pickup_requests — Sender on-demand parcel collection request."""
    __tablename__ = "pickup_requests"

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    pickup_address_id = db.Column(db.Integer, db.ForeignKey("shipment_addresses.id", ondelete="RESTRICT"), nullable=False)
    requested_start = db.Column(db.DateTime, nullable=False)
    requested_end = db.Column(db.DateTime, nullable=False)
    pickup_status = db.Column(db.String(30), default="PENDING", nullable=False)
    notes = db.Column(db.String(255), nullable=True)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="pickup_requests")
    pickup_address = db.relationship("ShipmentAddress", foreign_keys=[pickup_address_id])
    assignments = db.relationship("PickupAssignment", foreign_keys="PickupAssignment.pickup_request_id", back_populates="pickup_request", cascade="all, delete-orphan")


class PickupAssignment(AuditMixin, db.Model):
    """29. pickup_assignments — Driver/Staff assignment for physical collection."""
    __tablename__ = "pickup_assignments"

    pickup_request_id = db.Column(db.Integer, db.ForeignKey("pickup_requests.id", ondelete="CASCADE"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    pickup_request = db.relationship("PickupRequest", foreign_keys=[pickup_request_id], back_populates="assignments")
    employee = db.relationship("Employee", foreign_keys=[employee_id])
    driver = db.relationship("Driver", foreign_keys=[driver_id])
    vehicle = db.relationship("Vehicle", foreign_keys=[vehicle_id])


class ShipmentStatusHistory(AuditMixin, db.Model):
    """30. shipment_status_history — Append-only chronological status audit log."""
    __tablename__ = "shipment_status_history"

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    previous_status = db.Column(db.String(40), nullable=True)
    new_status = db.Column(db.String(40), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = db.Column(db.String(255), nullable=True)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="status_history")
    actor = db.relationship("User", foreign_keys=[actor_user_id])
