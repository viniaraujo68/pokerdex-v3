import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def needs_rehash(password_hash: str) -> bool:
    """True when argon2's parameters have moved on and the stored hash should be upgraded."""
    return _ph.check_needs_rehash(password_hash)


# Hash of a throwaway random secret. Verifying against it on the "unknown username"
# path costs the same argon2 work as a real login, so response time can't be used to
# enumerate which accounts exist.
_DUMMY_HASH = _ph.hash(secrets.token_urlsafe(32))


def dummy_verify(password: str) -> None:
    """Burn the same argon2 work as verify_password and discard the (always false) result."""
    verify_password(password, _DUMMY_HASH)


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Hash a session token for storage at rest.

    The raw token lives only in the httpOnly cookie; the DB stores this hash. A DB leak
    therefore no longer hands out live sessions. SHA-256 (not argon2) is deliberate: the
    token is already 256 bits of CSPRNG output, so it is not brute-forceable, and hashing
    it must stay cheap since it runs on every authenticated request.
    """
    return hashlib.sha256(token.encode()).hexdigest()
