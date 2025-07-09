from typing import List
from fastapi import HTTPException, status, Depends
from schemas.tenant import Tenant, TenantCreate, TenantUpdate
from schemas.auth import User
from services.tenant_service import tenant_service
from handlers.auth_handler import get_current_active_user


class TenantHandler:
    async def create_tenant(self, tenant_data: TenantCreate) -> Tenant:
        return await tenant_service.create_tenant(tenant_data)

    async def get_tenants(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        return await tenant_service.get_tenants(skip, limit)

    async def get_tenant(self, tenant_id: str) -> Tenant:
        tenant = await tenant_service.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        return tenant


tenant_handler = TenantHandler()