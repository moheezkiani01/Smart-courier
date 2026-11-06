from datetime import datetime
from app.extensions import db
from app.models.base import AuditMixin

class Invoice(AuditMixin, db.Model):
    """42. invoices — Billing document for booked shipment shipping fees."""
    __tablename__ = "invoices"
    __table_args__ = (
        db.CheckConstraint("subtotal_paisa >= 0", name="chk_invoice_subtotal_nonneg"),
        db.CheckConstraint("discount_paisa >= 0", name="chk_invoice_discount_nonneg"),
        db.CheckConstraint("tax_paisa >= 0", name="chk_invoice_tax_nonneg"),
        db.CheckConstraint("total_paisa >= 0", name="chk_invoice_total_nonneg"),
    )

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="RESTRICT"), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)

    subtotal_paisa = db.Column(db.Integer, nullable=False)
    discount_paisa = db.Column(db.Integer, default=0, nullable=False)
    tax_paisa = db.Column(db.Integer, default=0, nullable=False)
    total_paisa = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), default="PKR", nullable=False)
    invoice_status = db.Column(db.String(30), default="ISSUED", nullable=False)  # ISSUED, PAID, CANCELLED, REFUNDED
    issued_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_at = db.Column(db.DateTime, nullable=False)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="invoice")
    customer = db.relationship("Customer", foreign_keys=[customer_id])
    items = db.relationship("InvoiceItem", foreign_keys="InvoiceItem.invoice_id", back_populates="invoice", cascade="all, delete-orphan")
    payments = db.relationship("Payment", foreign_keys="Payment.invoice_id", back_populates="invoice", cascade="all, delete-orphan")

    @property
    def total_paid_paisa(self):
        paid = sum(p.amount_paisa for p in self.payments if p.payment_status == "SETTLED" and not p.is_deleted)
        refunded = sum(
            r.amount_paisa
            for p in self.payments
            for r in p.refunds
            if r.refund_status == "PROCESSED" and not r.is_deleted
        )
        return max(0, paid - refunded)

    @property
    def amount_due_paisa(self):
        return max(0, self.total_paisa - self.total_paid_paisa)

    def __repr__(self):
        return f"<Invoice num='{self.invoice_number}' total={self.total_paisa} status='{self.invoice_status}'>"


class InvoiceItem(AuditMixin, db.Model):
    """43. invoice_items — Line items in an invoice."""
    __tablename__ = "invoice_items"
    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="chk_invitem_qty_pos"),
        db.CheckConstraint("unit_price_paisa >= 0", name="chk_invitem_unit_nonneg"),
        db.CheckConstraint("line_total_paisa >= 0", name="chk_invitem_line_nonneg"),
    )

    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    shipment_service_id = db.Column(db.Integer, db.ForeignKey("shipment_services.id", ondelete="SET NULL"), nullable=True)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price_paisa = db.Column(db.Integer, nullable=False)
    line_total_paisa = db.Column(db.Integer, nullable=False)

    invoice = db.relationship("Invoice", foreign_keys=[invoice_id], back_populates="items")
    shipment_service = db.relationship("ShipmentService", foreign_keys=[shipment_service_id])


class Payment(AuditMixin, db.Model):
    """44. payments — Settled payment transaction against an invoice."""
    __tablename__ = "payments"
    __table_args__ = (
        db.CheckConstraint("amount_paisa > 0", name="chk_payment_amt_pos"),
    )

    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False)
    received_by_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    amount_paisa = db.Column(db.Integer, nullable=False)
    method = db.Column(db.String(30), nullable=False)  # CASH, BANK_TRANSFER, SIMULATED_ONLINE
    reference_code = db.Column(db.String(60), nullable=True)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    payment_status = db.Column(db.String(30), default="SETTLED", nullable=False)

    invoice = db.relationship("Invoice", foreign_keys=[invoice_id], back_populates="payments")
    received_by = db.relationship("Employee", foreign_keys=[received_by_employee_id])
    refunds = db.relationship("Refund", foreign_keys="Refund.payment_id", back_populates="payment", cascade="all, delete-orphan")


class CodCollection(AuditMixin, db.Model):
    """45. cod_collections — Cash-on-delivery collected from recipient by driver."""
    __tablename__ = "cod_collections"
    __table_args__ = (
        db.CheckConstraint("amount_paisa > 0", name="chk_cod_coll_amt_pos"),
    )

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="RESTRICT"), unique=True, nullable=False)
    collected_by_driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False)
    amount_paisa = db.Column(db.Integer, nullable=False)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    collection_status = db.Column(db.String(30), default="COLLECTED", nullable=False)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id], back_populates="cod_collection")
    collected_by = db.relationship("Driver", foreign_keys=[collected_by_driver_id])
    remittances = db.relationship("CodRemittance", foreign_keys="CodRemittance.cod_collection_id", back_populates="cod_collection", cascade="all, delete-orphan")

    @property
    def total_remitted_paisa(self):
        return sum(r.amount_paisa for r in self.remittances if r.remittance_status == "COMPLETED" and not r.is_deleted)

    @property
    def pending_remittance_paisa(self):
        return max(0, self.amount_paisa - self.total_remitted_paisa)


class CodRemittance(AuditMixin, db.Model):
    """46. cod_remittances — Remittance of collected COD funds back to sender."""
    __tablename__ = "cod_remittances"
    __table_args__ = (
        db.CheckConstraint("amount_paisa > 0", name="chk_cod_remit_amt_pos"),
    )

    cod_collection_id = db.Column(db.Integer, db.ForeignKey("cod_collections.id", ondelete="RESTRICT"), nullable=False)
    received_by_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    amount_paisa = db.Column(db.Integer, nullable=False)
    remitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reference_code = db.Column(db.String(60), nullable=False)
    remittance_status = db.Column(db.String(30), default="COMPLETED", nullable=False)

    cod_collection = db.relationship("CodCollection", foreign_keys=[cod_collection_id], back_populates="remittances")
    received_by = db.relationship("Employee", foreign_keys=[received_by_employee_id])


class Refund(AuditMixin, db.Model):
    """47. refunds — Reversal/refund against a settled invoice payment."""
    __tablename__ = "refunds"
    __table_args__ = (
        db.CheckConstraint("amount_paisa > 0", name="chk_refund_amt_pos"),
    )

    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False)
    authorized_by_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    amount_paisa = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    refund_status = db.Column(db.String(30), default="PROCESSED", nullable=False)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processed_at = db.Column(db.DateTime, nullable=True)

    payment = db.relationship("Payment", foreign_keys=[payment_id], back_populates="refunds")
    authorized_by = db.relationship("Employee", foreign_keys=[authorized_by_employee_id])


class Discount(AuditMixin, db.Model):
    """48. discounts — Promotional discount voucher / code."""
    __tablename__ = "discounts"
    __table_args__ = (
        db.CheckConstraint("discount_type IN ('FIXED', 'PERCENTAGE')", name="chk_discount_type"),
        db.CheckConstraint("value > 0", name="chk_discount_val_pos"),
    )

    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    discount_type = db.Column(db.String(20), nullable=False)  # FIXED (paisa) or PERCENTAGE (basis points)
    value = db.Column(db.Integer, nullable=False)
    valid_from = db.Column(db.Date, nullable=False)
    valid_until = db.Column(db.Date, nullable=False)
    max_redemptions = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"<Discount code='{self.code}' type='{self.discount_type}' val={self.value}>"


class ShipmentDiscount(AuditMixin, db.Model):
    """49. shipment_discounts — Association of applied discount to a shipment."""
    __tablename__ = "shipment_discounts"
    __table_args__ = (
        db.UniqueConstraint("shipment_id", "discount_id", name="uq_shipment_discount"),
        db.CheckConstraint("applied_amount_paisa >= 0", name="chk_discount_applied_nonneg"),
    )

    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    discount_id = db.Column(db.Integer, db.ForeignKey("discounts.id", ondelete="RESTRICT"), nullable=False)
    applied_amount_paisa = db.Column(db.Integer, nullable=False)

    shipment = db.relationship("Shipment", foreign_keys=[shipment_id])
    discount = db.relationship("Discount", foreign_keys=[discount_id])
