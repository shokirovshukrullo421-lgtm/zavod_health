"""
Yordamchi jadvallar: tanilmagan urinishlar, xabarlar, chegara qiymatlari.
"""
from sqlalchemy import Column, Integer, Text, Numeric, Boolean, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class UnrecognizedAttempt(Base):
    __tablename__ = "unrecognized_attempts"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    attempted_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    note = Column(Text)

    device = relationship("Device")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message_text = Column(Text, nullable=False)
    related_employee_id = Column(Integer, ForeignKey("employees.id"))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    is_read = Column(Boolean, nullable=False, default=False)

    sender = relationship("User", foreign_keys=[from_user_id])
    recipient = relationship("User", foreign_keys=[to_user_id])
    related_employee = relationship("Employee")


class Threshold(Base):
    __tablename__ = "thresholds"

    id = Column(Integer, primary_key=True)
    metric_name = Column(Text, nullable=False)
    max_value = Column(Numeric, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"))
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
