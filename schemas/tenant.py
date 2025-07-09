from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class TenantCreate(BaseModel):
    name: str
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = {}

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class Tenant(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    settings: Dict[str, Any] = {}
    is_active: bool = True
    created_at: datetime
    updated_at: datetime