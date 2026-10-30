from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.models import User
from tests.conftest import PASSWORD, auth_headers, login, make_account


def test_login_success_returns_token_and_user(client, hr_user):
    res = login(client, "hr@test.example")
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer" and body["access_token"]
    assert body["user"]["role"] == "hr_admin"
    assert "hashed_password" not in body["user"]


def test_login_is_case_insensitive_on_email(client, hr_user):
    assert login(client, "HR@Test.Example").status_code == 200


def test_login_wrong_password_rejected(client, hr_user):
    res = login(client, "hr@test.example", "WrongPass1")
    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect email or password"


def test_login_unknown_email_gives_same_error(client):
    res = login(client, "nobody@test.example")
    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect email or password"


def test_inactive_user_cannot_log_in(client, db):
    make_account(db, "gone@test.example", active=False)
    assert login(client, "gone@test.example").status_code == 403


def test_password_is_hashed_in_database(db, hr_user):
    stored = db.query(User).filter_by(email="hr@test.example").one().hashed_password
    assert stored != PASSWORD and stored.startswith("$2")


def test_protected_endpoint_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/employees").status_code == 401
    assert client.get("/api/analytics/dashboard").status_code == 401


def test_garbage_token_rejected(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert res.status_code == 401


def test_expired_token_rejected(client, hr_user):
    expired = jwt.encode(
        {"sub": str(hr_user.id), "role": "hr_admin", "jti": "x1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_token_signed_with_wrong_key_rejected(client, hr_user):
    forged = jwt.encode(
        {"sub": str(hr_user.id), "role": "hr_admin", "jti": "x2", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "some-other-secret-key-that-is-long-enough-123", algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_me_returns_current_user(client, hr_h):
    res = client.get("/api/auth/me", headers=hr_h)
    assert res.status_code == 200 and res.json()["email"] == "hr@test.example"


def test_logout_invalidates_token(client, hr_h):
    assert client.get("/api/auth/me", headers=hr_h).status_code == 200
    assert client.post("/api/auth/logout", headers=hr_h).status_code == 204
    assert client.get("/api/auth/me", headers=hr_h).status_code == 401


def test_employee_cannot_use_hr_endpoints(client, emp_h):
    assert client.get("/api/employees", headers=emp_h).status_code == 403
    assert client.get("/api/analytics/dashboard", headers=emp_h).status_code == 403
    res = client.post("/api/employees", headers=emp_h, json={})
    assert res.status_code == 403  # permission is checked before the body is validated


def test_change_password(client, hr_user, hr_h):
    res = client.put("/api/auth/me/password", headers=hr_h,
                     json={"current_password": PASSWORD, "new_password": "NewPassw0rd"})
    assert res.status_code == 204
    assert login(client, "hr@test.example", PASSWORD).status_code == 401
    assert login(client, "hr@test.example", "NewPassw0rd").status_code == 200


def test_change_password_rejects_wrong_current_and_weak_new(client, hr_h):
    bad_current = client.put("/api/auth/me/password", headers=hr_h,
                             json={"current_password": "nope12345", "new_password": "NewPassw0rd"})
    assert bad_current.status_code == 400
    weak = client.put("/api/auth/me/password", headers=hr_h,
                      json={"current_password": PASSWORD, "new_password": "short"})
    assert weak.status_code == 422
