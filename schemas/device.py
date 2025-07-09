from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"

class DeviceCreate(BaseModel):
    name: str
    device_type: str
    description: Optional[str] = None
    location: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = {}

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    status: Optional[DeviceStatus] = None

class Device(BaseModel):
    id: str
    name: str
    device_type: str
    tenant_id: str
    description: Optional[str] = None
    location: Optional[str] = None
    status: DeviceStatus = DeviceStatus.OFFLINE
    configuration: Dict[str, Any] = {}
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class CommandCreate(BaseModel):
    device_id: str
    command: str
    parameters: Optional[Dict[str, Any]] = {}

class Command(BaseModel):
    id: str
    device_id: str
    tenant_id: str
    command: str
    parameters: Dict[str, Any]
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    executed_at: Optional[datetime] = None
