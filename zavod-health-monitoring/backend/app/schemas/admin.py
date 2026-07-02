"""
Admin uchun so'rov/javob shakllari.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    full_name: str
    login: str
    password: str
    role: str  # 'doctor' / 'manager' / 'admin'


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: int
    full_name: str
    login: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ThresholdUpdate(BaseModel):
    max_value: float


class ThresholdOut(BaseModel):
    id: int
    metric_name: str
    max_value: float
    updated_at: datetime

    class Config:
        from_attributes = True
