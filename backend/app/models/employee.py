from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import EmploymentStatus, values
from app.database import Base


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(v) for v in values(EmploymentStatus))})", name="ck_employees_status"
        ),
        Index("ix_employees_dept_status", "department", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # always stored lowercase
    department: Mapped[str] = mapped_column(String(60))
    designation: Mapped[str] = mapped_column(String(100))
    joining_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default=EmploymentStatus.ACTIVE.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="employee", uselist=False)
    leave_requests = relationship("LeaveRequest", back_populates="employee", cascade="all, delete-orphan")
    onboarding_tasks = relationship(
        "OnboardingTask", back_populates="employee", cascade="all, delete-orphan", order_by="OnboardingTask.sort_order"
    )

    @property
    def has_login(self) -> bool:
        return self.user is not None
