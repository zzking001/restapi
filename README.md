# TSN REST API

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-2.0+-e92063.svg)](https://docs.pydantic.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

基于 **FastAPI** 的 TSN（时间敏感网络）REST API，提供两类查询能力：

- **日志轨** — 部署在 TSN 设备（端系统/交换机）上，为管理端提供设备本地运行日志的分页查询与多维过滤
- **网管轨** — 部署在机载网络控制器上，暴露 NETCONF 通知和 SNMP Trap 的查询端点（参照报告004 第4.2节）

当前为 **Phase 1**：使用本地 mock 数据文件开发调试。Phase 2 将接入设备 `/var/log/tsn/` 真实日志。

---

## 项目亮点

- 📋 **五类日志全覆盖** — 时间同步、流量调度、流过滤警管、网络资源配置、硬件资源性能
- 🛰️ **NETCONF + SNMP Trap** — 参照报告004 第4.2节，覆盖九类事件 + 三种 Trap
- 🔍 **多维过滤** — 按级别、设备ID、端口、事件类型等组合筛选
- 📄 **标准分页** — `page` / `page_size` 参数，`total` 总数返回
- ⚙️ **模块开关** — `TSN_API_MODULES` 环境变量控制部署模式（一套代码两类部署）
- 🧱 **模块化路由** — 按职责拆分为 `logs` / `mgmt` 两个路由模块
- ✅ **Pydantic 校验** — 请求/响应自动校验，类型安全，字段级文档
- 📖 **自动文档** — 启动后访问 `/docs`（Swagger）和 `/redoc`（ReDoc）

---

## 项目结构

```
restapi/
├── main.py                 # FastAPI 入口：创建 app、动态注册路由
├── models.py               # Pydantic 数据模型（日志模型 5 套 + 网管模型 2 套 + 枚举）
├── client.py               # Python 测试客户端（双 BASE 支持）
├── requirements.txt        # Python 依赖
├── .gitignore
├── data/                   # Mock 数据文件
│   ├── timesync.log        # 时间同步状态日志（15 条）
│   ├── scheduling.log      # 流量整形与调度日志（13 条）
│   ├── filtering.log       # 流过滤与警管日志（12 条）
│   ├── config.log          # 网络资源配置日志（9 条）
│   ├── hardware.log        # 硬件资源性能日志（11 条）
│   ├── netconf.log         # NETCONF 通知 mock（21 条）
│   └── snmp_trap.log       # SNMP Trap mock（9 条）
└── routers/                # 路由模块
    ├── __init__.py
    ├── logs.py             # 设备日志查询端点（5 × GET）
    └── mgmt.py             # 网管数据查询端点（2 × GET）
```

---

## 快速开始

### 1. 安装依赖

```bash
cd restapi
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 全模块部署（默认，注册全部路由）
uvicorn main:app --reload --host 0.0.0.0 --port 5000

# 仅日志轨 —— 部署在端系统/交换机
set TSN_API_MODULES=logs
uvicorn main:app --host 0.0.0.0 --port 5000

# 仅网管轨 —— 部署在机载网络控制器
set TSN_API_MODULES=mgmt
uvicorn main:app --host 0.0.0.0 --port 5001
```

服务启动后：
- API 地址: http://localhost:5000
- **Swagger 文档**: http://localhost:5000/docs
- **ReDoc 文档**: http://localhost:5000/redoc

### 3. 运行客户端测试

```bash
# 日志轨 + 网管轨分别测试
set TSN_API_BASE_MGMT=http://127.0.0.1:5001/api
python client.py
```

---

## API 概览

### 日志查询（日志轨：端系统 / 交换机本地查询）

所有日志端点支持通用参数：`page`（页码，≥1）、`page_size`（每页条数，1~200）、`level`（日志级别）。

| 方法 | 路由 | 专属过滤参数 | 说明 |
|------|------|-------------|------|
| `GET` | `/api/logs/timesync` | `device_id`, `port`, `event_type`, `clock_role` | 时间同步状态日志 |
| `GET` | `/api/logs/scheduling` | `device_id`, `port`, `schedule_type`, `queue`, `stream_id`, `event` | 流量整形与调度日志 |
| `GET` | `/api/logs/filtering` | `device_id`, `port`, `operation`, `resource_type`, `config_id`, `status` | 流过滤与警管日志 |
| `GET` | `/api/logs/config` | `device_id`, `event_type` | 网络资源配置日志 |
| `GET` | `/api/logs/hardware` | `device_id`, `metric_type` | 硬件资源性能日志 |

### 网管数据查询（网管轨：机载网络控制器上报查询）

| 方法 | 路由 | 专属过滤参数 | 说明 |
|------|------|-------------|------|
| `GET` | `/api/mgmt/netconf` | `severity`, `device_id`, `port_id`, `event_type` | NETCONF 通知（9 种事件类型） |
| `GET` | `/api/mgmt/snmp` | `device_id`, `trap_type` | SNMP Trap（3 种 Trap 类型） |

---

## cURL 示例

```bash
# ==================== 日志查询 ====================
# 时间同步 — 过滤 ERROR + 指定设备
curl "http://localhost:5000/api/logs/timesync?level=ERROR&device_id=SW-01"

# 时间同步 — 过滤事件类型 + 分页
curl "http://localhost:5000/api/logs/timesync?event_type=PERIODIC_STATS&page_size=3"

# 流量调度 — 过滤 Qbv 类型
curl "http://localhost:5000/api/logs/scheduling?schedule_type=802.1Qbv-TAS"

# 流量调度 — 按事件名称过滤
curl "http://localhost:5000/api/logs/scheduling?event=GCL_LOAD"

# 流过滤 — 过滤 Red 判定（超出警管速率）
curl "http://localhost:5000/api/logs/filtering?status=Red"

# 流过滤 — 按策略 ID 反查命中日志
curl "http://localhost:5000/api/logs/filtering?config_id=PSFP-03"

# 资源配置 — 过滤配置下发事件
curl "http://localhost:5000/api/logs/config?event_type=CONFIG_DEPLOY"

# 硬件资源 — 翻页超出范围（返回空数组）
curl "http://localhost:5000/api/logs/hardware?page=99&page_size=20"


# ==================== 网管数据查询 ====================
# NETCONF 通知 — 全部
curl "http://localhost:5001/api/mgmt/netconf"

# NETCONF — 过滤 ERROR + gPTP 偏移越限事件
curl "http://localhost:5001/api/mgmt/netconf?severity=ERROR&event_type=GPTP_OFFSET_OVER_LIMIT"

# NETCONF — 过滤 GM_CHANGE 事件
curl "http://localhost:5001/api/mgmt/netconf?event_type=GM_CHANGE"

# NETCONF — 按设备过滤
curl "http://localhost:5001/api/mgmt/netconf?device_id=SW-01"

# SNMP Trap — 全部
curl "http://localhost:5001/api/mgmt/snmp"

# SNMP — 过滤 gPTP 偏移 Trap
curl "http://localhost:5001/api/mgmt/snmp?trap_type=GPTP_OFFSET_OVER_LIMIT"

# SNMP — 空页边界
curl "http://localhost:5001/api/mgmt/snmp?page=99"
```

---

## 数据格式

所有数据文件使用 `|` 分隔符，每行一条记录。`kv_pairs` / `oid_values` 以 `k1=v1,k2=v2` 格式存储可变键值对。

### 日志格式

**时间同步**（9 字段）：
```
timestamp|device_id|port|level|gptp_domain|clock_role|event_type|kv_pairs|description
```

**流量调度**（9 字段）：
```
timestamp|device_id|port|level|schedule_type|queue|stream_id|event|kv_pairs
```

**流过滤警管**（9 字段）：
```
timestamp|device_id|port|level|operation|resource_type|config_id|status|kv_pairs
```

**资源配置**（6 字段）：
```
timestamp|device_id|level|event_type|description|kv_pairs
```

**硬件资源**（5 字段）：
```
timestamp|device_id|level|metric_type|kv_pairs
```

### 网管数据格式

**NETCONF 通知**（6 字段）：
```
event_time|device_id|port_id|event_type|severity|kv_pairs
```

**SNMP Trap**（5 字段）：
```
timestamp|device_id|trap_oid|trap_type|oid_values
```

---

## NETCONF 事件类型 & SNMP Trap 类型

### NETCONF 通知（9 种）

| 事件类型 | 说明 | 典型 kv_pairs |
|---------|------|--------------|
| `GPTP_OFFSET_OVER_LIMIT` | gPTP 时间偏移越限 | gptp_offset, threshold, gm_identity |
| `GM_CHANGE` | Grandmaster 时钟切换 | old_gm_identity, new_gm_identity, gm_priority |
| `QBV_JITTER_OVER_LIMIT` | Qbv 门控抖动越限 | jitter, threshold, queue, gcl_state |
| `GCL_UPDATE` | 门控列表更新 | gcl_version, port, queue_count |
| `STREAM_DROP_OVER_LIMIT` | 流丢包率越限 | stream_id, drop_rate, threshold |
| `POLICER_BANDWIDTH_OVER_LIMIT` | 警管带宽越限 | stream_id, cir, eir, bandwidth_usage |
| `FLOW_RESERVATION_FAILED` | 流预留失败 | stream_id, reason |
| `PORT_LINK_DOWN` | 端口链路中断 | port_state, previous_state, detection_method |
| `PERIODIC_STATS` | 周期性统计上报 | gptp_offset, cpu_percent, mem_percent |

### SNMP Trap（3 种）

| Trap 类型 | 说明 | 典型 OID 值 |
|---------|------|------------|
| `GPTP_OFFSET_OVER_LIMIT` | gPTP 时间偏移越限 | tsnGptpOffset, tsnGptpGmId, tsnGptpOffsetThreshold |
| `QBV_JITTER_OVER_LIMIT` | Qbv 门控抖动越限 | tsnQbvJitter, tsnQbvWindowId, tsnQbvJitterThreshold |
| `PERIODIC_STATUS_REPORT` | 周期性状态报告 | tsnDevicePortStatus, tsnClockRole, ifIndex |

---

## 部署模式

通过 `TSN_API_MODULES` 环境变量控制路由注册：

| 环境变量值 | 注册路由 | 部署目标 |
|-----------|---------|---------|
| `all`（默认） | `/api/logs/*` + `/api/mgmt/*` | 开发/调试模式 |
| `logs` | `/api/logs/*` | 端系统 / 交换机 |
| `mgmt` | `/api/mgmt/*` | 机载网络控制器 |

```python
# main.py 动态注册逻辑
MODULES = os.environ.get("TSN_API_MODULES", "all").lower().replace(" ", "")

if MODULES in ("all", "logs"):
    from routers import logs
    app.include_router(logs.router)

if MODULES in ("all", "mgmt"):
    from routers import mgmt
    app.include_router(mgmt.router)
```

---

## 工艺模式

### 日志 / 网管查询流程

```
HTTP GET /api/logs/timesync?level=ERROR&device_id=SW-01
    │
    ▼
logs.py → load_timesync_logs()
    │       读取 data/timesync.log
    │       逐行 split("|") → TimeSyncLogEntry 模型
    ▼
内存过滤（level, device_id, ...）
    │
    ▼
_paginate() 分页切片
    │
    ▼
TimeSyncLogResponse {total, page, page_size, logs}
```

网管数据查询（`/api/mgmt/*`）流程相同，仅替换对应的加载器、过滤字段和响应模型。

### 模型设计原则

所有 TSN 数据结构采用"核心字段强类型 + 灵活字段折叠进 kv_pairs/oid_values 字典"策略：
- 通用字段（时间戳、设备ID、端口、级别等）→ Pydantic 强类型字段，支持类型校验和自动化文档
- 事件专属字段（如 gPTP 的 offset/threshold/gmIdentity，调度的 jitter/周期/门控状态）→ 折叠进 `kv_pairs: dict[str, str]`，无需为每种事件类型定义独立模型

---

## 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| **FastAPI** | ≥0.115 | 异步 Web 框架 |
| **Uvicorn** | ≥0.30 | ASGI 服务器 |
| **Pydantic** | ≥2.0 | 数据校验与序列化 |
| **Requests** | ≥2.32 | HTTP 客户端测试 |
| **Python** | 3.10+ | 运行环境 |

---

## 版本路线

| 阶段 | 状态 | 内容 |
|------|------|------|
| **Phase 1** | ✅ 完成 | 日志轨：mock 文件 + 五类查询端点（5~9 个参数/端点，含 page、page_size）+ 分页；网管轨：NETCONF + SNMP Trap 查询端点 |
| **Phase 2** | 待开发 | 接入设备 `/var/log/tsn/` 真实日志路径 |
| **Phase 3** | 规划中 | 时间范围过滤 + 日志级别阈值告警 |

---

## License

MIT
