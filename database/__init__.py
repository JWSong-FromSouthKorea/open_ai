from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import Config

Base = declarative_base()
engine = create_engine(Config.database_uri, future=True, pool_pre_ping=True, pool_size=20, pool_reset_on_return=None,)
SessionLocal = sessionmaker(bind=engine)


def create_tables(_args=None):
    """
    Creates the tables specified in app.db.models
    Args:
        _args: Arguments parsed from the command line when used from the cli
    """
    # Needed for the models to be discovered
    from database.models import User, SearchLog  # noqa F401
    print(f"Creating database at: {engine.url}")
    Base.metadata.create_all(engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def export_session():
    return SessionLocal()
