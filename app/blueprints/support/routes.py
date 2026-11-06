from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.support import support_bp
from app.security.rbac import roles_required
from app.models.support import SupportTicket, TicketMessage, Notification, AppSetting
from app.models.shipments import Shipment
from app.models.catalog import Customer
from app.forms.support_forms import TicketForm, TicketReplyForm
from app.services.support_service import SupportService

@support_bp.route("/tickets", methods=["GET"])
@login_required
def tickets():
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    query = SupportTicket.query.filter_by(is_deleted=False)

    if current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN"):
        if hasattr(current_user, "customer") and current_user.customer:
            query = query.filter_by(customer_id=current_user.customer.id)
        else:
            query = query.filter(SupportTicket.id == -1)
    elif current_user.has_role("BRANCH_MANAGER") and not current_user.has_role("SUPER_ADMIN"):
        branch_id = current_user.employee.primary_branch_id if hasattr(current_user, "employee") and current_user.employee else None
        if branch_id:
            query = query.outerjoin(Shipment, SupportTicket.shipment_id == Shipment.id).filter(
                (Shipment.origin_branch_id == branch_id) | (Shipment.destination_branch_id == branch_id) | (SupportTicket.shipment_id == None)
            )

    if q:
        query = query.filter(SupportTicket.ticket_number.contains(q) | SupportTicket.subject.contains(q))
    if status_filter:
        query = query.filter(SupportTicket.ticket_status == status_filter)

    ticket_list = query.order_by(SupportTicket.opened_at.desc()).all()
    return render_template("support/tickets.html", tickets=ticket_list, q=q, current_status=status_filter)

@support_bp.route("/tickets/new", methods=["GET", "POST"])
@login_required
def new_ticket():
    form = TicketForm()
    is_customer = current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN")
    customers = Customer.query.filter_by(is_deleted=False).all()

    if is_customer and hasattr(current_user, "customer") and current_user.customer:
        form.customer_id.choices = [(current_user.customer.id, current_user.customer.full_name)]
        form.customer_id.data = current_user.customer.id
        shipments = Shipment.query.filter_by(customer_id=current_user.customer.id, is_deleted=False).all()
    else:
        form.customer_id.choices = [(c.id, f"{c.full_name} ({c.customer_code})") for c in customers]
        shipments = Shipment.query.filter_by(is_deleted=False).order_by(Shipment.booked_at.desc()).limit(30).all()

    form.shipment_id.choices = [(0, "None / General Inconvenience")] + [(s.id, f"{s.tracking_number} — {s.shipment_status}") for s in shipments]

    if form.validate_on_submit():
        if is_customer and hasattr(current_user, "customer") and current_user.customer:
            cid = current_user.customer.id
        else:
            if form.shipment_id.data and form.shipment_id.data > 0:
                sh = db.session.get(Shipment, form.shipment_id.data)
                cid = sh.customer_id if sh else (form.customer_id.data or (customers[0].id if customers else None))
            else:
                cid = form.customer_id.data or (customers[0].id if customers else None)

        if not cid:
            flash("Valid customer account is required to open a support ticket.", "danger")
            return render_template("support/new_ticket.html", form=form, is_customer=is_customer)

        shipment_val = form.shipment_id.data if form.shipment_id.data and form.shipment_id.data > 0 else None
        try:
            ticket = SupportService.open_ticket(
                customer_id=cid,
                subject=form.subject.data.strip(),
                initial_body=form.body.data.strip(),
                actor_user_id=current_user.id,
                priority=form.priority.data,
                shipment_id=shipment_val,
            )
            flash(f"Support ticket #{ticket.ticket_number} created.", "success")
            return redirect(url_for("support.ticket_detail", ticket_id=ticket.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error opening ticket: {str(e)}", "danger")

    return render_template("support/new_ticket.html", form=form, is_customer=is_customer)

@support_bp.route("/tickets/<int:ticket_id>", methods=["GET", "POST"])
@login_required
def ticket_detail(ticket_id):
    ticket = SupportTicket.query.filter_by(id=ticket_id, is_deleted=False).first_or_404()

    is_customer = current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN")
    if is_customer:
        if not (current_user.customer and current_user.customer.id == ticket.customer_id):
            abort(403)

    reply_form = TicketReplyForm()
    if reply_form.validate_on_submit():
        is_internal = reply_form.is_internal.data if not is_customer else False
        emp_id = current_user.employee.id if hasattr(current_user, "employee") and current_user.employee else None
        cust_id = current_user.customer.id if hasattr(current_user, "customer") and current_user.customer else None

        try:
            SupportService.reply(
                ticket_id=ticket.id,
                body=reply_form.body.data.strip(),
                actor_user_id=current_user.id,
                is_internal=is_internal,
                employee_id=emp_id,
                customer_id=cust_id,
            )
            flash("Reply posted to ticket.", "success")
            return redirect(url_for("support.ticket_detail", ticket_id=ticket.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error posting reply: {str(e)}", "danger")

    # Filter internal messages for customer
    messages = [m for m in ticket.messages if not m.is_deleted]
    if is_customer:
        messages = [m for m in messages if not m.is_internal]

    return render_template("support/ticket_detail.html", ticket=ticket, messages=messages, reply_form=reply_form, is_customer=is_customer)

@support_bp.route("/tickets/<int:ticket_id>/close", methods=["POST"])
@login_required
def close_ticket(ticket_id):
    ticket = SupportTicket.query.filter_by(id=ticket_id, is_deleted=False).first_or_404()

    # Object-level authorization check
    is_cust = current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN")
    if is_cust:
        if not (current_user.customer and current_user.customer.id == ticket.customer_id):
            abort(403)
    else:
        if not (current_user.has_role("SUPER_ADMIN") or current_user.has_role("SUPPORT_AGENT") or current_user.has_role("BRANCH_MANAGER")):
            abort(403)

    try:
        SupportService.close_ticket(ticket_id=ticket.id, actor_user_id=current_user.id)
        flash(f"Ticket #{ticket.ticket_number} resolved and closed.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Error closing ticket: {str(e)}", "danger")
    return redirect(url_for("support.ticket_detail", ticket_id=ticket.id))

@support_bp.route("/notifications", methods=["GET"])
@login_required
def notifications():
    query = Notification.query.filter_by(is_deleted=False)
    if current_user.has_role("CUSTOMER") and hasattr(current_user, "customer") and current_user.customer:
        query = query.filter_by(customer_id=current_user.customer.id)
    notifs = query.order_by(Notification.created_for_event_at.desc()).limit(50).all()
    return render_template("support/notifications.html", notifications=notifs)
