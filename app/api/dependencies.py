from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.session_manager import validate_session
from app.database import get_db


def get_current_session(
    x_session_token: str = Header(default=None, alias="X-Session-Token"),
    db: Session = Depends(get_db),
):
    if not x_session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token is required",
        )

    session = validate_session(db, x_session_token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return session


def get_current_user(current_session=Depends(get_current_session)):
    return current_session.user
