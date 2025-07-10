from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
import os
from typing import Dict, Any
from schemas.auth import User
from handlers.auth_handler import get_current_active_user
from celery_tasks import process_device_analytics, generate_tenant_report
from datetime import datetime, timedelta, UTC

REPORTS_DIR = "reports"

router = APIRouter()


@router.post("/devices/{device_id}/process")
async def process_device_data(
        device_id: str,
        data: Dict[str, Any],
        current_user: User = Depends(get_current_active_user)
):
    task = process_device_analytics.delay(current_user.tenant_id, device_id, data)
    return {"task_id": task.id, "status": "processing"}


@router.post("/reports/generate")
async def generate_report(
        report_type: str = Query(..., description="Type of report to generate"),
        days_back: int = Query(30, description="Number of days back to include"),
        current_user: User = Depends(get_current_active_user)
):
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days_back)

    date_range = {
        "start": start_date.isoformat(),
        "end": end_date.isoformat()
    }

    task = generate_tenant_report.delay(current_user.tenant_id, report_type, date_range)
    return {"task_id": task.id, "status": "generating"}

@router.get("/reports/download/{filename}")
async def download_report(filename: str, current_user: User = Depends(get_current_active_user)):
    filepath = os.path.join(REPORTS_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type='application/pdf', filename=filename)
    else:
        raise HTTPException(status_code=404, detail="Report not found")


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    from celery_app import celery_app
    result = celery_app.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None
    }