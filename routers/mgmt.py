"""网管数据查询路由 —— NETCONF 通知 + SNMP Trap 的 GET 端点 + 解析器。"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query
from models import (
    NetconfEventType, NetconfSeverity,
    NetconfNotificationEntry, NetconfNotificationResponse,
    SnmpTrapType, SnmpTrapEntry, SnmpTrapResponse,
)

router = APIRouter(prefix="/api/mgmt", tags=["网管"])
DATA_DIR = Path(__file__).parent.parent / "data"


# ==================== 工具函数（复用 logs.py 模式）====================

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
    """读取数据文件，返回非空行列表。"""
    fp = DATA_DIR / filename
    if not fp.exists():
        return []
    with open(fp, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _paginate(items: list, page: int, page_size: int, list_key: str) -> dict:
    """对已过滤的列表做分页，返回 {total, page, page_size, list_key: items}。"""
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {"total": total, "page": page, "page_size": page_size, list_key: items[start:end]}


# ==================== 加载器 ====================

def load_netconf_notifications() -> list[NetconfNotificationEntry]:
    """格式: event_time|device_id|port_id|event_type|severity|kv_pairs"""
    notifications: list[NetconfNotificationEntry] = []
    for line in _read_lines("netconf.log"):
        parts = line.split("|")
        if len(parts) < 6:
            continue
        try:
            notifications.append(NetconfNotificationEntry(
                event_time=parts[0],
                device_id=parts[1],
                port_id=parts[2],
                event_type=NetconfEventType(parts[3]),
                severity=NetconfSeverity(parts[4]),
                kv_pairs=_parse_kv(parts[5]),
            ))
        except (ValueError, IndexError):
            continue
    return notifications


def load_snmp_traps() -> list[SnmpTrapEntry]:
    """格式: timestamp|device_id|trap_oid|trap_type|oid_values"""
    traps: list[SnmpTrapEntry] = []
    for line in _read_lines("snmp_trap.log"):
        parts = line.split("|")
        if len(parts) < 5:
            continue
        try:
            traps.append(SnmpTrapEntry(
                timestamp=parts[0],
                device_id=parts[1],
                trap_oid=parts[2],
                trap_type=SnmpTrapType(parts[3]),
                oid_values=_parse_kv(parts[4]),
            ))
        except (ValueError, IndexError):
            continue
    return traps


# ==================== 端点 1: /api/mgmt/netconf ====================

@router.get("/netconf", response_model=NetconfNotificationResponse)
def get_netconf_notifications(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    severity: Optional[NetconfSeverity] = Query(None, description="严重级别"),
    device_id: Optional[str] = Query(None, description="设备标识"),
    port_id: Optional[str] = Query(None, description="端口标识"),
    event_type: Optional[NetconfEventType] = Query(None, description="事件类型"),
):
    notifications = load_netconf_notifications()
    if severity is not None:
        notifications = [n for n in notifications if n.severity == severity]
    if device_id is not None:
        notifications = [n for n in notifications if n.device_id == device_id]
    if port_id is not None:
        notifications = [n for n in notifications if n.port_id == port_id]
    if event_type is not None:
        notifications = [n for n in notifications if n.event_type == event_type]
    return _paginate(notifications, page, page_size, "notifications")


# ==================== 端点 2: /api/mgmt/snmp ====================

@router.get("/snmp", response_model=SnmpTrapResponse)
def get_snmp_traps(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    device_id: Optional[str] = Query(None, description="设备标识"),
    trap_type: Optional[SnmpTrapType] = Query(None, description="Trap 类型"),
):
    traps = load_snmp_traps()
    if device_id is not None:
        traps = [t for t in traps if t.device_id == device_id]
    if trap_type is not None:
        traps = [t for t in traps if t.trap_type == trap_type]
    return _paginate(traps, page, page_size, "traps")
