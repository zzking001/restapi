"""TSN 设备本地日志查询路由 —— 五类日志的 GET 端点 + 流式加载器。

采用流式读取：逐行解析 → 过滤 → 分页，仅在内存中保留当前页数据，
避免全量加载大日志文件导致 OOM。
"""

import os
from pathlib import Path
from typing import Optional, Callable
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
LOG_DIR = Path(os.environ.get("TSN_LOG_DIR", Path(__file__).parent.parent / "data"))


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


def _stream_file(
    filename: str,
    parse_line: Callable,
    filter_pred: Callable,
    page: int,
    page_size: int,
) -> dict:
    """流式读取日志文件：逐行解析 → 过滤 → 分页。

    只将当前页的 page_size 条记录保留在内存中，其余匹配行仅做计数，
    无论日志文件多大，内存占用始终控制在 O(page_size) 级别。

    Args:
        filename: data 目录下的日志文件名
        parse_line: 解析单行字符串为 Pydantic 对象的函数
        filter_pred: 过滤条件函数，返回 True 表示命中
        page: 页码（从 1 开始）
        page_size: 每页条数

    Returns:
        {"total": int, "page": int, "page_size": int, "logs": list}
    """
    fp = LOG_DIR / filename
    if not fp.exists():
        return {"total": 0, "page": page, "page_size": page_size, "logs": []}

    result: list = []
    total = 0
    skip = (page - 1) * page_size   # 当前页之前需要跳过的匹配条数

    with open(fp, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = parse_line(line)
            except (ValueError, IndexError):
                continue
            if not filter_pred(entry):
                continue

            total += 1
            if total <= skip:
                continue
            if len(result) < page_size:
                result.append(entry)

    return {"total": total, "page": page, "page_size": page_size, "logs": result}


# ==================== 流式加载器 ====================

def load_timesync_logs(
    level: Optional[LogLevel] = None,
    device_id: Optional[str] = None,
    port: Optional[str] = None,
    event_type: Optional[str] = None,
    clock_role: Optional[ClockRole] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """格式: timestamp|device_id|port|level|gptp_domain|clock_role|event_type|kv_pairs|description"""

    def parse(line: str) -> TimeSyncLogEntry:
        parts = line.split("|")
        if len(parts) < 9:
            raise ValueError
        return TimeSyncLogEntry(
            timestamp=parts[0],
            device_id=parts[1],
            port=parts[2],
            level=LogLevel(parts[3]),
            gptp_domain=int(parts[4]),
            clock_role=ClockRole(parts[5]),
            event_type=parts[6],
            kv_pairs=_parse_kv(parts[7]),
            description=parts[8],
        )

    def match(entry: TimeSyncLogEntry) -> bool:
        if level is not None and entry.level != level:
            return False
        if device_id is not None and entry.device_id != device_id:
            return False
        if port is not None and entry.port != port:
            return False
        if event_type is not None and entry.event_type != event_type:
            return False
        if clock_role is not None and entry.clock_role != clock_role:
            return False
        return True

    return _stream_file("timesync.log", parse, match, page, page_size)


def load_scheduling_logs(
    level: Optional[LogLevel] = None,
    device_id: Optional[str] = None,
    port: Optional[str] = None,
    schedule_type: Optional[str] = None,
    queue: Optional[str] = None,
    stream_id: Optional[str] = None,
    event: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """格式: timestamp|device_id|port|level|schedule_type|queue|stream_id|event|kv_pairs"""

    def parse(line: str) -> SchedulingLogEntry:
        parts = line.split("|")
        if len(parts) < 9:
            raise ValueError
        return SchedulingLogEntry(
            timestamp=parts[0],
            device_id=parts[1],
            port=parts[2],
            level=LogLevel(parts[3]),
            schedule_type=parts[4],
            queue=parts[5],
            stream_id=parts[6],
            event=parts[7],
            kv_pairs=_parse_kv(parts[8]),
        )

    def match(entry: SchedulingLogEntry) -> bool:
        if level is not None and entry.level != level:
            return False
        if device_id is not None and entry.device_id != device_id:
            return False
        if port is not None and entry.port != port:
            return False
        if schedule_type is not None and entry.schedule_type != schedule_type:
            return False
        if queue is not None and entry.queue != queue:
            return False
        if stream_id is not None and entry.stream_id != stream_id:
            return False
        if event is not None and entry.event != event:
            return False
        return True

    return _stream_file("scheduling.log", parse, match, page, page_size)


def load_filtering_logs(
    level: Optional[LogLevel] = None,
    device_id: Optional[str] = None,
    port: Optional[str] = None,
    operation: Optional[str] = None,
    resource_type: Optional[str] = None,
    config_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """格式: timestamp|device_id|port|level|operation|resource_type|config_id|status|kv_pairs"""

    def parse(line: str) -> FilteringLogEntry:
        parts = line.split("|")
        if len(parts) < 9:
            raise ValueError
        return FilteringLogEntry(
            timestamp=parts[0],
            device_id=parts[1],
            port=parts[2],
            level=LogLevel(parts[3]),
            operation=parts[4],
            resource_type=parts[5],
            config_id=parts[6],
            status=parts[7],
            kv_pairs=_parse_kv(parts[8]),
        )

    def match(entry: FilteringLogEntry) -> bool:
        if level is not None and entry.level != level:
            return False
        if device_id is not None and entry.device_id != device_id:
            return False
        if port is not None and entry.port != port:
            return False
        if operation is not None and entry.operation != operation:
            return False
        if resource_type is not None and entry.resource_type != resource_type:
            return False
        if config_id is not None and entry.config_id != config_id:
            return False
        if status is not None and entry.status != status:
            return False
        return True

    return _stream_file("filtering.log", parse, match, page, page_size)


def load_config_logs(
    level: Optional[LogLevel] = None,
    device_id: Optional[str] = None,
    event_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """格式: timestamp|device_id|level|event_type|description|kv_pairs"""

    def parse(line: str) -> ConfigLogEntry:
        parts = line.split("|")
        if len(parts) < 6:
            raise ValueError
        return ConfigLogEntry(
            timestamp=parts[0],
            device_id=parts[1],
            level=LogLevel(parts[2]),
            event_type=parts[3],
            description=parts[4],
            kv_pairs=_parse_kv(parts[5]),
        )

    def match(entry: ConfigLogEntry) -> bool:
        if level is not None and entry.level != level:
            return False
        if device_id is not None and entry.device_id != device_id:
            return False
        if event_type is not None and entry.event_type != event_type:
            return False
        return True

    return _stream_file("config.log", parse, match, page, page_size)


def load_hardware_logs(
    level: Optional[LogLevel] = None,
    device_id: Optional[str] = None,
    metric_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """格式: timestamp|device_id|level|metric_type|kv_pairs"""

    def parse(line: str) -> HardwareLogEntry:
        parts = line.split("|")
        if len(parts) < 5:
            raise ValueError
        return HardwareLogEntry(
            timestamp=parts[0],
            device_id=parts[1],
            level=LogLevel(parts[2]),
            metric_type=parts[3],
            kv_pairs=_parse_kv(parts[4]),
        )

    def match(entry: HardwareLogEntry) -> bool:
        if level is not None and entry.level != level:
            return False
        if device_id is not None and entry.device_id != device_id:
            return False
        if metric_type is not None and entry.metric_type != metric_type:
            return False
        return True

    return _stream_file("hardware.log", parse, match, page, page_size)


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
    return load_timesync_logs(
        level=level, device_id=device_id, port=port,
        event_type=event_type, clock_role=clock_role,
        page=page, page_size=page_size,
    )


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
    event: Optional[str] = Query(None, description="调度事件名称，如 GCL_LOAD、QUEUE_OVERFLOW"),
):
    return load_scheduling_logs(
        level=level, device_id=device_id, port=port,
        schedule_type=schedule_type, queue=queue, stream_id=stream_id, event=event,
        page=page, page_size=page_size,
    )


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
    config_id: Optional[str] = Query(None, description="过滤策略/配置标识，按策略 ID 反查命中日志"),
    status: Optional[str] = Query(None, description="状态/判定结果"),
):
    return load_filtering_logs(
        level=level, device_id=device_id, port=port,
        operation=operation, resource_type=resource_type,
        config_id=config_id, status=status,
        page=page, page_size=page_size,
    )


# ==================== 端点 4: /api/logs/config ====================

@router.get("/config", response_model=ConfigLogResponse)
def get_config_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    level: Optional[LogLevel] = Query(None, description="日志级别"),
    device_id: Optional[str] = Query(None, description="设备标识"),
    event_type: Optional[str] = Query(None, description="事件类型"),
):
    return load_config_logs(
        level=level, device_id=device_id, event_type=event_type,
        page=page, page_size=page_size,
    )


# ==================== 端点 5: /api/logs/hardware ====================

@router.get("/hardware", response_model=HardwareLogResponse)
def get_hardware_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    level: Optional[LogLevel] = Query(None, description="日志级别"),
    device_id: Optional[str] = Query(None, description="设备标识"),
    metric_type: Optional[str] = Query(None, description="指标类型"),
):
    return load_hardware_logs(
        level=level, device_id=device_id, metric_type=metric_type,
        page=page, page_size=page_size,
    )
