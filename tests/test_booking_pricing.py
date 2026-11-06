import pytest
from app.models.shipments import Shipment
from app.services.shipment_service import ShipmentService

def test_atomic_shipment_booking(app):
    """Verify atomic booking with immutable address snapshots and quote capture."""
    with app.app_context():
        sender = {
            "name": "Ali Hassan",
            "phone": "0300-1112233",
            "zone_id": 1,
            "line1": "Plot 10, F-7 Markaz",
            "city": "Islamabad",
            "postal_code": "44000"
        }
        recipient = {
            "name": "Hamza Tariq",
            "phone": "0321-9988776",
            "zone_id": 2,
            "line1": "Street 5, Gulberg III",
            "city": "Lahore",
            "postal_code": "54000"
        }
        items = [{"description": "Business Contracts", "quantity": 1, "weight_grams": 400, "declared_value_paisa": 100000}]

        shipment = ShipmentService.book_shipment(
            customer_id=1,
            origin_branch_id=1,
            destination_branch_id=2,
            service_type_id=1,
            parcel_category_id=1,
            packaging_type_id=1,
            sender_data=sender,
            recipient_data=recipient,
            items_data=items,
            actor_user_id=1,
            cod_due_paisa=50000,
        )

        assert shipment.id is not None
        assert shipment.tracking_number.startswith("SC")
        assert shipment.shipment_status == "BOOKED"
        assert len(shipment.items) == 1
        assert shipment.sender_address.person_name == "Ali Hassan"
        assert shipment.recipient_address.person_name == "Hamza Tariq"
        assert shipment.invoice is not None
        assert shipment.invoice.total_paisa == shipment.total_charge_paisa

def test_status_transition_validation(app):
    """Verify state machine accepts valid transitions and rejects illegal skips."""
    with app.app_context():
        shipment = Shipment.query.filter_by(shipment_status="BOOKED").first()
        assert shipment is not None

        # Valid transition: BOOKED -> AT_ORIGIN_HUB
        ShipmentService.transition(
            shipment_id=shipment.id,
            target_status="AT_ORIGIN_HUB",
            actor_user_id=1,
            reason="Received directly at branch counter"
        )
        assert shipment.shipment_status == "AT_ORIGIN_HUB"

        # Invalid transition: AT_ORIGIN_HUB -> DELIVERED (must fail)
        with pytest.raises(ValueError):
            ShipmentService.transition(
                shipment_id=shipment.id,
                target_status="DELIVERED",
                actor_user_id=1,
                reason="Direct delivery attempt invalid"
            )
