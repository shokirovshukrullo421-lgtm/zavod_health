"""
Login endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password
from app.core.jwt import create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autentifikatsiya"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login == data.login).first()

    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu hisob faol emas",
        )

    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(access_token=token, role=user.role, full_name=user.full_name)
