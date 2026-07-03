"""
GenData — 认证模块
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
import bcrypt as _bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta

from models import get_db, User
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, FREE_TRIAL_GENS

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

class AuthInput(BaseModel):
    email: str
    password: str

def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(401, "无效Token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(401, "用户不存在")
    return user

@router.post("/register")
def register(body: AuthInput, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, "邮箱已注册")
    hashed = _bcrypt.hashpw(body.password.encode(), _bcrypt.gensalt()).decode()
    user = User(email=body.email, password_hash=hashed, free_gens_used=0)
    db.add(user)
    db.commit()
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "email": user.email, "plan": "free", "free_gens_left": FREE_TRIAL_GENS}}

@router.post("/login")
def login(body: AuthInput, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not _bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(401, "邮箱或密码错误")
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "email": user.email, "plan": user.plan or "free"}}

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
        "plan": user.plan or "free",
        "balance_yuan": user.balance_cents / 100,
        "free_gens_left": max(0, FREE_TRIAL_GENS - (user.free_gens_used or 0)),
    }
