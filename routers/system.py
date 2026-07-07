"""系统监控路由：CPU / 内存 / 运行时间（只读）。"""

import os
import aiofiles

from fastapi import APIRouter, HTTPException

from models import CPUResponse, CPUInfo

router = APIRouter(prefix="/api", tags=["系统监控"])

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)


async def read_text_file_async(filename: str) -> str | None:
    """异步读取 data/ 目录下的文本文件。"""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            return await f.read()
    except FileNotFoundError:
        return None


# ==================== CPU ====================

@router.get("/cpus", response_model=CPUResponse)
async def get_cpus():
    text = await read_text_file_async("cpuinfo.txt")
    if text is None:
        raise HTTPException(status_code=500, detail="cpuinfo.txt 不存在")
    cpus = _parse_cpuinfo(text)
    return CPUResponse(count=len(cpus), cpus=cpus)


def _parse_cpuinfo(text: str) -> list[CPUInfo]:
    """解析 /proc/cpuinfo 格式文本。"""
    result = []
    for block in text.strip().split("\n\n"):
        cpu_dict: dict = {}
        for line in block.strip().split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                cpu_dict[key.strip()] = value.strip()
        if cpu_dict:
            result.append(CPUInfo(**cpu_dict))
    return result


# ==================== 内存 ====================

@router.get("/memory", response_model=dict)
async def get_memory():
    text = await read_text_file_async("meminfo.txt")
    if text is None:
        raise HTTPException(status_code=500, detail="meminfo.txt 不存在")
    return _parse_meminfo(text)


def _parse_meminfo(text: str) -> dict:
    """解析 /proc/meminfo 格式文本。"""
    mem: dict = {}
    for line in text.strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip()
            if value.endswith("kB"):
                value = value[:-2].strip()
            try:
                mem[key.strip()] = int(value)
            except ValueError:
                mem[key.strip()] = value
    return mem


# ==================== 运行时间 ====================

@router.get("/uptime", response_model=dict)
async def get_uptime():
    text = await read_text_file_async("uptime.txt")
    if text is None:
        raise HTTPException(status_code=500, detail="uptime.txt 不存在")
    return _parse_uptime(text)


def _parse_uptime(text: str) -> dict:
    """解析 /proc/uptime 格式。"""
    parts = text.strip().split()
    uptime_seconds = float(parts[0]) if len(parts) > 0 else 0
    idle_seconds = float(parts[1]) if len(parts) > 1 else 0
    return {
        "uptime_seconds": uptime_seconds,
        "idle_seconds": idle_seconds,
        "uptime_days": round(uptime_seconds / 86400, 2),
    }
