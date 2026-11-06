from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

class CustomerForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=150)])
    customer_code = StringField("Customer Code", validators=[Optional(), Length(max=50)])
    email = StringField("Email Address", validators=[Optional(), Email(), Length(max=180)])
    phone = StringField("Phone Number", validators=[DataRequired(), Length(max=30)])
    submit = SubmitField("Save Customer")

class CustomerAddressForm(FlaskForm):
    zone_id = SelectField("Service Zone", coerce=int, validators=[DataRequired()])
    label = StringField("Address Label (e.g. Office, Warehouse, Home)", validators=[DataRequired(), Length(max=50)])
    line1 = StringField("Street Address", validators=[DataRequired(), Length(max=255)])
    city = StringField("City", validators=[DataRequired(), Length(max=100)])
    postal_code = StringField("Postal Code", validators=[Optional(), Length(max=20)])
    submit = SubmitField("Save Address")

class CustomerContactForm(FlaskForm):
    name = StringField("Contact Person Name", validators=[DataRequired(), Length(max=120)])
    phone = StringField("Contact Phone", validators=[DataRequired(), Length(max=30)])
    contact_type = SelectField("Contact Type", choices=[("BILLING", "Billing"), ("OPERATIONS", "Operations"), ("GENERAL", "General")])
    is_primary = BooleanField("Primary Contact")
    submit = SubmitField("Save Contact")

class RecipientProfileForm(FlaskForm):
    name = StringField("Recipient Name", validators=[DataRequired(), Length(max=150)])
    phone = StringField("Recipient Phone", validators=[DataRequired(), Length(max=30)])
    email = StringField("Recipient Email", validators=[Optional(), Email(), Length(max=180)])
    zone_id = SelectField("Service Zone", coerce=int, validators=[DataRequired()])
    line1 = StringField("Street Address", validators=[DataRequired(), Length(max=255)])
    city = StringField("City", validators=[DataRequired(), Length(max=100)])
    postal_code = StringField("Postal Code", validators=[Optional(), Length(max=20)])
    submit = SubmitField("Save Recipient")
