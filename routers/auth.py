import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import store
from services.auth import create_token, verify_token, hash_password, verify_password

logger = logging.getLogger(__name__)
router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = verify_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = store.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> int:
    return get_current_user(credentials)["id"]


@router.post("/auth/register")
async def register(body: dict):
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password required")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if store.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user_id = store.create_user(email, hash_password(password))
    token = create_token(user_id, email)
    logger.info(f"[auth] registered user_id={user_id} email={email}")
    return {"token": token, "email": email, "user_id": user_id}


@router.post("/auth/login")
async def login(body: dict):
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    user = store.get_user_by_email(email)
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"], email)
    logger.info(f"[auth] login user_id={user['id']}")
    return {"token": token, "email": email, "user_id": user["id"]}


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user_id": user["id"], "email": user["email"]}
