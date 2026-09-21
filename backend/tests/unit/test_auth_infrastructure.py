"""
Unit tests for Phase 13's two new infrastructure adapters:
Argon2PasswordHasher (IPasswordHasher) and JWTHandler (ITokenService).
Pure, no DB, no FastAPI -- these are infrastructure-layer components
tested in isolation, same convention as test_structural_validator.py.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.infrastructure.jwt_handler import JWTHandler
from app.infrastructure.password_hasher import Argon2PasswordHasher
from app.services.exceptions import InvalidTokenError


def test_password_hash_round_trips_correctly():
    hasher = Argon2PasswordHasher()
    hashed = hasher.hash("correct horse battery staple")

    assert hashed != "correct horse battery staple"  # never store plaintext
    assert hasher.verify("correct horse battery staple", hashed) is True


def test_password_verify_rejects_wrong_password():
    hasher = Argon2PasswordHasher()
    hashed = hasher.hash("correct horse battery staple")

    assert hasher.verify("wrong password", hashed) is False


def test_jwt_issue_and_verify_round_trip():
    handler = JWTHandler()
    doctor_id = "11111111-1111-1111-1111-111111111111"

    token = handler.issue(doctor_id)
    assert handler.verify(token) == doctor_id


def test_jwt_verify_rejects_expired_token():
    # Construct an already-expired token directly (not via handler.issue(),
    # which always sets a future expiration) -- real proof the expiration
    # claim is actually checked, not just present and ignored.
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    handler = JWTHandler()
    with pytest.raises(InvalidTokenError):
        handler.verify(expired_token)


def test_jwt_verify_rejects_tampered_token():
    """A real tampered token, not a synthetic invalid string, so signature
    verification itself is what catches this.

    WHY THE TAMPERING IS DONE ON THE DECODED BYTES. This test previously
    flipped the LAST character of the base64url signature, which was
    intermittently wrong -- it passed ~95% of runs and failed the rest.

    An HS256 signature is 32 bytes, which base64url-encodes to 43
    characters. 43 x 6 = 258 bits for 256 bits of signature, so the final
    character carries 4 significant bits plus 2 bits of padding that
    decoding discards. Flipping it to "A" (value 0) therefore leaves the
    decoded 32 bytes UNCHANGED whenever the original character's four
    significant bits were already zero -- i.e. for the characters A-D, which
    is 4 of 64 possible values. The token then still verifies and
    pytest.raises sees nothing.

    Measured on 5,000 distinct signatures: 268 (5.36%) were unchanged by
    that flip, matching the observed failure rate. (The `exp` claim has
    second resolution, so a probe that reissues within one second measures
    the same token repeatedly and misses this entirely.)

    Decoding, flipping one byte and re-encoding changes the signature bytes
    unconditionally, so the assertion holds for every possible token.
    """
    handler = JWTHandler()
    token = handler.issue("11111111-1111-1111-1111-111111111111")

    head, payload, signature = token.rsplit(".", 2)
    raw = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
    flipped = bytes([raw[0] ^ 0xFF]) + raw[1:]
    tampered_signature = base64.urlsafe_b64encode(flipped).rstrip(b"=").decode()
    tampered = f"{head}.{payload}.{tampered_signature}"

    assert tampered_signature != signature
    with pytest.raises(InvalidTokenError):
        handler.verify(tampered)


def test_jwt_verify_rejects_token_signed_with_a_different_secret():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "iat": now,
        "exp": now + timedelta(minutes=60),
    }
    forged_token = jwt.encode(
        payload, "a-completely-different-secret-key-value", algorithm=settings.JWT_ALGORITHM
    )

    handler = JWTHandler()
    with pytest.raises(InvalidTokenError):
        handler.verify(forged_token)
