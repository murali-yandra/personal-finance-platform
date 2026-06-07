from uuid import UUID

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from app.domains.users.models import User, UserSettings


def test_user_settings_defaults_and_uuid_primary_key() -> None:
    user = User(
        email="murali@example.com",
        password_hash="argon2-placeholder-hash",
        display_name="Murali Yandra",
    )
    settings = UserSettings(user_id=user.id)

    assert isinstance(settings.id, UUID)
    assert settings.user_id == user.id
    assert settings.notification_mode == "LOW_CONFIDENCE_ONLY"
    assert settings.ai_suggestions_enabled is False
    assert settings.historical_import_mode is None
    assert settings.preferred_language == "en"


def test_user_settings_table_has_required_columns() -> None:
    table = UserSettings.__table__

    assert table.name == "user_settings"
    assert table.c.id.primary_key is True
    assert table.c.id.nullable is False
    assert table.c.user_id.nullable is False
    assert table.c.notification_mode.nullable is False
    assert table.c.ai_suggestions_enabled.nullable is False
    assert table.c.historical_import_mode.nullable is True
    assert table.c.preferred_language.nullable is False
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False


def test_user_settings_table_has_user_foreign_key_and_unique_constraint() -> None:
    table = UserSettings.__table__
    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    unique_constraints = {
        constraint.name: constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert len(foreign_keys) == 1
    assert [column.name for column in foreign_keys[0].columns] == ["user_id"]
    assert [element.target_fullname for element in foreign_keys[0].elements] == [
        "users.id"
    ]
    assert [
        column.name for column in unique_constraints["uq_user_settings_user"].columns
    ] == ["user_id"]


def test_user_to_user_settings_relationship_is_one_to_one() -> None:
    user_relationship = User.__mapper__.relationships["settings"]
    settings_relationship = UserSettings.__mapper__.relationships["user"]

    assert user_relationship.uselist is False
    assert user_relationship.back_populates == "user"
    assert settings_relationship.uselist is False
    assert settings_relationship.back_populates == "settings"
