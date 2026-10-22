from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

_engine_args = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    _engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401  (registers tables)

    Base.metadata.create_all(engine)
