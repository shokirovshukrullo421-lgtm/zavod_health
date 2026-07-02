"""
Zavod xodimlari (skanerlanadigan, portalga login qilmaydigan shaxslar).
"""
from sqlalchemy import Column, Integer, Text, Boolean, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    position = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)  # soft delete
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    departments = relationship("EmployeeDepartment", back_populates="employee")


class EmployeeDepartment(Base):
    __tablename__ = "employee_departments"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)

    employee = relationship("Employee", back_populates="departments")
    department = relationship("Department")
