from datetime import date
from sqlalchemy import text
from app.extensions import db
from app.models.shipments import Shipment
from app.models.dispatch import Driver, Vehicle
from app.models.organization import Employee
from app.services.shipment_service import ShipmentService
from app.services.hub_service import HubService
from app.services.dispatch_service import DispatchService
from app.services.finance_service import FinanceService

def test_complete_end_to_end_courier_lifecycle(app):
    """
    Simulate full operational courier workflow from booking to delivered payment:
    1. Booking with frozen quote & invoice creation
    2. Pickup assignment and execution
    3. Hub scan and transit
    4. Route stop sequencing
    5. Driver delivery attempt and proof verification
    6. Invoice financial settlement
    7. Database consistency verification
    """
    with app.app_context():
        emp = Employee.query.first()
        # Step 1: Book Shipment (LHR -> KHI, Standard Service)
        sender = {"name": "Kamran Electronics", "phone": "0300-5551122", "zone_id": 1, "line1": "Gulberg", "city": "Lahore"}
        recipient = {"name": "Tariq Goods", "phone": "0333-7778899", "zone_id": 2, "line1": "Clifton", "city": "Karachi"}
        items = [{"description": "Laptop Adapter", "quantity": 1, "weight_grams": 600, "declared_value_paisa": 450000}]

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
            declared_value_paisa=450000,
            cod_due_paisa=350000,
        )
        assert shipment.shipment_status == "BOOKED"
        tracking_num = shipment.tracking_number
        invoice = shipment.invoice
        assert invoice is not None
        assert invoice.total_paisa > 0

        # Step 2: Pickup Assignment & Pickup
        ShipmentService.transition(shipment.id, "PICKUP_ASSIGNED", actor_user_id=1, reason="Driver scheduled for pickup")
        assert shipment.shipment_status == "PICKUP_ASSIGNED"

        ShipmentService.transition(shipment.id, "PICKED_UP", actor_user_id=1, reason="Parcel picked up from merchant")
        assert shipment.shipment_status == "PICKED_UP"

        # Step 3: Hub Arrival & Scan
        scan = HubService.record_scan(shipment.id, hub_id=1, employee_id=emp.id, actor_user_id=1, scan_code="INBOUND")
        assert scan.id is not None
        assert shipment.current_hub_id == 1

        ShipmentService.transition(shipment.id, "AT_ORIGIN_HUB", actor_user_id=1, reason="Sorted at Lahore Hub")
        assert shipment.shipment_status == "AT_ORIGIN_HUB"

        # Step 4: Transfer to Destination Hub
        transfer = HubService.initiate_transfer(shipment.id, from_hub_id=1, to_hub_id=2, employee_id=emp.id, actor_user_id=1)
        assert transfer.transfer_status == "IN_TRANSIT"
        assert shipment.shipment_status == "IN_TRANSIT"

        HubService.receive_transfer(transfer.id, employee_id=emp.id, actor_user_id=1)
        assert shipment.shipment_status == "AT_DESTINATION_HUB"

        # Step 5: Route Dispatch & Delivery
        driver = Driver.query.first()
        vehicle = Vehicle.query.first()
        route = DispatchService.create_route(
            branch_id=1,
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            route_code=f"RT-E2E-{tracking_num[-4:]}",
            route_date=date.today(),
            actor_user_id=1,
        )
        stop = DispatchService.add_route_stop(route.id, shipment.id, stop_sequence=1, stop_type="DELIVERY", actor_user_id=1)
        assert shipment.shipment_status == "OUT_FOR_DELIVERY"

        # Step 6: Driver Delivers with Proof
        attempt = DispatchService.record_attempt(shipment.id, driver.id, "SUCCESS", actor_user_id=1, route_stop_id=stop.id)
        assert attempt.outcome == "SUCCESS"

        proof = DispatchService.record_delivery_proof(attempt.id, received_by_name="Tariq Mahmood (Owner)", actor_user_id=1)
        assert proof.id is not None
        assert shipment.shipment_status == "DELIVERED"

        # Step 7: Invoice Settlement
        payment = FinanceService.record_payment(
            invoice_id=invoice.id,
            amount_paisa=invoice.amount_due_paisa,
            method="CASH",
            reference_code="E2E-PAID",
            employee_id=emp.id,
            actor_user_id=1,
        )
        assert payment.id is not None
        assert invoice.invoice_status == "PAID"

        # Step 8: Database Integrity Final Audit
        conn = db.engine.connect()
        violations = conn.execute(text("PRAGMA foreign_key_check")).fetchall()
        assert len(violations) == 0, f"Integrity violations found: {violations}"
