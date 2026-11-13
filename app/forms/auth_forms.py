from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=180)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")

    def validate_password(self, field):
        import os
        from flask import current_app
        pwd = field.data or ""
        email = (self.email.data or "").strip().lower()

        # Check if viva testing is enabled
        viva_enabled = False
        try:
            viva_enabled = (
                current_app.config.get("VIVA_TESTING_ENABLED", False)
                or current_app.config.get("VIVA_LOGIN_PICKER_ENABLED", False)
                or os.environ.get("VIVA_TESTING_ENABLED", "").lower() in ("true", "1", "yes")
                or os.environ.get("VIVA_LOGIN_PICKER_ENABLED", "").lower() in ("true", "1", "yes")
            )
        except Exception:
            pass

        from app.services.viva_demo_accounts_service import is_viva_demo_email
        if viva_enabled and is_viva_demo_email(email):
            if len(pwd) < 3:
                raise ValidationError("Password must be at least 3 characters long.")
        else:
            if len(pwd) < 6:
                raise ValidationError("Field must be at least 6 characters long.")

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
