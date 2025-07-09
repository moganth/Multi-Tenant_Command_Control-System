from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Any
from schemas.auth import User
from schemas.device import Command, CommandCreate
from handlers.auth_handler import get_current_active_user
from celery_tasks import send_bulk_command
from utils.database import get_database

router = APIRouter()


@router.post("/bulk")
async def send_bulk_device_command(
        device_ids: List[str],
        command: str,
        parameters: Dict[str, Any] = {},
        current_user: User = Depends(get_current_active_user)
):
    """Send command to multiple devices"""
    task = send_bulk_command.delay(current_user.tenant_id, device_ids, command, parameters)
    return {"task_id": task.id, "status": "processing", "device_count": len(device_ids)}


@router.get("/")
async def get_commands(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        device_id: str = Query(None, description="Filter by device ID"),
        status: str = Query(None, description="Filter by status"),
        current_user: User = Depends(get_current_active_user)
):
    """Get command history"""
    db = await get_database()

    filter_dict = {"tenant_id": current_user.tenant_id}
    if device_id:
        filter_dict["device_id"] = device_id
    if status:
        filter_dict["status"] = status

    cursor = db.commands.find(filter_dict).skip(skip).limit(limit).sort("created_at", -1)
    commands = []

    async for doc in cursor:
        commands.append(Command(**doc, id=doc["_id"]))

    return commands


@router.get("/{command_id}")
async def get_command(
        command_id: str,
        current_user: User = Depends(get_current_active_user)
):
    """Get specific command"""
    db = await get_database()

    doc = await db.commands.find_one({
        "_id": command_id,
        "tenant_id": current_user.tenant_id
    })

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found"
        )

    return Command(**doc, id=doc["_id"])