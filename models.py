"""Pydantic 数据模型 —— 统一管理所有请求/响应结构。"""
#用于定义传输数据的数据结构，包括字段类型、字段名称、字段描述、字段默认值等

from typing import Optional
from pydantic import BaseModel, Field



# ==================== 只读资源模型 ====================

class TSNCapability(BaseModel):
    """网卡 TSN 能力。"""
    capable: bool
    hw_timestamp: bool
    qbv_supported: bool
    qbu_supported: bool
    qci_supported: bool
    qav_supported: bool
    gptp_capable: bool


class InterfaceInfo(BaseModel):
    """网卡信息。"""
    name: str
    ip: str
    mac: str
    status: str
    speed: str
    mtu: int
    tsn: TSNCapability


class InterfaceTSNResponse(BaseModel):
    """网卡 TSN 能力响应。"""
    interface: str
    tsn: TSNCapability


# ==================== 五类 TSN 设备日志模型（报告004 第4.1节）====================

from datetime import datetime
from enum import Enum


# ---------- 通用枚举 ----------

class LogLevel(str, Enum):
    FATAL = "FATAL"
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"


# ---------- 1. 时间同步状态日志（报告004 第4.1.1节）----------

class ClockRole(str, Enum):
    GM = "GM"
    BC = "BC"
    SLAVE = "Slave"
    P2P_MASTER = "P2P Master"
    P2P_SLAVE = "P2P Slave"


class TimeSyncEventType(str, Enum):
    GM_CHANGE = "GM_CHANGE"
    SYNC_LOST = "SYNC_LOST"
    SYNC_RECOVERED = "SYNC_RECOVERED"
    OFFSET_ALARM = "OFFSET_ALARM"
    FREQ_ALARM = "FREQ_ALARM"
    PORT_STATE_CHANGE = "PORT_STATE_CHANGE"
    PKT_LOSS = "PKT_LOSS"
    PKT_ERROR = "PKT_ERROR"
    PORT_ENABLE = "PORT_ENABLE"
    PORT_DISABLE = "PORT_DISABLE"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    PERIODIC_STATS = "PERIODIC_STATS"   # 周期性统计


class TimeSyncLogEntry(BaseModel):
    """时间同步状态日志 —— 单条记录。"""
    timestamp: str = Field(..., description="日志产生时间，精确到 ns（ISO 8601）")
    device_id: str = Field(..., description="设备唯一标识，如 SW-01、ES-05")
    port: str = Field(..., description="物理端口 / 逻辑端口，如 PORT-01、P1")
    level: LogLevel = Field(..., description="日志级别")
    gptp_domain: int = Field(0, description="802.1AS 域编号")
    clock_role: ClockRole = Field(..., description="时钟角色")
    event_type: TimeSyncEventType = Field(..., description="事件类型")
    kv_pairs: dict[str, str] = Field(
        default_factory=dict,
        description="关键字段键值对（offsetFromMaster, meanPathDelay, freqOffset, "
                    "gmIdentity, gmPriority, syncInterval, portState, syncLostCount, "
                    "residenceTime 等）"
    )
    description: str = Field("", description="描述信息")


class TimeSyncLogResponse(BaseModel):
    """时间同步日志查询响应。"""
    total: int
    page: int
    page_size: int
    logs: list[TimeSyncLogEntry]


# ---------- 2. 流量整形与调度日志（报告004 第4.1.2节）----------

class ScheduleType(str, Enum):
    TAS = "802.1Qbv-TAS"       # 时间感知调度
    CBS = "802.1Qav-CBS"       # 信用整形
    CQF = "802.1Qch-CQF"       # 周期感知调度
    PREEMPT = "802.1Qbu+802.3br"  # 帧抢占


class SchedulingLogEntry(BaseModel):
    """流量整形与调度日志 —— 单条记录。"""
    timestamp: str = Field(..., description="UTC 时间戳")
    device_id: str = Field(..., description="设备ID/设备型号")
    port: str = Field(..., description="端口号（物理端口+逻辑队列号）")
    level: LogLevel = Field(..., description="日志级别")
    schedule_type: ScheduleType = Field(..., description="调度/整形类型")
    queue: str = Field(..., description="队列标识")
    stream_id: str = Field(..., description="流标识 Stream ID/MAC")
    event: str = Field(..., description="事件名称")
    kv_pairs: dict[str, str] = Field(
        default_factory=dict,
        description="关键字段键值对（GCL版本号、门控状态、信用值、抢占计数、帧级业务字段等）"
    )


class SchedulingLogResponse(BaseModel):
    """流量调度日志查询响应。"""
    total: int
    page: int
    page_size: int
    logs: list[SchedulingLogEntry]


# ---------- 3. 流过滤与警管日志（报告004 第4.1.3节，交换机专用）----------

class FilterOperation(str, Enum):
    ALLOW = "允许"
    DROP = "丢弃"
    MARK = "标记"
    RATE_LIMIT = "限流"
    BLOCK = "阻塞"


class FilterResourceType(str, Enum):
    FLOW_FILTER = "流过滤"
    POLICING = "警管"
    STREAM_GATE = "流监管"


class FilterStatus(str, Enum):
    HIT = "命中"
    MISS = "未命中"
    GREEN = "Green"
    YELLOW = "Yellow"
    RED = "Red"
    VIOLATION = "违规"


class FilteringLogEntry(BaseModel):
    """流过滤与警管日志 —— 单条记录。"""
    timestamp: str = Field(..., description="时间戳")
    device_id: str = Field(..., description="设备ID/交换机ID")
    port: str = Field(..., description="端口号（入端口+出端口）")
    level: LogLevel = Field(..., description="日志级别")
    operation: FilterOperation = Field(..., description="动作")
    resource_type: FilterResourceType = Field(..., description="资源类型")
    config_id: str = Field(..., description="匹配规则ID/策略ID/Meter ID")
    status: FilterStatus = Field(..., description="状态/判定结果")
    kv_pairs: dict[str, str] = Field(
        default_factory=dict,
        description="关键字段键值对（源/目的MAC、VLAN+PCP、CIR/CBS、令牌桶统计等）"
    )


class FilteringLogResponse(BaseModel):
    """流过滤日志查询响应。"""
    total: int
    page: int
    page_size: int
    logs: list[FilteringLogEntry]


# ---------- 4. 网络资源配置日志（报告004 第4.1.4节）----------

class ConfigEventType(str, Enum):
    TOPOLOGY_CHANGE = "LLDP_TOPO_CHANGE"
    CONFIG_DEPLOY = "CONFIG_DEPLOY"
    CONFIG_VERIFY = "CONFIG_VERIFY"
    CBS_UPDATE = "CBS_UPDATE"
    PSFP_UPDATE = "PSFP_UPDATE"


class ConfigLogEntry(BaseModel):
    """网络资源配置日志 —— 单条记录。"""
    timestamp: str = Field(..., description="时间戳")
    device_id: str = Field(..., description="设备ID")
    level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
    event_type: ConfigEventType = Field(..., description="事件类型")
    description: str = Field("", description="描述信息")
    kv_pairs: dict[str, str] = Field(
        default_factory=dict,
        description="关键字段键值对（邻居设备ID、TSN能力协商结果、配置参数变更等）"
    )


class ConfigLogResponse(BaseModel):
    """资源配置日志查询响应。"""
    total: int
    page: int
    page_size: int
    logs: list[ConfigLogEntry]


# ---------- 5. 硬件资源性能日志（报告004 第4.1.5节）----------

class HardwareMetricType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    BUFFER = "buffer"
    POWER = "power"
    THERMAL = "thermal"


class HardwareLogEntry(BaseModel):
    """硬件资源性能日志 —— 单条记录（周期性）。"""
    timestamp: str = Field(..., description="时间戳")
    device_id: str = Field(..., description="设备ID")
    level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
    metric_type: HardwareMetricType = Field(..., description="指标类型")
    kv_pairs: dict[str, str] = Field(
        default_factory=dict,
        description="关键字段键值对（cpu_percent, mem_percent, buffer_usage, "
                    "fan_speed, temperature 等）"
    )


class HardwareLogResponse(BaseModel):
    """硬件资源日志查询响应。"""
    total: int
    page: int
    page_size: int
    logs: list[HardwareLogEntry]
