import os
import hashlib
import secrets
import base64
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from cryptography.hazmat.primitives.ciphers.aead import AESSIV
import bcrypt
from dotenv import load_dotenv

load_dotenv()
JWT_SECRET                 = os.getenv("JWT_SECRET")
JWT_ALGORITHM              = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_EXPIRE_DAYS        = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
RESET_EXPIRE_HOURS         = int(os.getenv("RESET_TOKEN_EXPIRE_HOURS", "1"))


def _derive_siv_key(env_var_name: str) -> bytes:
    raw = os.getenv(env_var_name, "")
    if not raw:
        raise RuntimeError(f"{env_var_name} is not set in environment")
    return hashlib.sha512(raw.encode("utf-8")).digest()   # → 64 bytes

ENC_KEY = _derive_siv_key("ENCRYPTION_KEY")

def encrypt_field(plaintext: str) -> bytes:
    siv = AESSIV(ENC_KEY)
    return siv.encrypt(plaintext.lower().encode("utf-8"), [])

def decrypt_field(ciphertext: bytes) -> str:
    siv = AESSIV(ENC_KEY)
    return siv.decrypt(bytes(ciphertext), []).decode("utf-8")

def encrypt_for_search(plaintext: str) -> bytes:
    return encrypt_field(plaintext)

#Password hashin
def hash_password(plain: str) -> str:
    prehash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    salt    = bcrypt.gensalt(rounds=12)
    hashed  = bcrypt.hashpw(prehash.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    prehash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    return bcrypt.checkpw(prehash.encode("utf-8"), hashed.encode("utf-8"))

#JWT
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire    = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


#Reset token

def generate_reset_token() -> tuple[str, str]:
    raw        = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


def hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


#Refresh token

def generate_refresh_token() -> tuple[str, str]:
    raw        = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()