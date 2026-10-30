from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import LeaveStatus, LeaveType, values
from app.database import Base


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_leave_dates_order"),
        CheckConstraint("days > 0", name="ck_leave_days_positive"),
        CheckConstraint(f"leave_type IN ({', '.join(repr(v) for v in values(LeaveType))})", name="ck_leave_type"),
        CheckConstraint(f"status IN ({', '.join(repr(v) for v in values(LeaveStatus))})", name="ck_leave_status"),
        Index("ix_leave_employee_dates", "employee_id", "start_date", "end_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    leave_type: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[int] = mapped_column(Integer)  # working days (Mon-Fri) in the range
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=LeaveStatus.PENDING.value, index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    employee = relationship("Employee", back_populates="leave_requests")

    @property
    def employee_name(self) -> str:
        return self.employee.full_name
