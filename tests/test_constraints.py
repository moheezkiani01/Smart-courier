import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.auth import User, Role, UserRole

def test_sqlite_foreign_keys_pragma_enabled(app):
    """Verify SQLite foreign key enforcement is strictly active."""
    with app.app_context():
        conn = db.engine.connect()
        fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert fk == 1, "PRAGMA foreign_keys is NOT enabled!"

def test_sqlite_foreign_key_check_zero_violations(app):
    """Verify database has zero relational integrity violations across all 55 tables."""
    with app.app_context():
        conn = db.engine.connect()
        violations = conn.execute(text("PRAGMA foreign_key_check")).fetchall()
        assert len(violations) == 0, f"Found foreign key violations: {violations}"

def test_duplicate_user_email_fails_unique_constraint(app):
    """Verify email uniqueness constraint is enforced."""
    with app.app_context():
        dup_user = User(
            full_name="Duplicate User",
            email="admin@smartcourier.pk",  # Already exists from seed
        )
        dup_user.set_password("Password123!")
        db.session.add(dup_user)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

def test_foreign_key_to_nonexistent_entity_fails(app):
    """Verify foreign key constraint fails when referencing non-existent parent."""
    with app.app_context():
        invalid_mapping = UserRole(
            user_id=999999,  # Nonexistent user
            role_id=1
        )
        db.session.add(invalid_mapping)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
