"""TSN 流 CRUD + PTP 同步状态路由。"""

import asyncio
import logging
import os

import aiofiles

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from models import (
    StreamCreate, StreamUpdate, StreamPatch, StreamResponse,
)

logger = logging.getLogger("tsn")
router = APIRouter(prefix="/api/tsn", tags=["TSN 配置"])

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)

# ==================== 流存储 + 并发锁 ====================

_streams: list[dict] = [
    {
        "id": 1, "stream_id": "a0-00-00-00-00-00-00-01",
        "talker": "TSN-Talker-01", "listener": "TSN-Listener-01",
        "vlan": 100, "pcp": 3, "bandwidth": "100Mbps", "status": "active",
    },
    {
        "id": 2, "stream_id": "a0-00-00-00-00-00-00-02",
        "talker": "TSN-Talker-02", "listener": "TSN-Listener-01",
        "vlan": 200, "pcp": 2, "bandwidth": "50Mbps", "status": "active",
    },
]
_stream_lock = asyncio.Lock()


def _next_id(items: list[dict]) -> int:
    return max(d["id"] for d in items) + 1 if items else 1


def _find(items: list[dict], sid: int) -> dict | None:
    return next((s for s in items if s["id"] == sid), None)


# ==================== 流 CRUD ====================

@router.get("/streams", response_model=list[StreamResponse])
async def list_streams():
    async with _stream_lock:
        return [StreamResponse(**s) for s in _streams]


@router.get("/streams/{sid}", response_model=StreamResponse)
async def get_stream(sid: int):
    async with _stream_lock:
        stream = _find(_streams, sid)
        if stream is None:
            raise HTTPException(status_code=404, detail="流未找到")
        return StreamResponse(**stream)


@router.post("/streams", status_code=201, response_model=StreamResponse)
async def add_stream(stream: StreamCreate):
    async with _stream_lock:
        new_data = stream.model_dump()
        new_data["id"] = _next_id(_streams)
        _streams.append(new_data)
        return StreamResponse(**new_data)


@router.put("/streams/{sid}", response_model=StreamResponse)
async def full_update_stream(sid: int, stream: StreamUpdate):
    """全量替换流 —— 所有字段必填。"""
    async with _stream_lock:
        existing = _find(_streams, sid)
        if existing is None:
            raise HTTPException(status_code=404, detail="流未找到")
        new_data = stream.model_dump()
        new_data["id"] = sid
        existing.clear()
        existing.update(new_data)
        return StreamResponse(**existing)


@router.patch("/streams/{sid}", response_model=StreamResponse)
async def partial_update_stream(sid: int, stream: StreamPatch):
    """部分更新流 —— 只更新传入的字段，其余保持。"""
    async with _stream_lock:
        existing = _find(_streams, sid)
        if existing is None:
            raise HTTPException(status_code=404, detail="流未找到")
        patch_data = stream.model_dump(exclude_unset=True)
        existing.update(patch_data)
        return StreamResponse(**existing)


@router.delete("/streams/{sid}", status_code=204)
async def delete_stream(sid: int):
    async with _stream_lock:
        existing = _find(_streams, sid)
        if existing is None:
            raise HTTPException(status_code=404, detail="流未找到")
        _streams.remove(existing)
    return Response(status_code=204)


# ==================== PTP 状态（只读） ====================

async def _read_text_async(filename: str) -> str | None:
    filepath = os.path.join(DATA_DIR, filename)
    try:
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            return await f.read()
    except FileNotFoundError:
        return None


def _parse_ptp_status(text: str) -> dict:
    status: dict = {}
    for line in text.strip().split("\n"):
        if "=" in line:
            key, _, value = line.partition("=")
            status[key.strip()] = value.strip()
    return status


@router.get("/ptp/status", response_model=dict)
async def get_ptp_status():
    text = await _read_text_async("ptp_status.txt")
    if text is None:
        raise HTTPException(status_code=500, detail="ptp_status.txt 不存在")
    return _parse_ptp_status(text)
