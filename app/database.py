from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    from app.models import audit, care, consent, postoffice, rbac, relationship, session, terminology, user  # noqa: F401
    from app.terminology.term_service import seed_demo_terms

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_demo_terms(db)
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
