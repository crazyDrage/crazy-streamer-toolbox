import hashlib
import hmac
import secrets


class PasswordHash:
    """A password kept as a salted PBKDF2 hash, "pbkdf2_sha256$<rounds>$<salt>$<hash>", never as the text itself."""

    ROUNDS = 300_000

    @classmethod
    def make(cls, password: str) -> str:
        if not password:
            raise ValueError("the password is empty")
        salt = secrets.token_hex(16)
        return f"pbkdf2_sha256${cls.ROUNDS}${salt}${cls._hash(password, salt, cls.ROUNDS)}"

    @classmethod
    def verify(cls, stored: str, password: str) -> bool:
        try:
            kind, rounds, salt, expected = stored.split("$")
        except (AttributeError, ValueError):
            return False
        if kind != "pbkdf2_sha256" or not password:
            return False
        return hmac.compare_digest(cls._hash(password, salt, int(rounds)), expected)

    @staticmethod
    def _hash(password: str, salt: str, rounds: int) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), rounds).hex()
