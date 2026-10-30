from datetime import date, datetime, timedelta

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.core.constants import DEPARTMENTS, EmploymentStatus
from app.schemas.auth import validate_new_password

MIN_JOINING_DATE = date(2000, 1, 1)


class _EmployeeFields(BaseModel):
    @field_validator("full_name", "designation", check_fields=False)
    @classmethod
    def strip_and_check(cls, v):
        if v is None:
            return v
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("Must be at least 2 characters")
        return v

    @field_validator("email", check_fields=False)
    @classmethod
    def lowercase_email(cls, v):
        return v.lower() if v else v

    @field_validator("department", check_fields=False)
    @classmethod
    def valid_department(cls, v):
        if v is not None and v not in DEPARTMENTS:
            raise ValueError(f"Department must be one of: {', '.join(DEPARTMENTS)}")
        return v

    @field_validator("joining_date", check_fields=False)
    @classmethod
    def valid_joining_date(cls, v):
        if v is None:
            return v
        if v < MIN_JOINING_DATE:
            raise ValueError("Joining date is too far in the past")
        if v > date.today() + timedelta(days=365):
            raise ValueError("Joining date cannot be more than a year in the future")
        return v


class EmployeeCreate(_EmployeeFields):
    full_name: str
    email: EmailStr
    department: str
    designation: str
    joining_date: date
    # Optional: if given, a login account (role=employee) is created with this temporary password.
    initial_password: str | None = None

    @field_validator("initial_password")
    @classmethod
    def check_password(cls, v):
        return validate_new_password(v) if v else None


class EmployeeUpdate(_EmployeeFields):
    full_name: str | None = None
    email: EmailStr | None = None
    department: str | None = None
    designation: str | None = None
    joining_date: date | None = None


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    department: str
    designation: str
    joining_date: date
    status: EmploymentStatus
    has_login: bool
    created_at: datetime


class OnboardingSummary(BaseModel):
    total: int
    completed: int
    in_progress: int
    pending: int
    percent: int


class EmployeeDetail(EmployeeOut):
    onboarding: OnboardingSummary
