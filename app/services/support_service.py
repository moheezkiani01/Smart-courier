from datetime import datetime
from app.extensions import db
from app.models.support import SupportTicket, TicketMessage, Notification
from app.services.audit_service import log_audit
from app.utils.helpers import generate_ticket_number

class SupportService:
    @staticmethod
    def open_ticket(
        customer_id: int,
        subject: str,
        initial_body: str,
        actor_user_id: int,
        priority: str = "MEDIUM",
        shipment_id: int = None,
    ) -> SupportTicket:
        ticket = SupportTicket(
            ticket_number=generate_ticket_number(),
            customer_id=customer_id,
            shipment_id=shipment_id,
            subject=subject.strip(),
            priority=priority,
            ticket_status="OPEN",
            opened_at=datetime.utcnow(),
            created_by=actor_user_id,
        )
        db.session.add(ticket)
        db.session.flush()

        msg = TicketMessage(
            ticket_id=ticket.id,
            sender_user_id=actor_user_id,
            sender_customer_id=customer_id,
            body=initial_body.strip(),
            is_internal=False,
            posted_at=datetime.utcnow(),
            created_by=actor_user_id,
        )
        db.session.add(msg)

        log_audit(
            action="OPEN_TICKET",
            entity_type="SupportTicket",
            entity_id=ticket.id,
            after={"ticket_number": ticket.ticket_number, "subject": ticket.subject},
            user_id=actor_user_id,
        )

        db.session.commit()
        return ticket

    @staticmethod
    def reply(
        ticket_id: int,
        body: str,
        actor_user_id: int,
        is_internal: bool = False,
        employee_id: int = None,
        customer_id: int = None,
    ) -> TicketMessage:
        ticket = SupportTicket.query.filter_by(id=ticket_id, is_deleted=False).first()
        if not ticket:
            raise ValueError("Ticket not found.")

        msg = TicketMessage(
            ticket_id=ticket.id,
            sender_user_id=actor_user_id,
            sender_employee_id=employee_id,
            sender_customer_id=customer_id,
            body=body.strip(),
            is_internal=is_internal,
            posted_at=datetime.utcnow(),
            created_by=actor_user_id,
        )
        db.session.add(msg)

        if not is_internal and ticket.ticket_status == "OPEN":
            ticket.ticket_status = "IN_PROGRESS"

        ticket.updated_at = datetime.utcnow()
        ticket.updated_by = actor_user_id

        db.session.commit()
        return msg

    @staticmethod
    def close_ticket(ticket_id: int, actor_user_id: int) -> SupportTicket:
        ticket = SupportTicket.query.filter_by(id=ticket_id, is_deleted=False).first()
        if not ticket:
            raise ValueError("Ticket not found.")

        ticket.ticket_status = "CLOSED"
        ticket.closed_at = datetime.utcnow()
        ticket.updated_at = datetime.utcnow()
        ticket.updated_by = actor_user_id

        log_audit(
            action="CLOSE_TICKET",
            entity_type="SupportTicket",
            entity_id=ticket.id,
            after={"status": "CLOSED"},
            user_id=actor_user_id,
        )

        db.session.commit()
        return ticket
