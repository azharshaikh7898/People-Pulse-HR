from datetime import date, datetime

from pydantic import BaseModel


class DepartmentCount(BaseModel):
    department: str
    count: int


class LeaveCounts(BaseModel):
    pending: int
    approved: int
    rejected: int


class OnboardingCounts(BaseModel):
    total: int
    completed: int
    in_progress: int
    pending: int
    employees_onboarding: int  # employees with at least one unfinished task


class RecentEmployee(BaseModel):
    id: int
    full_name: str
    department: str
    designation: str
    joining_date: date
    created_at: datetime


class RecentLeave(BaseModel):
    id: int
    employee_name: str
    leave_type: str
    start_date: date
    end_date: date
    days: int
    status: str
    created_at: datetime


class DashboardOut(BaseModel):
    total_active_employees: int
    total_inactive_employees: int
    departments: list[DepartmentCount]
    leaves: LeaveCounts
    onboarding: OnboardingCounts
    recent_employees: list[RecentEmployee]
    recent_leaves: list[RecentLeave]
