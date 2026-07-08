"""TSN 设备 CRUD 路由（内存存储，asyncio.Lock 并发保护）。"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from models import (
    DeviceCreate, DeviceUpdate, DevicePatch, DeviceResponse,
)
#给这个文件创建一个专属的日志记录器
logger = logging.getLogger("devices")
#创建路由对象，用于注册路由和分组
#prefix="/api"，表示路由前缀，这个路由器下所有端点的 URL 都自动加 /api
#tags=["设备管理"]，/docs 页面上，这组端点归在"设备管理"标题下
router = APIRouter(prefix="/api", tags=["设备管理"])

# ==================== 种子数据 + 并发锁 ====================

_devices: list[dict] = [
    {
        "id": 1, "name": "TSN-Talker-01", "type": "talker",
        "mac": "00:1b:44:11:3a:b7", "stream_id": "a0-00-00-00-00-00-00-01",
        "vlan": 100, "pcp": 3, "status": "online",
    },
    {
        "id": 2, "name": "TSN-Listener-01", "type": "listener",
        "mac": "00:1b:44:11:3a:b8", "stream_id": "a0-00-00-00-00-00-00-01",
        "vlan": 100, "pcp": 3, "status": "online",
    },
    {
        "id": 3, "name": "TSN-Bridge-A", "type": "bridge",
        "mac": "00:1b:44:11:3a:b9", "stream_id": "-",
        "vlan": 100, "pcp": 3, "status": "online",
    },
]
_lock = asyncio.Lock()

# ==================== 辅助函数 ====================
def _next_id(items: list[dict]) -> int:
    return max(d["id"] for d in items) + 1 if items else 1


def _find(items: list[dict], device_id: int) -> dict | None:
    return next((d for d in items if d["id"] == device_id), None)


# ==================== GET ====================

@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices():
    async with _lock:
        return [DeviceResponse(**d) for d in _devices]


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: int):
    async with _lock:
        device = _find(_devices, device_id)
        if device is None:
            raise HTTPException(status_code=404, detail="设备未找到")
        return DeviceResponse(**device)


# ==================== POST ====================

@router.post("/devices", status_code=201, response_model=DeviceResponse)
async def add_device(device: DeviceCreate):
    async with _lock:
        new_data = device.model_dump()
        new_data["id"] = _next_id(_devices)
        _devices.append(new_data)
        return DeviceResponse(**new_data)


# ==================== PUT（全量替换，新增） ====================

@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def full_update_device(device_id: int, device: DeviceUpdate):
    """全量替换设备 —— 请求体必须包含所有字段。"""
    async with _lock:
        existing = _find(_devices, device_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="设备未找到")
        new_data = device.model_dump()
        new_data["id"] = device_id
        existing.clear()
        existing.update(new_data)
        return DeviceResponse(**existing)


# ==================== PATCH（部分更新，原 PUT 行为迁移） ====================

@router.patch("/devices/{device_id}", response_model=DeviceResponse)
async def partial_update_device(device_id: int, device: DevicePatch):
    """部分更新设备 —— 只更新传入的字段，其余保持不变。"""
    async with _lock:
        existing = _find(_devices, device_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="设备未找到")
        patch_data = device.model_dump(exclude_unset=True)
        existing.update(patch_data)
        return DeviceResponse(**existing)


# ==================== DELETE ====================

@router.delete("/devices/{device_id}", status_code=204)
async def delete_device(device_id: int):
    async with _lock:
        existing = _find(_devices, device_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="设备未找到")
        _devices.remove(existing)
    return Response(status_code=204)
