"""
GenData — 数据生成核心路由
"""
import os, json, time, threading
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime

from models import get_db, User, Task
from routes.auth import get_current_user
from core.llm import analyze_schema
from core.data_generator import generate_data, export_csv, export_json, export_sql
from config import MAX_ROWS_PER_GEN, MIN_ROWS_PER_GEN, TASK_EXPIRE_HOURS

router = APIRouter(prefix="/api", tags=["generation"])
TASKS_DIR = "data/tasks"

os.makedirs(TASKS_DIR, exist_ok=True)

@router.get("/prices")
def prices():
    from config import PRICE_PER_GEN, PRICE_MONTHLY_PERSONAL, PRICE_MONTHLY_ENTERPRISE, FREE_TRIAL_GENS
    return {
        "pay_per_use": PRICE_PER_GEN,
        "personal_monthly": PRICE_MONTHLY_PERSONAL,
        "enterprise_monthly": PRICE_MONTHLY_ENTERPRISE,
        "free_trial": FREE_TRIAL_GENS,
    }

@router.post("/generate/analyze")
async def analyze(
    schema: str = Form(...),
    user: User = Depends(get_current_user),
):
    """上传SQL Schema并分析"""
    try:
        result = await analyze_schema(schema)
        return {"tables": result.get("tables", [])}
    except Exception as e:
        raise HTTPException(500, f"分析失败: {str(e)}")

@router.post("/generate/run")
async def run_generation(
    schema_json: str = Form(...),
    row_count: int = Form(1000),
    output_format: str = Form("csv"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """执行数据生成"""
    if row_count < MIN_ROWS_PER_GEN:
        row_count = MIN_ROWS_PER_GEN
    if row_count > MAX_ROWS_PER_GEN:
        row_count = MAX_ROWS_PER_GEN

    try:
        schema = json.loads(schema_json)
    except json.JSONDecodeError:
        raise HTTPException(400, "无效的schema_json格式")

    # 创建任务
    task = Task(
        user_id=user.id,
        status="pending",
        schema_analysis=schema,
        row_count=row_count,
        output_format=output_format,
    )
    db.add(task)
    db.commit()

    # 异步执行
    thread = threading.Thread(target=_do_generate, args=(task.id, row_count, output_format, schema, db), daemon=True)
    thread.start()

    return {"task_id": task.id, "status": "pending"}

def _do_generate(task_id: int, row_count: int, output_format: str, schema: dict, db: Session):
    """后台执行数据生成"""
    from sqlalchemy.orm import Session as Sess
    from models import SessionLocal

    session = SessionLocal()
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        task.status = "running"
        session.commit()

        # 生成数据
        data = generate_data(schema, row_count)
        total_rows = sum(len(rows) for rows in data.values())
        task.output_rows = total_rows

        # 导出
        if output_format == "json":
            exported = export_json(data)
            ext = "json"
        elif output_format == "sql":
            exported = export_sql(data, schema)
            ext = "sql"
        else:
            exported = export_csv(data)
            ext = "csv"

        # 写入文件
        output_path = os.path.join(TASKS_DIR, f"task_{task_id}")
        os.makedirs(output_path, exist_ok=True)

        for tname, content in exported.items():
            file_path = os.path.join(output_path, f"{tname}.{ext}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        # 生成清单文件
        manifest = []
        for tname in exported:
            size = os.path.getsize(os.path.join(output_path, f"{tname}.{ext}"))
            manifest.append({"table": tname, "rows": len(data.get(tname, [])), "size": size})

        with open(os.path.join(output_path, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        task.status = "done"
        task.output_path = output_path
        session.commit()

    except Exception as e:
        task = session.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "failed"
            task.error_msg = str(e)
            session.commit()
    finally:
        session.close()

@router.get("/tasks")
def list_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.user_id == user.id).order_by(Task.id.desc()).limit(20).all()
    return [
        {
            "id": t.id,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else "",
            "row_count": t.row_count,
            "output_format": t.output_format,
            "output_rows": t.output_rows,
            "error_msg": t.error_msg,
            "has_output": t.status == "done",
        }
        for t in tasks
    ]

@router.get("/tasks/{task_id}/download")
def download_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status != "done" or not task.output_path:
        raise HTTPException(400, "任务未完成")

    # 打包下载
    import shutil, tempfile
    zip_path = os.path.join(TASKS_DIR, f"task_{task_id}.zip")
    shutil.make_archive(zip_path.replace(".zip", ""), "zip", task.output_path)
    return FileResponse(zip_path, filename=f"gendata_task_{task_id}.zip", media_type="application/zip")

@router.get("/tasks/{task_id}")
def get_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    return {
        "id": task.id,
        "status": task.status,
        "created_at": task.created_at.isoformat() if task.created_at else "",
        "schema_sql": task.schema_sql,
        "row_count": task.row_count,
        "output_format": task.output_format,
        "output_rows": task.output_rows,
        "error_msg": task.error_msg,
    }
