"""
Kirish nazorati qurilmalari (Dahua face recognition).
"""
from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    device_code = Column(Text, nullable=False)

    department = relationship("Department")
