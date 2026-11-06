from datetime import datetime
from sqlalchemy import CheckConstraint
from app.extensions import db

class AuditMixin:
    """Universal audit and lifecycle mixin applied to all 55 business models."""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="ACTIVE")
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'DEACTIVE', 'PENDING')",
            name="%(table_name)s_status_check"
        ),
    )

    def soft_delete(self, user_id=None):
        """Perform a standard soft-delete on this entity."""
        self.is_deleted = True
        self.status = "DEACTIVE"
        self.deleted_at = datetime.utcnow()
        self.deleted_by = user_id
        self.updated_at = datetime.utcnow()
        self.updated_by = user_id

    def restore(self, user_id=None):
        """Restore a soft-deleted entity."""
        self.is_deleted = False
        self.status = "ACTIVE"
        self.deleted_at = None
        self.deleted_by = None
        self.updated_at = datetime.utcnow()
        self.updated_by = user_id
