import os
import hmac
import hashlib
import secrets
import base64
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import bcrypt
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
RESET_EXPIRE_HOURS = int(os.getenv("RESET_TOKEN_EXPIRE_HOURS", "1"))

def _derive_key(env_var_name: str) -> bytes:
    raw = os.getenv(env_var_name, "")
    if not raw:
        raise RuntimeError(f"{env_var_name} is not set in environment")
    return hashlib.sha256(raw.encode("utf-8")).digest() 

ENC_KEY = _derive_key("ENCRYPTION_KEY")
HMAC_KEY = _derive_key("HMAC_KEY")

def hash_password(plain: str) -> str:
    prehash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    password_bytes = prehash.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    prehash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    return bcrypt.checkpw(prehash.encode("utf-8"), hashed.encode("utf-8"))

def _get_iv(plaintext: str) -> bytes:
    hm = hmac.new(HMAC_KEY, plaintext.lower().encode(), hashlib.sha256).digest()
    return hm[:12]

def generate_reset_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash

def hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

def create_access_token(data: dict,expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode,JWT_SECRET,algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    

def generate_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash

def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def encrypt_field(plaintext: str) -> bytes:
    aesgcm = AESGCM(ENC_KEY)
    iv = _get_iv(plaintext)
    ct = aesgcm.encrypt(iv, plaintext.encode(), None)
    return base64.b64encode(iv + ct)

def decrypt_field(ciphertext: bytes) -> str:
    data = base64.b64decode(ciphertext)
    iv, ct = data[:12], data[12:]
    aesgcm = AESGCM(ENC_KEY)
    return aesgcm.decrypt(iv, ct, None).decode()

def compute_hmac(plaintext: str) -> str:
    return hmac.new(HMAC_KEY, plaintext.lower().encode(), hashlib.sha256).hexdigest()

    

