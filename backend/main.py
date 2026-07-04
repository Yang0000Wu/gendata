"""
GenData — 仿真数据生成 SaaS
"""
import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from routes.auth import router as auth_router
from routes.billing import router as billing_router
from routes.generation import router as generation_router
from routes.payment import router as payment_router
from config import HOST, PORT

app = FastAPI(title="GenData", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API 路由 ──
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(generation_router)
app.include_router(payment_router)

# ── 静态文件 ──
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
