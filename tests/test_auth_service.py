import itertools
import unittest
from datetime import date

import pyotp
from cryptography.fernet import Fernet

from tests.fakes import FakeRepo
from web_app.auth_service import (
    AuthService,
    AuthStatus,
    RegistrationForm,
    ValidationError,
)
from web_app.config import Settings
from web_app.security import FieldCipher

PASSWORD = "Clave-Segura-2026!"
EMAIL = "ana@mail.com"
T0 = 1_800_000_015.0


class Clock:
    def __init__(self, now=T0):
        self.now = now

    def __call__(self):
        return self.now


def make_form(**over):
    data = dict(
        email=EMAIL, password=PASSWORD, password_confirm=PASSWORD, full_name="Ana Pérez",
        document_id="1020304050", birth_date=date(1990, 5, 17), phone="+57 300 123 4567",
        address="Calle 1 # 2-3", blood_type="O+", medical_conditions="Alergia a la penicilina",
        monthly_income=3_000_000.0, declared_debt=500_000.0, credit_score=720, consent=True,
    )
    data.update(over)
    return RegistrationForm(**data)


class AuthServiceBase(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.repo = FakeRepo(self.clock)
        self.settings = Settings(database_url="x", encryption_keys="x", max_failed_attempts=5, lockout_minutes=15)
        self.cipher = FieldCipher(Fernet.generate_key().decode())
        self.svc = AuthService(self.repo, self.cipher, self.settings, clock=self.clock)

    def code(self, secret, offset=0):
        return pyotp.TOTP(secret).at(int(self.clock.now) + 30 * offset)

    def register_active(self):
        reg = self.svc.register(make_form())
        res = self.svc.confirm_enrollment(EMAIL, self.code(reg.otp_secret))
        self.assertIs(res.status, AuthStatus.OK)
        self.clock.now += 30  # el siguiente código será de un paso nuevo
        return reg.otp_secret


class RegistrationTest(AuthServiceBase):
    def test_sensitive_data_is_not_stored_in_plaintext(self):
        self.svc.register(make_form())
        row = self.repo.users[EMAIL]
        blob = " ".join(str(v) for v in row.values())
        for secret in ["1020304050", "Ana Pérez", "penicilina", "3000000", "300 123", PASSWORD]:
            self.assertNotIn(secret, blob)
        self.assertEqual(self.cipher.decrypt_json(row["pii_enc"])["document_id"], "1020304050")

    def test_invalid_data_is_rejected(self):
        for over in [
            dict(password="corta", password_confirm="corta"),
            dict(password_confirm="Otra-Clave-2026!"),
            dict(email="no-es-correo"),
            dict(birth_date=date(2020, 1, 1)),
            dict(credit_score=5000),
            dict(consent=False),
        ]:
            with self.assertRaises(ValidationError, msg=over):
                self.svc.register(make_form(**over))
        self.assertEqual(self.repo.users, {})

    def test_duplicate_confirmed_email_rejected_but_pending_can_retry(self):
        self.svc.register(make_form())
        self.svc.register(make_form())  # pendiente: se reemplaza
        reg = self.svc.register(make_form())
        self.svc.confirm_enrollment(EMAIL, self.code(reg.otp_secret))
        with self.assertRaises(ValidationError):
            self.svc.register(make_form())

    def test_enrollment_wrong_code(self):
        reg = self.svc.register(make_form())
        bad = "000000" if self.code(reg.otp_secret) != "000000" else "111111"
        self.assertIs(self.svc.confirm_enrollment(EMAIL, bad).status, AuthStatus.INVALID)
        self.assertFalse(self.repo.users[EMAIL]["otp_confirmed"])


class LoginCasesTest(AuthServiceBase):
    """Las 8 combinaciones de (usuario, contraseña, OTP) correctos/incorrectos."""

    def test_only_all_correct_succeeds(self):
        secret = self.register_active()
        for user_ok, pw_ok, otp_ok in itertools.product([True, False], repeat=3):
            with self.subTest(user=user_ok, password=pw_ok, otp=otp_ok):
                self.repo.attempts.clear()  # aislar del rate limit
                self.clock.now += 30
                email = EMAIL if user_ok else "otra@mail.com"
                password = PASSWORD if pw_ok else "Incorrecta-2026!"
                code = self.code(secret) if otp_ok else "000000"
                res = self.svc.authenticate(email, password, code)
                if user_ok and pw_ok and otp_ok:
                    self.assertIs(res.status, AuthStatus.OK)
                else:
                    self.assertIs(res.status, AuthStatus.INVALID)  # mismo resultado siempre
                    self.assertFalse(self.repo.attempts[-1]["success"])

    def test_failure_reasons_are_logged_internally(self):
        secret = self.register_active()
        self.svc.authenticate("otra@mail.com", PASSWORD, "000000")
        self.svc.authenticate(EMAIL, "Incorrecta-2026!", self.code(secret))
        self.svc.authenticate(EMAIL, PASSWORD, "000000")
        self.svc.authenticate(EMAIL, "Incorrecta-2026!", "000000")
        self.assertEqual(
            [a["reason"] for a in self.repo.attempts[-4:]],
            ["unknown_user", "bad_password", "bad_otp", "bad_password+bad_otp"],
        )

    def test_otp_cannot_be_reused(self):
        secret = self.register_active()
        code = self.code(secret)
        self.assertIs(self.svc.authenticate(EMAIL, PASSWORD, code).status, AuthStatus.OK)
        res = self.svc.authenticate(EMAIL, PASSWORD, code)
        self.assertIs(res.status, AuthStatus.INVALID)
        self.assertEqual(self.repo.attempts[-1]["reason"], "otp_replay")

    def test_otp_not_burned_when_password_is_wrong(self):
        secret = self.register_active()
        code = self.code(secret)
        self.svc.authenticate(EMAIL, "Incorrecta-2026!", code)
        self.assertIs(self.svc.authenticate(EMAIL, PASSWORD, code).status, AuthStatus.OK)

    def test_clock_drift_of_one_step_is_accepted_two_is_not(self):
        secret = self.register_active()
        self.assertIs(self.svc.authenticate(EMAIL, PASSWORD, self.code(secret, +1)).status, AuthStatus.OK)
        self.clock.now += 120
        self.assertIs(self.svc.authenticate(EMAIL, PASSWORD, self.code(secret, +3)).status, AuthStatus.INVALID)

    def test_unconfirmed_account_cannot_login(self):
        reg = self.svc.register(make_form())
        res = self.svc.authenticate(EMAIL, PASSWORD, self.code(reg.otp_secret))
        self.assertIs(res.status, AuthStatus.INVALID)
        self.assertIn("otp_not_confirmed", self.repo.attempts[-1]["reason"])


class RateLimitTest(AuthServiceBase):
    def fail_n(self, n, email=EMAIL):
        for _ in range(n):
            self.svc.authenticate(email, "Incorrecta-2026!", "000000")
            self.clock.now += 1

    def test_locks_after_max_failures_even_with_correct_credentials(self):
        secret = self.register_active()
        self.fail_n(5)
        res = self.svc.authenticate(EMAIL, PASSWORD, self.code(secret))
        self.assertIs(res.status, AuthStatus.LOCKED)
        self.assertGreater(res.retry_after, 0)

    def test_lock_does_not_extend_while_locked(self):
        self.register_active()
        self.fail_n(5)
        n = len(self.repo.attempts)
        self.svc.authenticate(EMAIL, PASSWORD, "000000")
        self.assertEqual(len(self.repo.attempts), n)

    def test_unlocks_after_window(self):
        secret = self.register_active()
        self.fail_n(5)
        self.clock.now += 15 * 60
        self.assertIs(self.svc.authenticate(EMAIL, PASSWORD, self.code(secret)).status, AuthStatus.OK)

    def test_four_failures_do_not_lock(self):
        secret = self.register_active()
        self.fail_n(4)
        self.assertIs(self.svc.authenticate(EMAIL, PASSWORD, self.code(secret)).status, AuthStatus.OK)

    def test_unknown_email_is_rate_limited_the_same_way(self):
        self.fail_n(5, email="fantasma@mail.com")
        res = self.svc.authenticate("fantasma@mail.com", PASSWORD, "123456")
        self.assertIs(res.status, AuthStatus.LOCKED)

    def test_success_resets_counter(self):
        secret = self.register_active()
        self.fail_n(4)
        self.assertIs(self.svc.authenticate(EMAIL, PASSWORD, self.code(secret)).status, AuthStatus.OK)
        self.clock.now += 30
        self.fail_n(4)
        self.clock.now += 30
        self.assertIs(self.svc.authenticate(EMAIL, PASSWORD, self.code(secret)).status, AuthStatus.OK)

    def test_enrollment_attempts_are_limited_too(self):
        reg = self.svc.register(make_form())
        for _ in range(5):
            self.svc.confirm_enrollment(EMAIL, "000000")
        res = self.svc.confirm_enrollment(EMAIL, self.code(reg.otp_secret))
        self.assertIs(res.status, AuthStatus.LOCKED)
