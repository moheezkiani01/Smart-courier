import os
from flask import Flask, render_template
from app.config import config_by_name, normalize_database_url
from app.extensions import db, migrate, login_manager, csrf
from app.utils.helpers import paisa_to_pkr, format_datetime

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "development"))

    app = Flask(__name__, instance_relative_config=True)
    target_config = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(target_config)

    # Validate production prerequisites
    if config_name == "production":
        # Dynamically bind runtime environment variables
        if "DATABASE_URL" in os.environ:
            app.config["SQLALCHEMY_DATABASE_URI"] = normalize_database_url(os.environ["DATABASE_URL"])
        if "SECRET_KEY" in os.environ:
            app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if not db_uri or db_uri.startswith("sqlite"):
            raise RuntimeError(
                "DATABASE_URL environment variable pointing to persistent PostgreSQL is required in production. "
                "Render Free web services have ephemeral storage; SQLite does not persist across restarts or redeploys."
            )
        secret = app.config.get("SECRET_KEY", "")
        if not secret or secret == "smart-courier-dev-secret-key-3.10":
            raise RuntimeError(
                "A dedicated, strong SECRET_KEY environment variable is required in production and must not use the default development key."
            )
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Ensure instance & upload folders exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login_manager.init_app(app)
    csrf.init_app(app)

    # User loader for Flask-Login
    from app.models.auth import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.filter_by(id=int(user_id), is_deleted=False).first()

    # Template Context Processors
    @app.context_processor
    def utility_processor():
        return {
            "paisa_to_pkr": paisa_to_pkr,
            "format_datetime": format_datetime,
            "app_title": "Smart Courier Management",
        }

    # Health check endpoint for Render and operational monitoring
    @app.route("/healthz", methods=["GET"])
    def health_check():
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "healthy", "service": "smart-courier"}, 200
        except Exception:
            return {"status": "unhealthy", "error": "Database unavailable"}, 503

    # Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html", error=e), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html", error=e), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html", error=e), 404

    @app.errorhandler(409)
    def conflict(e):
        return render_template("errors/409.html", error=e), 409

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html", error=e), 500

    # Register Blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.customers import customers_bp
    from app.blueprints.catalog import catalog_bp
    from app.blueprints.shipments import shipments_bp
    from app.blueprints.hubs import hubs_bp
    from app.blueprints.dispatch import dispatch_bp
    from app.blueprints.drivers import drivers_bp
    from app.blueprints.finance import finance_bp
    from app.blueprints.support import support_bp
    from app.blueprints.tracking import tracking_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(catalog_bp, url_prefix="/catalog")
    app.register_blueprint(shipments_bp, url_prefix="/shipments")
    app.register_blueprint(hubs_bp, url_prefix="/hubs")
    app.register_blueprint(dispatch_bp, url_prefix="/dispatch")
    app.register_blueprint(drivers_bp, url_prefix="/driver")
    app.register_blueprint(finance_bp, url_prefix="/finance")
    app.register_blueprint(support_bp, url_prefix="/support")
    app.register_blueprint(tracking_bp, url_prefix="/tracking")

    # Register CLI Commands
    from app.cli import register_commands
    register_commands(app)

    @app.context_processor
    def inject_permissions():
        from flask_login import current_user
        from app.security.rbac import get_user_capabilities
        return dict(caps=get_user_capabilities(current_user) if current_user.is_authenticated else {})

    return app
