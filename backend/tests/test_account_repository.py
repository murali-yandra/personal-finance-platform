from decimal import Decimal

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.domains.accounts.enums import AccountStatus, AccountType
from app.domains.accounts.exceptions import DuplicateAccountIdentityError
from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.users.models import User


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def test_create_account_persists_user_owned_account(session: Session) -> None:
    user = _create_user(session, "owner@example.com")
    repository = AccountRepository(session)

    account = repository.create_account(
        _account(user_id=user.id, account_name="Salary Account")
    )
    repository.commit()

    stored_account = session.get(Account, account.id)
    assert stored_account is not None
    assert stored_account.user_id == user.id
    assert stored_account.account_name == "Salary Account"


def test_get_account_by_id_is_scoped_to_user(session: Session) -> None:
    owner = _create_user(session, "owner@example.com")
    other_user = _create_user(session, "other@example.com")
    account = _persist_account(session, owner.id, account_name="Salary Account")
    repository = AccountRepository(session)

    assert repository.get_account_by_id(account.id, owner.id) is not None
    assert repository.get_account_by_id(account.id, other_user.id) is None


def test_list_accounts_is_scoped_to_user_and_excludes_archived_by_default(
    session: Session,
) -> None:
    owner = _create_user(session, "owner@example.com")
    other_user = _create_user(session, "other@example.com")
    active_account = _persist_account(
        session,
        owner.id,
        account_name="Active Account",
        status=AccountStatus.ACTIVE,
        last_four_digits="1001",
    )
    pending_account = _persist_account(
        session,
        owner.id,
        account_name="Pending Account",
        status=AccountStatus.PENDING,
        last_four_digits="1002",
    )
    disabled_account = _persist_account(
        session,
        owner.id,
        account_name="Disabled Account",
        status=AccountStatus.DISABLED,
        last_four_digits="1003",
    )
    archived_account = _persist_account(
        session,
        owner.id,
        account_name="Archived Account",
        status=AccountStatus.ARCHIVED,
        last_four_digits="1004",
    )
    _persist_account(
        session,
        other_user.id,
        account_name="Other User Account",
        last_four_digits="2001",
    )
    repository = AccountRepository(session)

    default_accounts = repository.list_accounts(owner.id)
    all_accounts = repository.list_accounts(owner.id, include_archived=True)

    assert {account.id for account in default_accounts} == {
        active_account.id,
        pending_account.id,
        disabled_account.id,
    }
    assert {account.id for account in all_accounts} == {
        active_account.id,
        pending_account.id,
        disabled_account.id,
        archived_account.id,
    }


def test_update_account_is_scoped_to_user(session: Session) -> None:
    owner = _create_user(session, "owner@example.com")
    other_user = _create_user(session, "other@example.com")
    account = _persist_account(session, owner.id, account_name="Old Name")
    repository = AccountRepository(session)

    cross_user_update = repository.update_account(
        account.id,
        other_user.id,
        {"account_name": "Cross User Name"},
    )
    owner_update = repository.update_account(
        account.id,
        owner.id,
        {
            "account_name": "New Name",
            "account_type": AccountType.CASH,
            "opening_balance": Decimal("25.00"),
            "status": AccountStatus.ACTIVE,
        },
    )
    repository.commit()

    stored_account = session.get(Account, account.id)
    assert cross_user_update is None
    assert owner_update is not None
    assert stored_account is not None
    assert stored_account.account_name == "New Name"
    assert stored_account.account_type == "CASH"
    assert stored_account.opening_balance == Decimal("25.00")
    assert stored_account.status == "ACTIVE"


def test_archive_account_sets_archived_status_without_cross_user_access(
    session: Session,
) -> None:
    owner = _create_user(session, "owner@example.com")
    other_user = _create_user(session, "other@example.com")
    account = _persist_account(
        session,
        owner.id,
        account_name="Salary Account",
        status=AccountStatus.ACTIVE,
    )
    repository = AccountRepository(session)

    cross_user_archive = repository.archive_account(account.id, other_user.id)
    owner_archive = repository.archive_account(account.id, owner.id)
    repository.commit()

    stored_account = session.get(Account, account.id)
    assert cross_user_archive is None
    assert owner_archive is not None
    assert stored_account is not None
    assert stored_account.status == "ARCHIVED"


def test_account_identity_exists_is_scoped_to_user(session: Session) -> None:
    owner = _create_user(session, "owner@example.com")
    other_user = _create_user(session, "other@example.com")
    account = _persist_account(
        session,
        owner.id,
        bank_name="ICICI",
        last_four_digits="0452",
        account_type=AccountType.BANK,
    )
    repository = AccountRepository(session)

    assert repository.account_identity_exists(
        user_id=owner.id,
        bank_name="ICICI",
        last_four_digits="0452",
        account_type=AccountType.BANK,
    )
    assert not repository.account_identity_exists(
        user_id=other_user.id,
        bank_name="ICICI",
        last_four_digits="0452",
        account_type=AccountType.BANK,
    )
    assert not repository.account_identity_exists(
        user_id=owner.id,
        bank_name="ICICI",
        last_four_digits="0452",
        account_type=AccountType.BANK,
        exclude_account_id=account.id,
    )


def test_create_account_maps_duplicate_identity_to_domain_error(
    session: Session,
) -> None:
    user = _create_user(session, "owner@example.com")
    repository = AccountRepository(session)
    repository.create_account(
        _account(
            user_id=user.id,
            bank_name="ICICI",
            last_four_digits="0452",
            account_type=AccountType.BANK,
        )
    )
    repository.commit()

    with pytest.raises(DuplicateAccountIdentityError):
        repository.create_account(
            _account(
                user_id=user.id,
                bank_name="ICICI",
                last_four_digits="0452",
                account_type=AccountType.BANK,
            )
        )


def test_update_account_maps_duplicate_identity_to_domain_error(
    session: Session,
) -> None:
    user = _create_user(session, "owner@example.com")
    existing_account = _persist_account(
        session,
        user.id,
        bank_name="ICICI",
        last_four_digits="0452",
        account_type=AccountType.BANK,
    )
    updated_account = _persist_account(
        session,
        user.id,
        bank_name="HDFC",
        last_four_digits="9999",
        account_type=AccountType.BANK,
    )
    repository = AccountRepository(session)

    with pytest.raises(DuplicateAccountIdentityError):
        repository.update_account(
            updated_account.id,
            user.id,
            {
                "bank_name": existing_account.bank_name,
                "last_four_digits": existing_account.last_four_digits,
                "account_type": existing_account.account_type,
            },
        )


def test_update_account_rejects_unsupported_fields(session: Session) -> None:
    user = _create_user(session, "owner@example.com")
    account = _persist_account(session, user.id)
    repository = AccountRepository(session)

    with pytest.raises(ValueError, match="Unsupported account update field"):
        repository.update_account(account.id, user.id, {"user_id": user.id})


def _create_user(session: Session, email: str) -> User:
    user = User(
        email=email,
        password_hash="hashed-password",
        display_name="Repository User",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _persist_account(
    session: Session,
    user_id,
    *,
    account_name: str = "Salary Account",
    account_type: AccountType = AccountType.BANK,
    bank_name: str = "ICICI",
    last_four_digits: str = "0452",
    status: AccountStatus = AccountStatus.PENDING,
) -> Account:
    account = _account(
        user_id=user_id,
        account_name=account_name,
        account_type=account_type,
        bank_name=bank_name,
        last_four_digits=last_four_digits,
        status=status,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def _account(
    *,
    user_id,
    account_name: str = "Salary Account",
    account_type: AccountType = AccountType.BANK,
    bank_name: str = "ICICI",
    last_four_digits: str = "0452",
    status: AccountStatus = AccountStatus.PENDING,
) -> Account:
    return Account(
        user_id=user_id,
        account_name=account_name,
        account_type=account_type.value,
        bank_name=bank_name,
        last_four_digits=last_four_digits,
        currency="INR",
        opening_balance=Decimal("0.00"),
        estimated_balance=Decimal("0.00"),
        status=status.value,
    )
