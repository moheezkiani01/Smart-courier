from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class TicketForm(FlaskForm):
    customer_id = SelectField("Customer Account", coerce=int, validators=[Optional()])
    subject = StringField("Issue Subject", validators=[DataRequired(), Length(max=150)])
    shipment_id = SelectField("Related Shipment (Optional)", coerce=int, validators=[Optional()])
    priority = SelectField("Priority", choices=[("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High"), ("URGENT", "Urgent")])
    body = TextAreaField("Describe your issue or query", validators=[DataRequired(), Length(min=10, max=2000)])
    submit = SubmitField("Submit Ticket")

class TicketReplyForm(FlaskForm):
    body = TextAreaField("Reply Message", validators=[DataRequired(), Length(min=2, max=2000)])
    is_internal = BooleanField("Staff Internal Note (Hidden from Customer)")
    submit = SubmitField("Post Reply")

class TrackingSearchForm(FlaskForm):
    tracking_number = StringField("Tracking Code", validators=[DataRequired(), Length(max=50)])
    submit = SubmitField("Track")
