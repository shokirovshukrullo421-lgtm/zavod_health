"""
Tashkiliy tuzilma: karyerlar va bo'limlar.
"""
from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Career(Base):
    __tablename__ = "careers"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    departments = relationship("Department", back_populates="career")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    career_id = Column(Integer, ForeignKey("careers.id"), nullable=False)
    name = Column(Text, nullable=False)

    career = relationship("Career", back_populates="departments")
