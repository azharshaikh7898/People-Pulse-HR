"""Async client for the PeoplePulse REST API.

The agent never touches the database. Every action goes through the API, so the backend's
role checks, validation and business rules always apply.
"""
import os

import httpx


RETRYABLE_MARK = "(retryable)"  # appended to transient errors so the agent harness knows it may retry


class HRApiError(Exception):
    """An API call failed. The message is safe to show to the model (it contains no secrets)."""


class HRClient:
    def __init__(self, base_url: str | None = None, email: str | None = None, password: str | None = None,
                 transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = (base_url or os.environ.get("HR_API_URL", "http://localhost:8000")).rstrip("/")
        self._email = email or os.environ.get("HR_API_EMAIL", "")
        self._password = password or os.environ.get("HR_API_PASSWORD", "")
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=30, transport=transport)
        self._token: str | None = None

    async def _login(self) -> None:
        if not self._email or not self._password:
            raise HRApiError("HR_API_EMAIL and HR_API_PASSWORD are not configured")
        res = await self._http.post("/api/auth/login", data={"username": self._email, "password": self._password})
        if res.status_code != 200:
            raise HRApiError("Could not sign in to the HR API with the configured account")
        self._token = res.json()["access_token"]

    async def request(self, method: str, path: str, *, params: dict | None = None, json: dict | None = None):
        clean = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        for attempt in (1, 2):
            if not self._token:
                await self._login()
            try:
                res = await self._http.request(method, path, params=clean, json=json,
                                               headers={"Authorization": f"Bearer {self._token}"})
            except httpx.HTTPError as exc:
                raise HRApiError(f"The HR API is unreachable ({type(exc).__name__}) {RETRYABLE_MARK}") from exc
            if res.status_code == 401 and attempt == 1:
                self._token = None  # token expired or revoked: sign in again once
                continue
            break
        if res.status_code >= 400:
            try:
                detail = res.json().get("detail", "")
            except ValueError:
                detail = ""
            mark = f" {RETRYABLE_MARK}" if res.status_code >= 500 or res.status_code == 429 else ""
            raise HRApiError(f"HR API error {res.status_code}: {detail or 'request failed'}{mark}")
        return None if res.status_code == 204 else res.json()

    async def aclose(self) -> None:
        await self._http.aclose()
