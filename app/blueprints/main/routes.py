"""Home and dashboard routes.

The dashboard only counts shipments that the logged-in user is allowed to see.
The weekly graph is computed in Python so the HTML stays simple.
"""
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for
from flask_login import current_user
from app.blueprints.main import main_bp
from app.models.shipments import Shipment
from app.models.finance import Invoice, CodCollection
from app.models.support import SupportTicket
from app.models.dispatch import Route, RouteStop


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        is_cust = current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN")
        is_driver = current_user.has_role("DRIVER") and not current_user.has_role("SUPER_ADMIN")
        is_fin = current_user.has_role("FINANCE_OFFICER")
        is_bm = current_user.has_role("BRANCH_MANAGER")
        is_super = current_user.has_role("SUPER_ADMIN")

        branch_id = None
        if hasattr(current_user, "employee") and current_user.employee:
            branch_id = current_user.employee.primary_branch_id

        # Restrict shipment statistics to the current user's scope.
        shipments_q = Shipment.query.filter_by(is_deleted=False)
        if is_cust:
            cid = current_user.customer.id if current_user.customer else -1
            shipments_q = shipments_q.filter_by(customer_id=cid)
        elif is_driver:
            driver = current_user.employee.driver_profile if (
                hasattr(current_user, "employee") and current_user.employee
                and current_user.employee.driver_profile
            ) else None
            if driver:
                route_ids = [r.id for r in Route.query.filter_by(driver_id=driver.id, is_deleted=False).all()]
                shipment_ids = [s.shipment_id for s in RouteStop.query.filter(
                    RouteStop.route_id.in_(route_ids), RouteStop.is_deleted == False
                ).all()] if route_ids else []
                shipments_q = shipments_q.filter(
                    Shipment.id.in_(shipment_ids) if shipment_ids else Shipment.id == -1
                )
            else:
                shipments_q = shipments_q.filter(Shipment.id == -1)
        elif is_bm and branch_id:
            shipments_q = shipments_q.filter(
                (Shipment.origin_branch_id == branch_id)
                | (Shipment.destination_branch_id == branch_id)
            )

        total_shipments = shipments_q.count()
        in_transit = shipments_q.filter(Shipment.shipment_status.in_([
            "IN_TRANSIT", "OUT_FOR_DELIVERY", "AT_ORIGIN_HUB", "AT_DESTINATION_HUB"
        ])).count()
        delivered = shipments_q.filter_by(shipment_status="DELIVERED").count()
        failed = shipments_q.filter_by(shipment_status="DELIVERY_FAILED").count()

        # Seven daily bars using actual shipment dates (no invented chart data).
        today = datetime.utcnow().date()
        dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
        daily_counts = {day: 0 for day in dates}
        first_day = datetime.combine(dates[0], datetime.min.time())
        for (booked_at,) in shipments_q.filter(
            Shipment.booked_at >= first_day
        ).with_entities(Shipment.booked_at).all():
            if booked_at and booked_at.date() in daily_counts:
                daily_counts[booked_at.date()] += 1
        highest = max(1, max(daily_counts.values()))
        weekly_activity = [
            {
                "label": day.strftime("%a"),
                "date": day.strftime("%d %b"),
                "value": daily_counts[day],
                "height": round(daily_counts[day] * 100 / highest),
            }
            for day in dates
        ]

        # Financial figures, also scoped to the logged-in user.
        total_revenue_paisa = 0
        pending_cod_paisa = 0
        customer_due_paisa = 0
        if is_cust:
            cid = current_user.customer.id if current_user.customer else -1
            cust_invoices = Invoice.query.filter_by(customer_id=cid, is_deleted=False).all()
            customer_due_paisa = sum(inv.amount_due_paisa for inv in cust_invoices)
        elif is_fin or is_super or is_bm:
            invoices_q = Invoice.query.filter_by(invoice_status="PAID", is_deleted=False)
            cod_q = CodCollection.query.filter_by(collection_status="COLLECTED", is_deleted=False)
            if is_bm and branch_id:
                branch_ship_ids = [s.id for s in shipments_q.all()]
                invoices_q = invoices_q.filter(
                    Invoice.shipment_id.in_(branch_ship_ids) if branch_ship_ids else Invoice.id == -1
                )
                cod_q = cod_q.filter(
                    CodCollection.shipment_id.in_(branch_ship_ids) if branch_ship_ids else CodCollection.id == -1
                )
            total_revenue_paisa = sum(inv.total_paisa for inv in invoices_q.all())
            pending_cod_paisa = sum(c.amount_paisa for c in cod_q.all())

        tickets_q = SupportTicket.query.filter(
            SupportTicket.ticket_status.in_(["OPEN", "IN_PROGRESS"]),
            SupportTicket.is_deleted == False,
        )
        if is_cust:
            cid = current_user.customer.id if current_user.customer else -1
            tickets_q = tickets_q.filter_by(customer_id=cid)
        open_tickets = tickets_q.count()

        showcase_entries = []
        if is_cust and current_user.email == "demo.merchant@smartcourier.pk":
            from app.services.showcase_service import get_showcase_entries
            showcase_entries = get_showcase_entries()

        recent_shipments = shipments_q.order_by(Shipment.booked_at.desc()).limit(5).all()
        return render_template(
            "main/dashboard.html",
            total_shipments=total_shipments,
            in_transit=in_transit,
            delivered=delivered,
            failed=failed,
            weekly_activity=weekly_activity,
            total_revenue_paisa=total_revenue_paisa,
            pending_cod_paisa=pending_cod_paisa,
            customer_due_paisa=customer_due_paisa,
            open_tickets=open_tickets,
            recent_shipments=recent_shipments,
            showcase_entries=showcase_entries,
            is_cust=is_cust,
        )
    return redirect(url_for("auth.login"))
