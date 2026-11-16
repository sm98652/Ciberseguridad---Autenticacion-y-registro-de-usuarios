import unittest

from cryptography.fernet import Fernet, InvalidToken

from web_app.security import (
    FieldCipher,
    hash_password,
    validate_password_policy,
    verify_password,
)


class PasswordPolicyTest(unittest.TestCase):
    def test_valid_password(self):
        self.assertEqual(validate_password_policy("Clave-Segura-2026!", "ana@mail.com"), [])

    def test_each_rule_is_enforced(self):
        cases = {
            "Ab1!": "al menos",
            "clave-segura-2026!": "mayúscula",
            "CLAVE-SEGURA-2026!": "minúscula",
            "Clave-Segura-Aqui!": "número",
            "ClaveSegura20260": "símbolo",
            "Ana.Perez-2026!x": "correo",
            "x" * 129: "superar",
        }
        for password, fragment in cases.items():
            errors = validate_password_policy(password, "ana.perez@mail.com")
            self.assertTrue(any(fragment in e for e in errors), (password, errors))

    def test_hash_roundtrip_and_never_plaintext(self):
        h = hash_password("Clave-Segura-2026!")
        self.assertNotIn("Clave-Segura", h)
        self.assertTrue(verify_password(h, "Clave-Segura-2026!"))
        self.assertFalse(verify_password(h, "otra"))
        self.assertFalse(verify_password("no-es-un-hash", "x"))


class FieldCipherTest(unittest.TestCase):
    def test_roundtrip(self):
        c = FieldCipher(Fernet.generate_key().decode())
        token = c.encrypt_json({"documento": "123456789"})
        self.assertNotIn("123456789", token)
        self.assertEqual(c.decrypt_json(token), {"documento": "123456789"})

    def test_wrong_key_fails(self):
        token = FieldCipher(Fernet.generate_key().decode()).encrypt("secreto")
        with self.assertRaises(InvalidToken):
            FieldCipher(Fernet.generate_key().decode()).decrypt(token)

    def test_key_rotation(self):
        old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        token = FieldCipher(old).encrypt("dato")
        self.assertEqual(FieldCipher(f"{new},{old}").decrypt(token), "dato")
