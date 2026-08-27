"""End-to-end SMS pipeline: raw event to transaction (Sprints 4-7)."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, select

from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.categories.models import Category
from app.domains.categories.repository import CategoryRepository
from app.domains.ingestion.models import RawEvent
from app.domains.ingestion.pipeline import SmsPipeline
from app.domains.ingestion.repository import RawEventRepository
from app.domains.ingestion.schemas import IngestSmsCommand
from app.domains.ingestion.service import IngestionService
from app.domains.merchants.models import Merchant, MerchantPattern
from app.domains.merchants.repository import MerchantRepository
from app.domains.merchants.service import MerchantService
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.service import TransactionService
from app.domains.users.models import User, UserSettings
from app.shared.enums import (
    AccountStatus,
    AccountType,
    PatternType,
    ProcessingStatus,
    TransactionDirection,
)

RECEIVED_AT = datetime(2026, 6, 2, 10, 0, 0)
HDFC_DEBIT = (
    "Rs.70.00 debited from A/C XXXX0452 at SmartQ on 02-06-26 10:00. "
    "Avl Bal Rs.12,345.67. Ref 998877"
)


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
def pipeline(db_session: Session) -> SmsPipeline:
    return SmsPipeline(
        raw_event_repository=RawEventRepository(db_session),
        account_repository=AccountRepository(db_session),
        transaction_service=TransactionService(
            repository=TransactionRepository(db_session),
            account_repository=AccountRepository(db_session),
        ),
        merchant_service=MerchantService(repository=MerchantRepository(db_session)),
        category_repository=CategoryRepository(db_session),
    )


@pytest.fixture
def ingestion(db_session: Session, pipeline: SmsPipeline) -> IngestionService:
    return IngestionService(
        repository=RawEventRepository(db_session),
        processor=pipeline,
    )


def _ingest(
    ingestion: IngestionService,
    user: User,
    message_text: str = HDFC_DEBIT,
    sender: str = "VK-HDFCBK",
    received_at: datetime = RECEIVED_AT,
):
    return ingestion.ingest_sms(
        IngestSmsCommand(
            user_id=user.id,
            message_text=message_text,
            received_at=received_at,
            sender=sender,
        )
    )


def _hdfc_account(db_session: Session, user: User) -> Account:
    account = Account(
        user_id=user.id,
        account_name="Salary",
        account_type=AccountType.BANK.value,
        bank_name="HDFC",
        last_four_digits="0452",
        status=AccountStatus.ACTIVE.value,
    )
    db_session.add(account)
    db_session.commit()
    return account


# ------------------------------------------------------------------ happy path


def test_sms_becomes_a_transaction(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    account = _hdfc_account(db_session, user)

    result = _ingest(ingestion, user)

    assert result.status is ProcessingStatus.PROCESSED
    assert result.transaction_id is not None

    transaction = db_session.get(Transaction, result.transaction_id)
    assert transaction.amount == Decimal("70.00")
    assert transaction.direction == TransactionDirection.DEBIT
    assert transaction.account_id == account.id
    assert transaction.merchant_raw == "SmartQ"
    assert transaction.reference_number == "998877"


def test_transaction_links_back_to_its_raw_event(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    """The raw event is the source of truth, so the link must survive."""
    _hdfc_account(db_session, user)

    result = _ingest(ingestion, user)

    transaction = db_session.get(Transaction, result.transaction_id)
    assert transaction.raw_event_id == result.raw_event_id


def test_raw_event_is_marked_processed(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    _hdfc_account(db_session, user)

    result = _ingest(ingestion, user)

    raw_event = db_session.get(RawEvent, result.raw_event_id)
    assert raw_event.processing_status == ProcessingStatus.PROCESSED


def test_sms_received_timestamp_is_preserved(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    _hdfc_account(db_session, user)

    result = _ingest(ingestion, user)

    transaction = db_session.get(Transaction, result.transaction_id)
    assert transaction.sms_received_timestamp == RECEIVED_AT
    assert transaction.transaction_timestamp == datetime(2026, 6, 2, 10, 0)


# ------------------------------------------------------------ account matching


def test_unknown_account_is_created_as_pending(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    """Real money must be recorded even when the account is not yet known."""
    result = _ingest(ingestion, user)

    assert result.status is ProcessingStatus.NEEDS_REVIEW

    accounts = list(db_session.exec(select(Account)).all())
    assert len(accounts) == 1
    assert accounts[0].status == AccountStatus.PENDING
    assert accounts[0].bank_name == "HDFC"
    assert accounts[0].last_four_digits == "0452"


def test_second_message_reuses_the_pending_account(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    _ingest(ingestion, user)
    _ingest(
        ingestion,
        user,
        message_text=(
            "Rs.90.00 debited from A/C XXXX0452 at Cafe on 03-06-26 11:00. Ref 5555"
        ),
        received_at=RECEIVED_AT.replace(day=3),
    )

    assert len(list(db_session.exec(select(Account)).all())) == 1


def test_message_is_matched_to_the_right_account_by_bank_and_digits(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    hdfc = _hdfc_account(db_session, user)
    icici = Account(
        user_id=user.id,
        account_type=AccountType.BANK.value,
        bank_name="ICICI",
        last_four_digits="0452",
        status=AccountStatus.ACTIVE.value,
    )
    db_session.add(icici)
    db_session.commit()

    result = _ingest(ingestion, user)

    transaction = db_session.get(Transaction, result.transaction_id)
    assert transaction.account_id == hdfc.id


def test_message_for_an_archived_account_is_still_recorded(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    """Archiving says the user stopped using the account; the bank says otherwise.

    Dropping the transaction would lose real money, and the accounts uniqueness
    constraint forbids creating a second account with the same bank and digits.
    So the transaction is posted to the real account and flagged for review.
    """
    account = _hdfc_account(db_session, user)
    account.status = AccountStatus.ARCHIVED.value
    db_session.add(account)
    db_session.commit()

    result = _ingest(ingestion, user)

    assert result.status is ProcessingStatus.NEEDS_REVIEW
    transaction = db_session.get(Transaction, result.transaction_id)
    assert transaction.account_id == account.id


def test_archiving_is_not_silently_reversed_by_an_incoming_message(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    account = _hdfc_account(db_session, user)
    account.status = AccountStatus.ARCHIVED.value
    db_session.add(account)
    db_session.commit()

    _ingest(ingestion, user)

    db_session.refresh(account)
    assert account.status == AccountStatus.ARCHIVED
    assert len(list(db_session.exec(select(Account)).all())) == 1


def test_a_live_account_is_preferred_over_an_archived_one(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    archived = Account(
        user_id=user.id,
        account_type=AccountType.CREDIT_CARD.value,
        bank_name="HDFC",
        last_four_digits="0452",
        status=AccountStatus.ARCHIVED.value,
    )
    db_session.add(archived)
    db_session.commit()
    live = _hdfc_account(db_session, user)

    result = _ingest(ingestion, user)

    transaction = db_session.get(Transaction, result.transaction_id)
    assert transaction.account_id == live.id
    assert result.status is ProcessingStatus.PROCESSED


# ----------------------------------------------------------- merchant resolution


def test_merchant_pattern_resolves_the_transaction_merchant(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    _hdfc_account(db_session, user)
    merchant = Merchant(merchant_name="SmartQ")
    db_session.add(merchant)
    db_session.commit()
    db_session.add(
        MerchantPattern(
            user_id=None,
            merchant_id=merchant.id,
            pattern="%SMARTQ%",
            pattern_type=PatternType.LIKE.value,
        )
    )
    db_session.commit()

    result = _ingest(ingestion, user)

    transaction = db_session.get(Transaction, result.transaction_id)
    assert transaction.merchant_id == merchant.id


def test_merchant_default_category_is_applied(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    _hdfc_account(db_session, user)
    category = Category(user_id=None, name="Food", is_system=True)
    db_session.add(category)
    db_session.commit()

    merchant = Merchant(merchant_name="SmartQ", default_category_id=category.id)
    db_session.add(merchant)
    db_session.commit()
    db_session.add(
        MerchantPattern(
            user_id=None,
            merchant_id=merchant.id,
            pattern="%SMARTQ%",
            pattern_type=PatternType.LIKE.value,
        )
    )
    db_session.commit()

    result = _ingest(ingestion, user)

    transaction = db_session.get(Transaction, result.transaction_id)
    assert transaction.category_id == category.id


def test_unmatched_merchant_leaves_the_field_unset(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    """A wrongly attributed merchant corrupts every report grouped by merchant."""
    _hdfc_account(db_session, user)

    result = _ingest(ingestion, user)

    transaction = db_session.get(Transaction, result.transaction_id)
    assert transaction.merchant_id is None
    assert transaction.merchant_raw == "SmartQ"


# ------------------------------------------------------------------ duplicates


def test_replayed_message_never_reaches_the_pipeline(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    _hdfc_account(db_session, user)
    _ingest(ingestion, user)

    second = _ingest(ingestion, user)

    assert second.is_duplicate is True
    assert len(list(db_session.exec(select(Transaction)).all())) == 1


def test_same_transaction_worded_differently_is_caught_by_the_fingerprint(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    """A different message hash still resolves to one transaction."""
    _hdfc_account(db_session, user)
    _ingest(ingestion, user)

    second = _ingest(
        ingestion,
        user,
        message_text=(
            "Rs.70 debited from A/C XXXX0452 at SMART-Q on 02-06-26 10:00. Ref 998877"
        ),
        received_at=RECEIVED_AT.replace(second=30),
    )

    assert second.status is ProcessingStatus.DUPLICATE
    assert len(list(db_session.exec(select(Transaction)).all())) == 1

    raw_event = db_session.get(RawEvent, second.raw_event_id)
    assert raw_event.processing_status == ProcessingStatus.DUPLICATE


# --------------------------------------------------------- unparseable messages


def test_otp_is_ignored_rather_than_failed(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    """Genuine parser gaps must stay visible instead of being buried in noise."""
    result = _ingest(
        ingestion,
        user,
        message_text="123456 is your OTP for Rs.2,500. Do not share it.",
    )

    assert result.status is ProcessingStatus.IGNORED
    assert len(list(db_session.exec(select(Transaction)).all())) == 0


def test_unreadable_transactional_message_is_flagged_unknown_format(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    result = _ingest(
        ingestion,
        user,
        message_text="Transaction of INR 500.00 on card XX1234 processed.",
    )

    assert result.status is ProcessingStatus.UNKNOWN_FORMAT

    raw_event = db_session.get(RawEvent, result.raw_event_id)
    assert raw_event.processing_error


def test_unparsed_messages_never_create_an_account(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    _ingest(ingestion, user, message_text="123456 is your OTP. Do not share it.")

    assert list(db_session.exec(select(Account)).all()) == []


def test_raw_event_survives_every_outcome(
    ingestion: IngestionService,
    user: User,
    db_session: Session,
) -> None:
    """Raw events are the source of truth and are retained permanently."""
    for text in (
        HDFC_DEBIT,
        "123456 is your OTP. Do not share it.",
        "Transaction of INR 500.00 processed.",
    ):
        _ingest(ingestion, user, message_text=text, received_at=RECEIVED_AT)

    assert len(list(db_session.exec(select(RawEvent)).all())) == 3
