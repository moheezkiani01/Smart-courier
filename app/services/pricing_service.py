from datetime import date
from app.models.catalog import RateCard, RateCardRule, PackagingType
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

        # 1. Locate valid rate card
        rate_card = RateCard.query.filter(
            RateCard.service_type_id == service_type_id,
            RateCard.origin_zone_id == origin_zone_id,
            RateCard.destination_zone_id == destination_zone_id,
            RateCard.valid_from <= query_date,
            RateCard.valid_until >= query_date,
            RateCard.is_deleted == False,
        ).first()

        if not rate_card:
            raise ValueError("No active rate card configured for this service and zone combination.")

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
            raise ValueError("No pricing rule found for the given weight.")

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

        # 4. Optional discount
        discount_paisa = 0
        discount_obj = None
        if discount_code:
            discount_obj = Discount.query.filter_by(code=discount_code.strip().upper(), is_deleted=False).first()
            if discount_obj and discount_obj.valid_from <= query_date <= discount_obj.valid_until:
                if discount_obj.discount_type == "FIXED":
                    discount_paisa = min(shipping_fee_paisa + packaging_fee_paisa, discount_obj.value)
                elif discount_obj.discount_type == "PERCENTAGE":
                    # value is in basis points e.g. 1000 = 10%
                    discount_paisa = ((shipping_fee_paisa + packaging_fee_paisa) * discount_obj.value) // 10000

        # 5. Tax (standard 0 for MVP or configurable)
        tax_paisa = 0
        total_paisa = max(0, shipping_fee_paisa + packaging_fee_paisa - discount_paisa + tax_paisa)

        return {
            "rate_card_id": rate_card.id,
            "rule_id": rule.id,
            "base_fee_paisa": shipping_fee_paisa,
            "packaging_fee_paisa": packaging_fee_paisa,
            "discount_paisa": discount_paisa,
            "discount_id": discount_obj.id if discount_obj else None,
            "tax_paisa": tax_paisa,
            "total_paisa": total_paisa,
            "currency": rate_card.currency,
        }
