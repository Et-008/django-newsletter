import base64
import hashlib
from typing import Optional

from django.conf import settings

try:
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover
    Fernet = None  # type: ignore


def _derive_fernet_key(raw_key: str) -> bytes:
    # Derive a 32-byte key from arbitrary string then urlsafe-b64 encode for Fernet
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Optional["Fernet"]:
    """
    Returns a Fernet instance using EMAIL_CONFIG_ENCRYPTION_KEY if present, else SECRET_KEY.
    Returns None if cryptography is not installed.
    """
    if Fernet is None:
        return None
    key_source = getattr(settings, "EMAIL_CONFIG_ENCRYPTION_KEY", None) or settings.SECRET_KEY
    key = _derive_fernet_key(key_source)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    f = get_fernet()
    if not f:
        # Fallback: store as-is (not recommended). Ensure requirements include cryptography.
        return plaintext
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    f = get_fernet()
    if not f:
        return ciphertext
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

