from app.models.support import SupportTicket, AuditLog
from app.services.support_service import SupportService
from app.services.audit_service import log_audit

def test_ticket_lifecycle_and_internal_note_isolation(app):
    """Verify ticket thread, customer visibility, and internal note secrecy."""
    with app.app_context():
        ticket = SupportService.open_ticket(
            customer_id=1,
            subject="Delayed Express Parcel",
            initial_body="Tracking status has not updated in 24 hours.",
            actor_user_id=1,
            priority="HIGH"
        )
        assert ticket.id is not None
        assert ticket.ticket_status == "OPEN"

        # Staff posts an internal note (customer must not see this)
        internal_note = SupportService.reply(
            ticket_id=ticket.id,
            body="Checked with hub: truck had a flat tyre, arriving tonight.",
            actor_user_id=1,
            is_internal=True,
            employee_id=1
        )
        assert internal_note.is_internal is True

        # Staff posts a public response
        public_reply = SupportService.reply(
            ticket_id=ticket.id,
            body="We are actively routing your parcel; expected delivery tomorrow morning.",
            actor_user_id=1,
            is_internal=False,
            employee_id=1
        )
        assert public_reply.is_internal is False
        assert ticket.ticket_status == "IN_PROGRESS"

        # Close ticket
        closed = SupportService.close_ticket(ticket.id, actor_user_id=1)
        assert closed.ticket_status == "CLOSED"

def test_audit_log_redaction(app):
    """Ensure passwords and secrets are redacted from audit entries."""
    with app.app_context():
        log_audit(
            action="CHANGE_PASSWORD",
            entity_type="User",
            entity_id=1,
            before={"password_hash": "scrypt:secret_hash"},
            after={"new_password": "PlainTextPasswordSecret!"},
            user_id=1
        )
        entry = AuditLog.query.filter_by(action="CHANGE_PASSWORD").order_by(AuditLog.occurred_at.desc()).first()
        assert entry is not None
        assert "[REDACTED]" in entry.before_json
        assert "[REDACTED]" in entry.after_json
        assert "PlainTextPasswordSecret!" not in entry.after_json
