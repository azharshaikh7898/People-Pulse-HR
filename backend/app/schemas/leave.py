from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.core.constants import LeaveStatus, LeaveType


class LeaveCreate(BaseModel):
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Please give a short reason (at least 3 characters)")
        if len(v) > 500:
            raise ValueError("Reason must be 500 characters or fewer")
        return v

    @model_validator(mode="after")
    def check_order(self):
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be before the start date")
        return self


class LeaveReview(BaseModel):
    decision: LeaveStatus
    note: str | None = None

    @field_validator("decision")
    @classmethod
    def only_final(cls, v):
        if v not in (LeaveStatus.APPROVED, LeaveStatus.REJECTED):
            raise ValueError("Decision must be 'approved' or 'rejected'")
        return v

    @field_validator("note")
    @classmethod
    def clean_note(cls, v):
        if v is None:
            return None
        v = v.strip()
        if len(v) > 500:
            raise ValueError("Note must be 500 characters or fewer")
        return v or None


class LeaveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: str
    leave_type: LeaveType
    start_date: date
    end_date: date
    days: int
    reason: str
    status: LeaveStatus
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime


class BalanceItem(BaseModel):
    leave_type: LeaveType
    allowance: int | None  # None = unlimited (unpaid)
    used: int
    pending: int
    remaining: int | None


class BalanceOut(BaseModel):
    employee_id: int
    year: int
    balances: list[BalanceItem]
