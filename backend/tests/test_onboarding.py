from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Employee, OnboardingTask
from app.services.onboarding import ONBOARDING_TEMPLATE
from tests.conftest import auth_headers, employee_payload


def create(client, headers, **overrides):
    res = client.post("/api/employees", headers=headers, json=employee_payload(**overrides))
    assert res.status_code == 201, res.text
    return res.json()


def tasks_for(client, headers, employee_id):
    res = client.get(f"/api/onboarding/tasks?employee_id={employee_id}", headers=headers)
    assert res.status_code == 200
    return res.json()


def test_creating_employee_generates_full_task_set(client, hr_h):
    emp = create(client, hr_h)
    tasks = tasks_for(client, hr_h, emp["id"])
    assert len(tasks) == len(ONBOARDING_TEMPLATE)
    assert {t["status"] for t in tasks} == {"pending"}
    assert {t["category"] for t in tasks} == {"it_setup", "documentation", "hr_orientation"}
    assert len({t["title"] for t in tasks}) == len(tasks)  # no duplicates
    assert emp["onboarding"] == {"total": len(tasks), "completed": 0, "in_progress": 0, "pending": len(tasks), "percent": 0}


def test_due_dates_are_relative_to_joining_date(client, hr_h):
    joining = date.today() + timedelta(days=10)
    emp = create(client, hr_h, joining_date=joining.isoformat())
    due = {t["title"]: t["due_date"] for t in tasks_for(client, hr_h, emp["id"])}
    assert due["Welcome session with HR"] == joining.isoformat()
    assert due["30-day check-in"] == (joining + timedelta(days=30)).isoformat()


def test_each_employee_gets_their_own_tasks(client, hr_h):
    a = create(client, hr_h)
    b = create(client, hr_h, email="b@example.com", full_name="Bela Nair")
    ids_a = {t["id"] for t in tasks_for(client, hr_h, a["id"])}
    ids_b = {t["id"] for t in tasks_for(client, hr_h, b["id"])}
    assert ids_a and ids_b and ids_a.isdisjoint(ids_b)


def test_failed_task_creation_rolls_back_the_employee(hr_h, db, monkeypatch):
    """The automation is transactional: if task creation fails, the employee must not be saved."""
    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure while creating tasks")

    monkeypatch.setattr("app.services.employees.onboarding_service.create_default_tasks", boom)
    quiet_client = TestClient(app, raise_server_exceptions=False)
    res = quiet_client.post("/api/employees", headers=hr_h, json=employee_payload(initial_password="Welcome123"))
    assert res.status_code == 500
    assert db.query(Employee).filter_by(email="asha.verma@example.com").count() == 0
    assert db.query(OnboardingTask).count() == 0


def test_duplicate_email_creates_no_extra_tasks(client, hr_h, db):
    create(client, hr_h)
    before = db.query(OnboardingTask).count()
    assert client.post("/api/employees", headers=hr_h, json=employee_payload()).status_code == 409
    assert db.query(OnboardingTask).count() == before


def test_hr_updates_task_status(client, hr_h):
    emp = create(client, hr_h)
    task = tasks_for(client, hr_h, emp["id"])[0]
    res = client.patch(f"/api/onboarding/tasks/{task['id']}", headers=hr_h, json={"status": "in_progress"})
    assert res.status_code == 200 and res.json()["status"] == "in_progress" and res.json()["completed_at"] is None
    res = client.patch(f"/api/onboarding/tasks/{task['id']}", headers=hr_h, json={"status": "completed"})
    assert res.json()["status"] == "completed" and res.json()["completed_at"] is not None
    res = client.patch(f"/api/onboarding/tasks/{task['id']}", headers=hr_h, json={"status": "pending"})
    assert res.json()["completed_at"] is None  # re-opening clears the completion time


def test_invalid_status_rejected(client, hr_h):
    task = tasks_for(client, hr_h, create(client, hr_h)["id"])[0]
    assert client.patch(f"/api/onboarding/tasks/{task['id']}", headers=hr_h, json={"status": "done"}).status_code == 422
    assert client.patch("/api/onboarding/tasks/99999", headers=hr_h, json={"status": "completed"}).status_code == 404


def test_progress_percentage(client, hr_h):
    emp = create(client, hr_h)
    tasks = tasks_for(client, hr_h, emp["id"])
    for t in tasks[:3]:
        client.patch(f"/api/onboarding/tasks/{t['id']}", headers=hr_h, json={"status": "completed"})
    client.patch(f"/api/onboarding/tasks/{tasks[3]['id']}", headers=hr_h, json={"status": "in_progress"})
    detail = client.get(f"/api/employees/{emp['id']}", headers=hr_h).json()["onboarding"]
    assert detail["completed"] == 3 and detail["in_progress"] == 1
    assert detail["percent"] == round(3 * 100 / len(tasks))
    row = next(p for p in client.get("/api/onboarding/progress", headers=hr_h).json() if p["employee_id"] == emp["id"])
    assert row["percent"] == detail["percent"] and row["total"] == len(tasks)


def test_task_filters(client, hr_h):
    emp = create(client, hr_h)
    tasks = tasks_for(client, hr_h, emp["id"])
    client.patch(f"/api/onboarding/tasks/{tasks[0]['id']}", headers=hr_h, json={"status": "completed"})
    done = client.get("/api/onboarding/tasks?status=completed", headers=hr_h).json()
    assert len(done) == 1
    it = client.get("/api/onboarding/tasks?category=it_setup", headers=hr_h).json()
    assert it and {t["category"] for t in it} == {"it_setup"}


def test_employee_updates_own_tasks_but_not_others(client, hr_h):
    mine = create(client, hr_h, email="mine@example.com", initial_password="Welcome123")
    other = create(client, hr_h, email="other@example.com", initial_password="Welcome123")
    my_h = auth_headers(client, "mine@example.com", "Welcome123")

    my_tasks = client.get("/api/onboarding/tasks", headers=my_h).json()
    assert len(my_tasks) == len(ONBOARDING_TEMPLATE) and {t["employee_id"] for t in my_tasks} == {mine["id"]}
    ok = client.patch(f"/api/onboarding/tasks/{my_tasks[0]['id']}", headers=my_h, json={"status": "completed"})
    assert ok.status_code == 200

    other_task = tasks_for(client, hr_h, other["id"])[0]
    denied = client.patch(f"/api/onboarding/tasks/{other_task['id']}", headers=my_h, json={"status": "completed"})
    assert denied.status_code == 403

    # Asking for someone else's tasks via the filter still only returns their own.
    sneaky = client.get(f"/api/onboarding/tasks?employee_id={other['id']}", headers=my_h).json()
    assert {t["employee_id"] for t in sneaky} == {mine["id"]}


def test_employee_sees_only_own_progress(client, hr_h):
    create(client, hr_h, email="mine@example.com", initial_password="Welcome123")
    create(client, hr_h, email="other@example.com")
    my_h = auth_headers(client, "mine@example.com", "Welcome123")
    rows = client.get("/api/onboarding/progress", headers=my_h).json()
    assert len(rows) == 1


def test_onboarding_requires_authentication(client):
    assert client.get("/api/onboarding/tasks").status_code == 401
    assert client.patch("/api/onboarding/tasks/1", json={"status": "completed"}).status_code == 401
