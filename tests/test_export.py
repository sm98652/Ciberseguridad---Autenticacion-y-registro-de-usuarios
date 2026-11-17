import csv
import io

from web_app.export import COLUMNS, users_to_csv


def _read(data: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))


def test_header_and_row():
    rows = _read(users_to_csv([{"email": "ana@correo.com", "full_name": "Ana Peña", "credit_score": 700}]))
    assert rows[0] == [header for _, header in COLUMNS]
    assert rows[1][0] == "ana@correo.com"
    assert "Ana Peña" in rows[1]
    assert "700" in rows[1]


def test_formula_injection_is_neutralized():
    rows = _read(users_to_csv([{"email": "x@y.co", "full_name": "=HYPERLINK(\"http://malo\")"}]))
    assert rows[1][2].startswith("'=")


def test_negative_numbers_are_not_escaped():
    rows = _read(users_to_csv([{"email": "x@y.co", "declared_debt": -5.0}]))
    assert rows[1][10] == "-5"


def test_never_exports_secrets():
    data = users_to_csv([{"email": "x@y.co", "password_hash": "$argon2id$...", "otp_secret": "ABC"}])
    assert b"argon2" not in data and b"ABC" not in data
