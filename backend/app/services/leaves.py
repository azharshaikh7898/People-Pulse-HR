"""Leave rules: working-day counting, overlap check, balances, review, cancel."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.constants import LEAVE_ALLOWANCE, EmploymentStatus, LeaveStatus, LeaveType
from app.core.errors import AppError, bad_request, conflict, forbidden, not_found
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.user import User
from app.schemas.leave import LeaveCreate

MAX_BACKDATE_DAYS = 30
MAX_ADVANCE_DAYS = 365
ACTIVE_STATUSES = (LeaveStatus.PENDING.value, LeaveStatus.APPROVED.value)


def count_working_days(start: date, end: date) -> int:
    """Mon-Fri days between start and end, inclusive. (Public holidays are not modelled.)"""
    total_days = (end - start).days + 1
    return sum(1 for i in range(total_days) if (start + timedelta(days=i)).weekday() < 5)


def _used_days(db: Session, employee_id: int, leave_type: str, year: int, statuses: tuple[str, ...]) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(LeaveRequest.days), 0)).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type == leave_type,
            LeaveRequest.status.in_(statuses),
            func.extract("year", LeaveRequest.start_date) == year,
        )
    ) or 0


def get_balance(db: Session, employee_id: int, year: int | None = None) -> dict:
    year = year or date.today().year
    items = []
    for leave_type in LeaveType:
        allowance = LEAVE_ALLOWANCE.get(leave_type)
        used = _used_days(db, employee_id, leave_type.value, year, (LeaveStatus.APPROVED.value,))
        pending = _used_days(db, employee_id, leave_type.value, year, (LeaveStatus.PENDING.value,))
        items.append({
            "leave_type": leave_type, "allowance": allowance, "used": used, "pending": pending,
            "remaining": None if allowance is None else allowance - used - pending,
        })
    return {"employee_id": employee_id, "year": year, "balances": items}


def create_request(db: Session, employee_id: int, data: LeaveCreate) -> LeaveRequest:
    today = date.today()
    if data.start_date < today - timedelta(days=MAX_BACKDATE_DAYS):
        raise bad_request(f"Leave cannot start more than {MAX_BACKDATE_DAYS} days in the past")
    if data.end_date > today + timedelta(days=MAX_ADVANCE_DAYS):
        raise bad_request("Leave cannot be requested more than a year ahead")
    if data.start_date.year != data.end_date.year:
        raise bad_request("A request cannot span two calendar years. Please submit one request per year")

    days = count_working_days(data.start_date, data.end_date)
    if days == 0:
        raise bad_request("The selected dates only contain weekends")

    # Lock this employee's row so two simultaneous requests cannot both pass the checks below.
    employee = db.scalar(select(Employee).where(Employee.id == employee_id).with_for_update())
    if not employee:
        raise not_found("Employee")
    if employee.status != EmploymentStatus.ACTIVE.value:
        raise forbidden("Inactive employees cannot request leave")

    overlap = db.scalar(
        select(LeaveRequest.id).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(ACTIVE_STATUSES),
            and_(LeaveRequest.start_date <= data.end_date, LeaveRequest.end_date >= data.start_date),
        ).limit(1)
    )
    if overlap:
        raise conflict("These dates overlap with an existing pending or approved leave request")

    allowance = LEAVE_ALLOWANCE.get(data.leave_type)
    if allowance is not None:
        taken = _used_days(db, employee_id, data.leave_type.value, data.start_date.year, ACTIVE_STATUSES)
        remaining = allowance - taken
        if days > remaining:
            raise AppError(
                422,
                f"Not enough {data.leave_type.value} leave: you requested {days} day(s) but only {max(remaining, 0)} remain",
            )

    leave = LeaveRequest(
        employee_id=employee_id, leave_type=data.leave_type.value, start_date=data.start_date,
        end_date=data.end_date, days=days, reason=data.reason, status=LeaveStatus.PENDING.value,
    )
    db.add(leave)
    db.commit()
    return get_request(db, leave.id)


def get_request(db: Session, leave_id: int) -> LeaveRequest:
    leave = db.scalar(
        select(LeaveRequest).options(joinedload(LeaveRequest.employee)).where(LeaveRequest.id == leave_id)
    )
    if not leave:
        raise not_found("Leave request")
    return leave


def list_requests(
    db: Session, employee_id: int | None, status: LeaveStatus | None, page: int, page_size: int
) -> tuple[list[LeaveRequest], int]:
    stmt = select(LeaveRequest).options(joinedload(LeaveRequest.employee))
    if employee_id is not None:
        stmt = stmt.where(LeaveRequest.employee_id == employee_id)
    if status:
        stmt = stmt.where(LeaveRequest.status == status.value)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    stmt = stmt.order_by(LeaveRequest.created_at.desc(), LeaveRequest.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt)), total


def review_request(db: Session, leave: LeaveRequest, reviewer: User, decision: LeaveStatus, note: str | None):
    if leave.status != LeaveStatus.PENDING.value:
        raise conflict(f"This request is already {leave.status} and can no longer be reviewed")
    if reviewer.employee_id is not None and reviewer.employee_id == leave.employee_id:
        raise forbidden("You cannot review your own leave request")
    leave.status = decision.value
    leave.reviewed_by = reviewer.id
    leave.reviewed_at = datetime.now(timezone.utc)
    leave.review_note = note
    db.commit()
    return leave


def cancel_request(db: Session, leave: LeaveRequest, user: User):
    if user.employee_id != leave.employee_id:
        raise forbidden("You can only cancel your own leave requests")
    can_cancel = leave.status == LeaveStatus.PENDING.value or (
        leave.status == LeaveStatus.APPROVED.value and leave.start_date > date.today()
    )
    if not can_cancel:
        raise conflict("Only pending requests, or approved requests that have not started, can be cancelled")
    leave.status = LeaveStatus.CANCELLED.value
    db.commit()
    return leave
