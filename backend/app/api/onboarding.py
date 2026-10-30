from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, is_hr
from app.core.constants import TaskCategory, TaskStatus
from app.core.errors import forbidden
from app.database import get_db
from app.models.user import User
from app.schemas.onboarding import ProgressOut, TaskOut, TaskStatusUpdate
from app.services import onboarding as onboarding_service

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.get("/tasks", response_model=list[TaskOut], summary="List onboarding tasks (employees only see their own)")
def list_tasks(
    employee_id: int | None = None,
    status: TaskStatus | None = None,
    category: TaskCategory | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_hr(user):
        if user.employee_id is None:
            return []
        employee_id = user.employee_id  # employees can never look at other people's tasks
    return onboarding_service.list_tasks(db, employee_id, status, category)


@router.patch("/tasks/{task_id}", response_model=TaskOut, summary="Update a task's status")
def update_task(
    task_id: int, body: TaskStatusUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    task = onboarding_service.get_task(db, task_id)
    if not is_hr(user) and task.employee_id != user.employee_id:
        raise forbidden("You can only update your own onboarding tasks")
    return onboarding_service.update_task_status(db, task, body.status)


@router.get("/progress", response_model=list[ProgressOut], summary="Onboarding progress per employee")
def progress(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if is_hr(user):
        return onboarding_service.get_progress(db)
    if user.employee_id is None:
        return []
    return onboarding_service.get_progress(db, employee_id=user.employee_id, only_active=False)
