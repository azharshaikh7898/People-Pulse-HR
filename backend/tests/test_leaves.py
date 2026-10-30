from datetime import date, timedelta

from app.core.constants import Role
from tests.conftest import auth_headers, leave_payload, make_account, next_monday


def submit(client, headers, start, **kw):
    return client.post("/api/leaves", headers=headers, json=leave_payload(start, **kw))


def balance(client, headers, year, leave_type="annual"):
    body = client.get(f"/api/leaves/balance?year={year}", headers=headers).json()
    return next(b for b in body["balances"] if b["leave_type"] == leave_type)


def test_employee_submits_leave_request(client, emp_h):
    start = next_monday()
    res = submit(client, emp_h, start)  # Mon-Fri week
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "pending" and body["days"] == 5
    assert body["employee_name"] == "Eli Employee"


def test_weekends_are_not_counted(client, emp_h):
    start = next_monday()
    res = submit(client, emp_h, start, days=7)  # Mon..Sun
    assert res.json()["days"] == 5


def test_weekend_only_request_rejected(client, emp_h):
    saturday = next_monday() + timedelta(days=5)
    res = submit(client, emp_h, saturday, days=2)
    assert res.status_code == 400 and "weekend" in res.json()["detail"]


def test_end_before_start_rejected(client, emp_h):
    start = next_monday()
    body = {"leave_type": "annual", "start_date": start.isoformat(),
            "end_date": (start - timedelta(days=1)).isoformat(), "reason": "Bad dates"}
    res = client.post("/api/leaves", headers=emp_h, json=body)
    assert res.status_code == 422 and "End date" in res.json()["detail"]


def test_invalid_input_rejected(client, emp_h):
    start = next_monday()
    assert client.post("/api/leaves", headers=emp_h, json={**leave_payload(start), "leave_type": "holiday"}).status_code == 422
    assert client.post("/api/leaves", headers=emp_h, json={**leave_payload(start), "reason": " "}).status_code == 422
    assert client.post("/api/leaves", headers=emp_h, json={**leave_payload(start), "start_date": "not-a-date"}).status_code == 422


def test_dates_too_far_in_past_rejected(client, emp_h):
    old = date.today() - timedelta(days=90)
    res = submit(client, emp_h, old, days=1)
    assert res.status_code == 400


def test_request_spanning_two_years_rejected(client, emp_h):
    year = date.today().year
    body = {"leave_type": "annual", "start_date": f"{year}-12-29", "end_date": f"{year + 1}-01-02", "reason": "New year"}
    res = client.post("/api/leaves", headers=emp_h, json=body)
    assert res.status_code == 400


def test_overlapping_requests_rejected(client, emp_h):
    start = next_monday()
    assert submit(client, emp_h, start).status_code == 201
    exact = submit(client, emp_h, start)
    partial = submit(client, emp_h, start + timedelta(days=2), days=2)
    inside = submit(client, emp_h, start + timedelta(days=1), days=1)
    for res in (exact, partial, inside):
        assert res.status_code == 409 and "overlap" in res.json()["detail"]


def test_back_to_back_requests_do_not_overlap(client, emp_h):
    start = next_monday()
    assert submit(client, emp_h, start, days=5).status_code == 201
    assert submit(client, emp_h, start + timedelta(days=7), days=5).status_code == 201


def test_cancelled_and_rejected_requests_do_not_block_dates(client, emp_h, hr_h):
    start = next_monday()
    first = submit(client, emp_h, start).json()
    assert client.post(f"/api/leaves/{first['id']}/cancel", headers=emp_h).status_code == 200
    second = submit(client, emp_h, start)
    assert second.status_code == 201
    client.patch(f"/api/leaves/{second.json()['id']}/review", headers=hr_h, json={"decision": "rejected"})
    assert submit(client, emp_h, start).status_code == 201


def test_other_employees_can_take_the_same_dates(client, emp_h, db):
    start = next_monday()
    make_account(db, "second@test.example", Role.EMPLOYEE, "Sam Second")
    second_h = auth_headers(client, "second@test.example")
    assert submit(client, emp_h, start).status_code == 201
    assert submit(client, second_h, start).status_code == 201


def test_insufficient_balance_rejected(client, emp_h):
    start = next_monday()
    # casual allowance is 6 days; a 2-week block has 10 working days
    res = submit(client, emp_h, start, days=14, leave_type="casual")
    assert res.status_code == 422 and "Not enough casual leave" in res.json()["detail"]


def test_balance_counts_pending_then_approved_and_restores_on_reject(client, emp_h, hr_h):
    start = next_monday()
    year = start.year
    assert balance(client, emp_h, year)["remaining"] == 18
    leave = submit(client, emp_h, start).json()  # 5 days
    b = balance(client, emp_h, year)
    assert (b["pending"], b["used"], b["remaining"]) == (5, 0, 13)

    client.patch(f"/api/leaves/{leave['id']}/review", headers=hr_h, json={"decision": "approved"})
    b = balance(client, emp_h, year)
    assert (b["pending"], b["used"], b["remaining"]) == (0, 5, 13)

    other = submit(client, emp_h, start + timedelta(days=14)).json()
    client.patch(f"/api/leaves/{other['id']}/review", headers=hr_h, json={"decision": "rejected"})
    assert balance(client, emp_h, year)["remaining"] == 13  # rejected days are given back


def test_cumulative_requests_cannot_exceed_allowance(client, emp_h):
    start = next_monday()
    for week in range(3):  # 15 of 18 annual days
        assert submit(client, emp_h, start + timedelta(weeks=week)).status_code == 201
    over = submit(client, emp_h, start + timedelta(weeks=3))  # needs 5, only 3 left
    assert over.status_code == 422 and "only 3 remain" in over.json()["detail"]
    assert submit(client, emp_h, start + timedelta(weeks=3), days=3).status_code == 201  # exactly 3 fits


def test_unpaid_leave_has_no_cap(client, emp_h):
    start = next_monday()
    assert submit(client, emp_h, start, days=21, leave_type="unpaid").status_code == 201
    unpaid = balance(client, emp_h, start.year, "unpaid")
    assert unpaid["allowance"] is None and unpaid["remaining"] is None


def test_hr_approves_request(client, emp_h, hr_h, hr_user):
    leave = submit(client, emp_h, next_monday()).json()
    res = client.patch(f"/api/leaves/{leave['id']}/review", headers=hr_h, json={"decision": "approved", "note": "Enjoy"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "approved" and body["review_note"] == "Enjoy" and body["reviewed_at"]


def test_hr_rejects_request(client, emp_h, hr_h):
    leave = submit(client, emp_h, next_monday()).json()
    res = client.patch(f"/api/leaves/{leave['id']}/review", headers=hr_h, json={"decision": "rejected", "note": "Release week"})
    assert res.status_code == 200 and res.json()["status"] == "rejected"


def test_request_cannot_be_reviewed_twice(client, emp_h, hr_h):
    leave = submit(client, emp_h, next_monday()).json()
    client.patch(f"/api/leaves/{leave['id']}/review", headers=hr_h, json={"decision": "approved"})
    again = client.patch(f"/api/leaves/{leave['id']}/review", headers=hr_h, json={"decision": "rejected"})
    assert again.status_code == 409


def test_review_decision_must_be_final(client, emp_h, hr_h):
    leave = submit(client, emp_h, next_monday()).json()
    for bad in ("pending", "cancelled", "maybe"):
        assert client.patch(f"/api/leaves/{leave['id']}/review", headers=hr_h, json={"decision": bad}).status_code == 422
    assert client.patch("/api/leaves/9999/review", headers=hr_h, json={"decision": "approved"}).status_code == 404


def test_employee_cannot_review(client, emp_h):
    leave = submit(client, emp_h, next_monday()).json()
    res = client.patch(f"/api/leaves/{leave['id']}/review", headers=emp_h, json={"decision": "approved"})
    assert res.status_code == 403


def test_hr_cannot_approve_own_request(client, hr_h):
    leave = submit(client, hr_h, next_monday()).json()
    res = client.patch(f"/api/leaves/{leave['id']}/review", headers=hr_h, json={"decision": "approved"})
    assert res.status_code == 403 and "own" in res.json()["detail"]


def test_employee_sees_only_own_requests(client, emp_h, hr_h, db):
    start = next_monday()
    make_account(db, "second@test.example", Role.EMPLOYEE, "Sam Second")
    second_h = auth_headers(client, "second@test.example")
    submit(client, emp_h, start)
    submit(client, second_h, start)
    mine = client.get("/api/leaves", headers=emp_h).json()
    assert mine["total"] == 1 and mine["items"][0]["employee_name"] == "Eli Employee"
    assert client.get("/api/leaves", headers=hr_h).json()["total"] == 2


def test_hr_filters_by_status_and_paginates(client, emp_h, hr_h):
    start = next_monday()
    ids = [submit(client, emp_h, start + timedelta(weeks=w), days=1).json()["id"] for w in range(3)]
    client.patch(f"/api/leaves/{ids[0]}/review", headers=hr_h, json={"decision": "approved"})
    pending = client.get("/api/leaves?status=pending", headers=hr_h).json()
    assert pending["total"] == 2
    page = client.get("/api/leaves?page=1&page_size=2", headers=hr_h).json()
    assert len(page["items"]) == 2 and page["pages"] == 2
    assert client.get("/api/leaves?status=bogus", headers=hr_h).status_code == 422


def test_employee_cancels_own_pending_request_only(client, emp_h, hr_h, db):
    start = next_monday()
    leave = submit(client, emp_h, start).json()
    make_account(db, "second@test.example", Role.EMPLOYEE, "Sam Second")
    second_h = auth_headers(client, "second@test.example")
    assert client.post(f"/api/leaves/{leave['id']}/cancel", headers=second_h).status_code == 403
    assert client.post(f"/api/leaves/{leave['id']}/cancel", headers=emp_h).json()["status"] == "cancelled"
    assert client.post(f"/api/leaves/{leave['id']}/cancel", headers=emp_h).status_code == 409  # already cancelled


def test_cannot_cancel_after_rejection(client, emp_h, hr_h):
    leave = submit(client, emp_h, next_monday()).json()
    client.patch(f"/api/leaves/{leave['id']}/review", headers=hr_h, json={"decision": "rejected"})
    assert client.post(f"/api/leaves/{leave['id']}/cancel", headers=emp_h).status_code == 409


def test_balance_is_private_but_hr_can_view_anyone(client, emp_h, hr_h, emp_user, hr_user):
    assert client.get(f"/api/leaves/balance?employee_id={hr_user.employee_id}", headers=emp_h).status_code == 403
    assert client.get(f"/api/leaves/balance?employee_id={emp_user.employee_id}", headers=hr_h).status_code == 200


def test_inactive_employee_cannot_request_leave(client, emp_h, hr_h, emp_user):
    client.post(f"/api/employees/{emp_user.employee_id}/deactivate", headers=hr_h)
    # The deactivated user's token no longer works at all.
    assert submit(client, emp_h, next_monday()).status_code == 401


def test_leave_requires_authentication(client):
    assert client.post("/api/leaves", json=leave_payload(next_monday())).status_code == 401
    assert client.get("/api/leaves").status_code == 401
