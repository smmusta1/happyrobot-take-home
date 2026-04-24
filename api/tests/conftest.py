import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from happyrobot_api import models  # noqa: F401  — register models with Base.metadata
from happyrobot_api.db import Base


@pytest.fixture
def db_session():
    """Fresh in-memory SQLite DB per test — fully isolated.

    StaticPool is required: SQLite `:memory:` creates a separate DB per connection,
    so without a shared pool, create_all() and queries can hit different databases.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session: Session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
