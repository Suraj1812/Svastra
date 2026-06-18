from datetime import datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

from sqlalchemy.orm import Session

from app.config import settings
from app.models.session import UserSession


def create_session(db: Session, user):
    plain_token = token_urlsafe(32)
    session = UserSession(
        user_id=user.id,
        session_token_hash=_hash_token(plain_token),
        expires_at=datetime.utcnow() + timedelta(hours=settings.session_ttl_hours),
        is_active=True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    session._issued_session_token = plain_token
    return session


def _hash_token(session_token: str):
    return sha256(session_token.encode("utf-8")).hexdigest()


def validate_session(db: Session, session_token: str):
    token_hash = _hash_token(session_token)
    session = (
        db.query(UserSession)
        .filter(
            UserSession.session_token_hash == token_hash,
            UserSession.is_active.is_(True),
        )
        .first()
    )

    # One-time migration path for sessions issued before token hashing was enabled.
    if session is None:
        session = (
            db.query(UserSession)
            .filter(
                UserSession.session_token_hash == session_token,
                UserSession.is_active.is_(True),
            )
            .first()
        )
        if session is not None:
            session.session_token_hash = token_hash
            db.commit()

    if session is None:
        return None

    if session.expires_at <= datetime.utcnow():
        session.is_active = False
        db.commit()
        return None

    return session


def destroy_session(db: Session, session_token: str):
    token_hash = _hash_token(session_token)
    session = (
        db.query(UserSession)
        .filter(UserSession.session_token_hash == token_hash, UserSession.is_active.is_(True))
        .first()
    )

    if session is None:
        session = (
            db.query(UserSession)
            .filter(
                UserSession.session_token_hash == session_token,
                UserSession.is_active.is_(True),
            )
            .first()
        )

    if session is None:
        return False

    session.is_active = False
    db.commit()
    return True


def logout(db: Session, session_token: str):
    return destroy_session(db, session_token)
