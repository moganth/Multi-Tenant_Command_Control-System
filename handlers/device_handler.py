from typing import List
from fastapi import HTTPException, status, Depends
from schemas.device import Device, DeviceCreate, DeviceUpdate, Command, CommandCreate
from schemas.auth import User
from services.device_service import device_service
from handlers.auth_handler import get_current_active_user


class DeviceHandler:
    async def create_device(
            self,
            device_data: DeviceCreate,
            current_user: User = Depends(get_current_active_user)
    ) -> Device:
        return await device_service.create_device(device_data, current_user.tenant_id)

    async def get_devices(
            self,
            skip: int = 0,
            limit: int = 100,
            current_user: User = Depends(get_current_active_user)
    ) -> List[Device]:
        return await device_service.get_devices(current_user.tenant_id, skip, limit)

    async def get_device(
            self,
            device_id: str,
            current_user: User = Depends(get_current_active_user)
    ) -> Device:
        device = await device_service.get_device(device_id, current_user.tenant_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        return device

    async def update_device(
            self,
            device_id: str,
            device_data: DeviceUpdate,
            current_user: User = Depends(get_current_active_user)
    ) -> Device:
        device = await device_service.update_device(device_id, current_user.tenant_id, device_data)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        return device

    async def delete_device(
            self,
            device_id: str,
            current_user: User = Depends(get_current_active_user)
    ) -> dict:
        success = await device_service.delete_device(device_id, current_user.tenant_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        return {"message": "Device deleted successfully"}

    async def send_command(
            self,
            command_data: CommandCreate,
            current_user: User = Depends(get_current_active_user)
    ) -> Command:
        return await device_service.send_command(command_data, current_user.tenant_id)


device_handler = DeviceHandler()