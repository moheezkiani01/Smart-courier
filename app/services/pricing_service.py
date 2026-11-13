from datetime import date
from app.extensions import db
from app.models.catalog import RateCard, RateCardRule, PackagingType, ServiceType
from app.models.organization import ServiceZone
from app.models.finance import Discount

class PricingService:
    @staticmethod
    def calculate_quote(
        service_type_id: int,
        origin_zone_id: int,
        destination_zone_id: int,
        weight_grams: int,
        packaging_type_id: int = None,
        discount_code: str = None,
        query_date: date = None,
    ) -> dict:
        """
        Calculate an exact price quote in integer paisa using active rate cards and weight rules.
        """
        if weight_grams <= 0:
            raise ValueError("Weight must be greater than zero grams.")

        if query_date is None:
            query_date = date.today()

        # 1. Locate valid rate card strictly for the requested service and route
        rate_card = RateCard.query.filter(
            RateCard.service_type_id == service_type_id,
            RateCard.origin_zone_id == origin_zone_id,
            RateCard.destination_zone_id == destination_zone_id,
            RateCard.valid_from <= query_date,
            RateCard.valid_until >= query_date,
            RateCard.is_deleted == False,
        ).first()

        # Strict requirement: Do not silently use unrelated routes or service rates
        if not rate_card:
            st = db.session.get(ServiceType, service_type_id)
            oz = db.session.get(ServiceZone, origin_zone_id)
            dz = db.session.get(ServiceZone, destination_zone_id)
            st_name = st.name if st else f"Service #{service_type_id}"
            oz_name = oz.name if oz else f"Zone #{origin_zone_id}"
            dz_name = dz.name if dz else f"Zone #{destination_zone_id}"
            raise ValueError(f"No active rate card configured for '{st_name}' between {oz_name} and {dz_name}.")

        # 2. Locate applicable weight rule
        rule = RateCardRule.query.filter(
            RateCardRule.rate_card_id == rate_card.id,
            RateCardRule.min_weight_grams <= weight_grams,
            RateCardRule.max_weight_grams >= weight_grams,
            RateCardRule.is_deleted == False,
        ).first()

        # If weight exceeds rules, find highest rule with extra_per_kg
        if not rule:
            rule = RateCardRule.query.filter(
                RateCardRule.rate_card_id == rate_card.id,
                RateCardRule.is_deleted == False,
            ).order_by(RateCardRule.max_weight_grams.desc()).first()

        if not rule:
            raise ValueError(f"No pricing rule found for weight {weight_grams}g on rate card #{rate_card.id}.")

        base_fee_paisa = rule.base_fee_paisa
        extra_fee_paisa = 0
        if weight_grams > rule.max_weight_grams and rule.extra_per_kg_paisa > 0:
            excess_grams = weight_grams - rule.max_weight_grams
            excess_kg = (excess_grams + 999) // 1000  # Ceiling to nearest kg
            extra_fee_paisa = excess_kg * rule.extra_per_kg_paisa

        shipping_fee_paisa = base_fee_paisa + extra_fee_paisa

        # 3. Packaging fee
        packaging_fee_paisa = 0
        if packaging_type_id:
            pkg = PackagingType.query.filter_by(id=packaging_type_id, is_deleted=False).first()
            if pkg:
                packaging_fee_paisa = pkg.fee_paisa

        # 4. Optional discount coupon
        discount_paisa = 0
        discount_obj = None
        discount_applied = False
        discount_message = None

        if discount_code and isinstance(discount_code, str) and discount_code.strip():
            clean_code = discount_code.strip().upper()
            discount_obj = Discount.query.filter_by(code=clean_code, is_deleted=False).first()
            if not discount_obj:
                discount_message = f"Coupon '{clean_code}' is invalid."
            elif not (discount_obj.valid_from <= query_date <= discount_obj.valid_until):
                discount_message = f"Coupon '{clean_code}' has expired or is not yet active."
            else:
                if discount_obj.discount_type == "FIXED":
                    discount_paisa = min(shipping_fee_paisa + packaging_fee_paisa, discount_obj.value)
                elif discount_obj.discount_type == "PERCENTAGE":
                    # value is in basis points e.g. 1000 = 10%
                    discount_paisa = ((shipping_fee_paisa + packaging_fee_paisa) * discount_obj.value) // 10000
                discount_applied = True
                discount_message = f"Coupon '{clean_code}' applied successfully!"

        # 5. Tax (standard 0 for MVP or configurable)
        tax_paisa = 0
        total_paisa = max(0, shipping_fee_paisa + packaging_fee_paisa - discount_paisa + tax_paisa)

        return {
            "rate_card_id": rate_card.id,
            "rule_id": rule.id,
            "base_fee_paisa": shipping_fee_paisa,
            "packaging_fee_paisa": packaging_fee_paisa,
            "discount_paisa": discount_paisa,
            "discount_id": discount_obj.id if (discount_obj and discount_applied) else None,
            "discount_code": discount_code.strip().upper() if (discount_code and isinstance(discount_code, str) and discount_code.strip()) else None,
            "discount_applied": discount_applied,
            "discount_message": discount_message,
            "tax_paisa": tax_paisa,
            "total_paisa": total_paisa,
            "currency": rate_card.currency,
        }
