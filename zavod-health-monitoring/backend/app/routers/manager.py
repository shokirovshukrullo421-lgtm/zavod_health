"""
Bo'lim mas'uli/rahbar endpoint'lari.

Faqat 'manager' va 'admin' rolidagi foydalanuvchilar uchun.
Mas'ul faqat o'ziga tayinlangan bo'lim(lar)dagi xodimlarni boshqara oladi.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_role
from app.models.user import User, UserDepartmentAssignment
from app.models.employee import Employee, EmployeeDepartment
from app.models.organization import Department
from app.schemas.manager import EmployeeCreate, EmployeeUpdate, EmployeeOut

router = APIRouter(prefix="/manager", tags=["Bo'lim mas'uli"])


def _get_allowed_department_ids(user: User, db: Session) -> list[int]:
    """Mas'ulning o'ziga tayinlangan bo'lim ID'larini qaytaradi. Admin uchun hamma bo'lim."""
    if user.role == "admin":
        return [d.id for d in db.query(Department).all()]
    assignments = db.query(UserDepartmentAssignment).filter(
        UserDepartmentAssignment.user_id == user.id
    ).all()
    return [a.department_id for a in assignments]


def _build_employee_out(emp: Employee, db: Session) -> EmployeeOut:
    """Employee modelini EmployeeOut sxemasiga o'giradi."""
    dept_links = db.query(EmployeeDepartment).filter(
        EmployeeDepartment.employee_id == emp.id
    ).all()
    dept_names = []
    for link in dept_links:
        dept = db.query(Department).filter(Department.id == link.department_id).first()
        if dept:
            dept_names.append(dept.name)

    return EmployeeOut(
        id=emp.id,
        first_name=emp.first_name,
        last_name=emp.last_name,
        position=emp.position,
        is_active=emp.is_active,
        departments=dept_names,
        created_at=emp.created_at,
        updated_at=emp.updated_at,
    )


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    """
    Mas'ulning o'z bo'lim(lar)idagi barcha faol xodimlar ro'yxati.
    """
    allowed_dept_ids = _get_allowed_department_ids(current_user, db)

    # Shu bo'limlardagi xodim ID'larini topish
    emp_dept_links = db.query(EmployeeDepartment).filter(
        EmployeeDepartment.department_id.in_(allowed_dept_ids)
    ).all()
    emp_ids = list({link.employee_id for link in emp_dept_links})

    employees = db.query(Employee).filter(
        Employee.id.in_(emp_ids),
        Employee.is_active == True,
    ).order_by(Employee.last_name).all()

    return [_build_employee_out(emp, db) for emp in employees]


@router.post("/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    """
    Yangi xodim qo'shish.
    Mas'ul faqat o'ziga tayinlangan bo'limlarga xodim qo'sha oladi.
    """
    allowed_dept_ids = _get_allowed_department_ids(current_user, db)

    # Yuborilgan bo'limlar mas'ulga ruxsat etilganmi tekshirish
    for dept_id in data.department_ids:
        if dept_id not in allowed_dept_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Siz {dept_id}-bo'limga xodim qo'sha olmaysiz",
            )
        # Bo'lim mavjudmi tekshirish
        dept = db.query(Department).filter(Department.id == dept_id).first()
        if dept is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bo'lim topilmadi: ID {dept_id}",
            )

    # Xodimni yaratish
    employee = Employee(
        first_name=data.first_name,
        last_name=data.last_name,
        position=data.position,
    )
    db.add(employee)
    db.flush()  # ID olish uchun

    # Bo'limlarga tayinlash
    for dept_id in data.department_ids:
        link = EmployeeDepartment(employee_id=employee.id, department_id=dept_id)
        db.add(link)

    db.commit()
    db.refresh(employee)

    return _build_employee_out(employee, db)


@router.put("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    """
    Xodim ma'lumotlarini tahrirlash.
    Faqat yuborilgan maydonlar o'zgaradi.
    """
    allowed_dept_ids = _get_allowed_department_ids(current_user, db)

    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.is_active == True,
    ).first()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Xodim topilmadi: ID {employee_id}",
        )

    # Xodim mas'ulning bo'limidami tekshirish
    emp_dept_links = db.query(EmployeeDepartment).filter(
        EmployeeDepartment.employee_id == employee_id
    ).all()
    emp_dept_ids = [link.department_id for link in emp_dept_links]
    if not any(d in allowed_dept_ids for d in emp_dept_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu xodim sizning bo'limingizga tegishli emas",
        )

    # Maydonlarni yangilash
    if data.first_name is not None:
        employee.first_name = data.first_name
    if data.last_name is not None:
        employee.last_name = data.last_name
    if data.position is not None:
        employee.position = data.position
    employee.updated_at = datetime.utcnow()

    # Bo'limlarni yangilash (agar yuborilgan bo'lsa)
    if data.department_ids is not None:
        for dept_id in data.department_ids:
            if dept_id not in allowed_dept_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Siz {dept_id}-bo'limga tayinlay olmaysiz",
                )
        # Eskisini o'chirib, yangisini yozish
        db.query(EmployeeDepartment).filter(
            EmployeeDepartment.employee_id == employee_id
        ).delete()
        for dept_id in data.department_ids:
            db.add(EmployeeDepartment(employee_id=employee_id, department_id=dept_id))

    db.commit()
    db.refresh(employee)

    return _build_employee_out(employee, db)


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    """
    Xodimni o'chirish (soft delete: is_active=False).
    Tarix saqlanib qoladi, xodim ro'yxatdan ko'rinmaydi.
    """
    allowed_dept_ids = _get_allowed_department_ids(current_user, db)

    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.is_active == True,
    ).first()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Xodim topilmadi: ID {employee_id}",
        )

    # Xodim mas'ulning bo'limidami tekshirish
    emp_dept_links = db.query(EmployeeDepartment).filter(
        EmployeeDepartment.employee_id == employee_id
    ).all()
    emp_dept_ids = [link.department_id for link in emp_dept_links]
    if not any(d in allowed_dept_ids for d in emp_dept_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu xodim sizning bo'limingizga tegishli emas",
        )

    # Soft delete
    employee.is_active = False
    employee.updated_at = datetime.utcnow()
    db.commit()
