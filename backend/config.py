"""
GenData — 仿真数据生成 SaaS 配置
"""
import os

# ── 服务器 ──
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# ── 数据库 ──
DB_PATH = os.getenv("DB_PATH", "data/gendata.db")

# ── JWT ──
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-gendata-saas-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天

# ── LLM ──
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# ── 计费 ──
# 个人版 99/月, 企业版 599/月, 按次 19/次
PRICE_PER_GEN = 19        # 按次 ¥
PRICE_MONTHLY_PERSONAL = 99
PRICE_MONTHLY_ENTERPRISE = 599
FREE_TRIAL_GENS = 1        # 首次注册送1次
MAX_ROWS_FREE_TIER = 10000

# ── 任务 ──
TASK_EXPIRE_HOURS = 72     # 72小时后自动删除任务文件

# ── 默认输出限制 ──
MAX_ROWS_PER_GEN = 1000000  # 单次最多生成100万条
MIN_ROWS_PER_GEN = 100      # 最少100条
