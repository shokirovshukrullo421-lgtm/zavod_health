"""
Joriy foydalanuvchini aniqlash va rolga asoslangan ruxsat berish.

Ishlatilishi:
    @router.get("/something")
    def endpoint(user: User = Depends(get_current_user)):
        ...

    @router.post("/admin-only")
    def endpoint(user: User = Depends(require_role("admin"))):
        ...
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.jwt import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Token ichidan foydalanuvchini topadi. Token noto'g'ri bo'lsa 401 qaytaradi."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Avtorizatsiyadan o'tilmagan yoki token yaroqsiz",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_error

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_error

    return user


def require_role(*allowed_roles: str):
    """Faqat ko'rsatilgan rol(lar)ga ruxsat beradigan dependency yaratadi."""

    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bu amal uchun ruxsatingiz yo'q (kerakli rol: {', '.join(allowed_roles)})",
            )
        return user

    return role_checker
