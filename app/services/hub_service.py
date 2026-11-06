from datetime import datetime
from app.extensions import db
from app.models.shipments import Shipment
from app.models.dispatch import ShipmentScan, HubTransfer, TrackingEvent
from app.models.organization import Hub
from app.services.shipment_service import ShipmentService
from app.services.audit_service import log_audit

class HubService:
    @staticmethod
    def record_scan(shipment_id: int, hub_id: int, employee_id: int, actor_user_id: int, scan_code: str, notes: str = None) -> ShipmentScan:
        shipment = Shipment.query.filter_by(id=shipment_id, is_deleted=False).first()
        if not shipment:
            raise ValueError("Shipment not found.")

        hub = Hub.query.filter_by(id=hub_id, is_deleted=False).first() if hub_id else None

        scan = ShipmentScan(
            shipment_id=shipment.id,
            hub_id=hub_id,
            scanned_by_employee_id=employee_id,
            scan_code=scan_code,
            scanned_at=datetime.utcnow(),
            notes=notes,
            created_by=actor_user_id,
        )
        db.session.add(scan)

        if hub_id:
            shipment.current_hub_id = hub_id

        # Add tracking event
        event = TrackingEvent(
            shipment_id=shipment.id,
            event_code=f"SCAN_{scan_code}",
            public_message=f"Parcel scanned at {hub.name if hub else 'location'} [{scan_code}].",
            occurred_at=datetime.utcnow(),
            hub_id=hub_id,
            actor_user_id=actor_user_id,
            visible_to_customer=True,
            created_by=actor_user_id,
        )
        db.session.add(event)

        log_audit(
            action="HUB_SCAN",
            entity_type="ShipmentScan",
            entity_id=shipment.id,
            after={"scan_code": scan_code, "hub_id": hub_id},
            user_id=actor_user_id,
        )
        db.session.commit()
        return scan

    @staticmethod
    def initiate_transfer(shipment_id: int, from_hub_id: int, to_hub_id: int, employee_id: int, actor_user_id: int) -> HubTransfer:
        if from_hub_id == to_hub_id:
            raise ValueError("Origin and destination hubs cannot be the same.")

        shipment = Shipment.query.filter_by(id=shipment_id, is_deleted=False).first()
        if not shipment:
            raise ValueError("Shipment not found.")

        transfer = HubTransfer(
            shipment_id=shipment.id,
            from_hub_id=from_hub_id,
            to_hub_id=to_hub_id,
            initiated_by_employee_id=employee_id,
            departed_at=datetime.utcnow(),
            transfer_status="IN_TRANSIT",
            created_by=actor_user_id,
        )
        db.session.add(transfer)

        # Verify shipment is in an eligible sorting state
        if shipment.shipment_status not in ["AT_ORIGIN_HUB", "AT_DESTINATION_HUB"]:
            raise ValueError(f"Shipment {shipment.tracking_number} is currently '{shipment.shipment_status}'. Parcels must be received and scanned at a sorting hub (AT_ORIGIN_HUB) before initiating freight transfers.")

        # Transition shipment to IN_TRANSIT
        ShipmentService.transition(
            shipment_id=shipment.id,
            target_status="IN_TRANSIT",
            actor_user_id=actor_user_id,
            reason=f"Transfer dispatched from hub {from_hub_id} to hub {to_hub_id}",
            hub_id=to_hub_id,
        )

        db.session.commit()
        return transfer

    @staticmethod
    def receive_transfer(transfer_id: int, employee_id: int, actor_user_id: int) -> HubTransfer:
        transfer = HubTransfer.query.filter_by(id=transfer_id, is_deleted=False).first()
        if not transfer:
            raise ValueError("Transfer record not found.")

        transfer.received_by_employee_id = employee_id
        transfer.received_at = datetime.utcnow()
        transfer.transfer_status = "RECEIVED"
        transfer.updated_at = datetime.utcnow()
        transfer.updated_by = actor_user_id

        # Update shipment location & transition
        shipment = db.session.get(Shipment, transfer.shipment_id)
        if shipment:
            shipment.current_hub_id = transfer.to_hub_id
            if shipment.shipment_status == "IN_TRANSIT":
                ShipmentService.transition(
                    shipment_id=shipment.id,
                    target_status="AT_DESTINATION_HUB",
                    actor_user_id=actor_user_id,
                    reason=f"Received at destination hub {transfer.to_hub_id}",
                    hub_id=transfer.to_hub_id,
                )

        db.session.commit()
        return transfer
