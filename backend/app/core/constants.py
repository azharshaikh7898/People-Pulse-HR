"""Shared enums and HR policy values."""
from enum import Enum


class Role(str, Enum):
    HR_ADMIN = "hr_admin"
    EMPLOYEE = "employee"


class EmploymentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class LeaveType(str, Enum):
    ANNUAL = "annual"
    SICK = "sick"
    CASUAL = "casual"
    UNPAID = "unpaid"


class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskCategory(str, Enum):
    IT_SETUP = "it_setup"
    DOCUMENTATION = "documentation"
    HR_ORIENTATION = "hr_orientation"


DEPARTMENTS = [
    "Engineering", "Human Resources", "Sales", "Marketing",
    "Finance", "Operations", "Design", "Customer Support",
]

# Yearly leave allowance in working days. Unpaid leave has no cap.
LEAVE_ALLOWANCE = {
    LeaveType.ANNUAL: 18,
    LeaveType.SICK: 10,
    LeaveType.CASUAL: 6,
}


def values(enum_cls) -> list[str]:
    return [e.value for e in enum_cls]
