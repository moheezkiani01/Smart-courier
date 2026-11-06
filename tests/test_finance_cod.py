import pytest
from app.models.finance import Invoice, CodCollection
from app.models.organization import Employee
from app.services.finance_service import FinanceService

def test_invoice_payment_settlement(app):
    """Verify posting payment settles invoice balance."""
    with app.app_context():
        emp = Employee.query.first()
        invoice = Invoice.query.filter_by(invoice_status="ISSUED").first()
        if not invoice:
            invoice = Invoice.query.first()
            invoice.invoice_status = "ISSUED"

        due = invoice.amount_due_paisa
        assert due > 0

        payment = FinanceService.record_payment(
            invoice_id=invoice.id,
            amount_paisa=due,
            method="CASH",
            reference_code="RECEIPT-001",
            employee_id=emp.id,
            actor_user_id=1,
        )

        assert payment.id is not None
        assert payment.payment_status == "SETTLED"
        assert invoice.invoice_status == "PAID"
        assert invoice.amount_due_paisa == 0

def test_refund_cannot_exceed_payment_amount(app):
    """Ensure financial refund invariants prevent over-refunding."""
    with app.app_context():
        emp = Employee.query.first()
        invoice = Invoice.query.filter_by(invoice_status="PAID").first()
        payment = invoice.payments[0]

        # Attempt to refund double the payment
        with pytest.raises(ValueError):
            FinanceService.process_refund(
                payment_id=payment.id,
                amount_paisa=payment.amount_paisa * 2,
                reason="Unauthorized excess claim",
                authorized_by_employee_id=emp.id,
                actor_user_id=1,
            )

def test_cod_collection_and_remittance(app):
    """Verify cash-on-delivery collection and merchant remittance reconciliation."""
    with app.app_context():
        emp = Employee.query.first()
        collection = CodCollection.query.first()
        assert collection is not None
        assert collection.amount_paisa > 0

        pending = collection.pending_remittance_paisa
        if pending > 0:
            remittance = FinanceService.remit_cod(
                collection_id=collection.id,
                amount_paisa=pending,
                reference_code="IBFT-BANK-SETTLE",
                employee_id=emp.id,
                actor_user_id=1,
            )
            assert remittance.id is not None
            assert collection.collection_status == "REMITTED"
            assert collection.pending_remittance_paisa == 0
