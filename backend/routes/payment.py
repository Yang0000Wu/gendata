"""
GenData — 支付模块（虎皮椒）
"""
import hashlib, time, random, string
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from models import get_db, User
from routes.auth import get_current_user

router = APIRouter(prefix="/api/pay", tags=["payment"])

# ── 虎皮椒配置 ──
PARTNER = "20211120185"
KEY = "fd3b480e6a1b729e6038ae2a7b747b2e"
PAY_URL = "https://api.dpweixin.com/payment/do.html"
NOTIFY_URL = "http://124.221.149.20/api/pay/notify"
CALLBACK_URL = "http://124.221.149.20/api/pay/callback"

# ── 充值档位（分为单位） ──
PLANS = {
    19:   {"name": "按次充值", "yuan": 19, "desc": "1次生成"},
    99:   {"name": "个人月付", "yuan": 99, "desc": "个人版月付"},
    599:  {"name": "企业月付", "yuan": 599, "desc": "企业版月付"},
}

def md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

@router.get("/plans")
def get_plans():
    return PLANS

@router.post("/create/{amount}")
def create_payment(amount: int, user: User = Depends(get_current_user)):
    """创建支付订单"""
    if amount not in PLANS:
        raise HTTPException(400, "无效金额")

    # 生成订单号
    order_no = f"GD{time.strftime('%Y%m%d%H%M%S')}{random.randint(1000,9999)}"

    # 构建签名字符串
    params = {
        "partner": PARTNER,
        "banktype": "WX",
        "paymoney": str(amount),
        "ordernumber": order_no,
        "callbackurl": CALLBACK_URL,
    }
    # 按 key 排序后拼接
    sorted_keys = sorted(params.keys())
    sign_str = "&".join(f"{k}={params[k]}" for k in sorted_keys) + KEY
    sign = md5(sign_str).upper()

    # 构建支付跳转 URL
    pay_params = params.copy()
    pay_params["hrefbackurl"] = NOTIFY_URL
    pay_params["attach"] = str(user.id)
    pay_params["sign"] = sign

    return {
        "pay_url": PAY_URL,
        "params": pay_params,
        "order_no": order_no,
        "amount": amount,
    }

@router.get("/notify")
async def pay_notify(request: Request, db: Session = Depends(get_db)):
    """支付异步通知"""
    params = dict(request.query_params)
    # 验证签名
    partner = params.get("partner")
    ordernumber = params.get("ordernumber")
    paymoney = params.get("paymoney")
    attach = params.get("attach")  # user_id
    sign = params.get("sign", "")

    if not all([partner, ordernumber, paymoney, attach, sign]):
        return HTMLResponse("fail")

    # 签名验证
    check_params = {
        "partner": partner,
        "ordernumber": ordernumber,
        "paymoney": paymoney,
    }
    sorted_keys = sorted(check_params.keys())
    sign_str = "&".join(f"{k}={check_params[k]}" for k in sorted_keys) + KEY
    expected_sign = md5(sign_str).upper()

    if sign != expected_sign:
        return HTMLResponse("sign_error")

    # 增加用户余额
    user_id = int(attach)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.balance_cents = (user.balance_cents or 0) + int(float(paymoney) * 100)
        db.commit()

    return HTMLResponse("ok")

@router.get("/callback")
async def pay_callback(request: Request):
    """支付成功回调（页面跳转）"""
    params = dict(request.query_params)
    ordernumber = params.get("ordernumber", "")
    return HTMLResponse(f"""
    <html><body>
    <h2>✅ 支付成功</h2>
    <p>订单号: {ordernumber}</p>
    <p>正在跳转...</p>
    <script>setTimeout(function(){{ window.location.href = '/'; }}, 2000)</script>
    </body></html>
    """)
