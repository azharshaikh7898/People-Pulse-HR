from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import TaskCategory, TaskStatus


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: str
    title: str
    description: str
    category: TaskCategory
    status: TaskStatus
    due_date: date | None
    completed_at: datetime | None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class ProgressOut(BaseModel):
    employee_id: int
    employee_name: str
    department: str
    joining_date: date
    total: int
    completed: int
    in_progress: int
    pending: int
    percent: int
