from datetime import datetime, date
from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.catalog import catalog_bp
from app.security.rbac import roles_required
from app.models.catalog import (
    ServiceType,
    ParcelCategory,
    PackagingType,
    RateCard,
    RateCardRule,
)
from app.models.organization import ServiceZone
from app.models.finance import Discount
from app.forms.catalog_forms import (
    ServiceTypeForm,
    ParcelCategoryForm,
    PackagingTypeForm,
    RateCardForm,
    RateCardRuleForm,
    DiscountForm,
)
from app.services.pricing_service import PricingService
from app.services.audit_service import log_audit

@catalog_bp.route("/rates", methods=["GET"])
@login_required
def rates():
    rate_cards = RateCard.query.filter_by(is_deleted=False).all()
    services = ServiceType.query.filter_by(is_deleted=False).all()
    packages = PackagingType.query.filter_by(is_deleted=False).all()
    categories = ParcelCategory.query.filter_by(is_deleted=False).all()
    return render_template(
        "catalog/rates.html",
        rate_cards=rate_cards,
        services=services,
        packages=packages,
        categories=categories,
    )

@catalog_bp.route("/rate-cards/new", methods=["GET", "POST"])
@login_required
@roles_required("SUPER_ADMIN", "BRANCH_MANAGER")
def new_rate_card():
    form = RateCardForm()
    services = ServiceType.query.filter_by(is_deleted=False).all()
    zones = ServiceZone.query.filter_by(is_deleted=False).all()
    form.service_type_id.choices = [(s.id, s.name) for s in services]
    form.origin_zone_id.choices = [(z.id, f"{z.name} ({z.city})") for z in zones]
    form.destination_zone_id.choices = [(z.id, f"{z.name} ({z.city})") for z in zones]

    if form.validate_on_submit():
        card = RateCard(
            service_type_id=form.service_type_id.data,
            origin_zone_id=form.origin_zone_id.data,
            destination_zone_id=form.destination_zone_id.data,
            valid_from=form.valid_from.data,
            valid_until=form.valid_until.data,
            currency=form.currency.data.strip().upper(),
            created_by=current_user.id,
        )
        db.session.add(card)
        db.session.flush()
        log_audit("CREATE_RATE_CARD", "RateCard", card.id, user_id=current_user.id)
        db.session.commit()
        flash("Rate card created. Now add weight tier rules.", "success")
        return redirect(url_for("catalog.rate_card_detail", card_id=card.id))
    return render_template("catalog/rate_card_form.html", form=form)

@catalog_bp.route("/rate-cards/<int:card_id>", methods=["GET", "POST"])
@login_required
def rate_card_detail(card_id):
    card = RateCard.query.filter_by(id=card_id, is_deleted=False).first_or_404()
    rule_form = RateCardRuleForm()

    if request.method == "POST":
        if not (current_user.has_role("SUPER_ADMIN") or current_user.has_role("BRANCH_MANAGER")):
            abort(403)
        if rule_form.validate_on_submit():
            try:
                rule = RateCardRule(
                    rate_card_id=card.id,
                    min_weight_grams=rule_form.min_weight_grams.data,
                    max_weight_grams=rule_form.max_weight_grams.data,
                    base_fee_paisa=rule_form.base_fee_paisa.data,
                    extra_per_kg_paisa=rule_form.extra_per_kg_paisa.data or 0,
                    created_by=current_user.id,
                )
                db.session.add(rule)
                db.session.commit()
                flash("Weight pricing band added to rate card.", "success")
                return redirect(url_for("catalog.rate_card_detail", card_id=card.id))
            except Exception as e:
                db.session.rollback()
                flash(f"Error adding rate rule: {str(e)}", "danger")

    return render_template("catalog/rate_card_detail.html", card=card, form=rule_form)

@catalog_bp.route("/calculator", methods=["GET", "POST"])
def calculator():
    services = ServiceType.query.filter_by(is_deleted=False).all()
    zones = ServiceZone.query.filter_by(is_deleted=False).all()
    packages = PackagingType.query.filter_by(is_deleted=False).all()

    quote_result = None
    error_message = None

    if request.method == "POST":
        try:
            service_type_id = int(request.form.get("service_type_id"))
            origin_zone_id = int(request.form.get("origin_zone_id"))
            dest_zone_id = int(request.form.get("destination_zone_id"))
            weight_grams = int(request.form.get("weight_grams", 500))
            pkg_id = request.form.get("packaging_type_id")
            packaging_type_id = int(pkg_id) if pkg_id else None
            coupon = request.form.get("discount_code", "").strip() or None

            quote_result = PricingService.calculate_quote(
                service_type_id=service_type_id,
                origin_zone_id=origin_zone_id,
                destination_zone_id=dest_zone_id,
                weight_grams=weight_grams,
                packaging_type_id=packaging_type_id,
                discount_code=coupon,
            )
        except Exception as e:
            error_message = str(e)

    return render_template(
        "catalog/calculator.html",
        services=services,
        zones=zones,
        packages=packages,
        quote=quote_result,
        error=error_message,
    )

@catalog_bp.route("/api/quote", methods=["POST"])
def quote_api():
    """Real-time JSON price calculation for booking wizard and frontend forms."""
    try:
        data = request.get_json() or request.form
        service_type_id = int(data.get("service_type_id"))
        origin_zone_id = int(data.get("origin_zone_id"))
        dest_zone_id = int(data.get("destination_zone_id"))
        weight_grams = int(data.get("weight_grams", 500))
        pkg_id = data.get("packaging_type_id")
        packaging_type_id = int(pkg_id) if pkg_id and int(pkg_id) > 0 else None
        coupon = data.get("discount_code", "").strip() or None

        quote = PricingService.calculate_quote(
            service_type_id=service_type_id,
            origin_zone_id=origin_zone_id,
            destination_zone_id=dest_zone_id,
            weight_grams=weight_grams,
            packaging_type_id=packaging_type_id,
            discount_code=coupon,
        )
        return jsonify({
            "status": "success",
            "quote": {
                "base_fee_pkr": quote["base_fee_paisa"] / 100.0,
                "packaging_fee_pkr": quote["packaging_fee_paisa"] / 100.0,
                "discount_pkr": quote["discount_paisa"] / 100.0,
                "tax_pkr": quote["tax_paisa"] / 100.0,
                "total_pkr": quote["total_paisa"] / 100.0,
                "currency": quote["currency"],
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
