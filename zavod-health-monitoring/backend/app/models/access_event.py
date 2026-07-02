"""
Kirish hodisalari — asosiy jarayon.

Oqim:
  1. Qurilma xodimni taniydi -> status='pending' bilan yozuv yaratiladi
  2. Shifokor portalda ko'radi (threshold bilan solishtirilgan holda)
  3. Shifokor tasdiqlaydi -> status='allowed' yoki 'medical_check'
"""
from sqlalchemy import Column, Integer, Text, Numeric, Boolean, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AccessEvent(Base):
    __tablename__ = "access_events"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    auth_method = Column(Text, nullable=False)  # 'face' / 'fingerprint'
    scanned_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    temperature = Column(Numeric(4, 1))
    mask_on = Column(Boolean)

    status = Column(Text, nullable=False, default="pending")  # pending / allowed / medical_check
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(TIMESTAMP)
    doctor_note = Column(Text)

    employee = relationship("Employee")
    device = relationship("Device")
    reviewer = relationship("User")
