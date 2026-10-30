"""Create the first HR administrator (works in any environment, including production).

    python -m scripts.create_admin --email you@company.com --name "Your Name"

The password is read from a hidden prompt, or from the ADMIN_PASSWORD environment variable
(useful for one-off runs in a hosting shell). It is never printed or logged.
"""
import argparse
import getpass
import os
import sys
from datetime import date

from sqlalchemy import select

from app.core.constants import Role
from app.core.security import hash_password
from app.database import SessionLocal
from app.models import Employee, User
from app.schemas.auth import validate_new_password
from app.schemas.employee import EmployeeCreate  # reuse the email validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an HR administrator account")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    try:
        email = EmployeeCreate(full_name=args.name, email=args.email, department="Human Resources",
                               designation="HR Administrator", joining_date=date.today()).email
    except ValueError as exc:
        sys.exit(f"Invalid input: {exc}")

    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Password: ")
    if not os.environ.get("ADMIN_PASSWORD") and getpass.getpass("Repeat password: ") != password:
        sys.exit("Passwords did not match.")
    try:
        validate_new_password(password)
    except ValueError as exc:
        sys.exit(f"Weak password: {exc}")

    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)) or db.scalar(select(Employee.id).where(Employee.email == email)):
            sys.exit("An account with this email already exists.")
        emp = Employee(full_name=" ".join(args.name.split()), email=email, department="Human Resources",
                       designation="HR Administrator", joining_date=date.today(), status="active")
        db.add(emp)
        db.flush()
        db.add(User(email=email, hashed_password=hash_password(password), role=Role.HR_ADMIN.value, employee_id=emp.id))
        db.commit()
    print(f"HR administrator created: {email}")


if __name__ == "__main__":
    main()
