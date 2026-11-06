from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, DateField, TextAreaField, FileField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

class RouteForm(FlaskForm):
    branch_id = SelectField("Operating Branch", coerce=int, validators=[DataRequired()])
    driver_id = SelectField("Assigned Driver", coerce=int, validators=[DataRequired()])
    vehicle_id = SelectField("Assigned Vehicle", coerce=int, validators=[DataRequired()])
    route_code = StringField("Route Code", validators=[DataRequired(), Length(max=50)])
    route_date = DateField("Delivery Date", validators=[DataRequired()])
    submit = SubmitField("Create Delivery Route")

class RouteStopForm(FlaskForm):
    shipment_id = SelectField("Shipment to Deliver", coerce=int, validators=[DataRequired()])
    stop_sequence = IntegerField("Stop Sequence Order", default=1, validators=[DataRequired(), NumberRange(min=1)])
    stop_type = SelectField("Stop Type", choices=[("DELIVERY", "Delivery Stop"), ("PICKUP", "Pickup Stop")])
    submit = SubmitField("Add Route Stop")

class VehicleForm(FlaskForm):
    branch_id = SelectField("Branch", coerce=int, validators=[DataRequired()])
    plate_number = StringField("Registration Plate Number", validators=[DataRequired(), Length(max=30)])
    vehicle_type = SelectField("Vehicle Type", choices=[("MOTORCYCLE", "Motorcycle / Bike"), ("VAN", "Delivery Van"), ("TRUCK", "Freight Truck")])
    capacity_grams = IntegerField("Load Capacity (Grams)", default=50000, validators=[DataRequired(), NumberRange(min=1000)])
    service_due_on = DateField("Next Service Due Date", validators=[Optional()])
    submit = SubmitField("Save Vehicle")

class DriverForm(FlaskForm):
    employee_id = SelectField("Select Employee", coerce=int, validators=[DataRequired()])
    license_number = StringField("Driving License Number", validators=[DataRequired(), Length(max=50)])
    license_expires_on = DateField("License Expiry Date", validators=[DataRequired()])
    submit = SubmitField("Save Driver Profile")

class HubScanForm(FlaskForm):
    shipment_id = SelectField("Select Parcel / Consignment", coerce=int, validators=[DataRequired()])
    hub_id = SelectField("Scanning Hub", coerce=int, validators=[DataRequired()])
    scan_code = SelectField("Scan Type", choices=[("INBOUND", "Inbound Receive"), ("OUTBOUND", "Outbound Dispatch"), ("SORT", "Sorting Inspection")])
    notes = StringField("Inspection Notes", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Record Hub Scan")

class HubTransferForm(FlaskForm):
    shipment_id = SelectField("Select Parcel", coerce=int, validators=[DataRequired()])
    from_hub_id = SelectField("Originating Hub", coerce=int, validators=[DataRequired()])
    to_hub_id = SelectField("Destination Hub", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Dispatch Transfer Manifest")

class DeliveryAttemptForm(FlaskForm):
    outcome = SelectField("Attempt Outcome", choices=[("SUCCESS", "Delivery Successful"), ("FAILED", "Delivery Failed"), ("RESCHEDULED", "Customer Rescheduled")])
    failure_reason = StringField("Reason if Failed", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Submit Attempt")

class DeliveryProofForm(FlaskForm):
    received_by_name = StringField("Receiver Full Name / CNIC", validators=[DataRequired(), Length(max=150)])
    signature_file = FileField("Proof Document / Signature")
    submit = SubmitField("Confirm Delivery Proof")
