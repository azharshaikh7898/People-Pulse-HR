from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, is_hr, require_hr
from app.core.constants import DEPARTMENTS, EmploymentStatus
from app.core.errors import bad_request, forbidden
from app.database import get_db
from app.models.user import User
from app.schemas.common import Page, make_page
from app.schemas.employee import EmployeeCreate, EmployeeDetail, EmployeeOut, EmployeeUpdate
from app.services import employees as employee_service
from app.services import onboarding as onboarding_service

router = APIRouter(prefix="/employees", tags=["Employees"])


def _detail(db: Session, employee) -> dict:
    data = EmployeeOut.model_validate(employee).model_dump()
    data["onboarding"] = onboarding_service.employee_summary(db, employee.id)
    return data


@router.get("/departments", response_model=list[str], summary="Allowed department names")
def departments(_: User = Depends(get_current_user)):
    return DEPARTMENTS


@router.get("", response_model=Page[EmployeeOut], summary="Search, filter and paginate employees (HR only)")
def list_employees(
    q: str | None = Query(None, max_length=100, description="Matches name, email or designation"),
    department: str | None = None,
    status_: EmploymentStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_hr),
):
    items, total = employee_service.list_employees(db, q, department, status_, page, page_size)
    return make_page(items, total, page, page_size)


@router.post(
    "", response_model=EmployeeDetail, status_code=status.HTTP_201_CREATED,
    summary="Create an employee and automatically generate their onboarding tasks (HR only)",
)
def create_employee(body: EmployeeCreate, db: Session = Depends(get_db), _: User = Depends(require_hr)):
    employee = employee_service.create_employee(db, body)
    return _detail(db, employee)


@router.get("/{employee_id}", response_model=EmployeeDetail)
def get_employee(employee_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not is_hr(user) and user.employee_id != employee_id:
        raise forbidden("You can only view your own employee record")
    return _detail(db, employee_service.get_employee(db, employee_id))


@router.put("/{employee_id}", response_model=EmployeeDetail, summary="Edit an employee (HR only)")
def update_employee(
    employee_id: int, body: EmployeeUpdate, db: Session = Depends(get_db), _: User = Depends(require_hr)
):
    employee = employee_service.get_employee(db, employee_id)
    return _detail(db, employee_service.update_employee(db, employee, body))


@router.post("/{employee_id}/deactivate", response_model=EmployeeDetail, summary="Deactivate an employee (HR only)")
def deactivate(employee_id: int, db: Session = Depends(get_db), actor: User = Depends(require_hr)):
    if actor.employee_id == employee_id:
        raise bad_request("You cannot deactivate your own account")
    employee = employee_service.get_employee(db, employee_id)
    return _detail(db, employee_service.set_status(db, employee, EmploymentStatus.INACTIVE))


@router.post("/{employee_id}/activate", response_model=EmployeeDetail, summary="Reactivate an employee (HR only)")
def activate(employee_id: int, db: Session = Depends(get_db), _: User = Depends(require_hr)):
    employee = employee_service.get_employee(db, employee_id)
    return _detail(db, employee_service.set_status(db, employee, EmploymentStatus.ACTIVE))
