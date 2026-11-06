from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, BooleanField, DateField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

class ServiceTypeForm(FlaskForm):
    code = StringField("Service Code", validators=[DataRequired(), Length(max=30)])
    name = StringField("Service Name", validators=[DataRequired(), Length(max=100)])
    target_days = IntegerField("Target Delivery Days", default=1, validators=[DataRequired(), NumberRange(min=1, max=30)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Save Service Type")

class ParcelCategoryForm(FlaskForm):
    code = StringField("Category Code", validators=[DataRequired(), Length(max=30)])
    name = StringField("Category Name", validators=[DataRequired(), Length(max=100)])
    is_fragile = BooleanField("Requires Fragile Handling")
    submit = SubmitField("Save Category")

class PackagingTypeForm(FlaskForm):
    code = StringField("Packaging Code", validators=[DataRequired(), Length(max=30)])
    name = StringField("Packaging Name", validators=[DataRequired(), Length(max=100)])
    fee_paisa = IntegerField("Packaging Fee (in Paisa, 100 Paisa = 1 PKR)", default=0, validators=[DataRequired(), NumberRange(min=0)])
    max_weight_grams = IntegerField("Max Weight (grams)", default=5000, validators=[DataRequired(), NumberRange(min=100)])
    submit = SubmitField("Save Packaging")

class RateCardForm(FlaskForm):
    service_type_id = SelectField("Service Type", coerce=int, validators=[DataRequired()])
    origin_zone_id = SelectField("Origin Zone", coerce=int, validators=[DataRequired()])
    destination_zone_id = SelectField("Destination Zone", coerce=int, validators=[DataRequired()])
    valid_from = DateField("Valid From", validators=[DataRequired()])
    valid_until = DateField("Valid Until", validators=[DataRequired()])
    currency = StringField("Currency Code", default="PKR", validators=[DataRequired(), Length(max=10)])
    submit = SubmitField("Save Rate Card")

class RateCardRuleForm(FlaskForm):
    min_weight_grams = IntegerField("Min Weight (grams)", default=0, validators=[DataRequired(), NumberRange(min=0)])
    max_weight_grams = IntegerField("Max Weight (grams)", default=1000, validators=[DataRequired(), NumberRange(min=1)])
    base_fee_paisa = IntegerField("Base Fee (Paisa)", default=25000, validators=[DataRequired(), NumberRange(min=0)])
    extra_per_kg_paisa = IntegerField("Extra Per Kg (Paisa)", default=5000, validators=[NumberRange(min=0)])
    submit = SubmitField("Save Weight Rule")

class DiscountForm(FlaskForm):
    code = StringField("Discount Coupon Code", validators=[DataRequired(), Length(max=40)])
    discount_type = SelectField("Discount Type", choices=[("FIXED", "Fixed Amount (Paisa)"), ("PERCENTAGE", "Percentage (Basis points: 1000 = 10%)")])
    value = IntegerField("Discount Value", validators=[DataRequired(), NumberRange(min=1)])
    valid_from = DateField("Valid From", validators=[DataRequired()])
    valid_until = DateField("Valid Until", validators=[DataRequired()])
    max_redemptions = IntegerField("Max Redemptions", validators=[Optional(), NumberRange(min=1)])
    submit = SubmitField("Save Discount")
