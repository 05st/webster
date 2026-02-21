from fastapi import HTTPException, Request
from sqlmodel import Session
import jwt
import time
from jwt import ExpiredSignatureError, InvalidTokenError

from constants import JWT_SECRET, JWT_ALGORITHM, SESSION_COOKIE_NAME, SESSION_TTL_SECONDS
from models import User, WebsiteEntry


def create_session_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": int(time.time()) + SESSION_TTL_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user_id(request: Request) -> int:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session token")
    user_id = decoded.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid session token")
    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session token")


def get_user(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_owned_entry(session: Session, user_id: int, website_entry_id: int) -> WebsiteEntry:
    entry = session.get(WebsiteEntry, website_entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Website entry not found")
    return entry
