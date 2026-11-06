from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

class PaymentForm(FlaskForm):
    amount_paisa = IntegerField("Payment Amount (in Paisa)", validators=[DataRequired(), NumberRange(min=1)])
    method = SelectField("Payment Method", choices=[("CASH", "Cash"), ("BANK_TRANSFER", "Bank Transfer"), ("SIMULATED_ONLINE", "Simulated Card / Online")])
    reference_code = StringField("Payment Reference / Slip No", validators=[Optional(), Length(max=80)])
    submit = SubmitField("Record Payment")

class CodRemittanceForm(FlaskForm):
    amount_paisa = IntegerField("Remittance Amount (in Paisa)", validators=[DataRequired(), NumberRange(min=1)])
    reference_code = StringField("Settlement Ref / Bank Receipt", validators=[Optional(), Length(max=80)])
    submit = SubmitField("Remit to Merchant")

class RefundForm(FlaskForm):
    amount_paisa = IntegerField("Refund Amount (in Paisa)", validators=[DataRequired(), NumberRange(min=1)])
    reason = StringField("Reason for Refund", validators=[DataRequired(), Length(max=255)])
    submit = SubmitField("Authorize Refund")
