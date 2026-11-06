from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=180)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Confirm New Password", validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")])
    submit = SubmitField("Update Password")

class ProfileForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=150)])
    phone = StringField("Phone Number", validators=[Length(max=30)])
    submit = SubmitField("Save Profile")

class RegisterForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=150)])
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=180)])
    phone = StringField("Phone Number", validators=[DataRequired(), Length(min=7, max=30)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")])
    agree_terms = BooleanField("I agree to the Terms of Service & Privacy Policy", default=True)
    submit = SubmitField("Register as Customer")
