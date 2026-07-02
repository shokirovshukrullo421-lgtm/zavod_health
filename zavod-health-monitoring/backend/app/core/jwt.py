"""
JWT token yaratish va tekshirish.
"""
from datetime import datetime, timedelta
from jose import jwt, JWTError

from app.core.config import settings


def create_access_token(user_id: int, role: str) -> str:
    """Login muvaffaqiyatli bo'lganda chaqiriladi, JWT token qaytaradi."""
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    """Token ichidagi ma'lumotni o'qiydi. Noto'g'ri/eskirgan bo'lsa None qaytaradi."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
