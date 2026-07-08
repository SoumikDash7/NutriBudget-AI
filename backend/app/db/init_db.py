from app.db.base_class import Base

# Import every model here

from app.models.user import User
from app.models.profile import Profile
from app.models.password_reset_token import PasswordResetToken
from app.models.otp import OTP
from app.models.calorie import CalorieLog
from app.models.budget import Collaboration, BudgetTransaction, BudgetNotification


def init_models():
    """
    Registers all ORM models.

    Alembic imports this module to discover metadata.
    """
    return Base.metadata