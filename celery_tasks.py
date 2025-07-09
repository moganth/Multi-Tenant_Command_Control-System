import asyncio

from loguru import logger
from bson import ObjectId
from datetime import datetime, timedelta

from celery_app import celery_app
from utils.database import get_database, connect_to_mongo
from utils.mqtt_client import mqtt_client
from utils.firebase_client import firebase_client


# Existing tasks from your original file
@celery_app.task(bind=True)
def send_bulk_command(self, tenant_id: str, device_ids: list, command: str, parameters: dict):
    """Send command to multiple devices"""
    try:
        results = []
        for device_id in device_ids:
            topic = f"tenant/{tenant_id}/device/{device_id}/command"
            payload = {
                "command_id": self.request.id,
                "command": command,
                "parameters": parameters,
                "timestamp": datetime.utcnow().isoformat()
            }

            mqtt_client.publish(topic, payload)
            results.append({"device_id": device_id, "status": "sent"})

        return {"status": "completed", "results": results}
    except Exception as e:
        logger.error(f"Error in bulk command task: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def process_device_analytics(self, tenant_id: str, device_id: str, data: dict):
    """Process device analytics data"""
    try:
        # Process analytics data
        processed_data = {
            "tenant_id": tenant_id,
            "device_id": device_id,
            "metrics": data,
            "processed_at": datetime.utcnow().isoformat()
        }

        # Send to Firebase for real-time updates
        firebase_client.send_real_time_update(
            tenant_id, "analytics", device_id, processed_data
        )

        return {"status": "completed", "processed_data": processed_data}
    except Exception as e:
        logger.error(f"Error in analytics task: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def health_check_devices(self, tenant_id: str):
    """Check health of all devices for a tenant"""
    try:
        # Send health check commands to all devices
        topic = f"tenant/{tenant_id}/broadcast/health_check"
        payload = {
            "command": "health_check",
            "timestamp": datetime.utcnow().isoformat()
        }

        mqtt_client.publish(topic, payload)

        return {"status": "completed", "message": "Health check initiated"}
    except Exception as e:
        logger.error(f"Error in health check task: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def generate_tenant_report(self, tenant_id: str, report_type: str, date_range: dict):
    """Generate reports for tenant"""
    try:
        # This would typically generate comprehensive reports
        report_data = {
            "tenant_id": tenant_id,
            "report_type": report_type,
            "date_range": date_range,
            "generated_at": datetime.utcnow().isoformat(),
            "status": "completed"
        }

        # Send notification about report completion
        firebase_client.send_notification(
            tenant_id, "report_generated", report_data
        )

        return report_data
    except Exception as e:
        logger.error(f"Error in report generation task: {e}")
        return {"status": "failed", "error": str(e)}


# New MQTT-triggered tasks
@celery_app.task(bind=True)
def update_device_status_task(self, tenant_id: str, device_id: str, status_data: dict):
    """Update device status in database (triggered by MQTT)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def update_status():
            await connect_to_mongo()
            db = await get_database()

            # Update device status in MongoDB
            update_data = {
                "status": status_data.get("status", "unknown"),
                "last_seen": status_data.get("timestamp", datetime.utcnow().isoformat()),
                "updated_at": datetime.utcnow().isoformat(),
                "connection_info": status_data.get("connection_info", {}),
                "system_info": status_data.get("system_info", {})
            }

            result = await db.devices.update_one(
                {"_id": device_id, "tenant_id": tenant_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                logger.info(f"Updated device status for {tenant_id}/{device_id}")

                # Send real-time update to Firebase
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
    """Process device telemetry data (triggered by MQTT)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def process_telemetry():
            await connect_to_mongo()
            db = await get_database()

            # Store telemetry data
            telemetry_doc = {
                "_id": str(ObjectId()),
                "tenant_id": tenant_id,
                "device_id": device_id,
                "timestamp": telemetry_data.get("timestamp", datetime.utcnow().isoformat()),
                "data": telemetry_data.get("data", {}),
                "metrics": telemetry_data.get("metrics", {}),
                "received_at": datetime.utcnow().isoformat()
            }

            await db.telemetry.insert_one(telemetry_doc)

            # Check for alerts based on telemetry data
            await check_telemetry_alerts(tenant_id, device_id, telemetry_data)

            # Send to Firebase for real-time dashboard updates
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
    """Update command status based on device response (triggered by MQTT)"""
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

            # Update command status
            update_data = {
                "status": response_data.get("status", "completed"),
                "result": response_data.get("result", {}),
                "executed_at": response_data.get("timestamp", datetime.utcnow().isoformat()),
                "response_data": response_data
            }

            result = await db.commands.update_one(
                {"_id": command_id, "tenant_id": tenant_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                logger.info(f"Updated command status for {command_id}")

                # Send real-time update to Firebase
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
    """Process device alerts (triggered by MQTT)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def process_alert():
            await connect_to_mongo()
            db = await get_database()

            # Store alert in database
            alert_doc = {
                "_id": str(ObjectId()),
                "tenant_id": tenant_id,
                "device_id": device_id,
                "alert_type": alert_data.get("type", "unknown"),
                "severity": alert_data.get("severity", "medium"),
                "message": alert_data.get("message", ""),
                "details": alert_data.get("details", {}),
                "timestamp": alert_data.get("timestamp", datetime.utcnow().isoformat()),
                "acknowledged": False,
                "resolved": False
            }

            await db.alerts.insert_one(alert_doc)

            # Send notification based on severity
            if alert_data.get("severity") in ["high", "critical"]:
                firebase_client.send_notification(
                    tenant_id, "critical_alert", {
                        "device_id": device_id,
                        "alert_type": alert_data.get("type"),
                        "message": alert_data.get("message"),
                        "severity": alert_data.get("severity")
                    }
                )

            # Send real-time update to Firebase
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
    """Update device heartbeat (triggered by MQTT)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def update_heartbeat():
            await connect_to_mongo()
            db = await get_database()

            # Update last heartbeat timestamp
            update_data = {
                "last_heartbeat": heartbeat_data.get("timestamp", datetime.utcnow().isoformat()),
                "status": "online",
                "updated_at": datetime.utcnow().isoformat()
            }

            result = await db.devices.update_one(
                {"_id": device_id, "tenant_id": tenant_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                logger.debug(f"Updated heartbeat for {tenant_id}/{device_id}")

            # Check for offline devices (no heartbeat in last 5 minutes)
            await check_offline_devices(tenant_id)

        loop.run_until_complete(update_heartbeat())
        loop.close()

        return {"status": "completed", "device_id": device_id}
    except Exception as e:
        logger.error(f"Error updating heartbeat: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def check_offline_devices_task(self, tenant_id: str):
    """Check for offline devices and send alerts"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def check_offline():
            await connect_to_mongo()
            db = await get_database()

            # Find devices that haven't sent heartbeat in last 5 minutes
            offline_threshold = datetime.utcnow() - timedelta(minutes=5)

            cursor = db.devices.find({
                "tenant_id": tenant_id,
                "last_heartbeat": {"$lt": offline_threshold.isoformat()},
                "status": {"$ne": "offline"}
            })

            offline_devices = []
            async for device in cursor:
                # Mark device as offline
                await db.devices.update_one(
                    {"_id": device["_id"]},
                    {"$set": {"status": "offline", "updated_at": datetime.utcnow().isoformat()}}
                )

                offline_devices.append(device["_id"])

                # Send alert for offline device
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


# Helper functions
async def check_telemetry_alerts(tenant_id: str, device_id: str, telemetry_data: dict):
    """Check telemetry data for alert conditions"""
    try:
        db = await get_database()

        # Get device configuration for alert thresholds
        device = await db.devices.find_one({"_id": device_id, "tenant_id": tenant_id})
        if not device:
            return

        alert_config = device.get("alert_config", {})
        metrics = telemetry_data.get("metrics", {})

        # Check temperature alerts
        if "temperature" in metrics and "temperature_threshold" in alert_config:
            temp = metrics["temperature"]
            threshold = alert_config["temperature_threshold"]

            if temp > threshold:
                # Trigger alert processing task
                process_device_alert_task.delay(tenant_id, device_id, {
                    "type": "temperature_high",
                    "severity": "high",
                    "message": f"Temperature exceeded threshold: {temp}°C > {threshold}°C",
                    "details": {"current_temp": temp, "threshold": threshold},
                    "timestamp": datetime.utcnow().isoformat()
                })

        # Add more alert conditions as needed

    except Exception as e:
        logger.error(f"Error checking telemetry alerts: {e}")


async def check_offline_devices(tenant_id: str):
    """Check for offline devices"""
    # Schedule the offline check task
    check_offline_devices_task.delay(tenant_id)


# Periodic tasks
@celery_app.task(bind=True)
def periodic_device_health_check(self):
    """Periodic task to check device health across all tenants"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def check_all_tenants():
            await connect_to_mongo()
            db = await get_database()

            # Get all active tenants
            cursor = db.tenants.find({"is_active": True})

            async for tenant in cursor:
                tenant_id = tenant["_id"]

                # Check offline devices for each tenant
                check_offline_devices_task.delay(tenant_id)

                # Send health check to all devices
                health_check_devices.delay(tenant_id)

        loop.run_until_complete(check_all_tenants())
        loop.close()

        return {"status": "completed", "message": "Health check initiated for all tenants"}
    except Exception as e:
        logger.error(f"Error in periodic health check: {e}")
        return {"status": "failed", "error": str(e)}


# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    'periodic-device-health-check': {
        'task': 'celery_tasks.periodic_device_health_check',
        'schedule': 300.0,  # Run every 5 minutes
    },
}
celery_app.conf.timezone = 'UTC'