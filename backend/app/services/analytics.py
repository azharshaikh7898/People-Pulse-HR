"""Dashboard numbers. Every figure comes from a database query."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.constants import EmploymentStatus, LeaveStatus, TaskStatus
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.onboarding import OnboardingTask


def _employee_count(db: Session, status: EmploymentStatus) -> int:
    return db.scalar(select(func.count(Employee.id)).where(Employee.status == status.value)) or 0


def _task_counts(db: Session) -> dict:
    rows = dict(
        db.execute(
            select(OnboardingTask.status, func.count(OnboardingTask.id))
            .join(Employee, Employee.id == OnboardingTask.employee_id)
            .where(Employee.status == EmploymentStatus.ACTIVE.value)
            .group_by(OnboardingTask.status)
        ).all()
    )
    unfinished = db.scalar(
        select(func.count(func.distinct(OnboardingTask.employee_id)))
        .join(Employee, Employee.id == OnboardingTask.employee_id)
        .where(Employee.status == EmploymentStatus.ACTIVE.value, OnboardingTask.status != TaskStatus.COMPLETED.value)
    ) or 0
    completed = rows.get(TaskStatus.COMPLETED.value, 0)
    in_progress = rows.get(TaskStatus.IN_PROGRESS.value, 0)
    pending = rows.get(TaskStatus.PENDING.value, 0)
    return {
        "total": completed + in_progress + pending, "completed": completed, "in_progress": in_progress,
        "pending": pending, "employees_onboarding": unfinished,
    }


def get_dashboard(db: Session) -> dict:
    departments = db.execute(
        select(Employee.department, func.count(Employee.id))
        .where(Employee.status == EmploymentStatus.ACTIVE.value)
        .group_by(Employee.department)
        .order_by(func.count(Employee.id).desc(), Employee.department)
    ).all()

    leave_rows = dict(db.execute(select(LeaveRequest.status, func.count(LeaveRequest.id)).group_by(LeaveRequest.status)).all())

    recent_employees = db.scalars(
        select(Employee).order_by(Employee.created_at.desc(), Employee.id.desc()).limit(5)
    ).all()
    recent_leaves = db.scalars(
        select(LeaveRequest).options(joinedload(LeaveRequest.employee))
        .order_by(LeaveRequest.created_at.desc(), LeaveRequest.id.desc()).limit(5)
    ).all()

    return {
        "total_active_employees": _employee_count(db, EmploymentStatus.ACTIVE),
        "total_inactive_employees": _employee_count(db, EmploymentStatus.INACTIVE),
        "departments": [{"department": d, "count": c} for d, c in departments],
        "leaves": {
            "pending": leave_rows.get(LeaveStatus.PENDING.value, 0),
            "approved": leave_rows.get(LeaveStatus.APPROVED.value, 0),
            "rejected": leave_rows.get(LeaveStatus.REJECTED.value, 0),
        },
        "onboarding": _task_counts(db),
        "recent_employees": [
            {"id": e.id, "full_name": e.full_name, "department": e.department, "designation": e.designation,
             "joining_date": e.joining_date, "created_at": e.created_at}
            for e in recent_employees
        ],
        "recent_leaves": [
            {"id": l.id, "employee_name": l.employee.full_name, "leave_type": l.leave_type,
             "start_date": l.start_date, "end_date": l.end_date, "days": l.days,
             "status": l.status, "created_at": l.created_at}
            for l in recent_leaves
        ],
    }
