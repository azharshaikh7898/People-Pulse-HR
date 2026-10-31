import json
from contextlib import asynccontextmanager

import httpx
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from pulseagent.hr_client import HRClient
from pulseagent.mcp_server import build_server

EMP = {"id": 7, "full_name": "Dev Mishra", "email": "dev@example.com", "department": "Human Resources",
       "designation": "Talent Partner", "joining_date": "2025-01-06", "status": "active", "has_login": False,
       "created_at": "x", "password_hash_should_not_leak": "nope",
       "onboarding": {"total": 11, "completed": 11, "in_progress": 0, "pending": 0, "percent": 100}}
LEAVE = {"id": 3, "employee_id": 7, "employee_name": "Dev Mishra", "leave_type": "sick", "start_date": "2026-11-05",
         "end_date": "2026-11-07", "days": 3, "status": "pending", "reason": "Flu", "review_note": None,
         "reviewed_at": None, "created_at": "x"}


class FakeApi:
    """Records requests and answers like the PeoplePulse API."""
    def __init__(self):
        self.calls: list[httpx.Request] = []
        self.login_count = 0
        self.expire_next = False
        self.forced: dict[str, tuple[int, dict]] = {}
        self.fail_times: dict[str, int] = {}  # path -> number of 503s before succeeding

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        if path == "/api/auth/login":
            self.login_count += 1
            return httpx.Response(200, json={"access_token": f"tok{self.login_count}"})
        if self.expire_next:
            self.expire_next = False
            return httpx.Response(401, json={"detail": "expired"})
        if self.fail_times.get(path, 0) > 0:
            self.fail_times[path] -= 1
            return httpx.Response(503, json={"detail": "temporarily unavailable"})
        if path in self.forced:
            code, body = self.forced[path]
            return httpx.Response(code, json=body)
        if path == "/api/employees":
            return httpx.Response(200, json={"items": [EMP], "total": 1, "page": 1, "page_size": 10, "pages": 1})
        if path.startswith("/api/employees/"):
            return httpx.Response(200, json=EMP)
        if path == "/api/leaves":
            return httpx.Response(200, json={"items": [LEAVE], "total": 1, "page": 1, "page_size": 10, "pages": 1})
        if path.endswith("/review"):
            return httpx.Response(200, json={**LEAVE, "status": json.loads(request.content)["decision"]})
        return httpx.Response(404, json={"detail": "not found"})


@pytest.fixture
def api():
    return FakeApi()


@pytest.fixture
def client(api):
    return HRClient("http://hr.test", "hr@example.com", "pw", transport=httpx.MockTransport(api.handler))


@pytest.fixture
def mcp_session(client):
    @asynccontextmanager
    async def open_session(read_only=True):
        server = build_server(client, read_only=read_only)
        async with create_connected_server_and_client_session(server._mcp_server) as session:
            yield session
    return open_session


@pytest.fixture
def agent_factory(mcp_session):
    """Builds an agent whose tools come from the real MCP server (in memory) and whose model is scripted."""
    from langgraph.checkpoint.memory import MemorySaver

    from pulseagent.agent import build_agent, load_hr_tools
    from pulseagent.testing import ScriptedChatModel

    @asynccontextmanager
    async def make(script, checkpointer=None, **kw):
        async with mcp_session(read_only=False) as session:
            tools = await load_hr_tools(session)
            model = ScriptedChatModel(script=script)
            kw.setdefault("retry_delay", 0)
            yield build_agent(model, tools, checkpointer or MemorySaver(), **kw), model, tools
    return make
