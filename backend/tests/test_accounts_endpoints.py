"""API contract for the accounts endpoints (Sprint 2, issues #64-#67)."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import authorization_header, register_user

ACCOUNTS_URL = "/api/v1/accounts"


async def _create_account(
    client: AsyncClient,
    headers: dict[str, str],
    **overrides,
) -> dict:
    payload = {
        "account_type": "BANK",
        "account_name": "Salary Account",
        "bank_name": "ICICI",
        "last_four_digits": "0452",
        "currency": "INR",
        "opening_balance": "0.00",
    }
    payload.update(overrides)
    response = await client.post(ACCOUNTS_URL, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.mark.asyncio
async def test_create_account_returns_created_envelope(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user

    response = await auth_client.post(
        ACCOUNTS_URL,
        json={
            "account_type": "BANK",
            "account_name": "Salary Account",
            "bank_name": "ICICI",
            "last_four_digits": "0452",
            "currency": "INR",
            "opening_balance": "0.00",
        },
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["account_type"] == "BANK"
    assert data["status"] == "ACTIVE"
    assert data["estimated_balance"] == "0.00"
    UUID(data["id"])


@pytest.mark.asyncio
async def test_create_account_rejects_unsupported_account_type(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user

    response = await auth_client.post(
        ACCOUNTS_URL,
        json={"account_type": "WALLET"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_account_rejects_duplicate(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    await _create_account(auth_client, headers)

    response = await auth_client.post(
        ACCOUNTS_URL,
        json={
            "account_type": "BANK",
            "bank_name": "ICICI",
            "last_four_digits": "0452",
        },
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACCOUNT_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_accounts_endpoints_require_authentication(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get(ACCOUNTS_URL)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_list_accounts_returns_only_non_archived(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    kept = await _create_account(auth_client, headers, last_four_digits="1111")
    archived = await _create_account(auth_client, headers, last_four_digits="2222")
    await auth_client.delete(f"{ACCOUNTS_URL}/{archived['id']}", headers=headers)

    response = await auth_client.get(ACCOUNTS_URL, headers=headers)

    assert response.status_code == 200
    ids = [account["id"] for account in response.json()["data"]]
    assert ids == [kept["id"]]


@pytest.mark.asyncio
async def test_list_accounts_can_include_archived(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account = await _create_account(auth_client, headers)
    await auth_client.delete(f"{ACCOUNTS_URL}/{account['id']}", headers=headers)

    response = await auth_client.get(
        ACCOUNTS_URL,
        params={"include_archived": "true"},
        headers=headers,
    )

    assert [item["id"] for item in response.json()["data"]] == [account["id"]]


@pytest.mark.asyncio
async def test_get_account_returns_the_account(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account = await _create_account(auth_client, headers)

    response = await auth_client.get(
        f"{ACCOUNTS_URL}/{account['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == account["id"]


@pytest.mark.asyncio
async def test_get_unknown_account_returns_not_found(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user

    response = await auth_client.get(f"{ACCOUNTS_URL}/{uuid4()}", headers=headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_account_owned_by_another_user_returns_not_found(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    """Cross-user access must be indistinguishable from a missing record."""
    _, headers = authenticated_user
    account = await _create_account(auth_client, headers)

    intruder_id = await register_user(auth_client, email="intruder@example.com")
    intruder_headers = authorization_header(intruder_id, email="intruder@example.com")

    response = await auth_client.get(
        f"{ACCOUNTS_URL}/{account['id']}",
        headers=intruder_headers,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_account_applies_only_submitted_fields(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account = await _create_account(auth_client, headers)

    response = await auth_client.patch(
        f"{ACCOUNTS_URL}/{account['id']}",
        json={"account_name": "Primary Salary"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["account_name"] == "Primary Salary"
    assert data["bank_name"] == "ICICI"
    assert data["last_four_digits"] == "0452"


@pytest.mark.asyncio
async def test_update_account_can_clear_an_optional_field(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    """An explicit null clears the field; an omitted field is untouched."""
    _, headers = authenticated_user
    account = await _create_account(auth_client, headers)

    response = await auth_client.patch(
        f"{ACCOUNTS_URL}/{account['id']}",
        json={"account_name": None},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["account_name"] is None


@pytest.mark.asyncio
async def test_update_account_rejects_invalid_status_transition(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account = await _create_account(auth_client, headers)

    response = await auth_client.patch(
        f"{ACCOUNTS_URL}/{account['id']}",
        json={"status": "PENDING"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_archive_account_returns_archived_status(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account = await _create_account(auth_client, headers)

    response = await auth_client.delete(
        f"{ACCOUNTS_URL}/{account['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "id": account["id"],
        "status": "ARCHIVED",
    }


@pytest.mark.asyncio
async def test_archived_account_is_still_retrievable(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    """Archiving must never delete the record."""
    _, headers = authenticated_user
    account = await _create_account(auth_client, headers)
    await auth_client.delete(f"{ACCOUNTS_URL}/{account['id']}", headers=headers)

    response = await auth_client.get(
        f"{ACCOUNTS_URL}/{account['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ARCHIVED"


@pytest.mark.asyncio
async def test_archived_account_cannot_be_updated(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account = await _create_account(auth_client, headers)
    await auth_client.delete(f"{ACCOUNTS_URL}/{account['id']}", headers=headers)

    response = await auth_client.patch(
        f"{ACCOUNTS_URL}/{account['id']}",
        json={"account_name": "Reopened"},
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_archive_account_owned_by_another_user_returns_not_found(
    auth_client: AsyncClient,
    authenticated_user: tuple[UUID, dict[str, str]],
) -> None:
    _, headers = authenticated_user
    account = await _create_account(auth_client, headers)

    intruder_id = await register_user(auth_client, email="intruder@example.com")
    intruder_headers = authorization_header(intruder_id, email="intruder@example.com")

    response = await auth_client.delete(
        f"{ACCOUNTS_URL}/{account['id']}",
        headers=intruder_headers,
    )

    assert response.status_code == 404
