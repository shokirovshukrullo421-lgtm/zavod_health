"""
Shifokor uchun so'rov/javob shakllari.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AccessEventListItem(BaseModel):
    """Pending ro'yxatdagi har bir hodisa."""
    id: int
    employee_id: int
    employee_full_name: str
    department_name: str
    career_name: str
    auth_method: str
    temperature: Optional[float]
    mask_on: Optional[bool]
    scanned_at: datetime
    status: str

    # Threshold bilan solishtirib chiqilgan ogohlantirish
    temperature_warning: bool   # True bo'lsa harorat me'yordan yuqori
    temperature_threshold: float  # qanday me'yor bilan solishtirildi

    class Config:
        from_attributes = True


class ReviewRequest(BaseModel):
    """Shifokor tasdiqlash uchun yuboradigan ma'lumot."""
    decision: str           # "allowed" yoki "medical_check"
    doctor_note: Optional[str] = None


class ReviewResponse(BaseModel):
    """Tasdiqdan keyin qaytariladigan javob."""
    access_event_id: int
    status: str
    reviewed_by: str
    reviewed_at: datetime
