from typing import List, Optional
from datetime import datetime, UTC
from schemas.device import Device, DeviceCreate, DeviceUpdate, Command, CommandCreate
from utils.database import get_database
from utils.mqtt_client import mqtt_client
from utils.firebase_client import firebase_client
from bson import ObjectId


class DeviceService:
    async def create_device(self, device_data: DeviceCreate, tenant_id: str) -> Device:
        db = await get_database()

        device_doc = {
            "_id": str(ObjectId()),
            "name": device_data.name,
            "device_type": device_data.device_type,
            "tenant_id": tenant_id,
            "description": device_data.description,
            "location": device_data.location,
            "status": "offline",
            "configuration": device_data.configuration,
            "last_seen": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        await db.devices.insert_one(device_doc)

        # Subscribe to device MQTT topics
        mqtt_client.subscribe(f"tenant/{tenant_id}/device/{device_doc['_id']}/status")
        mqtt_client.subscribe(f"tenant/{tenant_id}/device/{device_doc['_id']}/response")

        device = Device(**device_doc, id=device_doc["_id"])

        # Send real-time update
        firebase_client.send_real_time_update(
            tenant_id, "devices", device.id, device.model_dump()
        )

        return device

    async def get_devices(self, tenant_id: str, skip: int = 0, limit: int = 100) -> List[Device]:
        db = await get_database()

        cursor = db.devices.find({"tenant_id": tenant_id}).skip(skip).limit(limit)
        devices = []

        async for doc in cursor:
            devices.append(Device(**doc, id=doc["_id"]))

        return devices

    async def get_device(self, device_id: str, tenant_id: str) -> Optional[Device]:
        db = await get_database()

        doc = await db.devices.find_one({"_id": device_id, "tenant_id": tenant_id})
        if not doc:
            return None

        return Device(**doc, id=doc["_id"])

    async def update_device(self, device_id: str, tenant_id: str, device_data: DeviceUpdate) -> Optional[Device]:
        db = await get_database()

        update_data = {k: v for k, v in device_data.model_dump().items() if v is not None}
        update_data["updated_at"] = datetime.now(UTC)

        result = await db.devices.update_one(
            {"_id": device_id, "tenant_id": tenant_id},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            return None

        updated_doc = await db.devices.find_one({"_id": device_id, "tenant_id": tenant_id})
        device = Device(**updated_doc, id=updated_doc["_id"])

        # Send real-time update
        firebase_client.send_real_time_update(
            tenant_id, "devices", device.id, device.model_dump()
        )

        return device

    async def delete_device(self, device_id: str, tenant_id: str) -> bool:
        db = await get_database()

        result = await db.devices.delete_one({"_id": device_id, "tenant_id": tenant_id})

        if result.deleted_count > 0:
            # Send real-time update
            firebase_client.send_real_time_update(
                tenant_id, "devices", device_id, {"deleted": True}
            )
            return True

        return False

    async def send_command(self, command_data: CommandCreate, tenant_id: str) -> Command:
        db = await get_database()

        command_doc = {
            "_id": str(ObjectId()),
            "device_id": command_data.device_id,
            "tenant_id": tenant_id,
            "command": command_data.command,
            "parameters": command_data.parameters,
            "status": "pending",
            "result": None,
            "created_at": datetime.now(UTC),
            "executed_at": None
        }

        await db.commands.insert_one(command_doc)

        # Send command via MQTT
        mqtt_client.publish(
            f"tenant/{tenant_id}/device/{command_data.device_id}/command",
            {
                "command_id": command_doc["_id"],
                "command": command_data.command,
                "parameters": command_data.parameters
            }
        )

        command = Command(**command_doc, id=command_doc["_id"])

        # Send real-time update
        firebase_client.send_real_time_update(
            tenant_id, "commands", command.id, command.model_dump()
        )

        return command


device_service = DeviceService()