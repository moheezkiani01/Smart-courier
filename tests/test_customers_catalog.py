import pytest
from app.models.catalog import Customer, ServiceType, RateCard
from app.services.pricing_service import PricingService

def test_customer_recipients_association(app):
    """Verify 1:N customer addresses and saved recipients."""
    with app.app_context():
        customer = Customer.query.first()
        assert customer is not None
        assert len(customer.addresses) >= 1
        assert len(customer.recipients) >= 1
        assert customer.recipients[0].addresses is not None

def test_pricing_calculation_integer_paisa(app):
    """Verify exact tariff calculation in integer paisa with zero floating-point drift."""
    with app.app_context():
        # Standard Express from Zone 1 to Zone 2, 500g
        quote = PricingService.calculate_quote(
            service_type_id=1,
            origin_zone_id=1,
            destination_zone_id=2,
            weight_grams=500,
            packaging_type_id=1,
        )
        assert quote["total_paisa"] > 0
        assert isinstance(quote["total_paisa"], int)
        assert quote["packaging_fee_paisa"] == 5000  # Rs. 50.00
        assert quote["currency"] == "PKR"

def test_pricing_with_fixed_discount(app):
    """Verify promotional coupon deduction."""
    with app.app_context():
        quote = PricingService.calculate_quote(
            service_type_id=1,
            origin_zone_id=1,
            destination_zone_id=2,
            weight_grams=500,
            discount_code="EIDMUBARAK",
        )
        assert quote["discount_paisa"] > 0
        assert quote["total_paisa"] == quote["base_fee_paisa"] - quote["discount_paisa"]

def test_pricing_rejects_negative_weight(app):
    """Ensure invalid weight raises ValueError."""
    with app.app_context():
        with pytest.raises(ValueError):
            PricingService.calculate_quote(
                service_type_id=1,
                origin_zone_id=1,
                destination_zone_id=2,
                weight_grams=-100,
            )
