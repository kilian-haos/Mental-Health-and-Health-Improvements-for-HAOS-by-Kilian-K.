"""Key handling and encryption (pure Python + `cryptography`, which ships with Home Assistant).

Design (see docs/privacy.md):

* A **master key** (Fernet) lives in `.storage/mental_health.keys`.
* Every person has a **data key** (DEK, Fernet), wrapped with the master key. It encrypts
  numeric values (mood, sleep, weight, cycle dates …) – the server needs them at any time to
  run the analysis and to keep the sensors up to date.
* Every person has a **text key** (TEK, Fernet). It encrypts free texts (journal, good/bad
  things, goals) and cycle details (flow, pain, symptoms).
  - Without a personal PIN the TEK is wrapped with the master key.
  - With a personal PIN the TEK is wrapped **only** with a key derived from the PIN (scrypt).
    The server can then read those texts only while the person has unlocked a session; the
    text analysis catches up afterwards. Forgetting the PIN means: an admin can reset it, but
    the protected texts are lost for good (numbers are kept).

Honest limits: anyone with full file-system access *and* the master key (which is part of HA
backups) can decrypt everything that is not PIN-protected. Python cannot reliably wipe memory.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1


class CryptoError(Exception):
    """Decryption failed (wrong key/PIN or damaged data)."""


def new_key() -> bytes:
    return Fernet.generate_key()


def _f(key: bytes) -> Fernet:
    return Fernet(key)


def encrypt_bytes(key: bytes, data: bytes) -> str:
    return _f(key).encrypt(data).decode("ascii")


def decrypt_bytes(key: bytes, token: str) -> bytes:
    try:
        return _f(key).decrypt(token.encode("ascii"))
    except (InvalidToken, ValueError, AttributeError) as err:
        raise CryptoError("decryption failed") from err


def encrypt_json(key: bytes, obj: Any) -> str:
    return encrypt_bytes(key, json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def decrypt_json(key: bytes, token: str) -> Any:
    return json.loads(decrypt_bytes(key, token).decode("utf-8"))


def wrap_key(wrapping_key: bytes, key: bytes) -> str:
    return encrypt_bytes(wrapping_key, key)


def unwrap_key(wrapping_key: bytes, wrapped: str) -> bytes:
    return decrypt_bytes(wrapping_key, wrapped)


# ---------------------------------------------------------------- Passwörter/PINs
def derive_key(secret: str, salt: bytes, n: int = SCRYPT_N) -> bytes:
    """scrypt -> 32 Byte -> Fernet-Schlüssel (urlsafe base64)."""
    raw = hashlib.scrypt(secret.encode("utf-8"), salt=salt, n=n, r=SCRYPT_R, p=SCRYPT_P, dklen=32,
                         maxmem=64 * 1024 * 1024)
    return base64.urlsafe_b64encode(raw)


def new_salt() -> bytes:
    return os.urandom(16)


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def pin_wrap(pin: str, key: bytes) -> dict:
    """Schlüssel mit PIN umhüllen. Gibt {salt, n, wrapped} zurück."""
    salt = new_salt()
    return {"salt": b64(salt), "n": SCRYPT_N, "wrapped": wrap_key(derive_key(pin, salt), key)}


def pin_unwrap(pin: str, blob: dict) -> bytes:
    kek = derive_key(pin, unb64(blob["salt"]), int(blob.get("n", SCRYPT_N)))
    return unwrap_key(kek, blob["wrapped"])


def hash_secret(secret: str) -> dict:
    """Admin-PIN: nur Hash speichern (scrypt mit Salz)."""
    salt = new_salt()
    digest = hashlib.scrypt(secret.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32,
                            maxmem=64 * 1024 * 1024)
    return {"salt": b64(salt), "n": SCRYPT_N, "hash": b64(digest)}


def verify_secret(secret: str, stored: dict | None) -> bool:
    if not stored:
        return False
    try:
        digest = hashlib.scrypt(secret.encode("utf-8"), salt=unb64(stored["salt"]), n=int(stored.get("n", SCRYPT_N)),
                                r=SCRYPT_R, p=SCRYPT_P, dklen=32, maxmem=64 * 1024 * 1024)
    except (KeyError, ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, unb64(stored["hash"]))


def token() -> str:
    return secrets.token_urlsafe(24)


# ---------------------------------------------------------------- Schlüsselbund
class Keyring:
    """Holds the master key and every person's wrapped keys (serialisable dict)."""

    def __init__(self, data: dict | None = None) -> None:
        data = data or {}
        self.master: bytes = data["master"].encode("ascii") if data.get("master") else new_key()
        self.persons: dict[str, dict] = {k: dict(v) for k, v in (data.get("persons") or {}).items()}

    def to_dict(self) -> dict:
        return {"master": self.master.decode("ascii"), "persons": self.persons}

    # Personen
    def ensure_person(self, pid: str) -> None:
        if pid in self.persons:
            return
        self.persons[pid] = {
            "dek": wrap_key(self.master, new_key()),
            "tek": wrap_key(self.master, new_key()),
            "tek_pin": None,
        }

    def remove_person(self, pid: str) -> None:
        self.persons.pop(pid, None)

    def dek(self, pid: str) -> bytes:
        return unwrap_key(self.master, self.persons[pid]["dek"])

    def has_pin(self, pid: str) -> bool:
        return bool(self.persons.get(pid, {}).get("tek_pin"))

    def tek_without_pin(self, pid: str) -> bytes | None:
        """Textschlüssel, wenn keine PIN gesetzt ist (sonst None)."""
        p = self.persons[pid]
        if p.get("tek_pin") or not p.get("tek"):
            return None
        return unwrap_key(self.master, p["tek"])

    def tek_with_pin(self, pid: str, pin: str) -> bytes:
        p = self.persons[pid]
        if not p.get("tek_pin"):
            raise CryptoError("no pin set")
        return pin_unwrap(pin, p["tek_pin"])

    def set_pin(self, pid: str, tek: bytes, pin: str) -> None:
        """PIN setzen/ändern: TEK nur noch mit der PIN umhüllen."""
        p = self.persons[pid]
        p["tek_pin"] = pin_wrap(pin, tek)
        p["tek"] = None

    def remove_pin(self, pid: str, tek: bytes) -> None:
        p = self.persons[pid]
        p["tek"] = wrap_key(self.master, tek)
        p["tek_pin"] = None

    def reset_pin(self, pid: str) -> None:
        """Admin setzt die PIN zurück: neuer Textschlüssel, alte geschützte Texte sind verloren."""
        p = self.persons[pid]
        p["tek"] = wrap_key(self.master, new_key())
        p["tek_pin"] = None
        p["tek_gen"] = int(p.get("tek_gen", 0)) + 1

    def tek_gen(self, pid: str) -> int:
        return int(self.persons.get(pid, {}).get("tek_gen", 0))
