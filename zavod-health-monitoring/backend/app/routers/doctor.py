"""
Shifokor endpoint'lari.

Faqat 'doctor' rolidagi foydalanuvchilar uchun.
"""
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_role
from app.models.user import User
from app.models.access_event import AccessEvent
from app.models.employee import Employee, EmployeeDepartment
from app.models.organization import Department, Career
from app.models.device import Device
from app.models.misc import Threshold
from app.schemas.doctor import AccessEventListItem, ReviewRequest, ReviewResponse

router = APIRouter(prefix="/doctor", tags=["Shifokor"])


def _get_temperature_threshold(db: Session) -> float:
    """Bazadan harorat chegarasini oladi. Topilmasa 37.0 qaytaradi."""
    threshold = db.query(Threshold).filter(
        Threshold.metric_name == "temperature"
    ).first()
    return float(threshold.max_value) if threshold else 37.0


@router.get("/pending", response_model=list[AccessEventListItem])
def get_pending_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
):
    """
    Bugun kelgan, hali shifokor tasdiqlamagan hodisalar ro'yxati.
    Har bir hodisada harorat threshold bilan solishtirilgan ogohlantirish ham ko'rsatiladi.
    """
    temp_threshold = _get_temperature_threshold(db)
    today = date.today()

    events = (
        db.query(AccessEvent)
        .filter(
            AccessEvent.status == "pending",
        )
        .order_by(AccessEvent.scanned_at.desc())
        .all()
    )

    result = []
    for event in events:
        # Xodim ma'lumotlarini olish
        employee = db.query(Employee).filter(Employee.id == event.employee_id).first()

        # Xodimning bo'limi va karyerini topish (birinchi tayinlanganini olamiz)
        emp_dept = (
            db.query(EmployeeDepartment)
            .filter(EmployeeDepartment.employee_id == event.employee_id)
            .first()
        )
        department_name = "—"
        career_name = "—"
        if emp_dept:
            dept = db.query(Department).filter(Department.id == emp_dept.department_id).first()
            if dept:
                department_name = dept.name
                career = db.query(Career).filter(Career.id == dept.career_id).first()
                if career:
                    career_name = career.name

        result.append(AccessEventListItem(
            id=event.id,
            employee_id=event.employee_id,
            employee_full_name=f"{employee.first_name} {employee.last_name}" if employee else "—",
            department_name=department_name,
            career_name=career_name,
            auth_method=event.auth_method,
            temperature=float(event.temperature) if event.temperature is not None else None,
            mask_on=event.mask_on,
            scanned_at=event.scanned_at,
            status=event.status,
            temperature_warning=(
                float(event.temperature) > temp_threshold
                if event.temperature is not None else False
            ),
            temperature_threshold=temp_threshold,
        ))

    return result


@router.post("/review/{event_id}", response_model=ReviewResponse)
def review_event(
    event_id: int,
    data: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor")),
):
    """
    Shifokor hodisaga qaror qo'yadi: 'allowed' yoki 'medical_check'.
    """
    # Qaror to'g'riligini tekshirish
    if data.decision not in ("allowed", "medical_check"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Qaror faqat 'allowed' yoki 'medical_check' bo'lishi mumkin",
        )

    # Hodisani topish
    event = db.query(AccessEvent).filter(AccessEvent.id == event_id).first()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hodisa topilmadi: ID {event_id}",
        )

    # Allaqachon tasdiqlanganmi
    if event.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bu hodisa allaqachon ko'rib chiqilgan: {event.status}",
        )

    # Qarorni yozish
    event.status = data.decision
    event.reviewed_by = current_user.id
    event.reviewed_at = datetime.utcnow()
    event.doctor_note = data.doctor_note

    db.commit()
    db.refresh(event)

    return ReviewResponse(
        access_event_id=event.id,
        status=event.status,
        reviewed_by=current_user.full_name,
        reviewed_at=event.reviewed_at,
    )
