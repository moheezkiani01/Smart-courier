from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.finance import finance_bp
from app.security.rbac import roles_required
from app.models.finance import Invoice, Payment, Refund, CodCollection, CodRemittance, Discount
from app.forms.finance_forms import PaymentForm, CodRemittanceForm, RefundForm
from app.services.finance_service import FinanceService

@finance_bp.route("/invoices", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN", "FINANCE_OFFICER", "BRANCH_MANAGER", "CUSTOMER")
def invoices():
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    query = Invoice.query.filter_by(is_deleted=False)

    if current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN"):
        if hasattr(current_user, "customer") and current_user.customer:
            query = query.filter_by(customer_id=current_user.customer.id)
        else:
            query = query.filter(Invoice.id == -1)
    elif current_user.has_role("BRANCH_MANAGER") and not current_user.has_role("SUPER_ADMIN"):
        branch_id = current_user.employee.primary_branch_id if hasattr(current_user, "employee") and current_user.employee else None
        if branch_id:
            from app.models.shipments import Shipment
            query = query.join(Shipment, Invoice.shipment_id == Shipment.id).filter(
                (Shipment.origin_branch_id == branch_id) | (Shipment.destination_branch_id == branch_id)
            )

    if q:
        query = query.filter(Invoice.invoice_number.contains(q))
    if status_filter:
        query = query.filter(Invoice.invoice_status == status_filter)

    invoice_list = query.order_by(Invoice.issued_at.desc()).all()
    return render_template("finance/invoices.html", invoices=invoice_list, q=q, current_status=status_filter)

@finance_bp.route("/invoices/<int:invoice_id>", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN", "FINANCE_OFFICER", "BRANCH_MANAGER", "CUSTOMER")
def invoice_detail(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, is_deleted=False).first_or_404()

    if current_user.has_role("CUSTOMER") and not current_user.has_role("SUPER_ADMIN"):
        if not (current_user.customer and current_user.customer.id == invoice.customer_id):
            abort(403)
    elif current_user.has_role("BRANCH_MANAGER") and not current_user.has_role("SUPER_ADMIN"):
        branch_id = current_user.employee.primary_branch_id if hasattr(current_user, "employee") and current_user.employee else None
        if branch_id and invoice.shipment:
            if invoice.shipment.origin_branch_id != branch_id and invoice.shipment.destination_branch_id != branch_id:
                abort(403)

    payment_form = PaymentForm()
    payment_form.amount_paisa.data = invoice.amount_due_paisa
    refund_form = RefundForm()

    return render_template("finance/invoice_detail.html", invoice=invoice, payment_form=payment_form, refund_form=refund_form)

@finance_bp.route("/payments", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN", "FINANCE_OFFICER", "BOOKING_AGENT")
def record_payment():
    try:
        invoice_id = int(request.form.get("invoice_id", 0))
        amount_paisa = int(request.form.get("amount_paisa", 0))
    except (ValueError, TypeError):
        flash("Invalid invoice or payment parameters.", "danger")
        return redirect(url_for("finance.invoices"))

    if not invoice_id or amount_paisa <= 0:
        flash("Valid invoice and positive payment amount are required.", "danger")
        return redirect(url_for("finance.invoice_detail", invoice_id=invoice_id) if invoice_id else url_for("finance.invoices"))

    method = request.form.get("method")
    reference = request.form.get("reference_code", "").strip() or None

    emp_id = current_user.employee.id if hasattr(current_user, "employee") and current_user.employee else None
    try:
        payment = FinanceService.record_payment(
            invoice_id=invoice_id,
            amount_paisa=amount_paisa,
            method=method,
            reference_code=reference,
            employee_id=emp_id,
            actor_user_id=current_user.id,
        )
        flash(f"Payment of {payment.amount_paisa // 100} PKR recorded successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Payment Error: {str(e)}", "danger")

    return redirect(url_for("finance.invoice_detail", invoice_id=invoice_id))

@finance_bp.route("/refunds", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN", "FINANCE_OFFICER")
def process_refund():
    try:
        payment_id = int(request.form.get("payment_id", 0))
        invoice_id = int(request.form.get("invoice_id", 0))
        amount_paisa = int(request.form.get("amount_paisa", 0))
    except (ValueError, TypeError):
        flash("Invalid refund request parameters.", "danger")
        return redirect(url_for("finance.invoices"))

    reason = request.form.get("reason", "").strip()
    emp_id = current_user.employee.id if hasattr(current_user, "employee") and current_user.employee else None
    try:
        FinanceService.process_refund(
            payment_id=payment_id,
            amount_paisa=amount_paisa,
            reason=reason,
            authorized_by_employee_id=emp_id,
            actor_user_id=current_user.id,
        )
        flash("Refund processed and credited.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Refund Error: {str(e)}", "danger")

    return redirect(url_for("finance.invoice_detail", invoice_id=invoice_id) if invoice_id else url_for("finance.invoices"))

@finance_bp.route("/cod", methods=["GET"])
@login_required
@roles_required("SUPER_ADMIN", "FINANCE_OFFICER")
def cod_summary():
    collections = CodCollection.query.filter_by(is_deleted=False).order_by(CodCollection.collected_at.desc()).all()
    remit_form = CodRemittanceForm()
    return render_template("finance/cod_summary.html", collections=collections, remit_form=remit_form)

@finance_bp.route("/cod/remit", methods=["POST"])
@login_required
@roles_required("SUPER_ADMIN", "FINANCE_OFFICER")
def remit_cod():
    try:
        collection_id = int(request.form.get("collection_id", 0))
        amount_paisa = int(request.form.get("amount_paisa", 0))
    except (ValueError, TypeError):
        flash("Invalid COD remittance parameters.", "danger")
        return redirect(url_for("finance.cod_summary"))

    reference = request.form.get("reference_code", "").strip() or None
    emp_id = current_user.employee.id if hasattr(current_user, "employee") and current_user.employee else None
    try:
        FinanceService.remit_cod(
            collection_id=collection_id,
            amount_paisa=amount_paisa,
            reference_code=reference,
            employee_id=emp_id,
            actor_user_id=current_user.id,
        )
        flash("COD funds remitted to merchant account.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"COD Remittance Error: {str(e)}", "danger")

    return redirect(url_for("finance.cod_summary"))
