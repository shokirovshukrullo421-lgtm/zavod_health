"""
Bo'lim mas'uli uchun so'rov/javob shakllari (xodim CRUD).
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EmployeeCreate(BaseModel):
    """Yangi xodim qo'shish."""
    first_name: str
    last_name: str
    position: Optional[str] = None
    department_ids: list[int]   # bir nechta bo'limga tayinlash mumkin


class EmployeeUpdate(BaseModel):
    """Xodim ma'lumotlarini tahrirlash (faqat yuborilgan maydonlar o'zgaradi)."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    department_ids: Optional[list[int]] = None


class EmployeeOut(BaseModel):
    """Xodim ma'lumotlari javobi."""
    id: int
    first_name: str
    last_name: str
    position: Optional[str]
    is_active: bool
    departments: list[str]   # bo'lim nomlari ro'yxati
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
