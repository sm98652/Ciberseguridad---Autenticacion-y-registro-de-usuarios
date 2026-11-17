"""Lógica de registro, login (usuario + contraseña + OTP) y rate limiting.

No depende de Streamlit ni de PostgreSQL: recibe un repositorio y un reloj, por
eso se puede probar con un repositorio en memoria (ver tests/).
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Callable

from . import otp
from .config import Settings
from .export import users_to_csv
from .repository import EmailAlreadyRegistered, UserRepository
from .security import (
    DUMMY_HASH,
    DUMMY_OTP_SECRET,
    FieldCipher,
    hash_password,
    needs_rehash,
    validate_password_policy,
    verify_password,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "No sé"]


class ValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


class AuthStatus(Enum):
    OK = "ok"
    INVALID = "invalid"  # mensaje único: no revela qué factor falló
    LOCKED = "locked"  # demasiados intentos fallidos


@dataclass(frozen=True)
class AuthResult:
    status: AuthStatus
    user_id: int | None = None
    email: str | None = None
    retry_after: int = 0  # segundos, solo si LOCKED


@dataclass
class RegistrationForm:
    email: str
    password: str
    password_confirm: str
    full_name: str
    document_id: str
    birth_date: date
    phone: str
    address: str
    blood_type: str
    medical_conditions: str
    monthly_income: float
    declared_debt: float
    credit_score: int
    consent: bool


@dataclass(frozen=True)
class RegistrationResult:
    email: str
    otp_secret: str
    provisioning_uri: str


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


class AuthService:
    def __init__(
        self,
        repo: UserRepository,
        cipher: FieldCipher,
        settings: Settings,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._repo = repo
        self._cipher = cipher
        self._s = settings
        self._clock = clock


    def register(self, form: RegistrationForm) -> RegistrationResult:
        email = normalize_email(form.email)
        errors = self._validate_registration(form, email)
        if errors:
            raise ValidationError(errors)

        secret = otp.new_secret()
        pii = {
            "full_name": form.full_name.strip(),
            "document_id": form.document_id.strip(),
            "birth_date": form.birth_date.isoformat(),
            "phone": form.phone.strip(),
            "address": form.address.strip(),
        }
        phi = {
            "blood_type": form.blood_type,
            "medical_conditions": form.medical_conditions.strip(),
        }
        credit = {
            "monthly_income": form.monthly_income,
            "declared_debt": form.declared_debt,
            "credit_score": form.credit_score,
        }
        try:
            self._repo.create_user(
                email=email,
                password_hash=hash_password(form.password),
                otp_secret_enc=self._cipher.encrypt(secret),
                pii_enc=self._cipher.encrypt_json(pii),
                phi_enc=self._cipher.encrypt_json(phi),
                credit_enc=self._cipher.encrypt_json(credit),
            )
        except EmailAlreadyRegistered:
            raise ValidationError(["Este correo ya está registrado."]) from None

        return RegistrationResult(
            email=email,
            otp_secret=secret,
            provisioning_uri=otp.provisioning_uri(secret, email, self._s.issuer),
        )

    def confirm_enrollment(self, email: str, code: str) -> AuthResult:
        """Paso final del registro: el usuario demuestra que su app genera códigos válidos."""
        email = normalize_email(email)
        now = self._clock()
        remaining = self._lock_remaining(email, now)
        if remaining:
            return AuthResult(AuthStatus.LOCKED, retry_after=remaining)

        user = self._repo.get_user_by_email(email)
        step = None
        if user is not None and not user.otp_confirmed:
            step = otp.match_step(self._cipher.decrypt(user.otp_secret_enc), code, now)
        if user is None or step is None or not self._repo.confirm_otp(user.id, step):
            self._repo.record_attempt(email, False, "enrollment_failed")
            return AuthResult(AuthStatus.INVALID)

        self._repo.record_attempt(email, True, "enrollment_ok")
        return AuthResult(AuthStatus.OK, user_id=user.id, email=email)


    def authenticate(self, email: str, password: str, code: str) -> AuthResult:
        email = normalize_email(email)
        now = self._clock()

        remaining = self._lock_remaining(email, now)
        if remaining:  # no se evalúa nada ni se registra: el bloqueo no se "extiende"
            return AuthResult(AuthStatus.LOCKED, retry_after=remaining)

        user = self._repo.get_user_by_email(email)

        # Se evalúan SIEMPRE los tres factores (con señuelos si el usuario no existe)
        # para que el tiempo de respuesta no delate cuál falló.
        password_ok = verify_password(user.password_hash if user else DUMMY_HASH, password or "")
        secret = self._cipher.decrypt(user.otp_secret_enc) if user else DUMMY_OTP_SECRET
        step = otp.match_step(secret, code, now)

        reasons: list[str] = []
        if user is None:
            reasons.append("unknown_user")
        else:
            if not password_ok:
                reasons.append("bad_password")
            if step is None:
                reasons.append("bad_otp")
            if not user.otp_confirmed:
                reasons.append("otp_not_confirmed")
            # El paso OTP solo se "gasta" si usuario y contraseña ya son correctos.
            if not reasons and not self._repo.advance_otp_step(user.id, step):
                reasons.append("otp_replay")

        if reasons:
            self._repo.record_attempt(email, False, "+".join(reasons))
            return AuthResult(AuthStatus.INVALID)

        if needs_rehash(user.password_hash):
            self._repo.update_password_hash(user.id, hash_password(password))
        self._repo.record_attempt(email, True, "ok")
        return AuthResult(AuthStatus.OK, user_id=user.id, email=email)


    def export_users_csv(self, requested_by: str) -> bytes:
        """CSV con los datos descifrados de las cuentas confirmadas. Solo administradores.

        El permiso se valida aquí además de en la página, para que ninguna otra
        pantalla pueda llamar esta función y saltarse el control.
        """
        if normalize_email(requested_by) not in self._s.admin_emails:
            raise PermissionError("Solo un administrador puede exportar los usuarios.")
        rows = []
        for user in self._repo.list_confirmed_users():
            row: dict[str, object] = {}
            for blob in (user.pii_enc, user.phi_enc, user.credit_enc):
                row.update(self._cipher.decrypt_json(blob))
            row["email"] = user.email
            row["created_at"] = user.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
            rows.append(row)
        return users_to_csv(rows)

    def _lock_remaining(self, email: str, now: float) -> int:
        """Segundos que faltan para poder reintentar (0 si no está bloqueado)."""
        window = self._s.lockout_minutes * 60
        since = datetime.fromtimestamp(now - window, tz=timezone.utc)
        failures = self._repo.recent_failures(email, since, self._s.max_failed_attempts)
        if len(failures) < self._s.max_failed_attempts:
            return 0
        # El bloqueo termina cuando el fallo más antiguo de los contados sale de la ventana.
        return max(1, math.ceil(failures[-1].timestamp() + window - now))

    def _validate_registration(self, f: RegistrationForm, email: str) -> list[str]:
        errors: list[str] = []
        today = datetime.fromtimestamp(self._clock(), tz=timezone.utc).date()

        if not _EMAIL_RE.match(email) or len(email) > 254:
            errors.append("Correo electrónico inválido.")
        errors += validate_password_policy(f.password, email)
        if f.password != f.password_confirm:
            errors.append("Las contraseñas no coinciden.")

        if not f.full_name.strip() or len(f.full_name) > 120:
            errors.append("Ingresa tu nombre completo (máx. 120 caracteres).")
        if not re.fullmatch(r"[A-Za-z0-9]{5,20}", f.document_id.strip()):
            errors.append("Documento de identidad inválido (5 a 20 letras o números).")
        phone_digits = re.sub(r"[\s\-+()]", "", f.phone)
        if not (phone_digits.isdigit() and 7 <= len(phone_digits) <= 15):
            errors.append("Teléfono inválido.")
        if not f.address.strip() or len(f.address) > 200:
            errors.append("Ingresa tu dirección (máx. 200 caracteres).")

        age = today.year - f.birth_date.year - ((today.month, today.day) < (f.birth_date.month, f.birth_date.day))
        if age < 18:
            errors.append("Debes ser mayor de edad para registrarte.")
        if f.blood_type not in BLOOD_TYPES:
            errors.append("Tipo de sangre inválido.")
        if len(f.medical_conditions) > 500:
            errors.append("Condiciones médicas: máximo 500 caracteres.")
        if f.monthly_income < 0 or f.declared_debt < 0:
            errors.append("Ingresos y deudas no pueden ser negativos.")
        if not 0 <= f.credit_score <= 1000:
            errors.append("El puntaje crediticio debe estar entre 0 y 1000.")
        if not f.consent:
            errors.append("Debes autorizar el tratamiento de tus datos personales.")
        return errors
