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

    @app.cli.command("seed-showcase")
    @click.option("--confirm", is_flag=True, default=False, help="Confirm intentional showcase dataset seeding")
    @click.option("--dry-run", is_flag=True, default=False, help="Preview showcase dataset without committing changes")
    @click.option("--email", default="demo.merchant@smartcourier.pk", help="Dedicated demo merchant email")
    @with_appcontext
    def seed_showcase_command(confirm, dry_run, email):
        """Seed 5 illustrative academic showcase entries for viva demonstration (opt-in only)."""
        allow_env = os.environ.get("ALLOW_SHOWCASE_SEED", "").lower() in ("true", "1", "yes")
        if not (confirm or allow_env) and not dry_run:
            raise click.ClickException(
                "Showcase seeding requires explicit confirmation to prevent unintended data creation. "
                "Run with --confirm or set ALLOW_SHOWCASE_SEED=true (or use --dry-run to preview)."
            )

        from app.services.showcase_service import seed_showcase
        res, count = seed_showcase(dry_run=dry_run, demo_email=email)
        click.echo(f"[*] {res['message']}")
        click.echo("-" * 75)
        for e in res.get("entries", []):
            click.echo(f"[{e['ref']}] {e['tracking_number']} | {e['status']} | {e['item']} ({e['weight_grams']}g)")
            click.echo(f"       Route: {e.get('origin', '—')} -> {e.get('destination', '—')}")
        click.echo("-" * 75)

    @app.cli.command("show-demo-entries")
    @with_appcontext
    def show_demo_entries_command():
        """Display generated tracking numbers and testing details for showcase demo records."""
        from app.services.showcase_service import get_showcase_entries
        entries = get_showcase_entries()
        if not entries:
            click.echo("[i] No showcase demo entries are currently seeded in this database.")
            click.echo("    Run 'flask --app run.py seed-showcase --confirm' to generate them.")
            return

        click.echo("\n" + "=" * 78)
        click.echo("SMART COURIER — ACADEMIC SHOWCASE TEST ENTRIES")
        click.echo("=" * 78)
        for e in entries:
            click.echo(f"Reference:   {e['ref']}")
            click.echo(f"Tracking #:  {e['tracking_number']}")
            click.echo(f"Status:      {e['status']}")
            click.echo(f"Consignment: {e['item']} ({e['weight_grams']}g)")
            click.echo(f"Route:       {e['origin']} -> {e['destination']}")
            click.echo(f"Tracking URL: /tracking/{e['tracking_number']}")
            click.echo(f"Demonstrates: {e['note']}")
            click.echo("-" * 78)

    @app.cli.command("verify-schema")
    @with_appcontext
    def verify_schema_command():
        """Verify all 55 business tables and SQLite FK enforcement."""
        success = verify_schema(app, db)
        if not success:
            raise click.ClickException("Schema verification failed!")
        click.echo("[+] Schema verification passed!")
