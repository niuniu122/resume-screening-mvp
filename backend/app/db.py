from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    pass


def normalize_database_url(database_url: str) -> str:
    # Render provides postgresql:// URLs which default to psycopg2 driver.
    # We use psycopg (v3), so rewrite to postgresql+psycopg://.
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def create_database_engine(database_url: str) -> Engine:
    normalized_url = normalize_database_url(database_url)
    connect_args = {"check_same_thread": False} if normalized_url.startswith("sqlite") else {"connect_timeout": 10}
    return create_engine(normalized_url, connect_args=connect_args, pool_pre_ping=True)


db_url = normalize_database_url(settings.database_url)
engine = create_database_engine(db_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def configure_database(database_url: str) -> None:
    global db_url, engine

    previous_engine = engine
    db_url = normalize_database_url(database_url)
    engine = create_database_engine(db_url)
    SessionLocal.configure(bind=engine)
    previous_engine.dispose()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
