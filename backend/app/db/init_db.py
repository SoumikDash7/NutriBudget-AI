from app.db.base_class import Base

# Import every model here

from app.models.user import User


def init_models():
    """
    Registers all ORM models.

    Alembic imports this module to discover metadata.
    """
    return Base.metadata