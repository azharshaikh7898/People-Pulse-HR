from datetime import timedelta

from tests.conftest import employee_payload, leave_payload, next_monday, auth_headers


def add_employee(client, hr_h, n, department="Engineering", password=None):
    payload = employee_payload(full_name=f"Person {n}", email=f"person{n}@example.com", department=department)
    if password:
        payload["initial_password"] = password
    res = client.post("/api/employees", headers=hr_h, json=payload)
    assert res.status_code == 201, res.text
    return res.json()


def dashboard(client, hr_h):
    res = client.get("/api/analytics/dashboard", headers=hr_h)
    assert res.status_code == 200
    return res.json()


def test_dashboard_with_only_the_hr_account(client, hr_h):
    d = dashboard(client, hr_h)
    assert d["total_active_employees"] == 1
    assert d["departments"] == [{"department": "Human Resources", "count": 1}]
    assert d["leaves"] == {"pending": 0, "approved": 0, "rejected": 0}
    assert d["onboarding"]["total"] == 0 and d["recent_leaves"] == []


def test_dashboard_counts_match_database(client, hr_h):
    add_employee(client, hr_h, 1, "Engineering")
    add_employee(client, hr_h, 2, "Engineering")
    add_employee(client, hr_h, 3, "Sales")
    d = dashboard(client, hr_h)
    assert d["total_active_employees"] == 4  # 3 + the HR admin
    dist = {x["department"]: x["count"] for x in d["departments"]}
    assert dist == {"Engineering": 2, "Sales": 1, "Human Resources": 1}
    assert d["departments"][0]["department"] == "Engineering"  # largest first


def test_inactive_employees_are_excluded_from_active_counts(client, hr_h):
    emp = add_employee(client, hr_h, 1)
    before = dashboard(client, hr_h)
    client.post(f"/api/employees/{emp['id']}/deactivate", headers=hr_h)
    after = dashboard(client, hr_h)
    assert after["total_active_employees"] == before["total_active_employees"] - 1
    assert after["total_inactive_employees"] == 1
    assert after["onboarding"]["total"] == 0  # their tasks no longer count


def test_leave_statistics(client, hr_h):
    e1 = add_employee(client, hr_h, 1, password="Welcome123")
    start = next_monday()
    h1 = auth_headers(client, "person1@example.com", "Welcome123")
    ids = []
    for week in range(3):
        res = client.post("/api/leaves", headers=h1, json=leave_payload(start + timedelta(weeks=week), days=1))
        ids.append(res.json()["id"])
    client.patch(f"/api/leaves/{ids[0]}/review", headers=hr_h, json={"decision": "approved"})
    client.patch(f"/api/leaves/{ids[1]}/review", headers=hr_h, json={"decision": "rejected"})
    d = dashboard(client, hr_h)
    assert d["leaves"] == {"pending": 1, "approved": 1, "rejected": 1}
    assert len(d["recent_leaves"]) == 3 and d["recent_leaves"][0]["employee_name"] == "Person 1"


def test_onboarding_statistics(client, hr_h):
    a = add_employee(client, hr_h, 1)
    b = add_employee(client, hr_h, 2)
    tasks_a = client.get(f"/api/onboarding/tasks?employee_id={a['id']}", headers=hr_h).json()
    per_employee = len(tasks_a)
    for t in tasks_a:
        client.patch(f"/api/onboarding/tasks/{t['id']}", headers=hr_h, json={"status": "completed"})
    tasks_b = client.get(f"/api/onboarding/tasks?employee_id={b['id']}", headers=hr_h).json()
    client.patch(f"/api/onboarding/tasks/{tasks_b[0]['id']}", headers=hr_h, json={"status": "in_progress"})

    o = dashboard(client, hr_h)["onboarding"]
    assert o["total"] == 2 * per_employee
    assert o["completed"] == per_employee
    assert o["in_progress"] == 1
    assert o["pending"] == per_employee - 1
    assert o["employees_onboarding"] == 1  # only B still has unfinished tasks


def test_recent_employees_are_newest_first_and_capped(client, hr_h):
    for n in range(7):
        add_employee(client, hr_h, n)
    recent = dashboard(client, hr_h)["recent_employees"]
    assert len(recent) == 5 and recent[0]["full_name"] == "Person 6"


def test_dashboard_requires_hr_role(client, emp_h):
    assert client.get("/api/analytics/dashboard", headers=emp_h).status_code == 403
    assert client.get("/api/analytics/dashboard").status_code == 401
