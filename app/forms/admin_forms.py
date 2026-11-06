from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, DateField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

class BranchForm(FlaskForm):
    code = StringField("Branch Code", validators=[DataRequired(), Length(max=20)])
    name = StringField("Branch Name", validators=[DataRequired(), Length(max=150)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    city = StringField("City", validators=[DataRequired(), Length(max=100)])
    address_line = StringField("Address Line", validators=[DataRequired(), Length(max=255)])
    submit = SubmitField("Save Branch")

class HubForm(FlaskForm):
    branch_id = SelectField("Parent Branch", coerce=int, validators=[DataRequired()])
    code = StringField("Hub Code", validators=[DataRequired(), Length(max=20)])
    name = StringField("Hub Name", validators=[DataRequired(), Length(max=150)])
    location_note = TextAreaField("Location Note", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Save Hub")

class EmployeeForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=150)])
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=180)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    password = PasswordField("Initial Password", validators=[DataRequired(), Length(min=8)])
    role_code = SelectField("Role Assignment", validators=[DataRequired()])
    primary_branch_id = SelectField("Primary Branch", coerce=int, validators=[DataRequired()])
    employee_no = StringField("Employee Number", validators=[DataRequired(), Length(max=50)])
    job_title = StringField("Job Title", validators=[DataRequired(), Length(max=100)])
    hired_on = DateField("Hired On Date", validators=[Optional()])
    submit = SubmitField("Save Staff Member")

class ServiceZoneForm(FlaskForm):
    code = StringField("Zone Code", validators=[DataRequired(), Length(max=30)])
    name = StringField("Zone Name", validators=[DataRequired(), Length(max=100)])
    city = StringField("City", validators=[DataRequired(), Length(max=100)])
    region = StringField("Region/Province", validators=[DataRequired(), Length(max=100)])
    postal_prefix = StringField("Postal Prefix", validators=[Optional(), Length(max=10)])
    submit = SubmitField("Save Service Zone")
