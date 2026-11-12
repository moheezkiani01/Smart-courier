import os
import click
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from app.extensions import db
from scripts.verify_schema import verify_schema
from app.services.init_service import init_production_catalog

def register_commands(app):
    @app.cli.command("init-prod")
    @click.option("--email", default=None, help="Optional superadmin email")
    @click.option("--password", default=None, help="Optional superadmin password")
    @click.option("--name", default=None, help="Superadmin full name")
    @with_appcontext
    def init_prod_command(email, password, name):
        """Secure, idempotent initialization guaranteeing all 9 roles, permissions, and catalog."""
        stats = init_production_catalog(admin_email=email, admin_password=password, admin_name=name)
        click.echo("[+] Production initialization complete:")
        click.echo(f"    - Roles created: {stats['roles_created']}")
        click.echo(f"    - Permissions created: {stats['permissions_created']}")
        click.echo(f"    - Branches created: {stats['branches_created']}")
        click.echo(f"    - Hubs created: {stats['hubs_created']}")
        click.echo(f"    - Service zones created: {stats['zones_created']}")
        click.echo(f"    - Service types created: {stats['services_created']}")
        click.echo(f"    - Packaging types created: {stats['packaging_created']}")
        click.echo(f"    - Rate cards created: {stats['rate_cards_created']}")
        click.echo(f"    - Rate rules created: {stats['rate_rules_created']}")
        if stats["admin_bootstrapped"]:
            click.echo("    - Superadmin account successfully bootstrapped.")

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
        # Ensure all roles and essential catalog exist first
        stats = init_production_catalog(admin_email=email, admin_password=password, admin_name=name)
        if stats["admin_bootstrapped"]:
            click.echo(f"[+] Superadmin account successfully bootstrapped via init_production_catalog!")
        else:
            click.echo("[i] Roles & essential catalog verified. Superadmin credentials not provided or already active.")

    @app.cli.command("verify-schema")
    @with_appcontext
    def verify_schema_command():
        """Verify all 55 business tables and SQLite FK enforcement."""
        success = verify_schema(app, db)
        if not success:
            raise click.ClickException("Schema verification failed!")
        click.echo("[+] Schema verification passed!")
