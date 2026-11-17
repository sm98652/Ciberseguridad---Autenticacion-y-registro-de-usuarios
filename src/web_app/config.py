"""Configuración leída desde variables de entorno (ver .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    database_url: str
    encryption_keys: str
    issuer: str = "Nuu"
    max_failed_attempts: int = 5
    lockout_minutes: int = 15
    admin_emails: frozenset[str] = field(default_factory=frozenset)


def _parse_emails(raw: str) -> frozenset[str]:
    return frozenset(e.strip().lower() for e in raw.split(",") if e.strip())


def get_settings() -> Settings:
    missing = [k for k in ("DATABASE_URL", "APP_ENCRYPTION_KEY") if not os.environ.get(k)]
    if missing:
        raise RuntimeError(
            f"Faltan variables de entorno: {', '.join(missing)}. Revisa .env.example."
        )
    return Settings(
        database_url=os.environ["DATABASE_URL"],
        encryption_keys=os.environ["APP_ENCRYPTION_KEY"],
        issuer=os.environ.get("APP_ISSUER", "Nuu"),
        max_failed_attempts=int(os.environ.get("MAX_FAILED_ATTEMPTS", "5")),
        lockout_minutes=int(os.environ.get("LOCKOUT_MINUTES", "15")),
        admin_emails=_parse_emails(os.environ.get("ADMIN_EMAILS", "")),
    )
