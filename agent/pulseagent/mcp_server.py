"""MCP server exposing PeoplePulse HR operations as tools.

Run (stdio):   python -m pulseagent.mcp_server
Read-only mode (default) does not even *register* the write tools, so a client cannot discover
or call them. Set HR_MCP_READ_ONLY=0 to enable them. The backend still enforces roles on every call.
"""
import os
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from pulseagent.hr_client import HRApiError, HRClient

Status = Literal["active", "inactive"]
LeaveStatus = Literal["pending", "approved", "rejected", "cancelled"]
TaskStatus = Literal["pending", "in_progress", "completed"]
Limit = Annotated[int, Field(ge=1, le=25, description="Maximum rows to return")]


def _emp(e: dict) -> dict:
    return {k: e[k] for k in ("id", "full_name", "email", "department", "designation", "joining_date", "status")}


def _leave(l: dict) -> dict:
    return {k: l[k] for k in ("id", "employee_id", "employee_name", "leave_type", "start_date", "end_date",
                              "days", "status", "reason")}


def _task(t: dict) -> dict:
    return {k: t[k] for k in ("id", "employee_id", "employee_name", "title", "category", "status", "due_date")}


def build_server(client: HRClient, read_only: bool = True) -> FastMCP:
    mcp = FastMCP("peoplepulse-hr")

    async def call(method: str, path: str, **kw):
        try:
            return await client.request(method, path, **kw)
        except HRApiError as exc:
            raise ToolError(str(exc)) from exc

    # ------------------------------ read tools ------------------------------
    @mcp.tool()
    async def search_employees(query: str | None = None, department: str | None = None,
                               status: Status | None = None, limit: Limit = 10) -> dict:
        """Search employees by name, email or designation, optionally filtered by department and status."""
        data = await call("GET", "/api/employees",
                          params={"q": query, "department": department, "status": status, "page_size": limit})
        return {"total": data["total"], "employees": [_emp(e) for e in data["items"]]}

    @mcp.tool()
    async def get_employee(employee_id: int) -> dict:
        """Full record for one employee, including onboarding progress."""
        e = await call("GET", f"/api/employees/{employee_id}")
        return {**_emp(e), "has_login": e["has_login"], "onboarding": e["onboarding"]}

    @mcp.tool()
    async def get_leave_balance(employee_id: int | None = None, year: int | None = None) -> dict:
        """Leave balance (annual, sick, casual, unpaid) for an employee. Defaults to the signed-in user and this year."""
        return await call("GET", "/api/leaves/balance", params={"employee_id": employee_id, "year": year})

    @mcp.tool()
    async def list_leave_requests(status: LeaveStatus | None = None, employee_id: int | None = None,
                                  limit: Limit = 10) -> dict:
        """List leave requests, newest first. Filter by status or employee."""
        data = await call("GET", "/api/leaves",
                          params={"status": status, "employee_id": employee_id, "page_size": limit})
        return {"total": data["total"], "requests": [_leave(l) for l in data["items"]]}

    @mcp.tool()
    async def list_onboarding_tasks(employee_id: int | None = None, status: TaskStatus | None = None,
                                    limit: Limit = 15) -> dict:
        """List onboarding tasks, optionally for one employee or one status."""
        tasks = await call("GET", "/api/onboarding/tasks", params={"employee_id": employee_id, "status": status})
        return {"total": len(tasks), "tasks": [_task(t) for t in tasks[:limit]]}

    @mcp.tool()
    async def get_onboarding_progress(limit: Limit = 10) -> dict:
        """Onboarding progress per employee, least complete first."""
        rows = await call("GET", "/api/onboarding/progress")
        return {"total": len(rows), "employees": rows[:limit]}

    @mcp.tool()
    async def get_dashboard_summary() -> dict:
        """Company-wide headcount, leave counts and onboarding totals (HR only)."""
        d = await call("GET", "/api/analytics/dashboard")
        return {k: d[k] for k in ("total_active_employees", "total_inactive_employees", "departments",
                                  "leaves", "onboarding")}

    # ------------------------------ write tools ------------------------------
    if not read_only:
        @mcp.tool()
        async def review_leave_request(leave_id: int, decision: Literal["approved", "rejected"],
                                       note: str | None = None) -> dict:
            """Approve or reject a PENDING leave request (HR only). Changes data."""
            return _leave(await call("PATCH", f"/api/leaves/{leave_id}/review",
                                     json={"decision": decision, "note": note}))

        @mcp.tool()
        async def update_onboarding_task(task_id: int, status: TaskStatus) -> dict:
            """Set an onboarding task's status. Changes data."""
            return _task(await call("PATCH", f"/api/onboarding/tasks/{task_id}", json={"status": status}))

    return mcp


if __name__ == "__main__":
    server = build_server(HRClient(), read_only=os.environ.get("HR_MCP_READ_ONLY", "1") != "0")
    server.run()  # stdio transport
