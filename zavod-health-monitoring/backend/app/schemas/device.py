"""
Dahua qurilmasidan keladigan ma'lumot shakli (Pydantic).
"""
from pydantic import BaseModel
from datetime import datetime


class DeviceEventIn(BaseModel):
    """
    Qurilma backend'ga shu formatda ma'lumot yuboradi.
    
    Misol:
    {
        "device_code": "DHI-001",
        "employee_id": 42,
        "auth_method": "face",
        "temperature": 36.6,
        "mask_on": true,
        "scanned_at": "2024-01-15T08:03:21"
    }
    """
    device_code: str           # qurilmaning o'z kodi (devices.device_code bilan mos keladi)
    employee_id: int           # bazadagi xodim ID si
    auth_method: str           # "face" yoki "fingerprint"
    temperature: float | None  # harorat (°C)
    mask_on: bool | None       # niqob bormi
    scanned_at: datetime | None = None  # agar None bo'lsa, server vaqti ishlatiladi


class DeviceEventOut(BaseModel):
    """Backend qurilmaga javob qaytaradi."""
    access_event_id: int
    status: str        # "pending" — shifokor tasdiqlaguncha
    message: str
