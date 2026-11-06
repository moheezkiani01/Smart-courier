from datetime import datetime
from app.extensions import db
from app.models.finance import Invoice, Payment, Refund, CodCollection, CodRemittance
from app.models.shipments import Shipment
from app.services.audit_service import log_audit

class FinanceService:
    @staticmethod
    def record_payment(
        invoice_id: int,
        amount_paisa: int,
        method: str,
        reference_code: str,
        employee_id: int,
        actor_user_id: int,
    ) -> Payment:
        if amount_paisa <= 0:
            raise ValueError("Payment amount must be greater than zero paisa.")

        invoice = Invoice.query.filter_by(id=invoice_id, is_deleted=False).with_for_update().first()
        if not invoice:
            raise ValueError("Invoice not found.")

        payment = Payment(
            invoice_id=invoice.id,
            received_by_employee_id=employee_id,
            amount_paisa=amount_paisa,
            method=method,
            reference_code=reference_code,
            paid_at=datetime.utcnow(),
            payment_status="SETTLED",
            created_by=actor_user_id,
        )
        invoice.payments.append(payment)
        db.session.add(payment)
        db.session.flush()

        # Check if invoice is fully settled
        if invoice.total_paid_paisa >= invoice.total_paisa:
            invoice.invoice_status = "PAID"
            invoice.updated_at = datetime.utcnow()
            invoice.updated_by = actor_user_id

        log_audit(
            action="PAYMENT_RECEIVED",
            entity_type="Invoice",
            entity_id=invoice.id,
            after={"amount_paisa": amount_paisa, "method": method, "ref": reference_code},
            user_id=actor_user_id,
        )

        db.session.commit()
        return payment

    @staticmethod
    def process_refund(
        payment_id: int,
        amount_paisa: int,
        reason: str,
        authorized_by_employee_id: int,
        actor_user_id: int,
    ) -> Refund:
        if amount_paisa <= 0:
            raise ValueError("Refund amount must be positive.")

        payment = Payment.query.filter_by(id=payment_id, is_deleted=False).with_for_update().first()
        if not payment:
            raise ValueError("Payment record not found.")

        existing_refunded = sum(r.amount_paisa for r in payment.refunds if r.refund_status == "PROCESSED" and not r.is_deleted)
        if existing_refunded + amount_paisa > payment.amount_paisa:
            raise ValueError(f"Refund exceeds settled payment amount. Available to refund: {payment.amount_paisa - existing_refunded} paisa.")

        refund = Refund(
            payment_id=payment.id,
            authorized_by_employee_id=authorized_by_employee_id,
            amount_paisa=amount_paisa,
            reason=reason.strip(),
            refund_status="PROCESSED",
            requested_at=datetime.utcnow(),
            processed_at=datetime.utcnow(),
            created_by=actor_user_id,
        )
        db.session.add(refund)
        payment.refunds.append(refund)
        db.session.flush()

        # Update invoice status if no longer fully covered
        invoice = payment.invoice
        if invoice.total_paid_paisa < invoice.total_paisa:
            invoice.invoice_status = "ISSUED"
            invoice.updated_at = datetime.utcnow()
            invoice.updated_by = actor_user_id

        log_audit(
            action="REFUND_ISSUED",
            entity_type="Payment",
            entity_id=payment.id,
            after={"refund_amount_paisa": amount_paisa, "reason": reason},
            user_id=actor_user_id,
        )

        db.session.commit()
        return refund

    @staticmethod
    def collect_cod(shipment_id: int, driver_id: int, amount_paisa: int, actor_user_id: int) -> CodCollection:
        if amount_paisa <= 0:
            raise ValueError("COD amount collected must be positive.")

        shipment = Shipment.query.filter_by(id=shipment_id, is_deleted=False).first()
        if not shipment:
            raise ValueError("Shipment not found.")

        existing = CodCollection.query.filter_by(shipment_id=shipment_id, is_deleted=False).first()
        if existing:
            raise ValueError("COD collection already recorded for this shipment.")

        collection = CodCollection(
            shipment_id=shipment_id,
            collected_by_driver_id=driver_id,
            amount_paisa=amount_paisa,
            collected_at=datetime.utcnow(),
            collection_status="COLLECTED",
            created_by=actor_user_id,
        )
        db.session.add(collection)

        log_audit(
            action="COD_COLLECTED",
            entity_type="Shipment",
            entity_id=shipment.id,
            after={"amount_paisa": amount_paisa, "driver_id": driver_id},
            user_id=actor_user_id,
        )

        db.session.commit()
        return collection

    @staticmethod
    def remit_cod(cod_collection_id: int = None, amount_paisa: int = 0, reference_code: str = None, employee_id: int = None, actor_user_id: int = None, collection_id: int = None) -> CodRemittance:
        target_id = cod_collection_id or collection_id
        if not target_id:
            raise ValueError("Collection ID is required.")
        if amount_paisa <= 0:
            raise ValueError("Remittance amount must be positive.")

        collection = CodCollection.query.filter_by(id=target_id, is_deleted=False).with_for_update().first()
        if not collection:
            raise ValueError("COD collection not found.")

        existing_remitted = sum(r.amount_paisa for r in collection.remittances if r.remittance_status == "COMPLETED" and not r.is_deleted)
        if existing_remitted + amount_paisa > collection.amount_paisa:
            raise ValueError(f"Remittance amount exceeds collected COD. Available: {collection.amount_paisa - existing_remitted} paisa.")

        remittance = CodRemittance(
            cod_collection_id=collection.id,
            received_by_employee_id=employee_id,
            amount_paisa=amount_paisa,
            remitted_at=datetime.utcnow(),
            reference_code=reference_code,
            remittance_status="COMPLETED",
            created_by=actor_user_id,
        )
        db.session.add(remittance)

        if existing_remitted + amount_paisa >= collection.amount_paisa:
            collection.collection_status = "REMITTED"
            collection.updated_at = datetime.utcnow()
            collection.updated_by = actor_user_id

        log_audit(
            action="COD_REMITTED",
            entity_type="CodCollection",
            entity_id=collection.id,
            after={"amount_paisa": amount_paisa, "ref": reference_code},
            user_id=actor_user_id,
        )

        db.session.commit()
        return remittance
