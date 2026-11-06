from app.extensions import db
from app.models.base import AuditMixin

class Customer(AuditMixin, db.Model):
    """13. customers — Customer master record."""
    __tablename__ = "customers"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    customer_code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(180), nullable=True)

    user = db.relationship("User", foreign_keys=[user_id], back_populates="customer")
    contacts = db.relationship("CustomerContact", foreign_keys="CustomerContact.customer_id", back_populates="customer", cascade="all, delete-orphan")
    addresses = db.relationship("CustomerAddress", foreign_keys="CustomerAddress.customer_id", back_populates="customer", cascade="all, delete-orphan")
    recipient_profiles = db.relationship("RecipientProfile", foreign_keys="RecipientProfile.customer_id", back_populates="customer", cascade="all, delete-orphan")
    shipments = db.relationship("Shipment", foreign_keys="Shipment.customer_id", back_populates="customer")

    @property
    def recipients(self):
        return self.recipient_profiles

    def __repr__(self):
        return f"<Customer code='{self.customer_code}' name='{self.full_name}'>"


class CustomerContact(AuditMixin, db.Model):
    """14. customer_contacts — Alternate or secondary customer contact."""
    __tablename__ = "customer_contacts"

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    contact_type = db.Column(db.String(40), default="PRIMARY", nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)

    customer = db.relationship("Customer", foreign_keys=[customer_id], back_populates="contacts")


class CustomerAddress(AuditMixin, db.Model):
    """15. customer_addresses — Saved addresses for customers."""
    __tablename__ = "customer_addresses"

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey("service_zones.id", ondelete="RESTRICT"), nullable=False)
    label = db.Column(db.String(60), default="Office", nullable=False)
    line1 = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=True)

    customer = db.relationship("Customer", foreign_keys=[customer_id], back_populates="addresses")
    zone = db.relationship("ServiceZone", foreign_keys=[zone_id])


class RecipientProfile(AuditMixin, db.Model):
    """16. recipient_profiles — Saved recipients associated with a sender customer."""
    __tablename__ = "recipient_profiles"

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(180), nullable=True)

    customer = db.relationship("Customer", foreign_keys=[customer_id], back_populates="recipient_profiles")
    addresses = db.relationship("RecipientAddress", foreign_keys="RecipientAddress.recipient_id", back_populates="recipient", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RecipientProfile name='{self.name}' phone='{self.phone}'>"


class RecipientAddress(AuditMixin, db.Model):
    """17. recipient_addresses — Saved destination address for recipient profile."""
    __tablename__ = "recipient_addresses"

    recipient_id = db.Column(db.Integer, db.ForeignKey("recipient_profiles.id", ondelete="CASCADE"), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey("service_zones.id", ondelete="RESTRICT"), nullable=False)
    line1 = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=True)

    recipient = db.relationship("RecipientProfile", foreign_keys=[recipient_id], back_populates="addresses")
    zone = db.relationship("ServiceZone", foreign_keys=[zone_id])


class ServiceType(AuditMixin, db.Model):
    """18. service_types — Speed/tier offering (Standard, Express, Overnight)."""
    __tablename__ = "service_types"

    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    target_days = db.Column(db.Integer, default=2, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<ServiceType code='{self.code}'>"


class ParcelCategory(AuditMixin, db.Model):
    """19. parcel_categories — Categorization (Documents, Fragile, Electronics)."""
    __tablename__ = "parcel_categories"

    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    is_fragile = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<ParcelCategory code='{self.code}'>"


class PackagingType(AuditMixin, db.Model):
    """20. packaging_types — Box/Flyer type with dimensions and packaging fee."""
    __tablename__ = "packaging_types"
    __table_args__ = (
        db.CheckConstraint("fee_paisa >= 0", name="chk_packaging_fee_nonneg"),
        db.CheckConstraint("max_weight_grams > 0", name="chk_packaging_weight_pos"),
    )

    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    fee_paisa = db.Column(db.Integer, default=0, nullable=False)
    max_weight_grams = db.Column(db.Integer, default=5000, nullable=False)

    def __repr__(self):
        return f"<PackagingType code='{self.code}'>"


class RateCard(AuditMixin, db.Model):
    """21. rate_cards — Pricing schedule between origin and destination zones."""
    __tablename__ = "rate_cards"
    __table_args__ = (
        db.UniqueConstraint("service_type_id", "origin_zone_id", "destination_zone_id", "valid_from", name="uq_rate_card_matrix"),
    )

    service_type_id = db.Column(db.Integer, db.ForeignKey("service_types.id", ondelete="RESTRICT"), nullable=False)
    origin_zone_id = db.Column(db.Integer, db.ForeignKey("service_zones.id", ondelete="RESTRICT"), nullable=False)
    destination_zone_id = db.Column(db.Integer, db.ForeignKey("service_zones.id", ondelete="RESTRICT"), nullable=False)
    valid_from = db.Column(db.Date, nullable=False)
    valid_until = db.Column(db.Date, nullable=False)
    currency = db.Column(db.String(10), default="PKR", nullable=False)

    service_type = db.relationship("ServiceType", foreign_keys=[service_type_id])
    origin_zone = db.relationship("ServiceZone", foreign_keys=[origin_zone_id])
    destination_zone = db.relationship("ServiceZone", foreign_keys=[destination_zone_id])
    rules = db.relationship("RateCardRule", foreign_keys="RateCardRule.rate_card_id", back_populates="rate_card", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RateCard id={self.id} st={self.service_type_id} from={self.origin_zone_id} to={self.destination_zone_id}>"


class RateCardRule(AuditMixin, db.Model):
    """22. rate_card_rules — Weight slabs and pricing within a rate card."""
    __tablename__ = "rate_card_rules"
    __table_args__ = (
        db.CheckConstraint("min_weight_grams < max_weight_grams", name="chk_weight_range"),
        db.CheckConstraint("base_fee_paisa >= 0", name="chk_base_fee_nonneg"),
        db.CheckConstraint("extra_per_kg_paisa >= 0", name="chk_extra_per_kg_nonneg"),
    )

    rate_card_id = db.Column(db.Integer, db.ForeignKey("rate_cards.id", ondelete="CASCADE"), nullable=False)
    min_weight_grams = db.Column(db.Integer, default=0, nullable=False)
    max_weight_grams = db.Column(db.Integer, nullable=False)
    base_fee_paisa = db.Column(db.Integer, nullable=False)
    extra_per_kg_paisa = db.Column(db.Integer, default=0, nullable=False)

    rate_card = db.relationship("RateCard", foreign_keys=[rate_card_id], back_populates="rules")
