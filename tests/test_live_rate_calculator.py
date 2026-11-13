import pytest
from app.services.pricing_service import PricingService
from app.services.shipment_service import ShipmentService
from app.models.catalog import RateCard, ServiceType
from app.models.organization import ServiceZone
from app.models.auth import User
from app.models.finance import Invoice

def test_api_quote_empty_coupon(client):
    """Test API calculation when coupon is None, empty string, or omitted."""
    # 1. discount_code is None (explicit null from JS)
    res1 = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 500,
        "discount_code": None
    })
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1["status"] == "success"
    assert data1["quote"]["base_fee_pkr"] == 450.0
    assert data1["quote"]["discount_pkr"] == 0.0
    assert data1["quote"]["total_pkr"] == 450.0
    assert data1["quote"]["discount_applied"] is False

    # 2. discount_code is empty string
    res2 = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 500,
        "discount_code": ""
    })
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["quote"]["total_pkr"] == 450.0
    assert data2["quote"]["discount_pkr"] == 0.0

    # 3. discount_code omitted entirely
    res3 = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 500
    })
    assert res3.status_code == 200
    data3 = res3.get_json()
    assert data3["quote"]["total_pkr"] == 450.0


def test_api_quote_valid_coupon_eidmubarak(client):
    """Test valid discount coupon EIDMUBARAK (10% discount)."""
    res = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 500,
        "discount_code": "EIDMUBARAK"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    q = data["quote"]
    assert q["base_fee_pkr"] == 450.0
    assert q["discount_pkr"] == 45.0  # 10% of 450
    assert q["total_pkr"] == 405.0   # 450 - 45
    assert q["discount_applied"] is True
    assert "applied successfully" in q["discount_message"]


def test_api_quote_invalid_coupon(client):
    """Test invalid discount coupon returns standard rate with informative message."""
    res = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 500,
        "discount_code": "INVALID99"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    q = data["quote"]
    assert q["base_fee_pkr"] == 450.0
    assert q["discount_pkr"] == 0.0
    assert q["total_pkr"] == 450.0
    assert q["discount_applied"] is False
    assert "invalid" in q["discount_message"].lower()


def test_api_quote_weights_500g_1kg_2kg(client):
    """Test 500g, 1000g, and 2000g weights on Lahore to Karachi route."""
    # 500g (Tier 0-1000g: base 450 PKR)
    res_500 = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 500
    })
    assert res_500.get_json()["quote"]["total_pkr"] == 450.0

    # 1000g (Tier 0-1000g: base 450 PKR)
    res_1000 = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 1000
    })
    assert res_1000.get_json()["quote"]["total_pkr"] == 450.0

    # 2000g (Tier 1001-5000g: base 750 PKR)
    res_2000 = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 2000
    })
    assert res_2000.get_json()["quote"]["total_pkr"] == 750.0


def test_api_quote_lahore_to_lahore_vs_lahore_to_karachi(client):
    """Test intra-city (Lahore to Lahore) and inter-city (Lahore to Karachi) tariffs."""
    # Intra-city: Lahore Metro (Zone 1) to Lahore Metro (Zone 1)
    res_intra = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 1,
        "weight_grams": 500
    })
    assert res_intra.status_code == 200
    assert res_intra.get_json()["quote"]["total_pkr"] == 250.0  # Intra-city base 250 PKR

    # Inter-city: Lahore Metro (Zone 1) to Karachi Central (Zone 2)
    res_inter = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 500
    })
    assert res_inter.status_code == 200
    assert res_inter.get_json()["quote"]["total_pkr"] == 450.0  # Inter-city base 450 PKR


def test_api_quote_field_validations(client):
    """Test validation errors on missing service, origin zone, destination zone, or invalid weight."""
    # Missing service_type_id
    res_no_svc = client.post("/catalog/api/quote", json={
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 500
    })
    assert res_no_svc.status_code == 400
    assert "service" in res_no_svc.get_json()["message"].lower()

    # Missing origin_zone_id
    res_no_orig = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 500
    })
    assert res_no_orig.status_code == 400
    assert "origin zone" in res_no_orig.get_json()["message"].lower()

    # Missing destination_zone_id
    res_no_dest = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "weight_grams": 500
    })
    assert res_no_dest.status_code == 400
    assert "destination zone" in res_no_dest.get_json()["message"].lower()

    # Non-positive weight
    res_bad_wt = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 2,
        "weight_grams": 0
    })
    assert res_bad_wt.status_code == 400
    assert "weight" in res_bad_wt.get_json()["message"].lower()


def test_api_quote_rejects_unconfigured_route_without_fallback(client, app):
    """Verify that unconfigured routes reject cleanly without falling back to unrelated routes."""
    res = client.post("/catalog/api/quote", json={
        "service_type_id": 1,
        "origin_zone_id": 1,
        "destination_zone_id": 9999,  # Non-existent zone
        "weight_grams": 500
    })
    assert res.status_code == 400
    err_msg = res.get_json()["message"]
    assert "No active rate card configured" in err_msg


def test_quote_matches_final_booking_invoice(app, client):
    """Verify exact parity between API quote, PricingService, and final booking Invoice."""
    with app.app_context():
        # 1. Fetch quote via API
        api_res = client.post("/catalog/api/quote", json={
            "service_type_id": 1,
            "origin_zone_id": 1,
            "destination_zone_id": 2,
            "weight_grams": 1000,
            "packaging_type_id": 1,
            "discount_code": "EIDMUBARAK"
        })
        assert api_res.status_code == 200
        api_quote = api_res.get_json()["quote"]

        # 2. Calculate quote directly via PricingService
        direct_quote = PricingService.calculate_quote(
            service_type_id=1,
            origin_zone_id=1,
            destination_zone_id=2,
            weight_grams=1000,
            packaging_type_id=1,
            discount_code="EIDMUBARAK"
        )

        assert api_quote["base_fee_pkr"] == direct_quote["base_fee_paisa"] / 100.0
        assert api_quote["packaging_fee_pkr"] == direct_quote["packaging_fee_paisa"] / 100.0
        assert api_quote["discount_pkr"] == direct_quote["discount_paisa"] / 100.0
        assert api_quote["total_pkr"] == direct_quote["total_paisa"] / 100.0

        # 3. Simulate booking via ShipmentService
        from app.extensions import db
        from app.models.finance import ShipmentDiscount, InvoiceItem
        from app.models.shipments import ShipmentService as ShipmentQuote, ShipmentAddress, ShipmentItem, ShipmentStatusHistory
        from app.models.dispatch import TrackingEvent

        admin = User.query.filter_by(email="admin@smartcourier.pk").first()
        shipment = ShipmentService.book_shipment(
            customer_id=1,
            origin_branch_id=1,
            destination_branch_id=2,
            service_type_id=1,
            parcel_category_id=1,
            packaging_type_id=1,
            sender_data={
                "name": "Parity Test Sender",
                "phone": "+923001234567",
                "line1": "Mall Road",
                "city": "Lahore",
                "zone_id": 1
            },
            recipient_data={
                "name": "Parity Test Recipient",
                "phone": "+923219876543",
                "line1": "Clifton Block 2",
                "city": "Karachi",
                "zone_id": 2
            },
            items_data=[{
                "description": "Rate Parity Test Consignment",
                "quantity": 1,
                "weight_grams": 1000,
                "declared_value_paisa": 100000
            }],
            actor_user_id=admin.id,
            discount_code="EIDMUBARAK"
        )

        invoice = Invoice.query.filter_by(shipment_id=shipment.id).first()
        assert invoice is not None
        assert invoice.total_paisa == direct_quote["total_paisa"]
        assert invoice.discount_paisa == direct_quote["discount_paisa"]
        assert invoice.subtotal_paisa == direct_quote["base_fee_paisa"] + direct_quote["packaging_fee_paisa"]
        assert invoice.total_paisa / 100.0 == api_quote["total_pkr"]

        # Clean up test shipment and associated child records to prevent test leakage
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        db.session.delete(invoice)
        ShipmentDiscount.query.filter_by(shipment_id=shipment.id).delete()
        TrackingEvent.query.filter_by(shipment_id=shipment.id).delete()
        ShipmentStatusHistory.query.filter_by(shipment_id=shipment.id).delete()
        ShipmentQuote.query.filter_by(shipment_id=shipment.id).delete()
        ShipmentAddress.query.filter_by(shipment_id=shipment.id).delete()
        ShipmentItem.query.filter_by(shipment_id=shipment.id).delete()
        db.session.delete(shipment)
        db.session.commit()
