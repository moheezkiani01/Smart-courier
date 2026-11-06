from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, BooleanField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

class ShipmentBookingForm(FlaskForm):
    customer_id = SelectField("Customer Account", coerce=int, validators=[Optional()])
    origin_branch_id = SelectField("Origin Branch", coerce=int, validators=[Optional()])
    destination_branch_id = SelectField("Destination Branch", coerce=int, validators=[Optional()])
    service_type_id = SelectField("Service Type", coerce=int, validators=[DataRequired()])
    parcel_category_id = SelectField("Parcel Category", coerce=int, validators=[DataRequired()])
    packaging_type_id = SelectField("Packaging Type", coerce=int, validators=[DataRequired()])

    # Saved Address Selectors (Customer convenience)
    use_saved_sender_address = SelectField("Use Saved Sender Address", coerce=int, validators=[Optional()])
    use_saved_recipient = SelectField("Use Saved Recipient", coerce=int, validators=[Optional()])

    # Sender Address Snapshot Fields
    sender_name = StringField("Sender Name", validators=[DataRequired(), Length(max=150)])
    sender_phone = StringField("Sender Phone", validators=[DataRequired(), Length(max=30)])
    sender_zone_id = SelectField("Sender Service Zone", coerce=int, validators=[DataRequired()])
    sender_line1 = StringField("Sender Complete Address", validators=[DataRequired(), Length(max=255)])
    sender_city = StringField("Sender City", validators=[DataRequired(), Length(max=100)])
    sender_postal = StringField("Sender Postal Code", validators=[Optional(), Length(max=20)])
    save_sender_address = BooleanField("Save this address to my Address Book", default=False)

    # Recipient Address Snapshot Fields
    recipient_name = StringField("Recipient Name", validators=[DataRequired(), Length(max=150)])
    recipient_phone = StringField("Recipient Phone", validators=[DataRequired(), Length(max=30)])
    recipient_zone_id = SelectField("Recipient Service Zone", coerce=int, validators=[DataRequired()])
    recipient_line1 = StringField("Recipient Complete Address", validators=[DataRequired(), Length(max=255)])
    recipient_city = StringField("Recipient City", validators=[DataRequired(), Length(max=100)])
    recipient_postal = StringField("Recipient Postal Code", validators=[Optional(), Length(max=20)])
    save_recipient = BooleanField("Save this recipient to my Address Book", default=False)

    # Parcel Item Details
    item_description = StringField("Item Description", default="Standard Document / Parcel", validators=[DataRequired(), Length(max=255)])
    item_quantity = IntegerField("Pieces / Quantity", default=1, validators=[DataRequired(), NumberRange(min=1)])
    weight_grams = IntegerField("Total Weight (Grams)", default=500, validators=[DataRequired(), NumberRange(min=10)])
    
    # Financials (Supported in both PKR and raw Paisa for backward compatibility)
    declared_value_pkr = IntegerField("Declared Item Value (PKR)", default=0, validators=[Optional(), NumberRange(min=0)])
    cod_due_pkr = IntegerField("Cash on Delivery Due (PKR)", default=0, validators=[Optional(), NumberRange(min=0)])
    declared_value_paisa = IntegerField("Declared Item Value (Paisa)", default=0, validators=[Optional(), NumberRange(min=0)])
    cod_due_paisa = IntegerField("Cash on Delivery Due (Paisa)", default=0, validators=[Optional(), NumberRange(min=0)])

    discount_code = StringField("Discount Coupon", validators=[Optional(), Length(max=40)])
    pickup_type = SelectField(
        "Pickup / Drop-off Preference",
        choices=[("PICKUP", "Doorstep Pickup (Courier collects from sender)"), ("DROP_OFF", "Branch Drop-off (I will drop at courier branch)")],
        default="PICKUP",
        validators=[DataRequired()]
    )
    pickup_time_slot = SelectField(
        "Preferred Pickup Time Window",
        choices=[
            ("MORNING", "Morning Window (09:00 AM - 01:00 PM)"),
            ("AFTERNOON", "Afternoon Window (01:00 PM - 05:00 PM)"),
            ("EVENING", "Evening Window (05:00 PM - 08:00 PM)")
        ],
        default="MORNING",
        validators=[Optional()]
    )
    schedule_pickup = BooleanField("Schedule Courier Pickup", default=True)
    pickup_notes = TextAreaField("Special Instructions / Access Notes", validators=[Optional(), Length(max=255)])

    submit = SubmitField("Confirm & Book Shipment")

class TransitionForm(FlaskForm):
    target_status = SelectField("Next Workflow Status", validators=[DataRequired()])
    reason = StringField("Transition Note / Reason", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Update Status")

class PickupAssignForm(FlaskForm):
    driver_id = SelectField("Assign Driver", coerce=int, validators=[DataRequired()])
    vehicle_id = SelectField("Assign Vehicle", coerce=int, validators=[Optional()])
    submit = SubmitField("Assign Pickup")
