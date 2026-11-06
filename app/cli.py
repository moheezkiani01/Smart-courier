import os
import click
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from app.extensions import db
from scripts.verify_schema import verify_schema

def register_commands(app):
    @app.cli.command("seed-demo")
    @click.option("--force", is_flag=True, default=False, help="Force seeding even if in production mode")
    @with_appcontext
    def seed_demo_command(force):
        """Seed fictional demonstrative data for testing and evaluation."""
        if (os.environ.get("APP_ENV") == "production" or current_app.config.get("ENV") == "production") and not force:
            raise click.ClickException(
                "Demo seeding is disabled in production to protect data integrity. "
                "Use --force only if this is an intentional demo environment."
            )
        from app.services.seed_service import seed_all
        seed_all()
        click.echo("[+] Demo database seeded successfully!")

    @app.cli.command("bootstrap-admin")
    @click.option("--email", default=None, help="Superadmin email (or set ADMIN_BOOTSTRAP_EMAIL env)")
    @click.option("--password", default=None, help="Superadmin password (or set ADMIN_BOOTSTRAP_PASSWORD env)")
    @click.option("--name", default="System Administrator", help="Superadmin full name")
    @with_appcontext
    def bootstrap_admin_command(email, password, name):
        """Secure, idempotent bootstrap command to initialize initial admin in production."""
        from app.models.auth import User, Role, UserRole

        email = email or os.environ.get("ADMIN_BOOTSTRAP_EMAIL")
        password = password or os.environ.get("ADMIN_BOOTSTRAP_PASSWORD")
        name = name or os.environ.get("ADMIN_BOOTSTRAP_NAME", "System Administrator")

        if not email or not password:
            click.echo("[i] No ADMIN_BOOTSTRAP_EMAIL / ADMIN_BOOTSTRAP_PASSWORD provided. Skipping admin bootstrap.")
            return

        # Ensure base roles exist
        admin_role = Role.query.filter_by(code="SUPER_ADMIN").first()
        if not admin_role:
            admin_role = Role(code="SUPER_ADMIN", name="Super Administrator", description="Full enterprise authority")
            db.session.add(admin_role)
            db.session.flush()

        # Check if an active superadmin already exists
        existing_admin = (
            db.session.query(User)
            .join(UserRole, User.id == UserRole.user_id)
            .filter(UserRole.role_id == admin_role.id, User.is_deleted == False)
            .first()
        )
        if existing_admin:
            click.echo(f"[i] Superadmin already exists ({existing_admin.email}). Admin bootstrap skipped.")
            return

        # Check if user with this email already exists
        user = User.query.filter_by(email=email.strip().lower(), is_deleted=False).first()
        if not user:
            user = User(
                full_name=name.strip(),
                email=email.strip().lower(),
                phone="+923000000000",
                password_hash=generate_password_hash(password),
                is_email_verified=True,
                status="ACTIVE",
            )
            db.session.add(user)
            db.session.flush()
        else:
            user.password_hash = generate_password_hash(password)
            user.status = "ACTIVE"

        # Assign SUPER_ADMIN role
        has_role = UserRole.query.filter_by(user_id=user.id, role_id=admin_role.id).first()
        if not has_role:
            user_role = UserRole(user_id=user.id, role_id=admin_role.id)
            db.session.add(user_role)

        db.session.commit()
        click.echo(f"[+] Superadmin ({user.email}) successfully bootstrapped!")

    @app.cli.command("verify-schema")
    @with_appcontext
    def verify_schema_command():
        """Verify all 55 business tables and SQLite FK enforcement."""
        success = verify_schema(app, db)
        if not success:
            raise click.ClickException("Schema verification failed!")
        click.echo("[+] Schema verification passed!")
