from datetime import date
from app.models.shipments import Shipment
from app.models.dispatch import Route, Driver, Vehicle
from app.services.hub_service import HubService
from app.services.dispatch_service import DispatchService

def test_hub_scan_and_tracking_event(app):
    """Verify hub scan updates location and emits a public tracking event."""
    with app.app_context():
        shipment = Shipment.query.first()
        scan = HubService.record_scan(
            shipment_id=shipment.id,
            hub_id=1,
            employee_id=1,
            actor_user_id=1,
            scan_code="INBOUND",
            notes="Sorted into bin 4"
        )
        assert scan.id is not None
        assert shipment.current_hub_id == 1
        assert len(shipment.tracking_events) > 0
        assert shipment.tracking_events[-1].visible_to_customer is True

def test_route_stop_and_delivery_attempt_failure(app):
    """Verify failed delivery creates an exception and keeps shipment undelivered."""
    with app.app_context():
        driver = Driver.query.first()
        vehicle = Vehicle.query.first()

        route = DispatchService.create_route(
            branch_id=1,
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            route_code=f"RT-TEST-{date.today().strftime('%m%d')}",
            route_date=date.today(),
            actor_user_id=1
        )
        assert route.id is not None

        shipment = Shipment.query.filter_by(shipment_status="OUT_FOR_DELIVERY").first()
        if not shipment:
            shipment = Shipment.query.first()
            shipment.shipment_status = "OUT_FOR_DELIVERY"

        stop = DispatchService.add_route_stop(
            route_id=route.id,
            shipment_id=shipment.id,
            stop_sequence=1,
            stop_type="DELIVERY",
            actor_user_id=1
        )
        assert stop.id is not None

        # Record failed attempt
        attempt = DispatchService.record_attempt(
            shipment_id=shipment.id,
            driver_id=driver.id,
            outcome="FAILED",
            actor_user_id=1,
            failure_reason="Gate locked / Consignee phone unanswered"
        )
        assert attempt.id is not None
        assert attempt.outcome == "FAILED"
        assert len(shipment.delivery_exceptions) > 0
        assert shipment.shipment_status != "DELIVERED"

def test_successful_delivery_proof_transitions_to_delivered(app):
    """Verify proof of delivery completes successful transition to DELIVERED."""
    with app.app_context():
        driver = Driver.query.first()
        shipment = Shipment.query.filter(Shipment.shipment_status != "DELIVERED").first()
        shipment.shipment_status = "OUT_FOR_DELIVERY"

        attempt = DispatchService.record_attempt(
            shipment_id=shipment.id,
            driver_id=driver.id,
            outcome="SUCCESS",
            actor_user_id=1,
        )
        assert attempt.outcome == "SUCCESS"

        proof = DispatchService.record_delivery_proof(
            attempt_id=attempt.id,
            received_by_name="Kashif Munir (CNIC 61101-1234567-1)",
            actor_user_id=1
        )
        assert proof.id is not None
        assert shipment.shipment_status == "DELIVERED"
