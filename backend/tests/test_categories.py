"""Category management (Sprint 7)."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.domains.categories.constants import DEFAULT_SYSTEM_CATEGORIES
from app.domains.categories.exceptions import (
    CategoryAlreadyExistsError,
    CategoryNotFoundError,
    CategoryValidationError,
    SystemCategoryProtectedError,
)
from app.domains.categories.models import Category
from app.domains.categories.repository import CategoryRepository
from app.domains.categories.service import CategoryService
from app.domains.users.models import User, UserSettings
from tests.conftest import authorization_header, register_user

CATEGORIES_URL = "/api/v1/categories"


@pytest.fixture
def user(db_session: Session) -> User:
    created = User(
        email="owner@example.com",
        password_hash="hash",
        display_name="Owner",
    )
    db_session.add(created)
    db_session.add(UserSettings(user_id=created.id))
    db_session.commit()
    return created


@pytest.fixture
def other_user(db_session: Session) -> User:
    created = User(
        email="intruder@example.com",
        password_hash="hash",
        display_name="Intruder",
    )
    db_session.add(created)
    db_session.add(UserSettings(user_id=created.id))
    db_session.commit()
    return created


@pytest.fixture
def system_categories(db_session: Session) -> list[Category]:
    """Seed the system categories the migration creates in a real database."""
    seeded = [
        Category(user_id=None, name=name, is_system=True)
        for name in DEFAULT_SYSTEM_CATEGORIES
    ]
    for category in seeded:
        db_session.add(category)
    db_session.commit()
    return seeded


@pytest.fixture
def service(db_session: Session) -> CategoryService:
    return CategoryService(repository=CategoryRepository(db_session))


def test_seed_list_matches_the_approved_schema() -> None:
    """04-database_schema.md section 6 lists exactly these 14 categories."""
    assert len(DEFAULT_SYSTEM_CATEGORIES) == 14
    assert "Food" in DEFAULT_SYSTEM_CATEGORIES
    assert "Miscellaneous" in DEFAULT_SYSTEM_CATEGORIES


def test_system_categories_are_visible_to_every_user(
    service: CategoryService,
    user: User,
    other_user: User,
    system_categories: list[Category],
) -> None:
    for account_holder in (user, other_user):
        names = {c.name for c in service.list_categories(account_holder.id)}
        assert set(DEFAULT_SYSTEM_CATEGORIES) <= names


def test_create_category_is_owned_by_the_user(
    service: CategoryService,
    user: User,
) -> None:
    category = service.create_category(user_id=user.id, name="Pets")

    assert category.user_id == user.id
    assert category.is_system is False


def test_user_categories_are_private(
    service: CategoryService,
    user: User,
    other_user: User,
) -> None:
    service.create_category(user_id=user.id, name="Pets")

    names = {c.name for c in service.list_categories(other_user.id)}
    assert "Pets" not in names


def test_duplicate_user_category_name_is_rejected(
    service: CategoryService,
    user: User,
) -> None:
    service.create_category(user_id=user.id, name="Pets")

    with pytest.raises(CategoryAlreadyExistsError):
        service.create_category(user_id=user.id, name="pets")


def test_two_users_may_use_the_same_category_name(
    service: CategoryService,
    user: User,
    other_user: User,
) -> None:
    first = service.create_category(user_id=user.id, name="Pets")
    second = service.create_category(user_id=other_user.id, name="Pets")

    assert first.id != second.id


def test_a_user_may_reuse_a_system_category_name(
    service: CategoryService,
    user: User,
    system_categories: list[Category],
) -> None:
    """The two live in separate uniqueness scopes."""
    category = service.create_category(user_id=user.id, name="Food")

    assert category.user_id == user.id


def test_empty_category_name_is_rejected(
    service: CategoryService,
    user: User,
) -> None:
    with pytest.raises(CategoryValidationError):
        service.create_category(user_id=user.id, name="   ")


def test_system_category_cannot_be_modified(
    service: CategoryService,
    user: User,
    system_categories: list[Category],
) -> None:
    food = next(c for c in system_categories if c.name == "Food")

    with pytest.raises(SystemCategoryProtectedError):
        service.update_category(
            user_id=user.id,
            category_id=food.id,
            name="Groceries",
        )


def test_user_category_can_be_renamed(
    service: CategoryService,
    user: User,
) -> None:
    category = service.create_category(user_id=user.id, name="Pets")

    updated = service.update_category(
        user_id=user.id,
        category_id=category.id,
        name="Pet Care",
    )

    assert updated.name == "Pet Care"


def test_another_users_category_is_not_found(
    service: CategoryService,
    user: User,
    other_user: User,
) -> None:
    category = service.create_category(user_id=user.id, name="Pets")

    with pytest.raises(CategoryNotFoundError):
        service.update_category(
            user_id=other_user.id,
            category_id=category.id,
            name="Stolen",
        )


def test_a_category_cannot_be_its_own_parent(
    service: CategoryService,
    user: User,
) -> None:
    category = service.create_category(user_id=user.id, name="Pets")

    with pytest.raises(CategoryValidationError):
        service.update_category(
            user_id=user.id,
            category_id=category.id,
            parent_category_id=category.id,
        )


def test_parent_must_be_visible(
    service: CategoryService,
    user: User,
) -> None:
    with pytest.raises(CategoryValidationError):
        service.create_category(
            user_id=user.id,
            name="Pets",
            parent_category_id=uuid4(),
        )


def test_a_system_category_may_be_a_parent(
    service: CategoryService,
    user: User,
    system_categories: list[Category],
) -> None:
    food = next(c for c in system_categories if c.name == "Food")

    category = service.create_category(
        user_id=user.id,
        name="Groceries",
        parent_category_id=food.id,
    )

    assert category.parent_category_id == food.id


def test_resolve_by_name_prefers_the_users_own_category(
    service: CategoryService,
    user: User,
    system_categories: list[Category],
) -> None:
    own = service.create_category(user_id=user.id, name="Food")

    resolved = service.resolve_by_name(user.id, "Food")

    assert resolved.id == own.id


def test_resolve_by_name_falls_back_to_a_system_category(
    service: CategoryService,
    user: User,
    system_categories: list[Category],
) -> None:
    resolved = service.resolve_by_name(user.id, "Transport")

    assert resolved is not None
    assert resolved.is_system is True


# -------------------------------------------------------------------- endpoints


@pytest.mark.asyncio
async def test_categories_require_authentication(auth_client: AsyncClient) -> None:
    assert (await auth_client.get(CATEGORIES_URL)).status_code == 401


@pytest.mark.asyncio
async def test_create_and_list_categories(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    created = await auth_client.post(
        CATEGORIES_URL,
        json={"name": "Pets"},
        headers=headers,
    )
    assert created.status_code == 201

    listed = await auth_client.get(CATEGORIES_URL, headers=headers)
    names = [item["name"] for item in listed.json()["data"]]
    assert "Pets" in names


@pytest.mark.asyncio
async def test_duplicate_category_returns_conflict(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    await auth_client.post(CATEGORIES_URL, json={"name": "Pets"}, headers=headers)

    response = await auth_client.post(
        CATEGORIES_URL,
        json={"name": "Pets"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CATEGORY_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_another_users_category_cannot_be_updated(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    created = await auth_client.post(
        CATEGORIES_URL,
        json={"name": "Pets"},
        headers=headers,
    )
    category_id = created.json()["data"]["id"]

    intruder_id = await register_user(auth_client, email="intruder@example.com")
    intruder_headers = authorization_header(intruder_id, email="intruder@example.com")

    response = await auth_client.patch(
        f"{CATEGORIES_URL}/{category_id}",
        json={"name": "Stolen"},
        headers=intruder_headers,
    )

    assert response.status_code == 404
