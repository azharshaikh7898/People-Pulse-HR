from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, is_hr, require_hr
from app.core.constants import LeaveStatus
from app.core.errors import bad_request, forbidden
from app.database import get_db
from app.models.user import User
from app.schemas.common import Page, make_page
from app.schemas.leave import BalanceOut, LeaveCreate, LeaveOut, LeaveReview
from app.services import leaves as leave_service

router = APIRouter(prefix="/leaves", tags=["Leave management"])


@router.post("", response_model=LeaveOut, status_code=status.HTTP_201_CREATED, summary="Submit a leave request")
def create_leave(body: LeaveCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.employee_id is None:
        raise bad_request("Your account is not linked to an employee profile")
    return leave_service.create_request(db, user.employee_id, body)


@router.get("", response_model=Page[LeaveOut], summary="List leave requests (HR sees all, employees see their own)")
def list_leaves(
    status_: LeaveStatus | None = Query(None, alias="status"),
    employee_id: int | None = None,
    mine: bool = Query(False, description="HR only: restrict to my own requests"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_hr(user):
        scope = user.employee_id
        if scope is None:
            return make_page([], 0, page, page_size)
    else:
        scope = user.employee_id if mine else employee_id
    items, total = leave_service.list_requests(db, scope, status_, page, page_size)
    return make_page(items, total, page, page_size)


@router.get("/balance", response_model=BalanceOut, summary="Leave balance for the current year")
def balance(
    employee_id: int | None = None,
    year: int | None = Query(None, ge=2000, le=2100, description="Defaults to the current year"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    target = employee_id if employee_id is not None else user.employee_id
    if target is None:
        raise bad_request("Your account is not linked to an employee profile")
    if not is_hr(user) and target != user.employee_id:
        raise forbidden("You can only view your own leave balance")
    return leave_service.get_balance(db, target, year)


@router.patch("/{leave_id}/review", response_model=LeaveOut, summary="Approve or reject a request (HR only)")
def review(leave_id: int, body: LeaveReview, db: Session = Depends(get_db), reviewer: User = Depends(require_hr)):
    leave = leave_service.get_request(db, leave_id)
    return leave_service.review_request(db, leave, reviewer, body.decision, body.note)


@router.post("/{leave_id}/cancel", response_model=LeaveOut, summary="Cancel your own request")
def cancel(leave_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    leave = leave_service.get_request(db, leave_id)
    return leave_service.cancel_request(db, leave, user)
