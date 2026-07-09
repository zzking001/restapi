"""TSN 设备本地日志查询路由 —— 五类日志的 GET 端点 + 解析器。"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query
from models import (
    LogLevel, ClockRole,
    TimeSyncLogEntry, TimeSyncLogResponse,
    SchedulingLogEntry, SchedulingLogResponse,
    FilteringLogEntry, FilteringLogResponse,
    ConfigLogEntry, ConfigLogResponse,
    HardwareLogEntry, HardwareLogResponse,
)

router = APIRouter(prefix="/api/logs", tags=["日志"])
DATA_DIR = Path(__file__).parent.parent / "data"


# ==================== 工具函数 ====================

def _parse_kv(raw: str) -> dict[str, str]:
    """把 'k1=v1,k2=v2' 解析为 {'k1':'v1','k2':'v2'}。"""
    if not raw or raw.strip() == "-":
        return {}
    result: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def _read_lines(filename: str) -> list[str]:
    """读取日志文件，返回非空行列表。文件不存在时返回空列表。"""
    fp = DATA_DIR / filename
    if not fp.exists():
        return []
    with open(fp, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


# ==================== 加载器 ====================
#对应data中各个log

def load_timesync_logs() -> list[TimeSyncLogEntry]:
    """格式: timestamp|device_id|port|level|gptp_domain|clock_role|event_type|kv_pairs|description"""
    logs: list[TimeSyncLogEntry] = []
    for line in _read_lines("timesync.log"):
        parts = line.split("|")
        if len(parts) < 9:
            continue
        try:
            logs.append(TimeSyncLogEntry(
                timestamp=parts[0],
                device_id=parts[1],
                port=parts[2],
                level=LogLevel(parts[3]),
                gptp_domain=int(parts[4]),
                clock_role=ClockRole(parts[5]),
                event_type=parts[6],
                kv_pairs=_parse_kv(parts[7]),
                description=parts[8],
            ))
        except (ValueError, IndexError):
            continue
    return logs


def load_scheduling_logs() -> list[SchedulingLogEntry]:
    """格式: timestamp|device_id|port|level|schedule_type|queue|stream_id|event|kv_pairs"""
    logs: list[SchedulingLogEntry] = []
    for line in _read_lines("scheduling.log"):
        parts = line.split("|")
        if len(parts) < 9:
            continue
        try:
            logs.append(SchedulingLogEntry(
                timestamp=parts[0],
                device_id=parts[1],
                port=parts[2],
                level=LogLevel(parts[3]),
                schedule_type=parts[4],
                queue=parts[5],
                stream_id=parts[6],
                event=parts[7],
                kv_pairs=_parse_kv(parts[8]),
            ))
        except (ValueError, IndexError):
            continue
    return logs


def load_filtering_logs() -> list[FilteringLogEntry]:
    """格式: timestamp|device_id|port|level|operation|resource_type|config_id|status|kv_pairs"""
    logs: list[FilteringLogEntry] = []
    for line in _read_lines("filtering.log"):
        parts = line.split("|")
        if len(parts) < 9:
            continue
        try:
            logs.append(FilteringLogEntry(
                timestamp=parts[0],
                device_id=parts[1],
                port=parts[2],
                level=LogLevel(parts[3]),
                operation=parts[4],
                resource_type=parts[5],
                config_id=parts[6],
                status=parts[7],
                kv_pairs=_parse_kv(parts[8]),
            ))
        except (ValueError, IndexError):
            continue
    return logs


def load_config_logs() -> list[ConfigLogEntry]:
    """格式: timestamp|device_id|level|event_type|description|kv_pairs"""
    logs: list[ConfigLogEntry] = []
    for line in _read_lines("config.log"):
        parts = line.split("|")
        if len(parts) < 6:
            continue
        try:
            logs.append(ConfigLogEntry(
                timestamp=parts[0],
                device_id=parts[1],
                level=LogLevel(parts[2]),
                event_type=parts[3],
                description=parts[4],
                kv_pairs=_parse_kv(parts[5]),
            ))
        except (ValueError, IndexError):
            continue
    return logs


def load_hardware_logs() -> list[HardwareLogEntry]:
    """格式: timestamp|device_id|level|metric_type|kv_pairs"""
    logs: list[HardwareLogEntry] = []
    for line in _read_lines("hardware.log"):
        parts = line.split("|")
        if len(parts) < 5:
            continue
        try:
            logs.append(HardwareLogEntry(
                timestamp=parts[0],
                device_id=parts[1],
                level=LogLevel(parts[2]),
                metric_type=parts[3],
                kv_pairs=_parse_kv(parts[4]),
            ))
        except (ValueError, IndexError):
            continue
    return logs


# ==================== 通用分页/过滤 → 响应 ====================

def _paginate(items: list, page: int, page_size: int) -> dict:
    """对已过滤的列表做分页，返回 {total, page, page_size, logs}。"""
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {"total": total, "page": page, "page_size": page_size, "logs": items[start:end]}


# ==================== 端点 1: /api/logs/timesync ====================

@router.get("/timesync", response_model=TimeSyncLogResponse)
def get_timesync_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    level: Optional[LogLevel] = Query(None, description="日志级别"),
    device_id: Optional[str] = Query(None, description="设备标识"),
    port: Optional[str] = Query(None, description="端口号"),
    event_type: Optional[str] = Query(None, description="事件类型，如 GM_CHANGE、SYNC_LOST、OFFSET_ALARM"),
    clock_role: Optional[ClockRole] = Query(None, description="时钟角色"),
):
    logs = load_timesync_logs()
    if level is not None:
        logs = [l for l in logs if l.level == level]
    if device_id is not None:
        logs = [l for l in logs if l.device_id == device_id]
    if port is not None:
        logs = [l for l in logs if l.port == port]
    if event_type is not None:
        logs = [l for l in logs if l.event_type == event_type]
    if clock_role is not None:
        logs = [l for l in logs if l.clock_role == clock_role]
    return _paginate(logs, page, page_size)


# ==================== 端点 2: /api/logs/scheduling ====================

@router.get("/scheduling", response_model=SchedulingLogResponse)
def get_scheduling_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    level: Optional[LogLevel] = Query(None, description="日志级别"),
    device_id: Optional[str] = Query(None, description="设备标识"),
    port: Optional[str] = Query(None, description="端口号"),
    schedule_type: Optional[str] = Query(None, description="调度/整形类型"),
    queue: Optional[str] = Query(None, description="队列标识"),
    stream_id: Optional[str] = Query(None, description="流标识"),
):
    logs = load_scheduling_logs()
    if level is not None:
        logs = [l for l in logs if l.level == level]
    if device_id is not None:
        logs = [l for l in logs if l.device_id == device_id]
    if port is not None:
        logs = [l for l in logs if l.port == port]
    if schedule_type is not None:
        logs = [l for l in logs if l.schedule_type == schedule_type]
    if queue is not None:
        logs = [l for l in logs if l.queue == queue]
    if stream_id is not None:
        logs = [l for l in logs if l.stream_id == stream_id]
    return _paginate(logs, page, page_size)


# ==================== 端点 3: /api/logs/filtering ====================

@router.get("/filtering", response_model=FilteringLogResponse)
def get_filtering_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    level: Optional[LogLevel] = Query(None, description="日志级别"),
    device_id: Optional[str] = Query(None, description="设备标识"),
    port: Optional[str] = Query(None, description="端口（入端口->出端口）"),
    operation: Optional[str] = Query(None, description="动作"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    status: Optional[str] = Query(None, description="状态/判定结果"),
):
    logs = load_filtering_logs()
    if level is not None:
        logs = [l for l in logs if l.level == level]
    if device_id is not None:
        logs = [l for l in logs if l.device_id == device_id]
    if port is not None:
        logs = [l for l in logs if l.port == port]
    if operation is not None:
        logs = [l for l in logs if l.operation == operation]
    if resource_type is not None:
        logs = [l for l in logs if l.resource_type == resource_type]
    if status is not None:
        logs = [l for l in logs if l.status == status]
    return _paginate(logs, page, page_size)


# ==================== 端点 4: /api/logs/config ====================

@router.get("/config", response_model=ConfigLogResponse)
def get_config_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    level: Optional[LogLevel] = Query(None, description="日志级别"),
    device_id: Optional[str] = Query(None, description="设备标识"),
    event_type: Optional[str] = Query(None, description="事件类型"),
):
    logs = load_config_logs()
    if level is not None:
        logs = [l for l in logs if l.level == level]
    if device_id is not None:
        logs = [l for l in logs if l.device_id == device_id]
    if event_type is not None:
        logs = [l for l in logs if l.event_type == event_type]
    return _paginate(logs, page, page_size)


# ==================== 端点 5: /api/logs/hardware ====================

@router.get("/hardware", response_model=HardwareLogResponse)
def get_hardware_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    level: Optional[LogLevel] = Query(None, description="日志级别"),
    device_id: Optional[str] = Query(None, description="设备标识"),
    metric_type: Optional[str] = Query(None, description="指标类型"),
):
    logs = load_hardware_logs()
    if level is not None:
        logs = [l for l in logs if l.level == level]
    if device_id is not None:
        logs = [l for l in logs if l.device_id == device_id]
    if metric_type is not None:
        logs = [l for l in logs if l.metric_type == metric_type]
    return _paginate(logs, page, page_size)
