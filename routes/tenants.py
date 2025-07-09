from fastapi import APIRouter, Depends, Query
from typing import List
from schemas.tenant import Tenant, TenantCreate, TenantUpdate
from handlers.tenant_handler import tenant_handler

router = APIRouter()

@router.post("/", response_model=Tenant)
async def create_tenant(tenant_data: TenantCreate):
    return await tenant_handler.create_tenant(tenant_data)

@router.get("/", response_model=List[Tenant])
async def get_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    return await tenant_handler.get_tenants(skip, limit)

@router.get("/{tenant_id}", response_model=Tenant)
async def get_tenant(tenant_id: str):
    return await tenant_handler.get_tenant(tenant_id)