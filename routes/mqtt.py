from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, UTC

from schemas.auth import User
from handlers.auth_handler import get_current_active_user
from celery_tasks import (
    send_bulk_command,
    check_offline_devices_task
)
from utils.mqtt_client import mqtt_client
from utils.database import get_database

router = APIRouter()


@router.post("/send-command")
async def send_mqtt_command(
        device_id: str,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        current_user: User = Depends(get_current_active_user)
):
    try:
        if parameters is None:
            parameters = {}

        topic = f"tenant/{current_user.tenant_id}/device/{device_id}/command"
        payload = {
            "command_id": f"cmd_{datetime.now(UTC).timestamp()}",
            "command": command,
            "parameters": parameters,
            "timestamp": datetime.now(UTC).isoformat(),
            "from_user": current_user.email
        }

        mqtt_client.publish(topic, payload)

        return {
            "status": "sent",
            "topic": topic,
            "command": command,
            "device_id": device_id,
            "timestamp": payload["timestamp"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")


@router.post("/broadcast-command")
async def broadcast_mqtt_command(
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        current_user: User = Depends(get_current_active_user)
):
    try:
        if parameters is None:
            parameters = {}

        topic = f"tenant/{current_user.tenant_id}/broadcast/{command}"
        payload = {
            "command_id": f"broadcast_{datetime.now(UTC).timestamp()}",
            "command": command,
            "parameters": parameters,
            "timestamp": datetime.now(UTC).isoformat(),
            "from_user": current_user.email
        }

        mqtt_client.publish(topic, payload)

        return {
            "status": "broadcasted",
            "topic": topic,
            "command": command,
            "timestamp": payload["timestamp"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to broadcast command: {str(e)}")


@router.post("/bulk-command")
async def send_bulk_mqtt_command(
        device_ids: List[str],
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        current_user: User = Depends(get_current_active_user)
):
    try:
        if parameters is None:
            parameters = {}

        task = send_bulk_command.delay(
            current_user.tenant_id,
            device_ids,
            command,
            parameters
        )

        return {
            "task_id": task.id,
            "status": "queued",
            "device_count": len(device_ids),
            "command": command
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue bulk command: {str(e)}")


@router.post("/subscribe-topic")
async def subscribe_to_topic(
        topic: str,
        current_user: User = Depends(get_current_active_user)
):
    try:
        if not topic.startswith(f"tenant/{current_user.tenant_id}/"):
            topic = f"tenant/{current_user.tenant_id}/{topic}"

        mqtt_client.subscribe(topic)

        return {
            "status": "subscribed",
            "topic": topic,
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to subscribe to topic: {str(e)}")


@router.get("/device-status")
async def get_device_status(
        current_user: User = Depends(get_current_active_user)
):
    try:
        db = await get_database()

        cursor = db.devices.find({"tenant_id": current_user.tenant_id})
        devices = []

        async for device in cursor:
            devices.append({
                "device_id": device["_id"],
                "name": device.get("name", "Unknown"),
                "status": device.get("status", "unknown"),
                "last_seen": device.get("last_seen"),
                "last_heartbeat": device.get("last_heartbeat"),
                "updated_at": device.get("updated_at")
            })

        return {
            "tenant_id": current_user.tenant_id,
            "devices": devices,
            "total_devices": len(devices),
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device status: {str(e)}")


@router.get("/telemetry/{device_id}")
async def get_device_telemetry(
        device_id: str,
        hours: int = Query(24, description="Hours of telemetry data to retrieve"),
        current_user: User = Depends(get_current_active_user)
):
    try:
        db = await get_database()

        start_time = datetime.now(UTC) - timedelta(hours=hours)

        cursor = db.telemetry.find({
            "tenant_id": current_user.tenant_id,
            "device_id": device_id,
            "timestamp": {"$gte": start_time.isoformat()}
        }).sort("timestamp", -1)

        telemetry_data = []
        async for record in cursor:
            telemetry_data.append({
                "timestamp": record["timestamp"],
                "data": record.get("data", {}),
                "metrics": record.get("metrics", {}),
                "received_at": record.get("received_at")
            })

        return {
            "device_id": device_id,
            "telemetry_data": telemetry_data,
            "total_records": len(telemetry_data),
            "time_range": {
                "from": start_time.isoformat(),
                "to": datetime.now(UTC).isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get telemetry data: {str(e)}")


@router.get("/alerts")
async def get_device_alerts(
        device_id: Optional[str] = Query(None, description="Filter alerts by device ID"),
        severity: Optional[str] = Query(None, description="Filter alerts by severity"),
        acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
        hours: int = Query(24, description="Hours of alerts to retrieve"),
        current_user: User = Depends(get_current_active_user)
):
    try:
        db = await get_database()

        query_filter = {"tenant_id": current_user.tenant_id}

        if device_id:
            query_filter["device_id"] = device_id

        if severity:
            query_filter["severity"] = severity

        if acknowledged is not None:
            query_filter["acknowledged"] = acknowledged

        start_time = datetime.now(UTC) - timedelta(hours=hours)
        query_filter["timestamp"] = {"$gte": start_time.isoformat()}

        cursor = db.alerts.find(query_filter).sort("timestamp", -1)

        alerts = []
        async for alert in cursor:
            alerts.append({
                "alert_id": alert["_id"],
                "device_id": alert["device_id"],
                "alert_type": alert["alert_type"],
                "severity": alert["severity"],
                "message": alert["message"],
                "details": alert.get("details", {}),
                "timestamp": alert["timestamp"],
                "acknowledged": alert["acknowledged"],
                "resolved": alert["resolved"]
            })

        return {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "filters": {
                "device_id": device_id,
                "severity": severity,
                "acknowledged": acknowledged,
                "hours": hours
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
        alert_id: str,
        current_user: User = Depends(get_current_active_user)
):
    try:
        db = await get_database()

        result = await db.alerts.update_one(
            {
                "_id": alert_id,
                "tenant_id": current_user.tenant_id
            },
            {
                "$set": {
                    "acknowledged": True,
                    "acknowledged_by": current_user.email,
                    "acknowledged_at": datetime.now(UTC).isoformat()
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {
            "status": "acknowledged",
            "alert_id": alert_id,
            "acknowledged_by": current_user.email,
            "acknowledged_at": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
        alert_id: str,
        resolution_notes: str = "",
        current_user: User = Depends(get_current_active_user)
):
    try:
        db = await get_database()

        result = await db.alerts.update_one(
            {
                "_id": alert_id,
                "tenant_id": current_user.tenant_id
            },
            {
                "$set": {
                    "resolved": True,
                    "resolved_by": current_user.email,
                    "resolved_at": datetime.now(UTC).isoformat(),
                    "resolution_notes": resolution_notes
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {
            "status": "resolved",
            "alert_id": alert_id,
            "resolved_by": current_user.email,
            "resolved_at": datetime.now(UTC).isoformat(),
            "resolution_notes": resolution_notes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}")


@router.get("/commands")
async def get_command_history(
        device_id: Optional[str] = Query(None, description="Filter commands by device ID"),
        status: Optional[str] = Query(None, description="Filter commands by status"),
        hours: int = Query(24, description="Hours of command history to retrieve"),
        current_user: User = Depends(get_current_active_user)
):
    try:
        db = await get_database()

        query_filter = {"tenant_id": current_user.tenant_id}

        if device_id:
            query_filter["device_id"] = device_id

        if status:
            query_filter["status"] = status

        start_time = datetime.now(UTC) - timedelta(hours=hours)
        query_filter["created_at"] = {"$gte": start_time.isoformat()}

        cursor = db.commands.find(query_filter).sort("created_at", -1)

        commands = []
        async for command in cursor:
            commands.append({
                "command_id": command["_id"],
                "device_id": command.get("device_id"),
                "command": command["command"],
                "parameters": command.get("parameters", {}),
                "status": command.get("status", "pending"),
                "created_at": command.get("created_at"),
                "executed_at": command.get("executed_at"),
                "result": command.get("result", {}),
                "from_user": command.get("from_user")
            })

        return {
            "commands": commands,
            "total_commands": len(commands),
            "filters": {
                "device_id": device_id,
                "status": status,
                "hours": hours
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get command history: {str(e)}")


@router.post("/health-check")
async def trigger_health_check(
        device_id: Optional[str] = Query(None, description="Check specific device, or all if not provided"),
        current_user: User = Depends(get_current_active_user)
):
    try:
        if device_id:
            topic = f"tenant/{current_user.tenant_id}/device/{device_id}/command"
            payload = {
                "command_id": f"health_{datetime.now(UTC).timestamp()}",
                "command": "health_check",
                "parameters": {},
                "timestamp": datetime.now(UTC).isoformat(),
                "from_user": current_user.email
            }

            mqtt_client.publish(topic, payload)

            return {
                "status": "health_check_sent",
                "device_id": device_id,
                "timestamp": payload["timestamp"]
            }
        else:
            task = check_offline_devices_task.delay(current_user.tenant_id)

            return {
                "status": "health_check_queued",
                "task_id": task.id,
                "tenant_id": current_user.tenant_id,
                "timestamp": datetime.now(UTC).isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger health check: {str(e)}")


@router.get("/statistics")
async def get_tenant_statistics(
        current_user: User = Depends(get_current_active_user)
):
    try:
        db = await get_database()

        device_stats = await db.devices.aggregate([
            {"$match": {"tenant_id": current_user.tenant_id}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]).to_list(length=None)

        start_time = datetime.now(UTC) - timedelta(hours=24)
        alert_stats = await db.alerts.aggregate([
            {
                "$match": {
                    "tenant_id": current_user.tenant_id,
                    "timestamp": {"$gte": start_time.isoformat()}
                }
            },
            {"$group": {
                "_id": "$severity",
                "count": {"$sum": 1}
            }}
        ]).to_list(length=None)

        telemetry_count = await db.telemetry.count_documents({
            "tenant_id": current_user.tenant_id,
            "timestamp": {"$gte": start_time.isoformat()}
        })

        command_stats = await db.commands.aggregate([
            {
                "$match": {
                    "tenant_id": current_user.tenant_id,
                    "created_at": {"$gte": start_time.isoformat()}
                }
            },
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]).to_list(length=None)

        return {
            "tenant_id": current_user.tenant_id,
            "device_statistics": {stat["_id"]: stat["count"] for stat in device_stats},
            "alert_statistics": {stat["_id"]: stat["count"] for stat in alert_stats},
            "telemetry_records_24h": telemetry_count,
            "command_statistics": {stat["_id"]: stat["count"] for stat in command_stats},
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.post("/mqtt-publish")
async def publish_custom_message(
        topic: str,
        payload: Dict[str, Any],
        current_user: User = Depends(get_current_active_user)
):
    try:

        if not topic.startswith(f"tenant/{current_user.tenant_id}/"):
            topic = f"tenant/{current_user.tenant_id}/{topic}"

        enhanced_payload = {
            **payload,
            "from_user": current_user.email,
            "timestamp": datetime.now(UTC).isoformat()
        }

        mqtt_client.publish(topic, enhanced_payload)

        return {
            "status": "published",
            "topic": topic,
            "payload": enhanced_payload,
            "timestamp": enhanced_payload["timestamp"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to publish message: {str(e)}")


@router.get("/mqtt-topics")
async def get_mqtt_topics(
        current_user: User = Depends(get_current_active_user)
):
    try:
        tenant_prefix = f"tenant/{current_user.tenant_id}"

        topics = {
            "device_topics": {
                "command": f"{tenant_prefix}/device/{{device_id}}/command",
                "status": f"{tenant_prefix}/device/{{device_id}}/status",
                "telemetry": f"{tenant_prefix}/device/{{device_id}}/telemetry",
                "response": f"{tenant_prefix}/device/{{device_id}}/response",
                "alert": f"{tenant_prefix}/device/{{device_id}}/alert",
                "heartbeat": f"{tenant_prefix}/device/{{device_id}}/heartbeat"
            },
            "broadcast_topics": {
                "general": f"{tenant_prefix}/broadcast/{{command}}",
                "health_check": f"{tenant_prefix}/broadcast/health_check",
                "firmware_update": f"{tenant_prefix}/broadcast/firmware_update",
                "config_update": f"{tenant_prefix}/broadcast/config_update"
            },
            "system_topics": {
                "notifications": f"{tenant_prefix}/system/notifications",
                "alerts": f"{tenant_prefix}/system/alerts",
                "logs": f"{tenant_prefix}/system/logs"
            }
        }

        return {
            "tenant_id": current_user.tenant_id,
            "mqtt_topics": topics,
            "description": "Available MQTT topics for your tenant. Use {device_id} as placeholder for actual device IDs.",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get MQTT topics: {str(e)}")