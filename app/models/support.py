from datetime import datetime
from app.extensions import db
from app.models.base import AuditMixin

class SupportTicket(AuditMixin, db.Model):
    """50. support_tickets — Customer complaint/inquiry ticket."""
    __tablename__ = "support_tickets"

    ticket_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True)
    assigned_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)

    subject = db.Column(db.String(200), nullable=False)
    priority = db.Column(db.String(20), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH, URGENT
    ticket_status = db.Column(db.String(30), default="OPEN", nullable=False)  # OPEN, IN_PROGRESS, RESOLVED, CLOSED
    opened_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    closed_at = db.Column(db.DateTime, nullable=True)

    customer = db.relationship("Customer", foreign_keys=[customer_id])
    shipment = db.relationship("Shipment", foreign_keys=[shipment_id])
    assigned_employee = db.relationship("Employee", foreign_keys=[assigned_employee_id])
    messages = db.relationship("TicketMessage", foreign_keys="TicketMessage.ticket_id", back_populates="ticket", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SupportTicket no='{self.ticket_number}' status='{self.ticket_status}'>"


class TicketMessage(AuditMixin, db.Model):
    """51. ticket_messages — Conversation stream / responses within a ticket."""
    __tablename__ = "ticket_messages"

    ticket_id = db.Column(db.Integer, db.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False)
    sender_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sender_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    sender_customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)

    body = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False, nullable=False)  # Hidden from customer
    posted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    ticket = db.relationship("SupportTicket", foreign_keys=[ticket_id], back_populates="messages")
    sender_user = db.relationship("User", foreign_keys=[sender_user_id])
    sender_employee = db.relationship("Employee", foreign_keys=[sender_employee_id])
    sender_customer = db.relationship("Customer", foreign_keys=[sender_customer_id])


class Notification(AuditMixin, db.Model):
    """52. notifications — In-app alerts and outgoing message logs."""
    __tablename__ = "notifications"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True)
    template_id = db.Column(db.Integer, db.ForeignKey("notification_templates.id", ondelete="SET NULL"), nullable=True)

    channel = db.Column(db.String(20), default="IN_APP", nullable=False)
    recipient = db.Column(db.String(180), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    delivery_status = db.Column(db.String(30), default="SENT", nullable=False)
    created_for_event_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
    customer = db.relationship("Customer", foreign_keys=[customer_id])
    shipment = db.relationship("Shipment", foreign_keys=[shipment_id])
    template = db.relationship("NotificationTemplate", foreign_keys=[template_id])


class NotificationTemplate(AuditMixin, db.Model):
    """53. notification_templates — System message templates."""
    __tablename__ = "notification_templates"

    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    channel = db.Column(db.String(20), default="IN_APP", nullable=False)
    subject_template = db.Column(db.String(200), nullable=False)
    body_template = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<NotificationTemplate code='{self.code}'>"


class AuditLog(AuditMixin, db.Model):
    """54. audit_logs — Security and entity change audit record."""
    __tablename__ = "audit_logs"

    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    entity_type = db.Column(db.String(60), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    action = db.Column(db.String(40), nullable=False)
    before_json = db.Column(db.Text, nullable=True)
    after_json = db.Column(db.Text, nullable=True)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    actor = db.relationship("User", foreign_keys=[actor_user_id])
    branch = db.relationship("Branch", foreign_keys=[branch_id])

    def __repr__(self):
        return f"<AuditLog action='{self.action}' entity='{self.entity_type}:{self.entity_id}'>"


class AppSetting(AuditMixin, db.Model):
    """55. app_settings — Global application configuration parameters."""
    __tablename__ = "app_settings"

    setting_key = db.Column(db.String(60), unique=True, nullable=False, index=True)
    value_json = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<AppSetting key='{self.setting_key}'>"
