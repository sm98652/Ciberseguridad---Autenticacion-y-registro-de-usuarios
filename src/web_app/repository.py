"""Contrato de acceso a datos. La implementación real está en db.py (PostgreSQL)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class EmailAlreadyRegistered(Exception):
    pass


@dataclass(frozen=True)
class User:
    id: int
    email: str
    password_hash: str
    otp_secret_enc: str
    otp_confirmed: bool
    otp_last_step: int


class UserRepository(Protocol):
    def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        otp_secret_enc: str,
        pii_enc: str,
        phi_enc: str,
        credit_enc: str,
    ) -> int:
        """Crea el usuario. Si el correo existe pero nunca confirmó su OTP, lo reemplaza.
        Lanza EmailAlreadyRegistered si ya existe una cuenta confirmada."""

    def get_user_by_email(self, email: str) -> User | None: ...

    def confirm_otp(self, user_id: int, step: int) -> bool:
        """Marca el OTP como configurado y guarda el paso usado. False si ya estaba confirmado."""

    def advance_otp_step(self, user_id: int, step: int) -> bool:
        """Guarda `step` solo si es mayor al último aceptado (atómico). False => reutilización."""

    def update_password_hash(self, user_id: int, password_hash: str) -> None: ...

    def record_attempt(self, email: str, success: bool, reason: str) -> None: ...

    def recent_failures(self, email: str, since: datetime, limit: int) -> list[datetime]:
        """Fallos posteriores a `since` y al último éxito, del más nuevo al más antiguo."""
