"""
Admin endpoint'lari.
Faqat 'admin' rolidagi foydalanuvchilar uchun.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_role
from app.core.security import hash_password
from app.models.user import User
from app.models.misc import Threshold
from app.schemas.admin import UserCreate, UserUpdate, UserOut, ThresholdUpdate, ThresholdOut

router = APIRouter(prefix="/admin", tags=["Admin"])

VALID_ROLES = ("doctor", "manager", "admin")


# ── Foydalanuvchilar ────────────────────────────────────────────

@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Barcha foydalanuvchilar ro'yxati."""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Yangi foydalanuvchi yaratish."""
    if data.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Noto'g'ri rol. Ruxsat etilgan: {', '.join(VALID_ROLES)}",
        )

    # Login takrorlanmasligini tekshirish
    existing = db.query(User).filter(User.login == data.login).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{data.login}' login allaqachon mavjud",
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parol kamida 6 ta belgidan iborat bo'lishi kerak",
        )

    user = User(
        full_name=data.full_name,
        login=data.login,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Foydalanuvchi ma'lumotlarini tahrirlash."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Foydalanuvchi topilmadi: ID {user_id}",
        )

    # O'zini o'chirib qo'yishining oldini olish
    if data.is_active is False and user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O'zingizni o'chirib qo'ya olmaysiz",
        )

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        if data.role not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Noto'g'ri rol: {data.role}",
            )
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password is not None:
        if len(data.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parol kamida 6 ta belgidan iborat bo'lishi kerak",
            )
        user.password_hash = hash_password(data.password)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Foydalanuvchini o'chirish."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O'zingizni o'chira olmaysiz",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Foydalanuvchi topilmadi: ID {user_id}",
        )

    db.delete(user)
    db.commit()


# ── Threshold (me'yor qiymatlari) ──────────────────────────────

@router.get("/thresholds", response_model=list[ThresholdOut])
def list_thresholds(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Barcha me'yor qiymatlari."""
    return db.query(Threshold).all()


@router.put("/thresholds/{metric_name}", response_model=ThresholdOut)
def update_threshold(
    metric_name: str,
    data: ThresholdUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Me'yor qiymatini yangilash (masalan harorat chegarasi)."""
    threshold = db.query(Threshold).filter(
        Threshold.metric_name == metric_name
    ).first()

    if threshold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Me'yor topilmadi: {metric_name}",
        )

    if data.max_value <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Me'yor qiymati musbat bo'lishi kerak",
        )

    threshold.max_value = data.max_value
    threshold.updated_by = current_user.id
    threshold.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(threshold)
    return threshold
