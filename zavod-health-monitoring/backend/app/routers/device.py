"""
Qurilma endpoint'i.

Dahua qurilma xodimni taniganda shu endpoint'ga POST so'rov yuboradi.
Backend:
  1. device_code orqali qurilmani topadi
  2. employee_id orqali xodimni tekshiradi (bazada bormi, activmi)
  3. access_events jadvaliga status='pending' bilan yozuv yaratadi
  4. Qurilmaga tasdiqlash javobi qaytaradi
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.access_event import AccessEvent
from app.models.device import Device
from app.models.employee import Employee
from app.schemas.device import DeviceEventIn, DeviceEventOut

router = APIRouter(prefix="/device", tags=["Qurilma"])


@router.post("/event", response_model=DeviceEventOut)
def receive_device_event(data: DeviceEventIn, db: Session = Depends(get_db)):
    """
    Dahua qurilmasidan kirish hodisasini qabul qilish.
    Hozircha himoyasiz — keyinroq API key qo'shiladi.
    """

    # 1. Qurilmani topish
    device = db.query(Device).filter(Device.device_code == data.device_code).first()
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Qurilma topilmadi: {data.device_code}",
        )

    # 2. Xodimni tekshirish
    employee = db.query(Employee).filter(
        Employee.id == data.employee_id,
        Employee.is_active == True,
    ).first()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Xodim topilmadi yoki faol emas: ID {data.employee_id}",
        )

    # 3. Kirish hodisasini yozish (status='pending' — shifokor tasdiqlaguncha)
    event = AccessEvent(
        employee_id=data.employee_id,
        device_id=device.id,
        auth_method=data.auth_method,
        temperature=data.temperature,
        mask_on=data.mask_on,
        scanned_at=data.scanned_at or datetime.utcnow(),
        status="pending",
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return DeviceEventOut(
        access_event_id=event.id,
        status="pending",
        message="Hodisa qayd etildi. Shifokor tasdig'i kutilmoqda.",
    )
