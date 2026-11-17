"""Implementación PostgreSQL del repositorio.

Crear las tablas:  uv run --env-file .env python -m web_app.db
"""

from __future__ import annotations

from datetime import datetime

import psycopg

from .config import get_settings
from .repository import EmailAlreadyRegistered, StoredUserData, User

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    email           TEXT        NOT NULL UNIQUE,
    password_hash   TEXT        NOT NULL,          -- Argon2id (nunca la contraseña)
    otp_secret_enc  TEXT        NOT NULL,          -- secreto TOTP cifrado (Fernet)
    otp_confirmed   BOOLEAN     NOT NULL DEFAULT FALSE,
    otp_last_step   BIGINT      NOT NULL DEFAULT 0, -- anti-replay
    pii_enc         TEXT        NOT NULL,          -- datos personales cifrados
    phi_enc         TEXT        NOT NULL,          -- datos de salud cifrados
    credit_enc      TEXT        NOT NULL,          -- datos crediticios cifrados
    consent_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id          BIGSERIAL PRIMARY KEY,
    email       TEXT        NOT NULL,
    success     BOOLEAN     NOT NULL,
    reason      TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_login_attempts_email_time
    ON login_attempts (email, created_at DESC);
"""


class PostgresUserRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def init_schema(self) -> None:
        with psycopg.connect(self._dsn) as conn:
            conn.execute(SCHEMA)

    def create_user(self, *, email, password_hash, otp_secret_enc, pii_enc, phi_enc, credit_enc) -> int:
        sql = """
            INSERT INTO users (email, password_hash, otp_secret_enc, pii_enc, phi_enc, credit_enc, consent_at)
            VALUES (%s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (email) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                otp_secret_enc = EXCLUDED.otp_secret_enc,
                pii_enc = EXCLUDED.pii_enc,
                phi_enc = EXCLUDED.phi_enc,
                credit_enc = EXCLUDED.credit_enc,
                consent_at = now(),
                otp_last_step = 0
            WHERE users.otp_confirmed = FALSE
            RETURNING id
        """
        params = (email, password_hash, otp_secret_enc, pii_enc, phi_enc, credit_enc)
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(sql, params).fetchone()
        if row is None:
            raise EmailAlreadyRegistered(email)
        return row[0]

    def get_user_by_email(self, email: str) -> User | None:
        sql = """SELECT id, email, password_hash, otp_secret_enc, otp_confirmed, otp_last_step
                 FROM users WHERE email = %s"""
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(sql, (email,)).fetchone()
        return User(*row) if row else None

    def confirm_otp(self, user_id: int, step: int) -> bool:
        sql = "UPDATE users SET otp_confirmed = TRUE, otp_last_step = %s WHERE id = %s AND otp_confirmed = FALSE"
        with psycopg.connect(self._dsn) as conn:
            return conn.execute(sql, (step, user_id)).rowcount == 1

    def advance_otp_step(self, user_id: int, step: int) -> bool:
        sql = "UPDATE users SET otp_last_step = %s WHERE id = %s AND otp_last_step < %s"
        with psycopg.connect(self._dsn) as conn:
            return conn.execute(sql, (step, user_id, step)).rowcount == 1

    def update_password_hash(self, user_id: int, password_hash: str) -> None:
        with psycopg.connect(self._dsn) as conn:
            conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))

    def record_attempt(self, email: str, success: bool, reason: str) -> None:
        with psycopg.connect(self._dsn) as conn:
            conn.execute(
                "INSERT INTO login_attempts (email, success, reason) VALUES (%s, %s, %s)",
                (email, success, reason),
            )

    def recent_failures(self, email: str, since: datetime, limit: int) -> list[datetime]:
        sql = """
            SELECT created_at FROM login_attempts
            WHERE email = %s AND success = FALSE AND created_at > %s
              AND created_at > COALESCE(
                    (SELECT max(created_at) FROM login_attempts WHERE email = %s AND success),
                    '-infinity')
            ORDER BY created_at DESC
            LIMIT %s
        """
        with psycopg.connect(self._dsn) as conn:
            return [r[0] for r in conn.execute(sql, (email, since, email, limit)).fetchall()]

    def list_confirmed_users(self) -> list[StoredUserData]:
        sql = """
            SELECT email, created_at, pii_enc, phi_enc, credit_enc
            FROM users
            WHERE otp_confirmed = TRUE
            ORDER BY created_at
        """
        with psycopg.connect(self._dsn) as conn:
            return [StoredUserData(*row) for row in conn.execute(sql).fetchall()]


if __name__ == "__main__":
    PostgresUserRepository(get_settings().database_url).init_schema()
    print("Esquema creado/verificado.")
