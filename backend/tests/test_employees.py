from app.models import Employee
from tests.conftest import PASSWORD, auth_headers, employee_payload, login


def create(client, headers, **overrides):
    return client.post("/api/employees", headers=headers, json=employee_payload(**overrides))


def test_hr_creates_employee(client, hr_h):
    res = create(client, hr_h)
    assert res.status_code == 201
    body = res.json()
    assert body["full_name"] == "Asha Verma"
    assert body["status"] == "active"
    assert body["has_login"] is False
    assert body["onboarding"]["total"] > 0


def test_email_is_normalised_to_lowercase(client, hr_h):
    res = create(client, hr_h, email="Mixed.Case@Example.com")
    assert res.status_code == 201 and res.json()["email"] == "mixed.case@example.com"


def test_duplicate_email_rejected(client, hr_h):
    assert create(client, hr_h).status_code == 201
    dup = create(client, hr_h, full_name="Someone Else")
    assert dup.status_code == 409
    assert "already exists" in dup.json()["detail"]


def test_duplicate_email_is_case_insensitive(client, hr_h):
    assert create(client, hr_h).status_code == 201
    assert create(client, hr_h, email="ASHA.VERMA@EXAMPLE.COM").status_code == 409


def test_cannot_reuse_an_existing_login_email(client, hr_h, hr_user):
    assert create(client, hr_h, email=hr_user.email).status_code == 409


def test_validation_errors(client, hr_h):
    bad_email = create(client, hr_h, email="not-an-email")
    assert bad_email.status_code == 422 and "email" in bad_email.json()["detail"]
    assert create(client, hr_h, department="Underwater Basket Weaving").status_code == 422
    assert create(client, hr_h, full_name="A").status_code == 422
    assert create(client, hr_h, joining_date="1990-01-01").status_code == 422
    assert create(client, hr_h, joining_date="2999-01-01").status_code == 422
    missing = client.post("/api/employees", headers=hr_h, json={"full_name": "Only Name"})
    assert missing.status_code == 422 and len(missing.json()["errors"]) >= 3


def test_nothing_saved_when_validation_fails(client, hr_h, db):
    create(client, hr_h, email="bad")
    assert db.query(Employee).filter_by(full_name="Asha Verma").count() == 0


def test_create_with_initial_password_allows_login(client, hr_h):
    res = create(client, hr_h, initial_password="Welcome123")
    assert res.status_code == 201 and res.json()["has_login"] is True
    login_res = login(client, "asha.verma@example.com", "Welcome123")
    assert login_res.status_code == 200 and login_res.json()["user"]["role"] == "employee"


def test_weak_initial_password_rejected(client, hr_h):
    assert create(client, hr_h, initial_password="short").status_code == 422
    assert create(client, hr_h, initial_password="onlyletters").status_code == 422


def test_get_update_employee(client, hr_h):
    emp_id = create(client, hr_h).json()["id"]
    assert client.get(f"/api/employees/{emp_id}", headers=hr_h).json()["email"] == "asha.verma@example.com"
    res = client.put(f"/api/employees/{emp_id}", headers=hr_h,
                     json={"designation": "Senior Engineer", "department": "Design"})
    assert res.status_code == 200
    assert res.json()["designation"] == "Senior Engineer" and res.json()["department"] == "Design"


def test_update_to_existing_email_rejected(client, hr_h):
    create(client, hr_h)
    other = create(client, hr_h, email="other@example.com").json()["id"]
    res = client.put(f"/api/employees/{other}", headers=hr_h, json={"email": "asha.verma@example.com"})
    assert res.status_code == 409


def test_update_with_empty_body_rejected(client, hr_h):
    emp_id = create(client, hr_h).json()["id"]
    assert client.put(f"/api/employees/{emp_id}", headers=hr_h, json={}).status_code == 400


def test_missing_employee_is_404(client, hr_h):
    assert client.get("/api/employees/9999", headers=hr_h).status_code == 404
    assert client.put("/api/employees/9999", headers=hr_h, json={"designation": "x1"}).status_code == 404


def test_deactivate_and_reactivate(client, hr_h):
    emp_id = create(client, hr_h, initial_password="Welcome123").json()["id"]
    res = client.post(f"/api/employees/{emp_id}/deactivate", headers=hr_h)
    assert res.status_code == 200 and res.json()["status"] == "inactive"
    assert login(client, "asha.verma@example.com", "Welcome123").status_code == 403  # login disabled too
    res = client.post(f"/api/employees/{emp_id}/activate", headers=hr_h)
    assert res.json()["status"] == "active"
    assert login(client, "asha.verma@example.com", "Welcome123").status_code == 200


def test_deactivated_users_existing_token_stops_working(client, hr_h):
    emp_id = create(client, hr_h, initial_password="Welcome123").json()["id"]
    headers = auth_headers(client, "asha.verma@example.com", "Welcome123")
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    client.post(f"/api/employees/{emp_id}/deactivate", headers=hr_h)
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_hr_cannot_deactivate_self(client, hr_h, hr_user):
    res = client.post(f"/api/employees/{hr_user.employee_id}/deactivate", headers=hr_h)
    assert res.status_code == 400


def test_search_filter_and_pagination(client, hr_h):
    names = [("Zara Khan", "Sales"), ("Amit Rao", "Engineering"), ("Maya Iyer", "Engineering"), ("Rohan Das", "Finance")]
    for i, (name, dept) in enumerate(names):
        create(client, hr_h, full_name=name, email=f"p{i}@example.com", department=dept)

    # The HR account from the fixture is also an employee, so 5 people exist in total.
    by_dept = client.get("/api/employees?department=Engineering", headers=hr_h).json()
    assert by_dept["total"] == 2 and {e["department"] for e in by_dept["items"]} == {"Engineering"}

    search = client.get("/api/employees?q=maya", headers=hr_h).json()
    assert search["total"] == 1 and search["items"][0]["full_name"] == "Maya Iyer"

    by_email = client.get("/api/employees?q=p3@example", headers=hr_h).json()
    assert by_email["total"] == 1

    page1 = client.get("/api/employees?page=1&page_size=2", headers=hr_h).json()
    page3 = client.get("/api/employees?page=3&page_size=2", headers=hr_h).json()
    assert page1["total"] == 5 and page1["pages"] == 3 and len(page1["items"]) == 2
    assert len(page3["items"]) == 1
    names_sorted = [e["full_name"] for e in client.get("/api/employees?page_size=100", headers=hr_h).json()["items"]]
    assert names_sorted == sorted(names_sorted)


def test_search_treats_wildcards_literally(client, hr_h):
    create(client, hr_h)
    assert client.get("/api/employees?q=%25", headers=hr_h).json()["total"] == 0  # a literal "%"


def test_status_filter_and_page_size_limit(client, hr_h):
    emp_id = create(client, hr_h).json()["id"]
    client.post(f"/api/employees/{emp_id}/deactivate", headers=hr_h)
    inactive = client.get("/api/employees?status=inactive", headers=hr_h).json()
    assert inactive["total"] == 1
    assert client.get("/api/employees?page_size=1000", headers=hr_h).status_code == 422
    assert client.get("/api/employees?status=bogus", headers=hr_h).status_code == 422


def test_employee_can_only_view_own_record(client, emp_h, emp_user, hr_user):
    own = client.get(f"/api/employees/{emp_user.employee_id}", headers=emp_h)
    assert own.status_code == 200
    other = client.get(f"/api/employees/{hr_user.employee_id}", headers=emp_h)
    assert other.status_code == 403


def test_employee_cannot_modify_employees(client, emp_h, emp_user):
    assert client.put(f"/api/employees/{emp_user.employee_id}", headers=emp_h, json={"designation": "CEO"}).status_code == 403
    assert client.post(f"/api/employees/{emp_user.employee_id}/deactivate", headers=emp_h).status_code == 403
