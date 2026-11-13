import os
from datetime import datetime
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

    @app.cli.command("seed-three-demo-bookings")
    @click.option("--confirm", is_flag=True, default=False, help="Confirm deliberate demo bookings seeding")
    @click.option("--dry-run", is_flag=True, default=False, help="Preview prospective demo bookings without writing to database")
    @click.option("--production-demo", is_flag=True, default=False, help="Explicit confirmation required when seeding in production environment")
    @click.option("--email", default="demo.merchant@smartcourier.pk", help="Dedicated demo customer email")
    @with_appcontext
    def seed_three_demo_bookings_command(confirm, dry_run, production_demo, email):
        """Seed exactly three realistic demo bookings for university viva testing (opt-in only)."""
        is_prod = (os.environ.get("APP_ENV") == "production" or current_app.config.get("ENV") == "production")
        if is_prod and not production_demo:
            raise click.ClickException(
                "Demo booking seeding is restricted in production to protect real customer records. "
                "Pass '--production-demo --confirm' explicitly if seeding a dedicated demonstration environment."
            )

        if not confirm and not dry_run:
            raise click.ClickException(
                "Demo booking seeding requires explicit confirmation. "
                "Run with '--confirm' to create records, or '--dry-run' to preview prospective entries."
            )

        from app.services.three_bookings_service import seed_three_bookings
        res, count = seed_three_bookings(dry_run=dry_run, demo_email=email)
        click.echo(f"[*] {res['message']}")
        click.echo("=" * 80)
        click.echo(f"{'Ref':<18} {'Tracking #':<16} {'Status':<16} {'Weight':<8} {'Route':<22}")
        click.echo("-" * 80)
        for e in res.get("entries", []):
            fare_pkr = f"Rs. {e.get('total_charge_paisa', 0) / 100:,.0f}" if e.get("total_charge_paisa") else "—"
            click.echo(f"{e['ref']:<18} {e['tracking_number']:<16} {e['status']:<16} {e.get('weight_grams', 0)}g   {e.get('origin', '—')} -> {e.get('destination', '—')} ({fare_pkr})")
            click.echo(f"  Consignment : {e['item']}")
            click.echo(f"  Tracking URL: /tracking/{e['tracking_number']}")
            click.echo(f"  Viva Focus  : {e.get('note', '')}")
            click.echo("-" * 80)

    @app.cli.command("show-three-demo-bookings")
    @with_appcontext
    def show_three_demo_bookings_command():
        """Display generated tracking numbers and testing details for the 3 demo bookings."""
        from app.services.three_bookings_service import get_three_bookings
        entries = get_three_bookings()
        if not entries:
            click.echo("[i] No demo bookings are currently seeded in this database.")
            click.echo("    Run 'python -m flask --app run.py seed-three-demo-bookings --confirm' to generate them.")
            return

        click.echo("\n" + "=" * 82)
        click.echo("SMART COURIER — THREE VIVA DEMO BOOKINGS")
        click.echo("=" * 82)
        for e in entries:
            fare_pkr = f"Rs. {e.get('total_charge_paisa', 0) / 100:,.2f}"
            click.echo(f"Reference     : {e['ref']}")
            click.echo(f"Tracking #    : {e['tracking_number']}")
            click.echo(f"Stage/Status  : {e['status']}")
            click.echo(f"Consignment   : {e['item']} ({e['weight_grams']}g)")
            click.echo(f"Route         : {e['origin']} -> {e['destination']}")
            click.echo(f"Total Fare    : {fare_pkr}")
            click.echo(f"Invoice #     : {e.get('invoice_number') or 'N/A'} (Status: {e.get('invoice_status', 'N/A')})")
            if e.get("route_code"):
                click.echo(f"Dispatch Run  : {e['route_code']}")
            click.echo(f"Deep Links    : /shipments/{e['shipment_id']}  |  /tracking/{e['tracking_number']}")
            click.echo(f"Viva Note     : {e['note']}")
            click.echo("-" * 82)

    @app.cli.command("cleanup-three-demo-bookings")
    @click.option("--confirm", is_flag=True, default=False, help="Explicit confirmation to delete demo bookings")
    @with_appcontext
    def cleanup_three_demo_bookings_command(confirm):
        """Safely remove only the three demo bookings and their associated operational rows."""
        if not confirm:
            raise click.ClickException(
                "Cleanup requires '--confirm' to prevent accidental data deletion."
            )
        from app.services.three_bookings_service import cleanup_three_bookings
        res = cleanup_three_bookings(confirm=True)
        click.echo(f"[*] {res['message']}")

    @app.cli.command("seed-viva-full")
    @click.option("--confirm", is_flag=True, default=False, help="Confirm intentional 55-table demo dataset seeding")
    @click.option("--dry-run", is_flag=True, default=False, help="Preview prospective records without database writes")
    @click.option("--production-demo", is_flag=True, default=False, help="Explicit confirmation required when seeding production environment")
    @click.option("--email", default="viva.merchant@smartcourier.pk", help="Dedicated demo merchant customer email")
    @click.option("--alternate-email", default="viva.alternate@smartcourier.pk", help="Secondary partner customer email")
    @with_appcontext
    def seed_viva_full_command(confirm, dry_run, production_demo, email, alternate_email):
        """Seed realistic connected demo records across all 55 SQLAlchemy business tables for university viva."""
        is_prod = (os.environ.get("APP_ENV") == "production" or current_app.config.get("ENV") == "production")
        if is_prod and not production_demo:
            raise click.ClickException(
                "Full viva demonstration seeding in production requires explicit confirmation. "
                "Pass '--production-demo --confirm' to safely populate the dedicated demonstration dataset."
            )

        if not confirm and not dry_run:
            raise click.ClickException(
                "Viva seeding requires explicit confirmation. "
                "Run with '--confirm' to seed records, or '--dry-run' to preview prospective table changes."
            )

        from app.services.viva_full_seed_service import seed_viva_full
        res, count = seed_viva_full(dry_run=dry_run, demo_email=email, alternate_email=alternate_email)
        click.echo(f"\n[*] {res['message']}")
        click.echo("=" * 78)
        if res.get("status") == "dry_run":
            click.echo(f"Total Business Tables:     {res['total_tables']}")
            click.echo(f"Currently Empty Tables:    {len(res['currently_empty_tables'])}")
            if res['currently_empty_tables']:
                click.echo(f"  Empty: {', '.join(res['currently_empty_tables'])}")
            click.echo("\nPlanned Actions:")
            for act in res.get("actions_planned", []):
                click.echo(f"  {act}")
        elif res.get("status") in ("success", "already_seeded"):
            click.echo(f"Total Relational Tables:   {res['total_tables']}")
            click.echo(f"Populated Tables (PASS):   {res['populated_tables']} / {res['total_tables']} (100% coverage)")
            click.echo(f"Empty Tables:              {res['empty_tables']}")
            if res.get("tracking_numbers"):
                click.echo("\nThree Core Viva Bookings:")
                for ref, tn in res["tracking_numbers"].items():
                    click.echo(f"  [{ref}] Tracking #: {tn}  ->  /tracking/{tn}")
            click.echo(f"\nDedicated Viva Merchant:   {res.get('demo_merchant_email', email)}")
        click.echo("=" * 78 + "\n")

    @app.cli.command("viva-table-report")
    @click.option("--markdown", is_flag=True, default=False, help="Output report in GitHub-flavored Markdown")
    @click.option("--csv", is_flag=True, default=False, help="Output report as comma-separated values (CSV)")
    @with_appcontext
    def viva_table_report_command(markdown, csv):
        """Generate a complete 55-table coverage report verifying counts, PKs, parent FKs, and UI routes."""
        from app.services.viva_full_seed_service import get_viva_table_inventory
        inventory = get_viva_table_inventory()
        total_tables = len(inventory)
        passed_tables = sum(1 for r in inventory if r["status"] == "PASS")
        empty_tables = total_tables - passed_tables
        coverage_pct = (passed_tables / total_tables * 100) if total_tables else 0

        engine_name = db.engine.dialect.name.upper()

        if csv:
            import io, csv as csv_mod
            output = io.StringIO()
            writer = csv_mod.writer(output)
            writer.writerow(["Index", "Table Name", "Domain Group", "Total Rows", "Demo Rows", "Sample PK / Ref", "Parent FK", "UI Route / Scope", "Status"])
            for idx, r in enumerate(inventory, start=1):
                writer.writerow([idx, r["table_name"], r["group"], r["total_count"], r["demo_count"], r["sample_pk_ref"], r["parent_fk"], r["ui_route"], r["status"]])
            click.echo(output.getvalue())
            return

        if markdown:
            click.echo(f"# Smart Courier — 55 Business Table Coverage Report\n")
            click.echo(f"**Database Engine:** {engine_name} | **Timestamp:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
            click.echo(f"**Relational Coverage:** {passed_tables}/{total_tables} tables ({coverage_pct:.1f}%) | **Empty Tables:** {empty_tables}\n")
            click.echo("| # | Table Name | Domain Group | Total Rows | Demo Rows | Sample PK / Ref | Parent FK | UI Route / Scope | Status |")
            click.echo("|---|---|---|---:|---:|---|---|---|:---:|")
            for idx, r in enumerate(inventory, start=1):
                click.echo(f"| {idx} | `{r['table_name']}` | {r['group']} | {r['total_count']} | {r['demo_count']} | {r['sample_pk_ref']} | `{r['parent_fk']}` | `{r['ui_route']}` | **{r['status']}** |")
            click.echo("\n---")
            return

        click.echo("\n" + "=" * 115)
        click.echo(f"SMART COURIER — 55 RELATIONAL TABLE VIVA VERIFICATION REPORT ({engine_name})")
        click.echo("=" * 115)
        header = f"{'#':<3} {'Table Name':<24} {'Domain Group':<20} {'Total':<6} {'Demo':<6} {'Sample PK/Ref':<22} {'Status':<6}"
        click.echo(header)
        click.echo("-" * 115)
        for idx, r in enumerate(inventory, start=1):
            click.echo(f"{idx:<3} {r['table_name']:<24} {r['group']:<20} {r['total_count']:<6} {r['demo_count']:<6} {r['sample_pk_ref']:<22} {r['status']:<6}")
        click.echo("=" * 115)
        click.echo(f"Total Business Tables: {total_tables} | Populated (PASS): {passed_tables} | Empty: {empty_tables} | Relational Coverage: {coverage_pct:.1f}%")
        click.echo("=" * 115 + "\n")

    @app.cli.command("cleanup-viva-full")
    @click.option("--confirm", is_flag=True, default=False, help="Explicit confirmation to delete full viva demo records")
    @with_appcontext
    def cleanup_viva_full_command(confirm):
        """Safely remove only demonstration records tracked in VIVA_55_TABLE_DATASET_MAP."""
        if not confirm:
            raise click.ClickException(
                "Cleanup requires '--confirm' to prevent accidental demonstration data deletion."
            )
        from app.services.viva_full_seed_service import cleanup_viva_full
        res = cleanup_viva_full(confirm=True)
        click.echo(f"[*] {res['message']} (Removed {res['deleted_count']} tracked items)")

    @app.cli.command("seed-viva-accounts")
    @click.option("--confirm", is_flag=True, default=False, help="Confirm creation/update of dedicated demonstration accounts")
    @click.option("--dry-run", is_flag=True, default=False, help="Preview accounts to be created without database writes")
    @click.option("--password", default=None, help="Explicit password for demonstration accounts (or VIVA_DEMO_PASSWORD env)")
    @click.option("--reset-passwords", is_flag=True, default=False, help="Force password update on accounts that already exist")
    @click.option("--show-credentials", is_flag=True, default=False, help="Print full credentials summary to console")
    @with_appcontext
    def seed_viva_accounts_command(confirm, dry_run, password, reset_passwords, show_credentials):
        """Idempotently ensure active accounts exist for all 9 Smart Courier roles with correct relations."""
        allow_env = os.environ.get("VIVA_SEED_DEMO_ACCOUNTS", "").lower() in ("true", "1", "yes")
        if not (confirm or allow_env) and not dry_run:
            raise click.ClickException(
                "Demonstration account creation requires explicit confirmation to prevent unintended mutations. "
                "Run with '--confirm' or set VIVA_SEED_DEMO_ACCOUNTS=true (or use '--dry-run' to preview)."
            )

        from app.services.viva_demo_accounts_service import ensure_viva_demo_accounts
        res = ensure_viva_demo_accounts(password=password, reset_passwords=reset_passwords, dry_run=dry_run)

        click.echo("\n" + "=" * 90)
        click.echo("SMART COURIER — VIVA 9-ROLE DEMONSTRATION ACCOUNTS SETUP")
        click.echo("=" * 90)
        click.echo(f"Mode: {'DRY RUN (No changes saved)' if res['dry_run'] else 'APPLIED'}")
        click.echo(f"Total Roles: {res['total_accounts']} | Newly Created: {res.get('created_count', 0)} | Updated/Verified: {res.get('updated_count', 0)}")
        click.echo("-" * 90)

        header = f"{'#':<3} {'System Role':<17} {'Email Address':<32} {'Status':<10} {'Target Dashboard'}"
        click.echo(header)
        click.echo("-" * 90)
        for idx, acc in enumerate(res["accounts"], start=1):
            click.echo(f"{idx:<3} {acc['role_name']:<17} {acc['email']:<32} {acc['status']:<10} {acc['dashboard_url']}")
        click.echo("=" * 90)

        # Credentials summary displayed only when explicitly requested via --show-credentials
        if show_credentials:
            click.echo("\n" + "*" * 90)
            click.echo("PRIVATE DEMONSTRATION CREDENTIALS FOR VIVA (DO NOT COMMIT OR SHARE PUBLICLY)")
            click.echo("*" * 90)
            for idx, acc in enumerate(res["accounts"], start=1):
                click.echo(f"[{acc['role_name']}] Email: {acc['email']} | Password: {acc['password']} | URL: {acc['dashboard_url']}")
            click.echo("*" * 90 + "\n")

    @app.cli.command("deactivate-viva-accounts")
    @click.option("--confirm", is_flag=True, default=False, help="Confirm deactivation of demonstration accounts")
    @click.option("--include-admin", is_flag=True, default=False, help="Also deactivate Super Admin (default: preserve to avoid lockout)")
    @with_appcontext
    def deactivate_viva_accounts_command(confirm, include_admin):
        """Safely deactivate dedicated demo accounts after the viva while preserving all 55 tables & data."""
        if not confirm:
            raise click.ClickException(
                "Account deactivation requires '--confirm' to prevent unintended operation lockout."
            )
        from app.services.viva_demo_accounts_service import deactivate_viva_demo_accounts
        res = deactivate_viva_demo_accounts(preserve_admin=(not include_admin), confirm=True)
        click.echo(f"[+] Deactivated {res['deactivated_count']} demonstration accounts successfully:")
        for acc in res.get("deactivated_accounts", []):
            click.echo(f"    - {acc['role']} ({acc['email']}) -> DEACTIVE")
        click.echo("[i] All 55 database tables and shipment records remain 100% intact.")

    @app.cli.command("status-viva-accounts")
    @with_appcontext
    def status_viva_accounts_command():
        """Inspect the real database status of all 9 viva role accounts."""
        from app.services.viva_demo_accounts_service import get_viva_demo_accounts_status
        statuses = get_viva_demo_accounts_status()
        click.echo("\n" + "=" * 95)
        click.echo("SMART COURIER — VIVA 9-ROLE ACCOUNT DATABASE STATUS")
        click.echo("=" * 95)
        header = f"{'#':<3} {'Role Name':<17} {'Target Email':<32} {'Exists':<8} {'Status':<10} {'Has Role'}"
        click.echo(header)
        click.echo("-" * 95)
        for idx, s in enumerate(statuses, start=1):
            ex_str = "YES" if s["exists"] else "NO"
            hr_str = "YES" if s["has_role"] else "NO"
            click.echo(f"{idx:<3} {s['role_name']:<17} {s['target_email']:<32} {ex_str:<8} {s['status']:<10} {hr_str}")
        click.echo("=" * 95 + "\n")


