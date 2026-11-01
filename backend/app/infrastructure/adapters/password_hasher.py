"""Password hashing adapter.

Uses bcrypt as in the reference project. A stdlib scrypt fallback is included only
for constrained local test environments where the optional bcrypt wheel is absent.
Installed project deployments use bcrypt from pyproject.toml.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import os
try:
    import bcrypt
except ImportError:  # pragma: no cover - fallback used only in minimal offline test environments
    bcrypt = None
from app.domain.ports.i_password_hasher import IPasswordHasher

class BcryptPasswordHasher(IPasswordHasher):
    """Application-facing password hashing adapter."""
    def hash(self, password: str) -> str:
        encoded = password.encode("utf-8")
        if bcrypt is not None:
            return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode("utf-8")
        salt = os.urandom(16)
        digest = hashlib.scrypt(encoded, salt=salt, n=2**14, r=8, p=1, dklen=32)
        return "scrypt$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()

