"""Repositorio en memoria para probar AuthService sin base de datos."""

from datetime import datetime, timezone

from web_app.repository import EmailAlreadyRegistered, User


class FakeRepo:
    def __init__(self, clock):
        self._clock = clock
        self.users: dict[str, dict] = {}
        self.attempts: list[dict] = []
        self._next_id = 1

    def _now(self):
        return datetime.fromtimestamp(self._clock(), tz=timezone.utc)

    def create_user(self, *, email, password_hash, otp_secret_enc, pii_enc, phi_enc, credit_enc):
        existing = self.users.get(email)
        if existing and existing["otp_confirmed"]:
            raise EmailAlreadyRegistered(email)
        uid = existing["id"] if existing else self._next_id
        if not existing:
            self._next_id += 1
        self.users[email] = dict(
            id=uid, email=email, password_hash=password_hash, otp_secret_enc=otp_secret_enc,
            otp_confirmed=False, otp_last_step=0, pii_enc=pii_enc, phi_enc=phi_enc, credit_enc=credit_enc,
        )
        return uid

    def get_user_by_email(self, email):
        u = self.users.get(email)
        return User(u["id"], u["email"], u["password_hash"], u["otp_secret_enc"],
                    u["otp_confirmed"], u["otp_last_step"]) if u else None

    def _by_id(self, user_id):
        return next(u for u in self.users.values() if u["id"] == user_id)

    def confirm_otp(self, user_id, step):
        u = self._by_id(user_id)
        if u["otp_confirmed"]:
            return False
        u["otp_confirmed"], u["otp_last_step"] = True, step
        return True

    def advance_otp_step(self, user_id, step):
        u = self._by_id(user_id)
        if u["otp_last_step"] < step:
            u["otp_last_step"] = step
            return True
        return False

    def update_password_hash(self, user_id, password_hash):
        self._by_id(user_id)["password_hash"] = password_hash

    def record_attempt(self, email, success, reason):
        self.attempts.append(dict(email=email, success=success, reason=reason, at=self._now()))

    def recent_failures(self, email, since, limit):
        mine = [a for a in self.attempts if a["email"] == email]
        last_ok = max((a["at"] for a in mine if a["success"]), default=None)
        fails = [a["at"] for a in mine if not a["success"] and a["at"] > since
                 and (last_ok is None or a["at"] > last_ok)]
        return sorted(fails, reverse=True)[:limit]
