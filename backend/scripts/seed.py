"""Development-only demo data.

    python -m scripts.seed            # only works on an empty database
    python -m scripts.seed --reset    # wipes all PeoplePulse tables first (asks you to type the DB name)

Refuses to run when ENVIRONMENT=production. All people are fictional and use example.com addresses.
"""
import argparse
import random
import sys
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.constants import LEAVE_ALLOWANCE, DEPARTMENTS, LeaveStatus, LeaveType, Role, TaskStatus
from app.core.security import hash_password
from app.database import SessionLocal, engine
from app.models import Employee, LeaveRequest, OnboardingTask, User
from app.services.leaves import count_working_days
from app.services.onboarding import create_default_tasks

# Development-only credentials (also listed in the README). They exist only if you run this script.
DEMO_HR = {"email": "hr.admin@example.com", "password": "HrAdmin#2026", "name": "Priya Sharma"}
DEMO_EMPLOYEE = {"email": "demo.employee@example.com", "password": "Employee#2026", "name": "Rahul Mehta"}

PEOPLE = [
    ("Aarav Patel", "Engineering", "Backend Engineer"), ("Ananya Iyer", "Engineering", "Frontend Engineer"),
    ("Vikram Singh", "Engineering", "Senior Software Engineer"), ("Neha Gupta", "Engineering", "QA Engineer"),
    ("Karan Malhotra", "Engineering", "DevOps Engineer"), ("Isha Reddy", "Engineering", "Data Engineer"),
    ("Rohan Desai", "Sales", "Account Executive"), ("Sneha Kulkarni", "Sales", "Sales Manager"),
    ("Arjun Nair", "Sales", "Business Development Associate"), ("Meera Joshi", "Marketing", "Content Strategist"),
    ("Siddharth Rao", "Marketing", "Growth Marketer"), ("Pooja Bhatt", "Marketing", "Brand Designer"),
    ("Aditya Verma", "Finance", "Financial Analyst"), ("Kavya Menon", "Finance", "Accountant"),
    ("Nikhil Chopra", "Operations", "Operations Manager"), ("Divya Pillai", "Operations", "Logistics Coordinator"),
    ("Manish Tiwari", "Operations", "Process Analyst"), ("Tanvi Shah", "Design", "Product Designer"),
    ("Harsh Agarwal", "Design", "UX Researcher"), ("Ritu Saxena", "Customer Support", "Support Lead"),
    ("Yash Kapoor", "Customer Support", "Support Specialist"), ("Simran Kaur", "Customer Support", "Support Specialist"),
    ("Dev Mishra", "Human Resources", "Talent Partner"), ("Lakshmi Narayan", "Human Resources", "HR Generalist"),
]


def confirm_safe_to_run(reset: bool) -> None:
    if settings.is_production:
        sys.exit("Refusing to seed: ENVIRONMENT=production. Demo accounts must never exist in production.")
    db_name = make_url(settings.DATABASE_URL).database
    with SessionLocal() as db:
        has_data = db.scalar(select(Employee.id).limit(1)) is not None or db.scalar(select(User.id).limit(1)) is not None
    if has_data and not reset:
        sys.exit("Database already contains data. Re-run with --reset to wipe it first.")
    if reset:
        typed = input(f"This DELETES all PeoplePulse data in database '{db_name}'. Type the database name to continue: ")
        if typed.strip() != db_name:
            sys.exit("Name did not match. Nothing was changed.")
        with engine.begin() as conn:
            conn.execute(text(
                "TRUNCATE users, employees, leave_requests, onboarding_tasks, revoked_tokens RESTART IDENTITY CASCADE"
            ))


def add_employee(db, name, department, designation, joining, email, role=None, password=None) -> Employee:
    emp = Employee(full_name=name, email=email, department=department, designation=designation,
                   joining_date=joining, status="active")
    db.add(emp)
    db.flush()
    if password:
        db.add(User(email=email, hashed_password=hash_password(password), role=(role or Role.EMPLOYEE).value,
                    employee_id=emp.id))
    create_default_tasks(db, emp)
    return emp


def simulate_onboarding(db, emp: Employee, rng: random.Random, today: date) -> None:
    """Older hires finished onboarding; recent hires are part-way through."""
    tenure = (today - emp.joining_date).days
    tasks = db.scalars(select(OnboardingTask).where(OnboardingTask.employee_id == emp.id)
                       .order_by(OnboardingTask.sort_order)).all()
    for task in tasks:
        days_overdue = (today - task.due_date).days
        if tenure > 45:
            done = True
        elif days_overdue >= 0:
            done = rng.random() < 0.5
        else:
            done = False
        if done:
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.combine(min(task.due_date, today), datetime.min.time(), tzinfo=timezone.utc)
        elif days_overdue >= -3 and rng.random() < 0.5:
            task.status = TaskStatus.IN_PROGRESS.value


def seed_leaves(db, emps: list[Employee], rng: random.Random, today: date) -> int:
    """Non-overlapping, within-allowance requests for this year, with a realistic status mix."""
    year = today.year
    count = 0
    for emp in emps:
        taken = {t: 0 for t in LEAVE_ALLOWANCE}
        busy: list[tuple[date, date]] = []
        for _ in range(rng.randint(0, 3)):
            leave_type = rng.choice([LeaveType.ANNUAL, LeaveType.ANNUAL, LeaveType.SICK, LeaveType.CASUAL])
            span = rng.randint(1, 4) if leave_type != LeaveType.ANNUAL else rng.randint(2, 6)
            earliest = max(date(year, 1, 1), emp.joining_date)
            latest = date(year, 12, 31) - timedelta(days=span)
            if earliest >= latest:
                continue
            start = earliest + timedelta(days=rng.randint(0, (latest - earliest).days))
            while start.weekday() >= 5:
                start += timedelta(days=1)
            end = start + timedelta(days=span - 1)
            days = count_working_days(start, end)
            if end.year != year or days == 0 or taken[leave_type] + days > LEAVE_ALLOWANCE[leave_type]:
                continue
            if any(s <= end and e >= start for s, e in busy):
                continue
            if end < today - timedelta(days=3):
                status = rng.choices(["approved", "rejected"], [0.85, 0.15])[0]
            elif start > today:
                status = rng.choices(["pending", "approved"], [0.7, 0.3])[0]
            else:
                status = "approved"
            busy.append((start, end))
            taken[leave_type] += days
            created = datetime.combine(max(start - timedelta(days=rng.randint(3, 14)), emp.joining_date),
                                       datetime.min.time(), tzinfo=timezone.utc)
            db.add(LeaveRequest(
                employee_id=emp.id, leave_type=leave_type.value, start_date=start, end_date=end, days=days,
                reason=rng.choice(["Family function", "Medical appointment", "Short vacation", "Personal work",
                                   "Travel home", "Feeling unwell", "Moving house"]),
                status=status, created_at=created,
                reviewed_at=None if status == "pending" else created + timedelta(days=1),
                review_note="Approved, enjoy!" if status == "approved" and rng.random() < 0.3 else None,
            ))
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data (development only)")
    parser.add_argument("--reset", action="store_true", help="wipe existing data first")
    args = parser.parse_args()
    confirm_safe_to_run(args.reset)

    rng = random.Random(42)  # fixed seed: same demo data every time
    today = date.today()
    emps: list[Employee] = []
    with SessionLocal() as db:
        hr = add_employee(db, DEMO_HR["name"], "Human Resources", "HR Manager", today - timedelta(days=900),
                          DEMO_HR["email"], Role.HR_ADMIN, DEMO_HR["password"])
        demo = add_employee(db, DEMO_EMPLOYEE["name"], "Engineering", "Software Engineer", today - timedelta(days=12),
                            DEMO_EMPLOYEE["email"], Role.EMPLOYEE, DEMO_EMPLOYEE["password"])
        emps += [hr, demo]
        for i, (name, dept, title) in enumerate(PEOPLE):
            assert dept in DEPARTMENTS
            # last 5 people joined recently so onboarding is visibly in progress
            days_ago = rng.randint(2, 20) if i >= len(PEOPLE) - 5 else rng.randint(60, 800)
            email = name.lower().replace(" ", ".") + "@example.com"
            emps.append(add_employee(db, name, dept, title, today - timedelta(days=days_ago), email))
        db.flush()
        for emp in emps:
            simulate_onboarding(db, emp, rng, today)
        leaves = seed_leaves(db, emps, rng, today)
        db.commit()
    print(f"Seeded {len(emps)} employees, {leaves} leave requests and {len(emps) * 11} onboarding tasks.")
    print(f"HR admin : {DEMO_HR['email']} / {DEMO_HR['password']}")
    print(f"Employee : {DEMO_EMPLOYEE['email']} / {DEMO_EMPLOYEE['password']}")


if __name__ == "__main__":
    main()
