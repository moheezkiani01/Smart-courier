from datetime import datetime, date
from app.extensions import db
from app.models.dispatch import (
    Route,
    RouteStop,
    DeliveryAttempt,
    DeliveryProof,
    DeliveryException,
    VehicleAssignment,
    Driver,
    Vehicle,
)
from app.models.shipments import Shipment
from app.services.shipment_service import ShipmentService
from app.services.audit_service import log_audit

class DispatchService:
    @staticmethod
    def create_route(branch_id: int, driver_id: int, vehicle_id: int, route_code: str, route_date: date, actor_user_id: int) -> Route:
        driver = Driver.query.filter_by(id=driver_id, is_deleted=False).first()
        if not driver:
            raise ValueError("Driver profile not found.")
        if driver.license_expires_on < date.today():
            raise ValueError(f"Driver driver license has expired on {driver.license_expires_on}.")

        vehicle = Vehicle.query.filter_by(id=vehicle_id, is_deleted=False).first()
        if not vehicle:
            raise ValueError("Vehicle not found.")

        route = Route(
            branch_id=branch_id,
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            route_code=route_code,
            route_date=route_date,
            route_status="PLANNED",
            created_by=actor_user_id,
        )
        db.session.add(route)
        db.session.flush()

        # Record vehicle assignment
        assignment = VehicleAssignment(
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            route_id=route.id,
            assigned_at=datetime.utcnow(),
            created_by=actor_user_id,
        )
        db.session.add(assignment)

        log_audit(
            action="CREATE_ROUTE",
            entity_type="Route",
            entity_id=route.id,
            after={"route_code": route_code, "driver_id": driver_id, "vehicle_id": vehicle_id},
            branch_id=branch_id,
            user_id=actor_user_id,
        )

        db.session.commit()
        return route

    @staticmethod
    def add_route_stop(route_id: int, shipment_id: int, stop_sequence: int, stop_type: str, actor_user_id: int) -> RouteStop:
        route = Route.query.filter_by(id=route_id, is_deleted=False).first()
        if not route:
            raise ValueError("Route not found.")

        shipment = Shipment.query.filter_by(id=shipment_id, is_deleted=False).first()
        if not shipment:
            raise ValueError("Shipment not found.")

        existing = RouteStop.query.filter_by(route_id=route_id, stop_sequence=stop_sequence, is_deleted=False).first()
        if existing:
            raise ValueError(f"Stop sequence {stop_sequence} is already assigned on this route.")

        stop = RouteStop(
            route_id=route_id,
            shipment_id=shipment_id,
            stop_sequence=stop_sequence,
            stop_type=stop_type,
            scheduled_at=datetime.utcnow(),
            created_by=actor_user_id,
        )
        db.session.add(stop)

        # Transition shipment according to stop type and lifecycle prerequisites
        if stop_type == "DELIVERY":
            if shipment.shipment_status not in ["AT_DESTINATION_HUB", "DELIVERY_FAILED", "OUT_FOR_DELIVERY"]:
                raise ValueError(
                    f"Shipment {shipment.tracking_number} is currently '{shipment.shipment_status}'. "
                    f"Delivery stops require parcels to be received at destination hub (AT_DESTINATION_HUB)."
                )
            if shipment.shipment_status != "OUT_FOR_DELIVERY":
                ShipmentService.transition(
                    shipment_id=shipment.id,
                    target_status="OUT_FOR_DELIVERY",
                    actor_user_id=actor_user_id,
                    reason=f"Assigned to delivery route {route.route_code}",
                )
        elif stop_type == "PICKUP":
            if shipment.shipment_status == "BOOKED":
                ShipmentService.transition(
                    shipment_id=shipment.id,
                    target_status="PICKUP_ASSIGNED",
                    actor_user_id=actor_user_id,
                    reason=f"Assigned to pickup on route {route.route_code}",
                )

        db.session.commit()
        return stop

    @staticmethod
    def record_attempt(shipment_id: int, driver_id: int, outcome: str, actor_user_id: int, route_stop_id: int = None, failure_reason: str = None) -> DeliveryAttempt:
        if outcome not in ["SUCCESS", "FAILED", "RESCHEDULED"]:
            raise ValueError("Outcome must be SUCCESS, FAILED, or RESCHEDULED.")

        shipment = Shipment.query.filter_by(id=shipment_id, is_deleted=False).first()
        if not shipment:
            raise ValueError("Shipment not found.")

        attempt = DeliveryAttempt(
            shipment_id=shipment_id,
            route_stop_id=route_stop_id,
            driver_id=driver_id,
            attempted_at=datetime.utcnow(),
            outcome=outcome,
            failure_reason=failure_reason,
            created_by=actor_user_id,
        )
        db.session.add(attempt)
        db.session.flush()

        if outcome == "FAILED":
            exception = DeliveryException(
                shipment_id=shipment_id,
                delivery_attempt_id=attempt.id,
                exception_code="ATTEMPT_FAILED",
                explanation=failure_reason or "Customer unavailable / address closed",
                opened_at=datetime.utcnow(),
                created_by=actor_user_id,
            )
            db.session.add(exception)

            if shipment.shipment_status == "OUT_FOR_DELIVERY":
                ShipmentService.transition(
                    shipment_id=shipment_id,
                    target_status="DELIVERY_FAILED",
                    actor_user_id=actor_user_id,
                    reason=f"Delivery attempt failed: {failure_reason}",
                )

        db.session.commit()
        return attempt

    @staticmethod
    def record_delivery_proof(attempt_id: int, received_by_name: str, actor_user_id: int, signed_filename: str = None, photo_filename: str = None) -> DeliveryProof:
        attempt = DeliveryAttempt.query.filter_by(id=attempt_id, is_deleted=False).first()
        if not attempt:
            raise ValueError("Delivery attempt not found.")
        if attempt.outcome != "SUCCESS":
            raise ValueError("Proof of delivery can only be submitted for a SUCCESSFUL attempt.")

        proof = DeliveryProof(
            shipment_id=attempt.shipment_id,
            delivery_attempt_id=attempt.id,
            received_by_name=received_by_name.strip(),
            signed_filename=signed_filename,
            photo_filename=photo_filename,
            delivered_at=datetime.utcnow(),
            created_by=actor_user_id,
        )
        db.session.add(proof)

        # Transition shipment to DELIVERED
        ShipmentService.transition(
            shipment_id=attempt.shipment_id,
            target_status="DELIVERED",
            actor_user_id=actor_user_id,
            reason=f"Delivered to {received_by_name}",
        )

        db.session.commit()
        return proof
