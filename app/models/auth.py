from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.base import AuditMixin

class User(AuditMixin, UserMixin, db.Model):
    """1. users — Primary user identity model."""
    __tablename__ = "users"

    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    is_email_verified = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    user_roles = db.relationship("UserRole", foreign_keys="UserRole.user_id", back_populates="user", cascade="all, delete-orphan")
    employee = db.relationship("Employee", foreign_keys="Employee.user_id", back_populates="user", uselist=False)
    customer = db.relationship("Customer", foreign_keys="Customer.user_id", back_populates="user", uselist=False)
    login_sessions = db.relationship("LoginSession", foreign_keys="LoginSession.user_id", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def roles(self):
        return [ur.role for ur in self.user_roles if ur.role and not ur.is_deleted]

    def has_role(self, role_code):
        return any(r.code == role_code for r in self.roles)

    def has_permission(self, perm_code):
        if self.has_role("SUPER_ADMIN"):
            return True
        for role in self.roles:
            for rp in role.role_permissions:
                if rp.permission and not rp.is_deleted and rp.permission.code == perm_code:
                    return True
        return False

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}'>"


class Role(AuditMixin, db.Model):
    """2. roles — Pre-seeded & custom roles."""
    __tablename__ = "roles"

    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    user_roles = db.relationship("UserRole", foreign_keys="UserRole.role_id", back_populates="role", cascade="all, delete-orphan")
    role_permissions = db.relationship("RolePermission", foreign_keys="RolePermission.role_id", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Role code='{self.code}'>"


class Permission(AuditMixin, db.Model):
    """3. permissions — Granular system permissions."""
    __tablename__ = "permissions"

    code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    module = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    role_permissions = db.relationship("RolePermission", foreign_keys="RolePermission.permission_id", back_populates="permission", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Permission code='{self.code}'>"


class UserRole(AuditMixin, db.Model):
    """4. user_roles — User to Role assignment."""
    __tablename__ = "user_roles"
    __table_args__ = (
        db.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    assigned_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    user = db.relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role = db.relationship("Role", foreign_keys=[role_id], back_populates="user_roles")
    assigned_by = db.relationship("User", foreign_keys=[assigned_by_user_id])


class RolePermission(AuditMixin, db.Model):
    """5. role_permissions — Role to Permission mapping."""
    __tablename__ = "role_permissions"
    __table_args__ = (
        db.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)

    role = db.relationship("Role", foreign_keys=[role_id], back_populates="role_permissions")
    permission = db.relationship("Permission", foreign_keys=[permission_id], back_populates="role_permissions")


class LoginSession(AuditMixin, db.Model):
    """6. login_sessions — Audit/security record of authenticated sessions."""
    __tablename__ = "login_sessions"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    ip_hint = db.Column(db.String(64), nullable=True)

    user = db.relationship("User", foreign_keys=[user_id], back_populates="login_sessions")
