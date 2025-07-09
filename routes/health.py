from fastapi import APIRouter, Depends
from schemas.auth import User
from handlers.auth_handler import get_current_active_user
from celery_tasks import health_check_devices
from utils.database import get_database
from utils.mqtt_client import mqtt_client

router = APIRouter()


@router.get("/")
async def health_check():
    """System health check"""
    try:
        # Check database connection
        db = await get_database()
        await db.command("ping")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check MQTT connection
    mqtt_status = "healthy" if mqtt_client.client.is_connected() else "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" and mqtt_status == "healthy" else "unhealthy",
        "components": {
            "database": db_status,
            "mqtt": mqtt_status
        }
    }


@router.post("/devices/check")
async def check_device_health(
        current_user: User = Depends(get_current_active_user)
):
    """Trigger health check for all tenant devices"""
    task = health_check_devices.delay(current_user.tenant_id)
    return {"task_id": task.id, "status": "initiated"}
