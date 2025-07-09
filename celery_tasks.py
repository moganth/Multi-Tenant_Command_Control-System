import asyncio

from loguru import logger
from bson import ObjectId
from datetime import datetime, timedelta, UTC

from celery_app import celery_app
from utils.database import get_database, connect_to_mongo
from utils.mqtt_client import mqtt_client
from utils.firebase_client import firebase_client

@celery_app.task(bind=True)
def send_bulk_command(self, tenant_id: str, device_ids: list, command: str, parameters: dict):
    try:
        results = []
        for device_id in device_ids:
            topic = f"tenant/{tenant_id}/device/{device_id}/command"
            payload = {
                "command_id": self.request.id,
                "command": command,
                "parameters": parameters,
                "timestamp": datetime.now(UTC).isoformat()
            }

            mqtt_client.publish(topic, payload)
            results.append({"device_id": device_id, "status": "sent"})

        return {"status": "completed", "results": results}
    except Exception as e:
        logger.error(f"Error in bulk command task: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def process_device_analytics(self, tenant_id: str, device_id: str, data: dict):
    try:
        processed_data = {
            "tenant_id": tenant_id,
            "device_id": device_id,
            "metrics": data,
            "processed_at": datetime.now(UTC).isoformat()
        }

        firebase_client.send_real_time_update(
            tenant_id, "analytics", device_id, processed_data
        )

        return {"status": "completed", "processed_data": processed_data}
    except Exception as e:
        logger.error(f"Error in analytics task: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def health_check_devices(self, tenant_id: str):
    try:
        topic = f"tenant/{tenant_id}/broadcast/health_check"
        payload = {
            "command": "health_check",
            "timestamp": datetime.now(UTC).isoformat()
        }

        mqtt_client.publish(topic, payload)

        return {"status": "completed", "message": "Health check initiated"}
    except Exception as e:
        logger.error(f"Error in health check task: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def generate_tenant_report(self, tenant_id: str, report_type: str, date_range: dict):
    try:
        report_data = {
            "tenant_id": tenant_id,
            "report_type": report_type,
            "date_range": date_range,
            "generated_at": datetime.now(UTC).isoformat(),
            "status": "completed"
        }

        firebase_client.send_notification(
            tenant_id, "report_generated", report_data
        )

        return report_data
    except Exception as e:
        logger.error(f"Error in report generation task: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def update_device_status_task(self, tenant_id: str, device_id: str, status_data: dict):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def update_status():
            await connect_to_mongo()
            db = await get_database()

            update_data = {
                "status": status_data.get("status", "unknown"),
                "last_seen": status_data.get("timestamp", datetime.now(UTC).isoformat()),
                "updated_at": datetime.now(UTC).isoformat(),
                "connection_info": status_data.get("connection_info", {}),
                "system_info": status_data.get("system_info", {})
            }

            result = await db.devices.update_one(
                {"_id": device_id, "tenant_id": tenant_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                logger.info(f"Updated device status for {tenant_id}/{device_id}")

                firebase_client.send_real_time_update(
                    tenant_id, "device_status", device_id, update_data
                )
            else:
                logger.warning(f"Device not found for status update: {tenant_id}/{device_id}")

        loop.run_until_complete(update_status())
        loop.close()

        return {"status": "completed", "device_id": device_id}
    except Exception as e:
        logger.error(f"Error updating device status: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def process_device_telemetry_task(self, tenant_id: str, device_id: str, telemetry_data: dict):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def process_telemetry():
            await connect_to_mongo()
            db = await get_database()

            telemetry_doc = {
                "_id": str(ObjectId()),
                "tenant_id": tenant_id,
                "device_id": device_id,
                "timestamp": telemetry_data.get("timestamp", datetime.now(UTC).isoformat()),
                "data": telemetry_data.get("data", {}),
                "metrics": telemetry_data.get("metrics", {}),
                "received_at": datetime.now(UTC).isoformat()
            }

            await db.telemetry.insert_one(telemetry_doc)

            await check_telemetry_alerts(tenant_id, device_id, telemetry_data)

            firebase_client.send_real_time_update(
                tenant_id, "telemetry", device_id, telemetry_doc
            )

            logger.info(f"Processed telemetry for {tenant_id}/{device_id}")

        loop.run_until_complete(process_telemetry())
        loop.close()

        return {"status": "completed", "device_id": device_id}
    except Exception as e:
        logger.error(f"Error processing telemetry: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def update_command_status_task(self, tenant_id: str, device_id: str, response_data: dict):

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def update_command():
            await connect_to_mongo()
            db = await get_database()

            command_id = response_data.get("command_id")
            if not command_id:
                logger.warning("No command_id in response data")
                return

            update_data = {
                "status": response_data.get("status", "completed"),
                "result": response_data.get("result", {}),
                "executed_at": response_data.get("timestamp", datetime.now(UTC).isoformat()),
                "response_data": response_data
            }

            result = await db.commands.update_one(
                {"_id": command_id, "tenant_id": tenant_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                logger.info(f"Updated command status for {command_id}")

                firebase_client.send_real_time_update(
                    tenant_id, "commands", command_id, update_data
                )
            else:
                logger.warning(f"Command not found for update: {command_id}")

        loop.run_until_complete(update_command())
        loop.close()

        return {"status": "completed", "command_id": response_data.get("command_id")}
    except Exception as e:
        logger.error(f"Error updating command status: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def process_device_alert_task(self, tenant_id: str, device_id: str, alert_data: dict):

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def process_alert():
            await connect_to_mongo()
            db = await get_database()

            alert_doc = {
                "_id": str(ObjectId()),
                "tenant_id": tenant_id,
                "device_id": device_id,
                "alert_type": alert_data.get("type", "unknown"),
                "severity": alert_data.get("severity", "medium"),
                "message": alert_data.get("message", ""),
                "details": alert_data.get("details", {}),
                "timestamp": alert_data.get("timestamp", datetime.now(UTC).isoformat()),
                "acknowledged": False,
                "resolved": False
            }

            await db.alerts.insert_one(alert_doc)

            if alert_data.get("severity") in ["high", "critical"]:
                firebase_client.send_notification(
                    tenant_id, "critical_alert", {
                        "device_id": device_id,
                        "alert_type": alert_data.get("type"),
                        "message": alert_data.get("message"),
                        "severity": alert_data.get("severity")
                    }
                )

            firebase_client.send_real_time_update(
                tenant_id, "alerts", alert_doc["_id"], alert_doc
            )

            logger.info(f"Processed alert for {tenant_id}/{device_id}: {alert_data.get('type')}")

        loop.run_until_complete(process_alert())
        loop.close()

        return {"status": "completed", "alert_type": alert_data.get("type")}
    except Exception as e:
        logger.error(f"Error processing alert: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def update_device_heartbeat_task(self, tenant_id: str, device_id: str, heartbeat_data: dict):

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def update_heartbeat():
            await connect_to_mongo()
            db = await get_database()

            update_data = {
                "last_heartbeat": heartbeat_data.get("timestamp", datetime.now(UTC).isoformat()),
                "status": "online",
                "updated_at": datetime.now(UTC).isoformat()
            }

            result = await db.devices.update_one(
                {"_id": device_id, "tenant_id": tenant_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                logger.debug(f"Updated heartbeat for {tenant_id}/{device_id}")

            await check_offline_devices(tenant_id)

        loop.run_until_complete(update_heartbeat())
        loop.close()

        return {"status": "completed", "device_id": device_id}
    except Exception as e:
        logger.error(f"Error updating heartbeat: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def check_offline_devices_task(self, tenant_id: str):

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def check_offline():
            await connect_to_mongo()
            db = await get_database()

            offline_threshold = datetime.now(UTC) - timedelta(minutes=5)

            cursor = db.devices.find({
                "tenant_id": tenant_id,
                "last_heartbeat": {"$lt": offline_threshold.isoformat()},
                "status": {"$ne": "offline"}
            })

            offline_devices = []
            async for device in cursor:

                await db.devices.update_one(
                    {"_id": device["_id"]},
                    {"$set": {"status": "offline", "updated_at": datetime.now(UTC).isoformat()}}
                )

                offline_devices.append(device["_id"])

                firebase_client.send_notification(
                    tenant_id, "device_offline", {
                        "device_id": device["_id"],
                        "device_name": device.get("name", "Unknown"),
                        "last_seen": device.get("last_heartbeat")
                    }
                )

            logger.info(f"Checked offline devices for {tenant_id}: {len(offline_devices)} offline")

        loop.run_until_complete(check_offline())
        loop.close()

        return {"status": "completed", "tenant_id": tenant_id}
    except Exception as e:
        logger.error(f"Error checking offline devices: {e}")
        return {"status": "failed", "error": str(e)}


async def check_telemetry_alerts(tenant_id: str, device_id: str, telemetry_data: dict):

    try:
        db = await get_database()

        device = await db.devices.find_one({"_id": device_id, "tenant_id": tenant_id})
        if not device:
            return

        alert_config = device.get("alert_config", {})
        metrics = telemetry_data.get("metrics", {})

        if "temperature" in metrics and "temperature_threshold" in alert_config:
            temp = metrics["temperature"]
            threshold = alert_config["temperature_threshold"]

            if temp > threshold:
                process_device_alert_task.delay(tenant_id, device_id, {
                    "type": "temperature_high",
                    "severity": "high",
                    "message": f"Temperature exceeded threshold: {temp}°C > {threshold}°C",
                    "details": {"current_temp": temp, "threshold": threshold},
                    "timestamp": datetime.now(UTC).isoformat()
                })


    except Exception as e:
        logger.error(f"Error checking telemetry alerts: {e}")


async def check_offline_devices(tenant_id: str):
    check_offline_devices_task.delay(tenant_id)


@celery_app.task(bind=True)
def periodic_device_health_check(self):

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def check_all_tenants():
            await connect_to_mongo()
            db = await get_database()

            cursor = db.tenants.find({"is_active": True})

            async for tenant in cursor:
                tenant_id = tenant["_id"]

                check_offline_devices_task.delay(tenant_id)

                health_check_devices.delay(tenant_id)

        loop.run_until_complete(check_all_tenants())
        loop.close()

        return {"status": "completed", "message": "Health check initiated for all tenants"}
    except Exception as e:
        logger.error(f"Error in periodic health check: {e}")
        return {"status": "failed", "error": str(e)}

celery_app.conf.beat_schedule = {
    'periodic-device-health-check': {
        'task': 'celery_tasks.periodic_device_health_check',
        'schedule': 300.0,  # Run every 5 minutes
    },
}
celery_app.conf.timezone = 'UTC'