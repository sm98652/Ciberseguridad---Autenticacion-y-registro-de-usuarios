"""Contraseñas (política + hash Argon2id) y cifrado de campos sensibles (Fernet)."""

from __future__ import annotations

import json
import secrets
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, MultiFernet

# ---------------------------------------------------------------- contraseñas

MIN_LENGTH = 12
MAX_LENGTH = 128  # evita enviar contraseñas enormes para agotar CPU al hashear

_COMMON_PASSWORDS = {
    "password1234",
    "contrasena123",
    "contraseña123",
    "qwertyuiop12",
    "123456789012",
    "administrador",
    "letmein12345",
}

_hasher = PasswordHasher()  # Argon2id con los parámetros por defecto de argon2-cffi


def validate_password_policy(password: str, email: str = "") -> list[str]:
    """Devuelve la lista de reglas incumplidas (vacía si la contraseña es válida)."""
    errors: list[str] = []
    if len(password) < MIN_LENGTH:
        errors.append(f"La contraseña debe tener al menos {MIN_LENGTH} caracteres.")
    if len(password) > MAX_LENGTH:
        errors.append(f"La contraseña no puede superar {MAX_LENGTH} caracteres.")
    if not any(c.islower() for c in password):
        errors.append("La contraseña debe incluir una minúscula.")
    if not any(c.isupper() for c in password):
        errors.append("La contraseña debe incluir una mayúscula.")
    if not any(c.isdigit() for c in password):
        errors.append("La contraseña debe incluir un número.")
    if not any(not c.isalnum() and not c.isspace() for c in password):
        errors.append("La contraseña debe incluir un símbolo (por ejemplo ! # $ % &).")
    local_part = email.split("@")[0].lower()
    if len(local_part) >= 3 and local_part in password.lower():
        errors.append("La contraseña no puede contener tu correo.")
    if password.lower() in _COMMON_PASSWORDS:
        errors.append("Esa contraseña es demasiado común.")
    return errors


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True si el hash se creó con parámetros más débiles que los actuales."""
    return _hasher.check_needs_rehash(password_hash)


# Hash/secreto "señuelo": se verifican cuando el usuario no existe para que la
# respuesta tarde lo mismo y no se pueda enumerar correos por tiempo de respuesta.
DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(24))
DUMMY_OTP_SECRET = "JBSWY3DPEHPK3PXP"

# ------------------------------------------------------------------- cifrado


class FieldCipher:
    """Cifrado simétrico autenticado (Fernet) para datos que hay que poder leer de nuevo.

    Acepta varias claves separadas por coma para rotación: cifra con la primera y
    descifra con cualquiera.
    """

    def __init__(self, keys: str) -> None:
        parts = [k.strip() for k in keys.split(",") if k.strip()]
        if not parts:
            raise ValueError("APP_ENCRYPTION_KEY no puede estar vacía.")
        self._fernet = MultiFernet([Fernet(k) for k in parts])

    def encrypt(self, text: str) -> str:
        return self._fernet.encrypt(text.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()

    def encrypt_json(self, data: dict[str, Any]) -> str:
        return self.encrypt(json.dumps(data, ensure_ascii=False))

    def decrypt_json(self, token: str) -> dict[str, Any]:
        return json.loads(self.decrypt(token))
