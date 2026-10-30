"""Automated onboarding: the task template, task creation, status updates, progress."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.constants import EmploymentStatus, TaskCategory, TaskStatus
from app.core.errors import not_found
from app.models.employee import Employee
from app.models.onboarding import OnboardingTask

# (title, description, category, due this many days after the joining date)
ONBOARDING_TEMPLATE: list[tuple[str, str, TaskCategory, int]] = [
    ("Provision laptop and accessories", "Order, configure and hand over the laptop, charger and peripherals.", TaskCategory.IT_SETUP, 0),
    ("Create company email and accounts", "Set up the email mailbox, chat and single sign-on accounts.", TaskCategory.IT_SETUP, 0),
    ("Set up VPN and security tools", "Install the VPN client, password manager and enable two-factor authentication.", TaskCategory.IT_SETUP, 1),
    ("Grant access to team tools", "Give access to the code repositories, project tracker and shared drives for the team.", TaskCategory.IT_SETUP, 2),
    ("Sign employment contract and NDA", "Collect the signed employment contract and non-disclosure agreement.", TaskCategory.DOCUMENTATION, 0),
    ("Submit ID proof and bank details", "Verify identity documents and record bank details for payroll.", TaskCategory.DOCUMENTATION, 3),
    ("Complete tax and benefits forms", "Fill in tax declaration and select benefits such as health insurance.", TaskCategory.DOCUMENTATION, 7),
    ("Welcome session with HR", "Introduce the company, culture, working hours and leave policy.", TaskCategory.HR_ORIENTATION, 0),
    ("Meet your manager and team", "Schedule an introduction with the reporting manager and team members.", TaskCategory.HR_ORIENTATION, 1),
    ("Review policies and code of conduct", "Read and acknowledge the code of conduct, security and anti-harassment policies.", TaskCategory.HR_ORIENTATION, 2),
    ("30-day check-in", "HR check-in to collect feedback on the first month.", TaskCategory.HR_ORIENTATION, 30),
]


def create_default_tasks(db: Session, employee: Employee) -> list[OnboardingTask]:
    """Adds the standard task set for a new employee to the session.

    It does NOT commit: the caller commits once, so the employee and their tasks
    are saved together or not at all.
    """
    tasks = [
        OnboardingTask(
            employee_id=employee.id,
            title=title,
            description=description,
            category=category.value,
            status=TaskStatus.PENDING.value,
            due_date=employee.joining_date + timedelta(days=offset),
            sort_order=index,
        )
        for index, (title, description, category, offset) in enumerate(ONBOARDING_TEMPLATE)
    ]
    db.add_all(tasks)
    return tasks


def get_task(db: Session, task_id: int) -> OnboardingTask:
    task = db.scalar(
        select(OnboardingTask).options(joinedload(OnboardingTask.employee)).where(OnboardingTask.id == task_id)
    )
    if not task:
        raise not_found("Onboarding task")
    return task


def update_task_status(db: Session, task: OnboardingTask, new_status: TaskStatus) -> OnboardingTask:
    task.status = new_status.value
    task.completed_at = datetime.now(timezone.utc) if new_status == TaskStatus.COMPLETED else None
    db.commit()
    return task


def list_tasks(
    db: Session,
    employee_id: int | None = None,
    status: TaskStatus | None = None,
    category: TaskCategory | None = None,
) -> list[OnboardingTask]:
    stmt = (
        select(OnboardingTask)
        .join(Employee)
        .options(joinedload(OnboardingTask.employee))
        .order_by(OnboardingTask.employee_id, OnboardingTask.sort_order)
    )
    if employee_id is not None:
        stmt = stmt.where(OnboardingTask.employee_id == employee_id)
    if status:
        stmt = stmt.where(OnboardingTask.status == status.value)
    if category:
        stmt = stmt.where(OnboardingTask.category == category.value)
    return list(db.scalars(stmt).unique())


def _count(status: TaskStatus):
    return func.coalesce(func.sum(case((OnboardingTask.status == status.value, 1), else_=0)), 0)


def _percent(done: int, total: int) -> int:
    return round(done * 100 / total) if total else 0


def get_progress(db: Session, employee_id: int | None = None, only_active: bool = True) -> list[dict]:
    """Per-employee progress, least complete first."""
    stmt = (
        select(
            Employee.id, Employee.full_name, Employee.department, Employee.joining_date,
            func.count(OnboardingTask.id),
            _count(TaskStatus.COMPLETED), _count(TaskStatus.IN_PROGRESS), _count(TaskStatus.PENDING),
        )
        .join(OnboardingTask, OnboardingTask.employee_id == Employee.id)
        .group_by(Employee.id)
    )
    if employee_id is not None:
        stmt = stmt.where(Employee.id == employee_id)
    if only_active:
        stmt = stmt.where(Employee.status == EmploymentStatus.ACTIVE.value)
    rows = db.execute(stmt).all()
    result = [
        {
            "employee_id": r[0], "employee_name": r[1], "department": r[2], "joining_date": r[3],
            "total": r[4], "completed": int(r[5]), "in_progress": int(r[6]), "pending": int(r[7]),
            "percent": _percent(int(r[5]), r[4]),
        }
        for r in rows
    ]
    result.sort(key=lambda x: (x["percent"], -x["joining_date"].toordinal()))
    return result


def employee_summary(db: Session, employee_id: int) -> dict:
    rows = get_progress(db, employee_id=employee_id, only_active=False)
    if not rows:
        return {"total": 0, "completed": 0, "in_progress": 0, "pending": 0, "percent": 0}
    r = rows[0]
    return {k: r[k] for k in ("total", "completed", "in_progress", "pending", "percent")}
