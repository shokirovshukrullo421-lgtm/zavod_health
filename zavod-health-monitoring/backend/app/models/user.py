"""
Portal foydalanuvchilari: shifokor, bo'lim mas'uli/rahbar, admin.
employees jadvalidan butunlay mustaqil.
"""
from sqlalchemy import Column, Integer, Text, Boolean, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name = Column(Text, nullable=False)
    login = Column(Text, nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False)  # 'doctor' / 'manager' / 'admin'
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    career_assignments = relationship("UserCareerAssignment", back_populates="user")
    department_assignments = relationship("UserDepartmentAssignment", back_populates="user")


class UserCareerAssignment(Base):
    """Shifokor qaysi karyer(lar)ga tayinlangan."""
    __tablename__ = "user_career_assignments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    career_id = Column(Integer, ForeignKey("careers.id"), nullable=False)

    user = relationship("User", back_populates="career_assignments")
    career = relationship("Career")


class UserDepartmentAssignment(Base):
    """Bo'lim mas'uli/rahbar qaysi bo'lim(lar)ga tayinlangan."""
    __tablename__ = "user_department_assignments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)

    user = relationship("User", back_populates="department_assignments")
    department = relationship("Department")
