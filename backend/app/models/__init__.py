# Import every model so Alembic and Base.metadata can see all tables.
from app.models.employee import Employee  # noqa: F401
from app.models.leave import LeaveRequest  # noqa: F401
from app.models.onboarding import OnboardingTask  # noqa: F401
from app.models.user import RevokedToken, User  # noqa: F401
