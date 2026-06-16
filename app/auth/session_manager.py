from datetime import datetime, timedelta
from secrets import token_urlsafe

from sqlalchemy.orm import Session

from app.config import settings
from app.models.session import UserSession


def create_session(db: Session, user):
    session = UserSession(
        user_id=user.id,
        session_token=token_urlsafe(32),
        expires_at=datetime.utcnow() + timedelta(hours=settings.session_ttl_hours),
        is_active=True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def validate_session(db: Session, session_token: str):
    session = (
        db.query(UserSession)
        .filter(
            UserSession.session_token == session_token,
            UserSession.is_active.is_(True),
        )
        .first()
    )

    if session is None:
        return None

    if session.expires_at <= datetime.utcnow():
        session.is_active = False
        db.commit()
        return None

    return session


def destroy_session(db: Session, session_token: str):
    session = (
        db.query(UserSession)
        .filter(UserSession.session_token == session_token, UserSession.is_active.is_(True))
        .first()
    )

    if session is None:
        return False

    session.is_active = False
    db.commit()
    return True


def logout(db: Session, session_token: str):
    return destroy_session(db, session_token)
