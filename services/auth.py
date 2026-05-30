import base64
import hashlib
import hmac
import json
import os
import time

_SECRET = os.getenv("JWT_SECRET", "noteai-dev-secret-change-in-production")
_TOKEN_EXPIRE_DAYS = 30


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * pad)


def create_token(user_id: int, email: str) -> str:
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64encode(json.dumps({
        "sub": user_id,
        "email": email,
        "exp": int(time.time()) + _TOKEN_EXPIRE_DAYS * 86400,
    }).encode())
    sig = _b64encode(hmac.new(
        _SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256
    ).digest())
    return f"{header}.{payload}.{sig}"


def verify_token(token: str) -> dict:
    try:
        header, payload, sig = token.split(".")
        expected = _b64encode(hmac.new(
            _SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256
        ).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        data = json.loads(_b64decode(payload))
        if data.get("exp", 0) < time.time():
            raise ValueError("token expired")
        return data
    except Exception:
        raise ValueError("Invalid or expired token")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return salt.hex() + ":" + dk.hex()


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt_hex, dk_hex = hashed.split(":")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False
