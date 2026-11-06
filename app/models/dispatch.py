from datetime import datetime, date
from app.extensions import db
from app.models.base import AuditMixin

class Route(AuditMixin, db.Model):
    """31. routes — Delivery run for a vehicle and driver on a specific date."""
    __tablename__ = "routes"

    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False)
    route_code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    route_date = db.Column(db.Date, default=date.today, nullable=False)
    route_status = db.Column(db.String(30), default="PLANNED", nullable=False)

    branch = db.relationship("Branch", foreign_keys=[branch_id], back_populates="routes")
    driver = db.relationship("Driver", foreign_keys=[driver_id])
    vehicle = db.relationship("Vehicle", foreign_keys=[vehicle_id])
    stops = db.relationship("RouteStop", foreign_keys="RouteStop.route_id", back_populates="route", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Route code='{self.route_code}' date='{self.route_date}'>"


class RouteStop(AuditMixin, db.Model):
    """32. route_stops — Sequenced stop along an assigned route."""
    __tablename__ = "route_stops"
    __table_args__ = (
        db.UniqueConstraint("route_id", "stop_sequence", name="uq_route_sequence"),
    )

    route_id = db.Column(db.Integer, db.ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="RESTRICT"), nullable=False)
    stop_sequence = db.Column(db.Integer, nullable=False)
    stop_type = db.Column(db.String(30), default="DELIVERY", nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    route = db.relationship("Route", foreign_keys=[route_id], back_populates="stops")
    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="route_stops")
    delivery_attempts = db.relationship("DeliveryAttempt", foreign_keys="DeliveryAttempt.route_stop_id", back_populates="route_stop")


class HubTransfer(AuditMixin, db.Model):
    """33. hub_transfers — Inter-hub freight transfer of parcels."""
    __tablename__ = "hub_transfers"
    __table_args__ = (
        db.CheckConstraint("from_hub_id != to_hub_id", name="chk_hub_transfer_distinct"),
    )

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    from_hub_id = db.Column(db.Integer, db.ForeignKey("hubs.id", ondelete="RESTRICT"), nullable=False)
    to_hub_id = db.Column(db.Integer, db.ForeignKey("hubs.id", ondelete="RESTRICT"), nullable=False)
    initiated_by_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    received_by_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    departed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    received_at = db.Column(db.DateTime, nullable=True)
    transfer_status = db.Column(db.String(30), default="IN_TRANSIT", nullable=False)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id])
    from_hub = db.relationship("Hub", foreign_keys=[from_hub_id])
    to_hub = db.relationship("Hub", foreign_keys=[to_hub_id])
    initiated_by = db.relationship("Employee", foreign_keys=[initiated_by_employee_id])
    received_by = db.relationship("Employee", foreign_keys=[received_by_employee_id])


class ShipmentScan(AuditMixin, db.Model):
    """34. shipment_scans — Physical barcode scan events at hubs or on the road."""
    __tablename__ = "shipment_scans"

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    hub_id = db.Column(db.Integer, db.ForeignKey("hubs.id", ondelete="SET NULL"), nullable=True)
    scanned_by_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    scan_code = db.Column(db.String(40), nullable=False)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.String(255), nullable=True)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="scans")
    hub = db.relationship("Hub", foreign_keys=[hub_id])
    scanned_by = db.relationship("Employee", foreign_keys=[scanned_by_employee_id])


class TrackingEvent(AuditMixin, db.Model):
    """35. tracking_events — Public & customer visible tracking milestones."""
    __tablename__ = "tracking_events"

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    status_history_id = db.Column(db.Integer, db.ForeignKey("shipment_status_history.id", ondelete="SET NULL"), nullable=True)
    event_code = db.Column(db.String(50), nullable=False)
    public_message = db.Column(db.String(255), nullable=False)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    hub_id = db.Column(db.Integer, db.ForeignKey("hubs.id", ondelete="SET NULL"), nullable=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    visible_to_customer = db.Column(db.Boolean, default=True, nullable=False)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="tracking_events")
    status_history = db.relationship("ShipmentStatusHistory", foreign_keys=[status_history_id])
    hub = db.relationship("Hub", foreign_keys=[hub_id])
    actor = db.relationship("User", foreign_keys=[actor_user_id])


class DeliveryAttempt(AuditMixin, db.Model):
    """36. delivery_attempts — Field delivery attempt recorded by a driver."""
    __tablename__ = "delivery_attempts"
    __table_args__ = (
        db.CheckConstraint("outcome IN ('SUCCESS', 'FAILED', 'RESCHEDULED')", name="chk_attempt_outcome"),
    )

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    route_stop_id = db.Column(db.Integer, db.ForeignKey("route_stops.id", ondelete="SET NULL"), nullable=True)
    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    outcome = db.Column(db.String(30), nullable=False)
    failure_reason = db.Column(db.String(255), nullable=True)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="delivery_attempts")
    route_stop = db.relationship("RouteStop", foreign_keys=[route_stop_id], back_populates="delivery_attempts")
    driver = db.relationship("Driver", foreign_keys=[driver_id])
    proof = db.relationship("DeliveryProof", foreign_keys="DeliveryProof.delivery_attempt_id", back_populates="delivery_attempt", uselist=False, cascade="all, delete-orphan")
    exceptions = db.relationship("DeliveryException", foreign_keys="DeliveryException.delivery_attempt_id", back_populates="delivery_attempt")


class DeliveryProof(AuditMixin, db.Model):
    """37. delivery_proofs — Electronic proof of successful delivery."""
    __tablename__ = "delivery_proofs"

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    delivery_attempt_id = db.Column(db.Integer, db.ForeignKey("delivery_attempts.id", ondelete="CASCADE"), unique=True, nullable=False)
    received_by_name = db.Column(db.String(150), nullable=False)
    signed_filename = db.Column(db.String(255), nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)
    delivered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="delivery_proof")
    delivery_attempt = db.relationship("DeliveryAttempt", foreign_keys=[delivery_attempt_id], back_populates="proof")


class DeliveryException(AuditMixin, db.Model):
    """38. delivery_exceptions — Exceptions, damages, or address inaccuracies."""
    __tablename__ = "delivery_exceptions"

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    delivery_attempt_id = db.Column(db.Integer, db.ForeignKey("delivery_attempts.id", ondelete="SET NULL"), nullable=True)
    exception_code = db.Column(db.String(50), nullable=False)
    explanation = db.Column(db.String(255), nullable=False)
    opened_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="delivery_exceptions")
    delivery_attempt = db.relationship("DeliveryAttempt", foreign_keys=[delivery_attempt_id], back_populates="exceptions")


class Vehicle(AuditMixin, db.Model):
    """39. vehicles — Fleet transport asset (motorcycle, van, truck)."""
    __tablename__ = "vehicles"

    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    plate_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    vehicle_type = db.Column(db.String(40), nullable=False)
    capacity_grams = db.Column(db.Integer, default=50000, nullable=False)
    service_due_on = db.Column(db.Date, nullable=True)

    branch = db.relationship("Branch", foreign_keys=[branch_id])

    def __repr__(self):
        return f"<Vehicle plate='{self.plate_number}' type='{self.vehicle_type}'>"


class Driver(AuditMixin, db.Model):
    """40. drivers — Courier delivery driver certification profile."""
    __tablename__ = "drivers"

    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), unique=True, nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    license_expires_on = db.Column(db.Date, nullable=False)

    employee = db.relationship("Employee", foreign_keys=[employee_id], back_populates="driver_profile")

    def __repr__(self):
        return f"<Driver license='{self.license_number}'>"


class VehicleAssignment(AuditMixin, db.Model):
    """41. vehicle_assignments — Active/historic driver vehicle allocations."""
    __tablename__ = "vehicle_assignments"

    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.id", ondelete="SET NULL"), nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    released_at = db.Column(db.DateTime, nullable=True)

    vehicle = db.relationship("Vehicle", foreign_keys=[vehicle_id])
    driver = db.relationship("Driver", foreign_keys=[driver_id])
    route = db.relationship("Route", foreign_keys=[route_id])
