"""Pydantic 数据模型 —— 统一管理所有请求/响应结构。"""
#用于定义传输数据的数据结构，包括字段类型、字段名称、字段描述、字段默认值等

from typing import Optional
from pydantic import BaseModel, Field


# ==================== TSN 设备模型 ====================

class DeviceBase(BaseModel):
    """设备共有字段。"""
    name: str
    type: str = "talker"
    mac: str = ""
    stream_id: str = "-"
    vlan: int = 100
    pcp: int = 3
    status: str = "online"


class DeviceCreate(DeviceBase):
    """POST 创建设备 —— name 必填，其余有默认值。"""
    name: str = Field(..., description="设备名称")


class DeviceUpdate(DeviceBase):
    """PUT 全量替换 —— 所有字段必传。"""
    name: str
    type: str
    mac: str
    stream_id: str
    vlan: int
    pcp: int
    status: str


class DevicePatch(BaseModel):
    """PATCH 部分更新 —— 所有字段可选。"""
    name: Optional[str] = None
    type: Optional[str] = None
    mac: Optional[str] = None
    stream_id: Optional[str] = None
    vlan: Optional[int] = None
    pcp: Optional[int] = None
    status: Optional[str] = None


class DeviceResponse(DeviceBase):
    """GET 响应 —— 带 id。"""
    id: int


# ==================== TSN 流模型 ====================

class StreamBase(BaseModel):
    """流共有字段。"""
    stream_id: str
    talker: str
    listener: str
    vlan: int = 100
    pcp: int = 3
    bandwidth: str = "100Mbps"
    status: str = "active"


class StreamCreate(StreamBase):
    """POST 创建流 —— stream_id 必填。"""
    stream_id: str = Field(..., description="流标识符")


class StreamUpdate(StreamBase):
    """PUT 全量替换流 —— 所有字段必传。"""
    stream_id: str
    talker: str
    listener: str
    vlan: int
    pcp: int
    bandwidth: str
    status: str


class StreamPatch(BaseModel):
    """PATCH 部分更新流 —— 所有字段可选。"""
    stream_id: Optional[str] = None
    talker: Optional[str] = None
    listener: Optional[str] = None
    vlan: Optional[int] = None
    pcp: Optional[int] = None
    bandwidth: Optional[str] = None
    status: Optional[str] = None


class StreamResponse(StreamBase):
    """GET 响应 —— 带 id。"""
    id: int


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


class CPUInfo(BaseModel):
    """单个 CPU 信息。"""
    processor: str = ""
    model_name: Optional[str] = Field(default="", alias="model name")
    cores: Optional[str] = None
    cache_size: Optional[str] = Field(default=None, alias="cache size")
    cpu_mhz: Optional[str] = Field(default=None, alias="cpu MHz")

    model_config = {"populate_by_name": True}


class CPUResponse(BaseModel):
    """CPU 列表响应。"""
    count: int
    cpus: list[CPUInfo]


class ErrorResponse(BaseModel):
    """统一错误响应。"""
    error: str
