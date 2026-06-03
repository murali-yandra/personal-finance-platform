from uuid import UUID

from app.domains.users.models import User


def test_user_entity_defaults_and_uuid_primary_key() -> None:
    user = User(
        email="murali@example.com",
        password_hash="argon2-placeholder-hash",
        display_name="Murali Yandra",
    )

    assert isinstance(user.id, UUID)
    assert user.email == "murali@example.com"
    assert user.password_hash == "argon2-placeholder-hash"
    assert user.display_name == "Murali Yandra"
    assert user.timezone == "Asia/Kolkata"
    assert user.default_currency == "INR"
    assert user.is_active is True
    assert user.deleted_at is None


def test_users_table_has_required_columns() -> None:
    table = User.__table__

    assert table.name == "users"
    assert table.c.id.primary_key is True
    assert table.c.id.nullable is False
    assert table.c.email.nullable is False
    assert table.c.password_hash.nullable is False
    assert table.c.display_name.nullable is False
    assert table.c.telegram_chat_id.nullable is True
    assert table.c.timezone.nullable is False
    assert table.c.default_currency.nullable is False
    assert table.c.is_active.nullable is False
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False
    assert table.c.deleted_at.nullable is True


def test_users_table_defines_required_indexes() -> None:
    indexes = {index.name: index for index in User.__table__.indexes}

    assert indexes["idx_users_email"].unique is True
    assert [column.name for column in indexes["idx_users_email"].columns] == ["email"]
    assert indexes["idx_users_telegram_chat_id"].unique is False
    assert [
        column.name for column in indexes["idx_users_telegram_chat_id"].columns
    ] == ["telegram_chat_id"]
