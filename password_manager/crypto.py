# crypto.py — Encryption & Decryption Engine
#
# We use TWO cryptography concepts here:
#
# 1. PBKDF2  (Password-Based Key Derivation Function 2)
#    → Turns your master password ("mypassword123") into a 32-byte
#      encryption KEY. This is a one-way, slow hash designed to resist
#      brute-force attacks.
#
# 2. Fernet Symmetric Encryption
#    → Uses the KEY from step 1 to ENCRYPT or DECRYPT any text.
#    → Same key encrypts AND decrypts (symmetric).
#    → If you don't have the key, the data is unreadable — forever.

import base64
import os
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# ─────────────────────────────────────────
# KEY DERIVATION
# ─────────────────────────────────────────

def derive_key(master_password: str, salt: bytes) -> bytes:
    """
    Converts a human-readable master password into a cryptographic key.

    Why not just use the password directly as the key?
    → Passwords are short and predictable. Fernet needs a specific
      32-byte key. PBKDF2 stretches the password into exactly that,
      while also making brute-force attacks 100,000x slower.

    Parameters:
        master_password: The user's master password (plain text string)
        salt: Random bytes mixed in to prevent rainbow table attacks

    Returns:
        A URL-safe base64-encoded 32-byte key (what Fernet needs)
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),   # SHA-256 hashing algorithm
        length=32,                   # Output: 32 bytes = 256-bit key
        salt=salt,
        iterations=480_000,          # Hash 480,000 times — makes brute-force slow!
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
    return key


def generate_salt() -> bytes:
    """
    Creates 16 random bytes to use as a salt.
    Salt is NOT secret — it's stored alongside the encrypted data.
    Its job is to make every encryption unique, even with the same password.
    """
    return os.urandom(16)   # os.urandom = cryptographically secure random bytes


# ─────────────────────────────────────────
# ENCRYPT / DECRYPT
# ─────────────────────────────────────────

def encrypt(plaintext: str, key: bytes) -> bytes:
    """
    Encrypts a plain text string using the Fernet key.

    Example:
        plaintext = "MySecret123!"
        → encrypted = b'gAAAAABh...' (looks like random garbage)

    The result includes:
        - The encrypted data
        - A timestamp
        - An HMAC signature (proves it wasn't tampered with)
    """
    f = Fernet(key)
    return f.encrypt(plaintext.encode('utf-8'))


def decrypt(token: bytes, key: bytes) -> Optional[str]:
    """
    Decrypts an encrypted token back to plain text.

    Returns None if:
        - The wrong key is used (wrong master password)
        - The data was tampered with
        - The token is corrupted

    This is how we detect a wrong master password!
    """
    try:
        f = Fernet(key)
        return f.decrypt(token).decode('utf-8')
    except (InvalidToken, Exception):
        return None   # Wrong key or corrupted data


def verify_master_password(stored_token: bytes, test_key: bytes) -> bool:
    """
    Checks if a master password (as a key) is correct.
    We encrypt a known test string during setup, then try to decrypt
    it when the user logs in. If decryption works → password is correct!
    """
    result = decrypt(stored_token, test_key)
    return result == 'VALID_MASTER_KEY'   # Our secret test string
