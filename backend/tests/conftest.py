"""Test setup.

Safety: tests run against a SEPARATE database whose name must end with "_test".
The schema is built by running the real Alembic migrations, so migrations are tested too.
"""
import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parent.parent
_env = {**dotenv_values(BACKEND_DIR / ".env"), **os.environ}
TEST_DATABASE_URL = _env.get("TEST_DATABASE_URL", "")

if not TEST_DATABASE_URL or not TEST_DATABASE_URL.split("?")[0].endswith("_test"):
    raise RuntimeError(
        "Refusing to run tests: set TEST_DATABASE_URL to a database whose name ends with '_test' "
        "(tests delete all data in it)."
    )

# Must be set BEFORE the app is imported so it connects to the test database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret-key-only-used-by-pytest-0123456789"
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.constants import Role  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Employee, User  # noqa: E402

assert settings.DATABASE_URL.split("?")[0].endswith("_test"), "App is not pointed at the test database"

PASSWORD = "Passw0rd!x"


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, employees, leave_requests, onboarding_tasks, revoked_tokens RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def make_account(db, email, role=Role.EMPLOYEE, name="Test Person", department="Engineering", active=True):
    emp = Employee(
        full_name=name, email=email, department=department, designation="Tester",
        joining_date=date(2024, 1, 15), status="active" if active else "inactive",
    )
    db.add(emp)
    db.flush()
    user = User(email=email, hashed_password=hash_password(PASSWORD), role=role.value,
                employee_id=emp.id, is_active=active)
    db.add(user)
    db.commit()
    return user


def login(client, email, password=PASSWORD):
    return client.post("/api/auth/login", data={"username": email, "password": password})


def auth_headers(client, email, password=PASSWORD):
    res = login(client, email, password)
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def hr_user(db):
    return make_account(db, "hr@test.example", Role.HR_ADMIN, "Hira Admin", "Human Resources")


@pytest.fixture
def emp_user(db):
    return make_account(db, "emp@test.example", Role.EMPLOYEE, "Eli Employee")


@pytest.fixture
def hr_h(client, hr_user):
    return auth_headers(client, hr_user.email)


@pytest.fixture
def emp_h(client, emp_user):
    return auth_headers(client, emp_user.email)


def employee_payload(**overrides):
    data = {
        "full_name": "Asha Verma", "email": "asha.verma@example.com", "department": "Engineering",
        "designation": "Software Engineer", "joining_date": date.today().isoformat(),
    }
    data.update(overrides)
    return data


def next_monday(weeks_ahead=1) -> date:
    """A Monday at least a week away, shifted so the Mon-Fri week stays inside one year."""
    today = date.today()
    monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7) + timedelta(weeks=weeks_ahead - 1)
    while monday.year != (monday + timedelta(days=4)).year:
        monday += timedelta(weeks=1)
    return monday


def leave_payload(start: date, days=5, leave_type="annual", reason="Family trip"):
    """days = number of calendar days starting at `start`."""
    return {
        "leave_type": leave_type, "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=days - 1)).isoformat(), "reason": reason,
    }
