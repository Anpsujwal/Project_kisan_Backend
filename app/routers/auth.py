from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field, constr
from ..db.database import users_col
from ..utils.auth import hash_password, verify_password, create_access_token, get_current_user
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError

router = APIRouter()

# Ensure unique index on email
try:
    users_col().create_index("email", unique=True)
except Exception:
    pass

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6, max_length=20)
    phone: constr(pattern=r"^\+?[1-9]\d{9,14}$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=20)


@router.post("/auth/register")
async def register(body: RegisterRequest):
    try:
        existing = users_col().find_one({"email": body.email.lower()})
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        doc: Dict[str, Any] = {
            "name": body.name,
            "email": body.email.lower(),
            "hashed_password": hash_password(body.password),
            "phone": body.phone,
        }
        try:
            res = users_col().insert_one(doc)
        except DuplicateKeyError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        uid = str(res.inserted_id)
        token = create_access_token(uid, {"email": doc["email"]})
        return {"access_token": token, "token_type": "bearer", "user": {"id": uid, "name": doc["name"], "email": doc["email"], "phone": doc["phone"]}}
    except ServerSelectionTimeoutError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable. Please try again later.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed due to a server error")


@router.post("/auth/login")
async def login(body: LoginRequest):
    user = users_col().find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    uid = str(user.get("_id"))
    token = create_access_token(uid, {"email": user.get("email")})
    return {"access_token": token, "token_type": "bearer", "user": {"id": uid, "name": user.get("name"), "email": user.get("email")}}


@router.get("/auth/me")
async def me(current = Depends(get_current_user)):
    return {"user": current}
