"""
GenData — 数据库模型
"""
import os, time
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from config import DB_PATH

os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    nickname = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 余额（分为单位）
    balance_cents = Column(Integer, default=0)

    # 订阅
    plan = Column(String, default="free")  # free / personal / enterprise
    plan_expires = Column(DateTime, nullable=True)

    # 免费试用次数
    free_gens_used = Column(Integer, default=0)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending")  # pending / running / done / failed
    created_at = Column(DateTime, default=datetime.utcnow)

    # 输入：SQL schema
    schema_sql = Column(Text, default="")
    schema_analysis = Column(JSON, default={})  # LLM分析结果

    # 参数
    row_count = Column(Integer, default=1000)
    output_format = Column(String, default="csv")  # csv / json / sql

    # 结果
    output_path = Column(String, nullable=True)
    output_rows = Column(Integer, default=0)
    error_msg = Column(String, nullable=True)

    # 计费
    cost_cents = Column(Integer, default=0)

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    key = Column(String, unique=True, index=True)
    name = Column(String, default="default")
    active = Column(Integer, default=1)

Base.metadata.create_all(bind=engine)
