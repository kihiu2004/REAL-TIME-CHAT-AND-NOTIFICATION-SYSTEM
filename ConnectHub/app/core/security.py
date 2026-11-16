import bcrypt

from app.config import settings

# bcrypt only considers the first 72 bytes of a password
MAX_PASSWORD_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:MAX_PASSWORD_BYTES]


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(_password_bytes(password), salt).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Check a plain-text password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            _password_bytes(password),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        # Malformed hash in the database: treat as a failed login
        return False
