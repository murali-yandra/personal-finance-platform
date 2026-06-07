from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

MIN_PASSWORD_LENGTH = 8


class PasswordPolicyError(ValueError):
    """Raised when a password does not meet platform security standards."""


class SecurityService:
    """Security utilities for password hashing and verification."""

    def __init__(self, password_hasher: PasswordHasher | None = None) -> None:
        self._password_hasher = password_hasher or PasswordHasher(type=Type.ID)

    def validate_password_policy(self, password: str) -> None:
        """Validate the approved minimum password policy."""
        if len(password) < MIN_PASSWORD_LENGTH:
            raise PasswordPolicyError("Password must be at least 8 characters long.")
        if not any(character.isupper() for character in password):
            raise PasswordPolicyError("Password must contain an uppercase letter.")
        if not any(character.islower() for character in password):
            raise PasswordPolicyError("Password must contain a lowercase letter.")
        if not any(character.isdigit() for character in password):
            raise PasswordPolicyError("Password must contain a number.")

    def hash_password(self, password: str) -> str:
        """Return an Argon2id hash for a valid plaintext password."""
        self.validate_password_policy(password)
        return self._password_hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a plaintext password against an Argon2 hash."""
        try:
            return self._password_hasher.verify(password_hash, password)
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            return False

    def password_needs_rehash(self, password_hash: str) -> bool:
        """Return whether a stored password hash should be upgraded."""
        try:
            return self._password_hasher.check_needs_rehash(password_hash)
        except InvalidHashError:
            return True


security_service = SecurityService()


def hash_password(password: str) -> str:
    """Hash a plaintext password using the platform security service."""
    return security_service.hash_password(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password using the platform security service."""
    return security_service.verify_password(password, password_hash)
