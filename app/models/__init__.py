"""
Models Registry for Smart Courier & Parcel Delivery Management System.
Imports and exposes all 55 SQLAlchemy business models.
"""
from app.models.base import AuditMixin

# Group A: Authentication & Access Control (6 tables, #1–6)
from app.models.auth import (
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    LoginSession,
)

# Group B: Organization, Employees & Service Zones (6 tables, #7–12)
from app.models.organization import (
    Branch,
    Hub,
    Employee,
    EmployeeBranch,
    ServiceZone,
    BranchZone,
)

# Group C: Customers, Addresses & Rate Catalogs (10 tables, #13–22)
from app.models.catalog import (
    Customer,
    CustomerContact,
    CustomerAddress,
    RecipientProfile,
    RecipientAddress,
    ServiceType,
    ParcelCategory,
    PackagingType,
    RateCard,
    RateCardRule,
)

# Group D: Shipment Booking & Pickup (8 tables, #23–30)
from app.models.shipments import (
    Shipment,
    ShipmentItem,
    ShipmentAddress,
    ShipmentService,
    ShipmentDocument,
    PickupRequest,
    PickupAssignment,
    ShipmentStatusHistory,
)

# Group E: Dispatch, Routing, Scans & Delivery (11 tables, #31–41)
from app.models.dispatch import (
    Route,
    RouteStop,
    HubTransfer,
    ShipmentScan,
    TrackingEvent,
    DeliveryAttempt,
    DeliveryProof,
    DeliveryException,
    Vehicle,
    Driver,
    VehicleAssignment,
)

# Group F: Finance, Payments & Discounts (8 tables, #42–49)
from app.models.finance import (
    Invoice,
    InvoiceItem,
    Payment,
    CodCollection,
    CodRemittance,
    Refund,
    Discount,
    ShipmentDiscount,
)

# Group G: Support, Notifications & Auditing (6 tables, #50–55)
from app.models.support import (
    SupportTicket,
    TicketMessage,
    Notification,
    NotificationTemplate,
    AuditLog,
    AppSetting,
)

__all__ = [
    "AuditMixin",
    # Group A (1-6)
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "LoginSession",
    # Group B (7-12)
    "Branch",
    "Hub",
    "Employee",
    "EmployeeBranch",
    "ServiceZone",
    "BranchZone",
    # Group C (13-22)
    "Customer",
    "CustomerContact",
    "CustomerAddress",
    "RecipientProfile",
    "RecipientAddress",
    "ServiceType",
    "ParcelCategory",
    "PackagingType",
    "RateCard",
    "RateCardRule",
    # Group D (23-30)
    "Shipment",
    "ShipmentItem",
    "ShipmentAddress",
    "ShipmentService",
    "ShipmentDocument",
    "PickupRequest",
    "PickupAssignment",
    "ShipmentStatusHistory",
    # Group E (31-41)
    "Route",
    "RouteStop",
    "HubTransfer",
    "ShipmentScan",
    "TrackingEvent",
    "DeliveryAttempt",
    "DeliveryProof",
    "DeliveryException",
    "Vehicle",
    "Driver",
    "VehicleAssignment",
    # Group F (42-49)
    "Invoice",
    "InvoiceItem",
    "Payment",
    "CodCollection",
    "CodRemittance",
    "Refund",
    "Discount",
    "ShipmentDiscount",
    # Group G (50-55)
    "SupportTicket",
    "TicketMessage",
    "Notification",
    "NotificationTemplate",
    "AuditLog",
    "AppSetting",
]
