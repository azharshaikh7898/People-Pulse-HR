from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_hr
from app.database import get_db
from app.models.user import User
from app.schemas.analytics import DashboardOut
from app.services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardOut, summary="Dashboard statistics (HR only)")
def dashboard(db: Session = Depends(get_db), _: User = Depends(require_hr)):
    return analytics_service.get_dashboard(db)
