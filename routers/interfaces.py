"""网络接口路由：网卡列表 / 详情 / TSN 能力（只读，带定时刷新缓存）。"""

import asyncio
import json
import logging
import os

import aiofiles

from fastapi import APIRouter, HTTPException

from models import InterfaceInfo, InterfaceTSNResponse

logger = logging.getLogger("interfaces")
router = APIRouter(prefix="/api", tags=["网络接口"])

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)

# ==================== 内存缓存 + 后台刷新 ====================

_refresh_interval: int = 10  # 秒
_cache: list[InterfaceInfo] = []
_cache_lock = asyncio.Lock()


async def _load_interfaces() -> list[InterfaceInfo] | None:
    """从文件加载网卡数据，失败返回 None。"""
    filepath = os.path.join(DATA_DIR, "interfaces.json")
    try:
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            raw = await f.read()
        data = json.loads(raw)
        return [InterfaceInfo(**item) for item in data]
    except FileNotFoundError:
        logger.error(f"{filepath} 不存在")
        return None
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"解析 {filepath} 失败: {e}")
        return None


async def _refresh_loop():
    """后台无限循环：每隔 _refresh_interval 秒重读文件更新缓存。"""
    global _cache
    while True:
        await asyncio.sleep(_refresh_interval)
        new_data = await _load_interfaces()
        if new_data is not None:
            async with _cache_lock:
                _cache = new_data
            logger.info(f"interfaces 缓存已刷新，共 {len(_cache)} 个网卡")
        else:
            logger.warning("刷新 interfaces 缓存失败，保留旧数据")


async def init_interfaces_cache():
    """启动时调用：加载初始数据 + 启动后台刷新任务。"""
    global _cache
    data = await _load_interfaces()
    if data is not None:
        _cache = data
        logger.info(f"interfaces 初始缓存加载完成，共 {len(_cache)} 个网卡")
    else:
        logger.error("启动时加载 interfaces 缓存失败！")
    asyncio.create_task(_refresh_loop())


# ==================== 路由 ====================

@router.get("/interfaces", response_model=list[InterfaceInfo])
async def list_interfaces():
    async with _cache_lock:
        if not _cache:
            raise HTTPException(status_code=500, detail="interfaces 缓存为空")
        return _cache


@router.get("/interfaces/{name}", response_model=InterfaceInfo)
async def get_interface(name: str):
    async with _cache_lock:
        for iface in _cache:
            if iface.name == name:
                return iface
    raise HTTPException(status_code=404, detail=f"接口 {name} 不存在")


@router.get("/interfaces/{name}/tsn", response_model=InterfaceTSNResponse)
async def get_interface_tsn(name: str):
    async with _cache_lock:
        for iface in _cache:
            if iface.name == name:
                return InterfaceTSNResponse(interface=name, tsn=iface.tsn)
    raise HTTPException(status_code=404, detail=f"接口 {name} 不存在")
