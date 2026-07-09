"""Pydantic 数据模型 —— 统一管理所有请求/响应结构。"""
#用于定义传输数据的数据结构，包括字段类型、字段名称、字段描述、字段默认值等

from typing import Optional
from pydantic import BaseModel, Field



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
#[时间戳] [设备ID] [端口号] [日志级别] [gPTP域] [时钟角色] [事件类型] [关键字段键值对] [描述信息]

#时钟角色，ClockRole 的值域是 IEEE 802.1AS 标准严格定义的，只有 5 种角色
class ClockRole(str, Enum):
    GM = "GM"
    BC = "BC"
    SLAVE = "Slave"
    P2P_MASTER = "P2P Master"
    P2P_SLAVE = "P2P Slave"

#[时间戳] [设备ID] [端口号] [日志级别] [gPTP域] [时钟角色] [事件类型] [关键字段键值对] [描述信息]
class TimeSyncLogEntry(BaseModel):
    """时间同步状态日志 —— 单条记录。"""
    timestamp: str = Field(..., description="日志产生时间，精确到 ns（ISO 8601）")
    device_id: str = Field(..., description="设备唯一标识，如 SW-01、ES-05")
    port: str = Field(..., description="物理端口 / 逻辑端口，如 PORT-01、P1")
    level: LogLevel = Field(..., description="日志级别")
    gptp_domain: int = Field(0, description="802.1AS 域编号")
    clock_role: ClockRole = Field(..., description="时钟角色")
    event_type: str = Field(..., description="事件类型，如 GM_CHANGE、SYNC_LOST、OFFSET_ALARM")
    kv_pairs: dict[str, str] = Field(
        default_factory=dict,
        description="关键字段键值对：offset（主从时间偏移ns）、delay（平均链路延迟ns）、"
                    "freq（频率偏差ppb）、gmId（上级GM时钟ID）、gmPriority（GM优先级）、"
                    "syncInt（Sync报文周期s）、State（端口gPTP状态）、"
                    "syncLost（连续丢失计数）、residence（交换机驻留时间ns）"
    )
    description: str = Field("", description="描述信息")


class TimeSyncLogResponse(BaseModel):#定义 API 返回给客户端的响应数据结构
    """时间同步日志查询响应。"""
    total: int
    page: int
    page_size: int
    logs: list[TimeSyncLogEntry]


# ---------- 2. 流量整形与调度日志（报告004 第4.1.2节）----------
#[时间戳] [设备ID] [端口] [级别] [调度类型] [队列] [流ID] [事件] [关键字段键值对]

class SchedulingLogEntry(BaseModel):
    """流量整形与调度日志 —— 单条记录。"""
    timestamp: str = Field(..., description="UTC 时间戳")
    device_id: str = Field(..., description="设备ID/设备型号")
    port: str = Field(..., description="端口号（物理端口+逻辑队列号）")
    level: LogLevel = Field(..., description="日志级别")
    schedule_type: str = Field(..., description="调度/整形类型，如 802.1Qbv-TAS、802.1Qav-CBS、802.1Qch-CQF、802.1Qbu+802.3br 等")
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
#[时间戳] [设备] [端口] [级别] [操作] [资源类型] [配置ID] [状态] [关键字段键值对]

class FilteringLogEntry(BaseModel):
    """流过滤与警管日志 —— 单条记录。"""
    timestamp: str = Field(..., description="时间戳")
    device_id: str = Field(..., description="设备ID/交换机ID")
    port: str = Field(..., description="端口号（入端口+出端口）")
    level: LogLevel = Field(..., description="日志级别")
    operation: str = Field(..., description="动作，如 允许、丢弃、标记、限流、阻塞 等")
    resource_type: str = Field(..., description="资源类型，如 流过滤、警管、流监管 等")
    config_id: str = Field(..., description="匹配规则ID/策略ID/Meter ID")
    status: str = Field(..., description="状态/判定结果，如 命中、未命中、Green、Yellow、Red、违规 等")
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
# 记录TSN网络中控制平面的详细配置流程，反映网络拓扑和流配置的变化，日志记录以下几点数据。
# （1）拓扑发现变化：记录LLDP（链路层发现协议）发现的邻居设备变化，特别是TSN能力字段的协商结果。
# （2）配置下发验证：记录机载网络控制器或地面网络控制器对CBS、PSFP等协议参数的修改操作。

class ConfigLogEntry(BaseModel):
    """网络资源配置日志 —— 单条记录。

    覆盖场景：
    （1）拓扑发现变化：LLDP发现的邻居设备变化及TSN能力协商结果；
    （2）配置下发验证：控制器对CBS、PSFP等协议参数的修改操作。
    """
    timestamp: str = Field(..., description="时间戳")
    device_id: str = Field(..., description="设备ID")
    level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
    event_type: str = Field(..., description="事件类型，如 LLDP_TOPO_CHANGE、CONFIG_DEPLOY、CONFIG_VERIFY、CBS_UPDATE、PSFP_UPDATE 等")
    description: str = Field("", description="描述信息")
    kv_pairs: dict[str, str] = Field(
        default_factory=dict,
        description="关键字段键值对。"
                    "拓扑变化场景：neighborId（邻居设备ID）、neighborPort、localPort、"
                    "tsnCapable、qbvSupported 等；"
                    "配置下发场景：configType（CBS/PSFP/CQF）、port、queue、"
                    "oldValue、newValue、verifyStatus 等"
    )


class ConfigLogResponse(BaseModel):
    """资源配置日志查询响应。"""
    total: int
    page: int
    page_size: int
    logs: list[ConfigLogEntry]


# ---------- 5. 硬件资源性能日志（报告004 第4.1.5节）----------
# 硬件资源性能日志主要对网络端系统和交换机的硬件资源（CPU利用率、内存利用率、缓冲区使用情况）
# 进行周期性的记录。

class HardwareLogEntry(BaseModel):
    """硬件资源性能日志 —— 单条记录（周期性）。

    对网络端系统和交换机的硬件资源进行周期性记录，
    包含 CPU利用率、内存利用率、缓冲区使用情况。
    """
    timestamp: str = Field(..., description="时间戳")
    device_id: str = Field(..., description="设备ID")
    level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
    metric_type: str = Field(..., description="指标类型，如 cpu、memory、buffer 等")
    kv_pairs: dict[str, str] = Field(
        default_factory=dict,
        description="关键字段键值对。"
                    "cpu：cpu_percent（CPU利用率%）、processCount 等；"
                    "memory：mem_total、mem_used、mem_percent（内存利用率%）等；"
                    "buffer：port、queue、buffer_used、buffer_percent（缓冲区使用率%）等"
    )


class HardwareLogResponse(BaseModel):
    """硬件资源日志查询响应。"""
    total: int
    page: int
    page_size: int
    logs: list[HardwareLogEntry]
