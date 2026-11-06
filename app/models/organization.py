from datetime import date
from app.extensions import db
from app.models.base import AuditMixin

class Branch(AuditMixin, db.Model):
    """7. branches — Physical courier branch/office."""
    __tablename__ = "branches"

    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    address_line = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)

    # Relationships
    hubs = db.relationship("Hub", foreign_keys="Hub.branch_id", back_populates="branch", cascade="all, delete-orphan")
    employees = db.relationship("Employee", foreign_keys="Employee.primary_branch_id", back_populates="primary_branch")
    employee_branches = db.relationship("EmployeeBranch", foreign_keys="EmployeeBranch.branch_id", back_populates="branch", cascade="all, delete-orphan")
    branch_zones = db.relationship("BranchZone", foreign_keys="BranchZone.branch_id", back_populates="branch", cascade="all, delete-orphan")
    routes = db.relationship("Route", foreign_keys="Route.branch_id", back_populates="branch")

    def __repr__(self):
        return f"<Branch code='{self.code}' name='{self.name}'>"


class Hub(AuditMixin, db.Model):
    """8. hubs — Operational sorting/transit hub operated by a branch."""
    __tablename__ = "hubs"

    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    location_note = db.Column(db.String(255), nullable=True)

    branch = db.relationship("Branch", foreign_keys=[branch_id], back_populates="hubs")

    def __repr__(self):
        return f"<Hub code='{self.code}' name='{self.name}'>"


class Employee(AuditMixin, db.Model):
    """9. employees — Staff member profile linked to User."""
    __tablename__ = "employees"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), unique=True, nullable=False)
    primary_branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    employee_no = db.Column(db.String(40), unique=True, nullable=False, index=True)
    job_title = db.Column(db.String(100), nullable=False)
    hired_on = db.Column(db.Date, nullable=False, default=date.today)

    user = db.relationship("User", foreign_keys=[user_id], back_populates="employee")
    primary_branch = db.relationship("Branch", foreign_keys=[primary_branch_id], back_populates="employees")
    employee_branches = db.relationship("EmployeeBranch", foreign_keys="EmployeeBranch.employee_id", back_populates="employee", cascade="all, delete-orphan")
    driver_profile = db.relationship("Driver", foreign_keys="Driver.employee_id", back_populates="employee", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Employee no='{self.employee_no}' title='{self.job_title}'>"


class EmployeeBranch(AuditMixin, db.Model):
    """10. employee_branches — Multi-branch assignment for employees."""
    __tablename__ = "employee_branches"
    __table_args__ = (
        db.UniqueConstraint("employee_id", "branch_id", name="uq_emp_branch"),
    )

    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    assigned_on = db.Column(db.Date, default=date.today, nullable=False)

    employee = db.relationship("Employee", foreign_keys=[employee_id], back_populates="employee_branches")
    branch = db.relationship("Branch", foreign_keys=[branch_id], back_populates="employee_branches")


class ServiceZone(AuditMixin, db.Model):
    """11. service_zones — Geographical service coverage zones."""
    __tablename__ = "service_zones"

    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    region = db.Column(db.String(100), nullable=False)
    postal_prefix = db.Column(db.String(20), nullable=True)

    branch_zones = db.relationship("BranchZone", foreign_keys="BranchZone.zone_id", back_populates="zone", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ServiceZone code='{self.code}' city='{self.city}'>"


class BranchZone(AuditMixin, db.Model):
    """12. branch_zones — Service zone coverage mapping per branch."""
    __tablename__ = "branch_zones"
    __table_args__ = (
        db.UniqueConstraint("branch_id", "zone_id", name="uq_branch_zone"),
    )

    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey("service_zones.id", ondelete="CASCADE"), nullable=False)
    pickup_enabled = db.Column(db.Boolean, default=True, nullable=False)
    delivery_enabled = db.Column(db.Boolean, default=True, nullable=False)

    branch = db.relationship("Branch", foreign_keys=[branch_id], back_populates="branch_zones")
    zone = db.relationship("ServiceZone", foreign_keys=[zone_id], back_populates="branch_zones")
