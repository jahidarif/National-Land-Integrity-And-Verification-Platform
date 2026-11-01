from __future__ import annotations
import base64
import hashlib
import hmac
try:
    import bcrypt
except ImportError:
    bcrypt = None
from app.domain.ports.i_password_verifier import IPasswordVerifier

class BcryptPasswordVerifier(IPasswordVerifier):
    def verify(self, password: str, password_hash: str) -> bool:
        try:
            if password_hash.startswith("scrypt$"):
                _, salt_text, digest_text = password_hash.split("$", 2)
                salt = base64.urlsafe_b64decode(salt_text.encode())
                expected = base64.urlsafe_b64decode(digest_text.encode())
                actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=len(expected))
                return hmac.compare_digest(actual, expected)
            if bcrypt is None: return False
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except (ValueError, TypeError):
            return False
