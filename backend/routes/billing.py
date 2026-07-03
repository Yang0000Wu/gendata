"""
GenData — 计费模块
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import get_db, User
from routes.auth import get_current_user
from config import PRICE_PER_GEN, FREE_TRIAL_GENS

router = APIRouter(prefix="/api/billing", tags=["billing"])

@router.get("/balance")
def get_balance(user: User = Depends(get_current_user)):
    return {"balance_yuan": user.balance_cents / 100}

@router.post("/deduct")
def deduct(cost: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """扣除余额。cost单位为分"""
    if cost <= 0:
        raise HTTPException(400, "无效金额")

    # 先看是否有免费次数
    free_left = FREE_TRIAL_GENS - (user.free_gens_used or 0)
    if free_left > 0:
        user.free_gens_used = (user.free_gens_used or 0) + 1
        db.commit()
        return {"method": "free", "cost": 0, "free_left": free_left - 1}

    # 再看订阅
    if user.plan in ("personal", "enterprise"):
        db.commit()
        return {"method": "plan", "cost": 0}

    # 按次扣费
    if (user.balance_cents or 0) < cost:
        raise HTTPException(402, "余额不足")

    user.balance_cents -= cost
    db.commit()
    return {"method": "pay_per_use", "cost": cost / 100, "balance": user.balance_cents / 100}

@router.get("/prices")
def get_prices():
    return {
        "pay_per_use": PRICE_PER_GEN,
        "plans": [
            {"id": "personal", "name": "个人版", "price": 99, "unit": "月", "rows_per_gen": 10000},
            {"id": "enterprise", "name": "企业版", "price": 599, "unit": "月", "rows_per_gen": 1000000},
        ],
        "free_trial": FREE_TRIAL_GENS,
    }
