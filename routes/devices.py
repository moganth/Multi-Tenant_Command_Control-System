from fastapi import APIRouter, Depends, Query
from typing import List
from schemas.device import Device, DeviceCreate, DeviceUpdate, Command, CommandCreate
from handlers.device_handler import device_handler

router = APIRouter()

@router.post("/", response_model=Device)
async def create_device(device_data: DeviceCreate = Depends(device_handler.create_device)):
    return device_data

@router.get("/", response_model=List[Device])
async def get_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    devices: List[Device] = Depends(device_handler.get_devices)
):
    return devices

@router.get("/{device_id}", response_model=Device)
async def get_device(device: Device = Depends(device_handler.get_device)):
    return device

@router.put("/{device_id}", response_model=Device)
async def update_device(device: Device = Depends(device_handler.update_device)):
    return device

@router.delete("/{device_id}")
async def delete_device(result: dict = Depends(device_handler.delete_device)):
    return result

@router.post("/commands", response_model=Command)
async def send_command(command: Command = Depends(device_handler.send_command)):
    return command
