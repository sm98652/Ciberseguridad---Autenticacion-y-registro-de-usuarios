"""TOTP con pyotp: ventana de tolerancia pequeña y detección de reutilización."""

from __future__ import annotations

import hmac
import time

import pyotp

DIGITS = 6
INTERVAL = 30  # segundos
WINDOW = 1  # acepta el paso anterior y el siguiente (deriva de reloj de ±30 s)


def new_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str, issuer: str) -> str:
    return pyotp.TOTP(secret, digits=DIGITS, interval=INTERVAL).provisioning_uri(
        name=email, issuer_name=issuer
    )


def match_step(secret: str, code: str, now: float | None = None) -> int | None:
    """Devuelve el paso (time step) al que corresponde `code`, o None si no coincide.

    No toca la base de datos: quien llama debe registrar el paso usado y rechazar
    cualquier código con paso <= al último aceptado (anti-replay).
    """
    code = (code or "").strip().replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    now = time.time() if now is None else now
    totp = pyotp.TOTP(secret, digits=DIGITS, interval=INTERVAL)
    current = int(now // INTERVAL)
    matched: int | None = None
    for step in range(current - WINDOW, current + WINDOW + 1):
        # compare_digest + sin salida anticipada: tiempo constante respecto al código
        if hmac.compare_digest(totp.generate_otp(step), code):
            matched = step
    return matched
