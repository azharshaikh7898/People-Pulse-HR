import json

READ_TOOLS = {"search_employees", "get_employee", "get_leave_balance", "list_leave_requests",
              "list_onboarding_tasks", "get_onboarding_progress", "get_dashboard_summary"}
WRITE_TOOLS = {"review_leave_request", "update_onboarding_task"}


def payload(result):
    return json.loads(result.content[0].text)


async def test_read_only_mode_hides_write_tools(mcp_session):
    async with mcp_session(read_only=True) as s:
        names = {t.name for t in (await s.list_tools()).tools}
    assert names == READ_TOOLS


async def test_write_tools_registered_only_when_enabled(mcp_session):
    async with mcp_session(read_only=False) as s:
        names = {t.name for t in (await s.list_tools()).tools}
    assert names == READ_TOOLS | WRITE_TOOLS


async def test_tool_schemas_validate_inputs(mcp_session):
    async with mcp_session() as s:
        too_big = await s.call_tool("search_employees", {"limit": 500})
        bad_status = await s.call_tool("search_employees", {"status": "fired"})
    assert too_big.isError and bad_status.isError


async def test_search_passes_filters_and_trims_fields(mcp_session, api):
    async with mcp_session() as s:
        result = await s.call_tool("search_employees", {"query": "dev", "department": "Human Resources", "limit": 5})
    data = payload(result)
    assert data["total"] == 1 and data["employees"][0]["full_name"] == "Dev Mishra"
    assert "created_at" not in data["employees"][0] and "password_hash_should_not_leak" not in data["employees"][0]
    q = dict(api.calls[-1].url.params)
    assert q == {"q": "dev", "department": "Human Resources", "page_size": "5"}  # unset filters are not sent


async def test_requests_carry_bearer_token(mcp_session, api):
    async with mcp_session() as s:
        await s.call_tool("get_employee", {"employee_id": 7})
    assert api.calls[-1].headers["authorization"] == "Bearer tok1"


async def test_expired_token_triggers_one_relogin(mcp_session, api):
    async with mcp_session() as s:
        await s.call_tool("get_employee", {"employee_id": 7})
        api.expire_next = True
        result = await s.call_tool("get_employee", {"employee_id": 7})
    assert not result.isError and api.login_count == 2
    assert api.calls[-1].headers["authorization"] == "Bearer tok2"


async def test_api_errors_become_tool_errors_with_the_reason(mcp_session, api):
    api.forced["/api/employees/99"] = (404, {"detail": "Employee not found"})
    async with mcp_session() as s:
        result = await s.call_tool("get_employee", {"employee_id": 99})
    assert result.isError and "Employee not found" in result.content[0].text and "404" in result.content[0].text


async def test_permission_denied_by_backend_is_reported(mcp_session, api):
    api.forced["/api/analytics/dashboard"] = (403, {"detail": "This action is restricted to HR administrators"})
    async with mcp_session() as s:
        result = await s.call_tool("get_dashboard_summary", {})
    assert result.isError and "restricted to HR" in result.content[0].text


async def test_review_tool_sends_decision_and_note(mcp_session, api):
    async with mcp_session(read_only=False) as s:
        result = await s.call_tool("review_leave_request", {"leave_id": 3, "decision": "approved", "note": "ok"})
    assert payload(result)["status"] == "approved"
    assert json.loads(api.calls[-1].content) == {"decision": "approved", "note": "ok"}
    assert api.calls[-1].method == "PATCH"


async def test_review_rejects_invalid_decision(mcp_session):
    async with mcp_session(read_only=False) as s:
        result = await s.call_tool("review_leave_request", {"leave_id": 3, "decision": "pending"})
    assert result.isError
