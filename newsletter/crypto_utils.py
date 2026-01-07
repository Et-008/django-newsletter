import base64
import hashlib
import hmac
from typing import Optional, Tuple

from django.conf import settings

try:
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover
    Fernet = None  # type: ignore


def _derive_fernet_key(raw_key: str) -> bytes:
    # Derive a 32-byte key from arbitrary string then urlsafe-b64 encode for Fernet
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_signing_key() -> bytes:
    """Get the signing key for HMAC operations."""
    key_source = getattr(settings, "ACCOUNT_ID_SIGNING_KEY", None) or settings.SECRET_KEY
    return key_source.encode("utf-8")


def generate_account_id(user_email: str) -> str:
    """
    Generate a signed accountId from user's email.
    Format: base64url(email).hmac_signature
    
    The email is base64 encoded (not encrypted) for transparency,
    and the HMAC signature ensures the token cannot be forged.
    """
    # Base64url encode the email
    encoded_email = base64.urlsafe_b64encode(user_email.encode("utf-8")).decode("utf-8")
    
    # Create HMAC signature
    signature = hmac.new(
        _get_signing_key(),
        encoded_email.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()[:32]  # Use first 32 chars for shorter token
    
    return f"{encoded_email}.{signature}"


def validate_account_id(account_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate and decode an accountId.
    
    Returns:
        Tuple of (is_valid, user_email_or_none)
        - If valid: (True, "user@example.com")
        - If invalid: (False, None)
    """
    if not account_id or "." not in account_id:
        return (False, None)
    
    try:
        parts = account_id.rsplit(".", 1)
        if len(parts) != 2:
            return (False, None)
        
        encoded_email, provided_signature = parts
        
        # Recalculate the expected signature
        expected_signature = hmac.new(
            _get_signing_key(),
            encoded_email.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:32]
        
        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(provided_signature, expected_signature):
            return (False, None)
        
        # Decode the email
        user_email = base64.urlsafe_b64decode(encoded_email.encode("utf-8")).decode("utf-8")
        return (True, user_email)
    
    except Exception:
        return (False, None)


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


# ============================================================================
# Unsubscribe Token Functions
# ============================================================================

def generate_unsubscribe_token(subscriber_email: str, account_id: str) -> str:
    """
    Generate a signed token for unsubscribe links in emails.
    Format: base64url(subscriber_email|account_id).hmac_signature
    
    This token identifies both the subscriber AND the specific newsletter
    they want to unsubscribe from.
    """
    # Combine subscriber email and account_id with a delimiter
    payload = f"{subscriber_email}|{account_id}"
    encoded_payload = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
    
    # Create HMAC signature
    signature = hmac.new(
        _get_signing_key(),
        encoded_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()[:32]
    
    return f"{encoded_payload}.{signature}"


def validate_unsubscribe_token(token: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and decode an unsubscribe token.
    
    Returns:
        Tuple of (is_valid, subscriber_email, account_id)
        - If valid: (True, "subscriber@example.com", "accountId...")
        - If invalid: (False, None, None)
    """
    if not token or "." not in token:
        return (False, None, None)
    
    try:
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return (False, None, None)
        
        encoded_payload, provided_signature = parts
        
        # Recalculate the expected signature
        expected_signature = hmac.new(
            _get_signing_key(),
            encoded_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:32]
        
        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(provided_signature, expected_signature):
            return (False, None, None)
        
        # Decode the payload
        payload = base64.urlsafe_b64decode(encoded_payload.encode("utf-8")).decode("utf-8")
        
        # Split subscriber email and account_id
        if "|" not in payload:
            return (False, None, None)
        
        subscriber_email, account_id = payload.split("|", 1)
        return (True, subscriber_email, account_id)
    
    except Exception:
        return (False, None, None)

