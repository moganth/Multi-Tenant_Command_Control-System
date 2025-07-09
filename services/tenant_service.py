from typing import List, Optional
from datetime import datetime, UTC
from schemas.tenant import Tenant, TenantCreate
from utils.database import get_database
from bson import ObjectId


class TenantService:
    async def create_tenant(self, tenant_data: TenantCreate) -> Tenant:
        db = await get_database()

        tenant_doc = {
            "_id": str(ObjectId()),
            "name": tenant_data.name,
            "description": tenant_data.description,
            "settings": tenant_data.settings,
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        await db.tenants.insert_one(tenant_doc)

        return Tenant(**tenant_doc, id=tenant_doc["_id"])

    async def get_tenants(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        db = await get_database()

        cursor = db.tenants.find().skip(skip).limit(limit)
        tenants = []

        async for doc in cursor:
            tenants.append(Tenant(**doc, id=doc["_id"]))

        return tenants

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        db = await get_database()

        doc = await db.tenants.find_one({"_id": tenant_id})
        if not doc:
            return None

        return Tenant(**doc, id=doc["_id"])


tenant_service = TenantService()