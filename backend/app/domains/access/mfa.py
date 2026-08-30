"""Time-based one-time password (TOTP) multi-factor authentication.

The design point that matters: **enrolment is two-step**. Generating a secret
does not turn MFA on. The user must prove they can produce a code from it, and
only then does the second factor start being required. Enabling on generation
alone would lock out anyone whose authenticator failed to scan the QR code,
with no way back in.

Recovery codes exist for the same reason. A lost phone must not mean a lost
account, so ten single-use codes are issued at enrolment, stored hashed like
passwords, and each works exactly once.
"""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from uuid import UUID

import pyotp
from sqlmodel import Session, select

from app.core.security import SecurityService
from app.domains.access.models import MfaRecoveryCode, UserMfa
from app.shared.exceptions.base import ApplicationError

ISSUER_NAME = "Personal Finance Tracker"
RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_BYTES = 5

# One step either side of now, so a code is accepted despite modest clock
# drift between the phone and the server. Wider would meaningfully extend the
# window in which a shoulder-surfed code still works.
TOTP_VALID_WINDOW = 1


class MfaAlreadyEnabledError(ApplicationError):
    """Raised when enrolling an account that already has MFA active."""

    def __init__(self) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message="Multi-factor authentication is already enabled.",
            status_code=HTTPStatus.CONFLICT,
        )


class MfaNotEnrolledError(ApplicationError):
    """Raised when confirming or using MFA before enrolment."""

    def __init__(self) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message="Multi-factor authentication has not been set up.",
            status_code=HTTPStatus.BAD_REQUEST,
        )


class InvalidMfaCodeError(ApplicationError):
    """Raised when a submitted code or recovery code is wrong."""

    def __init__(self) -> None:
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Invalid verification code.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )


class MfaRequiredError(ApplicationError):
    """Raised when a login needs a second factor.

    Carries no token: the password check has passed but authentication has
    not completed, so nothing usable is issued until the second factor does.
    """

    def __init__(self) -> None:
        super().__init__(
            code="MFA_REQUIRED",
            message="A multi-factor authentication code is required.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )


@dataclass(frozen=True)
class MfaEnrolment:
    """A pending enrolment, returned once at setup."""

    secret: str
    provisioning_uri: str
    recovery_codes: tuple[str, ...]


class MfaService:
    """Enrols, confirms and verifies second factors."""

    def __init__(
        self,
        session: Session,
        security_service: SecurityService | None = None,
    ) -> None:
        self._session = session
        self._security = security_service or SecurityService()

    def get_mfa(self, user_id: UUID) -> UserMfa | None:
        """Return the user's MFA record, enrolled or not."""
        statement = select(UserMfa).where(UserMfa.user_id == user_id)
        return self._session.exec(statement).first()

    def is_enabled(self, user_id: UUID) -> bool:
        """Return whether a confirmed second factor is required for this user."""
        record = self.get_mfa(user_id)
        return record is not None and record.is_enabled

    def begin_enrolment(self, user_id: UUID, email: str) -> MfaEnrolment:
        """Generate a secret and recovery codes without enabling anything yet.

        Re-enrolling before confirmation replaces the pending secret, so a user
        who abandoned a half-finished setup can simply start again.
        """
        existing = self.get_mfa(user_id)
        if existing is not None and existing.is_enabled:
            raise MfaAlreadyEnabledError()

        secret = pyotp.random_base32()
        record = existing or UserMfa(user_id=user_id, secret=secret)
        record.secret = secret
        record.is_enabled = False
        record.confirmed_at = None
        self._session.add(record)
        self._session.flush()

        codes = self._issue_recovery_codes(record.id)
        self._session.commit()
        self._session.refresh(record)

        provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=ISSUER_NAME,
        )
        return MfaEnrolment(
            secret=secret,
            provisioning_uri=provisioning_uri,
            recovery_codes=codes,
        )

    def confirm_enrolment(self, user_id: UUID, code: str) -> UserMfa:
        """Turn MFA on, but only once a real code proves the secret works."""
        record = self.get_mfa(user_id)
        if record is None:
            raise MfaNotEnrolledError()
        if record.is_enabled:
            raise MfaAlreadyEnabledError()
        if not _verify_totp(record.secret, code):
            raise InvalidMfaCodeError()

        record.is_enabled = True
        record.confirmed_at = _now()
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def verify(self, user_id: UUID, code: str) -> bool:
        """Verify a TOTP code or a single-use recovery code."""
        record = self.get_mfa(user_id)
        if record is None or not record.is_enabled:
            return False

        if _verify_totp(record.secret, code):
            record.last_used_at = _now()
            self._session.add(record)
            self._session.commit()
            return True

        return self._consume_recovery_code(record, code)

    def disable(self, user_id: UUID, code: str) -> None:
        """Turn MFA off, requiring a valid code to do so.

        Without the code an attacker holding a stolen access token could strip
        the second factor, which is the protection they are trying to defeat.
        """
        record = self.get_mfa(user_id)
        if record is None or not record.is_enabled:
            raise MfaNotEnrolledError()
        if not self.verify(user_id, code):
            raise InvalidMfaCodeError()

        for recovery in self._recovery_codes(record.id):
            self._session.delete(recovery)
        self._session.delete(record)
        self._session.commit()

    def regenerate_recovery_codes(self, user_id: UUID, code: str) -> tuple[str, ...]:
        """Replace the recovery codes, requiring a valid second factor."""
        record = self.get_mfa(user_id)
        if record is None or not record.is_enabled:
            raise MfaNotEnrolledError()
        if not self.verify(user_id, code):
            raise InvalidMfaCodeError()

        for recovery in self._recovery_codes(record.id):
            self._session.delete(recovery)
        self._session.flush()

        codes = self._issue_recovery_codes(record.id)
        self._session.commit()
        return codes

    def remaining_recovery_codes(self, user_id: UUID) -> int:
        """Return how many unused recovery codes are left."""
        record = self.get_mfa(user_id)
        if record is None:
            return 0
        return sum(
            1 for code in self._recovery_codes(record.id) if code.used_at is None
        )

    def _issue_recovery_codes(self, mfa_id: UUID) -> tuple[str, ...]:
        codes = tuple(
            secrets.token_hex(RECOVERY_CODE_BYTES).upper()
            for _ in range(RECOVERY_CODE_COUNT)
        )
        for plaintext in codes:
            self._session.add(
                MfaRecoveryCode(
                    mfa_id=mfa_id,
                    code_hash=self._security.hash_secret(plaintext),
                )
            )
        self._session.flush()
        return codes

    def _recovery_codes(self, mfa_id: UUID) -> list[MfaRecoveryCode]:
        statement = select(MfaRecoveryCode).where(MfaRecoveryCode.mfa_id == mfa_id)
        return list(self._session.exec(statement).all())

    def _consume_recovery_code(self, record: UserMfa, code: str) -> bool:
        """Spend a recovery code. Each one works exactly once."""
        candidate = code.strip().upper().replace("-", "").replace(" ", "")
        if not candidate:
            return False

        for recovery in self._recovery_codes(record.id):
            if recovery.used_at is not None:
                continue
            if self._security.verify_secret(candidate, recovery.code_hash):
                recovery.used_at = _now()
                record.last_used_at = _now()
                self._session.add(recovery)
                self._session.add(record)
                self._session.commit()
                return True
        return False


def _verify_totp(secret: str, code: str) -> bool:
    candidate = (code or "").strip().replace(" ", "")
    if not candidate.isdigit():
        return False
    # pyotp compares in constant time internally.
    return pyotp.TOTP(secret).verify(candidate, valid_window=TOTP_VALID_WINDOW)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
