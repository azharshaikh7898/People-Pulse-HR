from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import TaskCategory, TaskStatus, values
from app.database import Base


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"
    __table_args__ = (
        CheckConstraint(f"status IN ({', '.join(repr(v) for v in values(TaskStatus))})", name="ck_task_status"),
        CheckConstraint(f"category IN ({', '.join(repr(v) for v in values(TaskCategory))})", name="ck_task_category"),
        UniqueConstraint("employee_id", "title", name="uq_task_employee_title"),
        Index("ix_task_employee_status", "employee_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.PENDING.value, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee", back_populates="onboarding_tasks")

    @property
    def employee_name(self) -> str:
        return self.employee.full_name
