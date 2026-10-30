"""Employee business logic. Creating an employee also triggers onboarding automation."""
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.constants import EmploymentStatus, Role
from app.core.errors import bad_request, conflict, not_found
from app.core.security import hash_password
from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services import onboarding as onboarding_service


def _email_taken(db: Session, email: str, exclude_employee_id: int | None = None) -> bool:
    """True if the email belongs to another employee or to another person's login."""
    emp_stmt = select(Employee.id).where(Employee.email == email)
    user_stmt = select(User.id).where(User.email == email)
    if exclude_employee_id is not None:
        emp_stmt = emp_stmt.where(Employee.id != exclude_employee_id)
        user_stmt = user_stmt.where(or_(User.employee_id.is_(None), User.employee_id != exclude_employee_id))
    return db.scalar(emp_stmt) is not None or db.scalar(user_stmt) is not None


def get_employee(db: Session, employee_id: int) -> Employee:
    emp = db.scalar(select(Employee).options(selectinload(Employee.user)).where(Employee.id == employee_id))
    if not emp:
        raise not_found("Employee")
    return emp


def create_employee(db: Session, data: EmployeeCreate) -> Employee:
    """One transaction: employee row + optional login + all onboarding tasks."""
    if _email_taken(db, data.email):
        raise conflict("An employee with this email already exists")
    try:
        employee = Employee(
            full_name=data.full_name, email=data.email, department=data.department,
            designation=data.designation, joining_date=data.joining_date,
            status=EmploymentStatus.ACTIVE.value,
        )
        db.add(employee)
        db.flush()  # gets employee.id without committing
        if data.initial_password:
            db.add(User(
                email=data.email, hashed_password=hash_password(data.initial_password),
                role=Role.EMPLOYEE.value, employee_id=employee.id,
            ))
        onboarding_service.create_default_tasks(db, employee)
        db.commit()  # everything is saved together...
    except IntegrityError:
        db.rollback()  # ...or nothing is (also covers two requests racing on the same email)
        raise conflict("An employee with this email already exists")
    except Exception:
        db.rollback()
        raise
    return get_employee(db, employee.id)


def update_employee(db: Session, employee: Employee, data: EmployeeUpdate) -> Employee:
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise bad_request("No changes supplied")
    new_email = changes.get("email")
    if new_email and new_email != employee.email and _email_taken(db, new_email, exclude_employee_id=employee.id):
        raise conflict("An employee with this email already exists")
    try:
        for field, value in changes.items():
            setattr(employee, field, value)
        if new_email and employee.user:
            employee.user.email = new_email  # keep the login email in sync
        db.commit()
    except IntegrityError:
        db.rollback()
        raise conflict("An employee with this email already exists")
    return get_employee(db, employee.id)


def set_status(db: Session, employee: Employee, status: EmploymentStatus) -> Employee:
    employee.status = status.value
    if employee.user:
        employee.user.is_active = status == EmploymentStatus.ACTIVE
    db.commit()
    return employee


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_employees(
    db: Session, q: str | None, department: str | None, status: EmploymentStatus | None, page: int, page_size: int
) -> tuple[list[Employee], int]:
    stmt = select(Employee).options(selectinload(Employee.user))
    if q:
        like = f"%{_escape_like(q.strip())}%"
        stmt = stmt.where(or_(
            Employee.full_name.ilike(like, escape="\\"),
            Employee.email.ilike(like, escape="\\"),
            Employee.designation.ilike(like, escape="\\"),
        ))
    if department:
        stmt = stmt.where(Employee.department == department)
    if status:
        stmt = stmt.where(Employee.status == status.value)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    stmt = stmt.order_by(Employee.full_name, Employee.id).offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt)), total
