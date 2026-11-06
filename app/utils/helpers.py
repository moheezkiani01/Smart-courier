import uuid
from datetime import datetime

def paisa_to_pkr(paisa: int) -> str:
    """Format integer paisa to Pakistani Rupee currency string."""
    if paisa is None:
        paisa = 0
    pkr = paisa / 100.0
    return f"Rs. {pkr:,.2f}"

def pkr_to_paisa(pkr_value) -> int:
    """Convert PKR amount (float or str) to integer paisa."""
    if pkr_value is None or pkr_value == "":
        return 0
    try:
        val = float(pkr_value)
        return int(round(val * 100))
    except (ValueError, TypeError):
        return 0

def format_datetime(dt: datetime, fmt: str = "%b %d, %Y %I:%M %p") -> str:
    """Format UTC datetime for template display."""
    if not dt:
        return "—"
    return dt.strftime(fmt)

def generate_tracking_number() -> str:
    """Generate unique courier tracking code e.g. SC-PK-202611-AB12."""
    now = datetime.utcnow()
    rand_suffix = uuid.uuid4().hex[:6].upper()
    return f"SC{now.strftime('%y%m')}{rand_suffix}"

def generate_invoice_number() -> str:
    """Generate unique invoice number e.g. INV-2026-ABC123."""
    now = datetime.utcnow()
    rand_suffix = uuid.uuid4().hex[:5].upper()
    return f"INV-{now.strftime('%Y%m')}-{rand_suffix}"

def generate_ticket_number() -> str:
    """Generate unique ticket reference e.g. TKT-2026-ABC123."""
    now = datetime.utcnow()
    rand_suffix = uuid.uuid4().hex[:5].upper()
    return f"TKT-{now.strftime('%Y%m')}-{rand_suffix}"

def generate_customer_code() -> str:
    """Generate unique customer code e.g. CUST-2026-AB12."""
    now = datetime.utcnow()
    rand_suffix = uuid.uuid4().hex[:4].upper()
    return f"CUST-{now.strftime('%y%m')}-{rand_suffix}"

def generate_employee_code() -> str:
    """Generate unique employee code e.g. EMP-2026-AB12."""
    now = datetime.utcnow()
    rand_suffix = uuid.uuid4().hex[:4].upper()
    return f"EMP-{now.strftime('%y%m')}-{rand_suffix}"
