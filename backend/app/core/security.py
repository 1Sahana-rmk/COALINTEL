from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
from jose import jwt
import bcrypt
from config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8')[:72], hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for plaintext password."""
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt(12)
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def create_access_token(
    subject: Union[str, Any],
    role: str,
    subsidiary: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generate OAuth2 JWT bearer token with claims."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "role": role,
        "subsidiary": subsidiary,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
