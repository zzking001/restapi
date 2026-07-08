# TSN Device Log REST API

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-2.0+-e92063.svg)](https://docs.pydantic.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

基于 **FastAPI** 的 TSN（时间敏感网络）设备本地日志查询 REST API。部署在 TSN 设备（Ubuntu）上，为管理端（PyQt 桌面应用）提供五类设备运行日志的分页查询与多维过滤能力，附带自动生成的 Swagger 文档。

当前为 **Phase 1**：使用本地 mock 日志文件开发调试。Phase 2 将接入设备 `/var/log/tsn/` 真实日志。

---

## 项目亮点

- 📋 **五类日志全覆盖** — 时间同步、流量调度、流过滤警管、网络资源配置、硬件资源性能
- 🔍 **多维过滤** — 按日志级别、设备ID、端口、事件类型组合筛选
- 📄 **标准分页** — `page` / `page_size` 参数，`total` 总数返回
- ⚡ **异步架构** — 全链路 `async/await`，`aiofiles` 异步文件 I/O
- 🧱 **模块化路由** — 按职责拆分为 `interfaces` / `logs` 两个路由模块
- ✅ **Pydantic 校验** — 请求/响应自动校验，类型安全，字段级文档
- 🔃 **后台缓存刷新** — 网卡数据定时自动刷新（默认 10 秒）
- 📖 **自动文档** — 启动后访问 `/docs`（Swagger）和 `/redoc`（ReDoc）

---

## 项目结构

```
restapi/
├── main.py                 # FastAPI 入口：创建 app、注册路由、配置 lifespan
├── models.py               # Pydantic 数据模型（接口模型 + 五类日志模型 + 11个枚举）
├── client.py               # Python 测试客户端（接口 + 日志全端点测试）
├── requirements.txt        # Python 依赖
├── .gitignore
├── data/                   # 数据文件
│   ├── interfaces.json     # 网卡能力 mock 数据
│   ├── timesync.log        # 时间同步状态日志（15 条）
│   ├── scheduling.log      # 流量整形与调度日志（13 条）
│   ├── filtering.log       # 流过滤与警管日志（12 条）
│   ├── config.log          # 网络资源配置日志（9 条）
│   └── hardware.log        # 硬件资源性能日志（11 条）
└── routers/                # 路由模块
    ├── __init__.py
    ├── interfaces.py       # 网卡列表 / 详情 / TSN 能力（只读 + 缓存）
    └── logs.py             # 五类日志查询端点 + 解析器（5 × GET）
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
# 开发模式（热重载）
uvicorn main:app --reload --host 0.0.0.0 --port 5000

# 或直接运行
python main.py
```

服务启动后：
- API 地址: http://localhost:5000
- **Swagger 文档**: http://localhost:5000/docs
- **ReDoc 文档**: http://localhost:5000/redoc

### 3. 运行客户端测试

```bash
python client.py
```

---

## API 概览

### 网络接口（只读）

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/interfaces` | 列出所有网卡（缓存读取） |
| `GET` | `/api/interfaces/{name}` | 指定网卡详情 |
| `GET` | `/api/interfaces/{name}/tsn` | 指定网卡 TSN 能力 |

### 日志查询（只读，分页 + 过滤）

所有日志端点支持通用参数：`page`（页码，≥1）、`page_size`（每页条数，1~200）、`level`（日志级别）。

| 方法 | 路由 | 专属过滤参数 | 说明 |
|------|------|-------------|------|
| `GET` | `/api/logs/timesync` | `device_id`, `port`, `event_type`, `clock_role` | 时间同步状态日志 |
| `GET` | `/api/logs/scheduling` | `device_id`, `port`, `schedule_type`, `queue`, `stream_id` | 流量整形与调度日志 |
| `GET` | `/api/logs/filtering` | `device_id`, `port`, `operation`, `resource_type`, `status` | 流过滤与警管日志 |
| `GET` | `/api/logs/config` | `device_id`, `event_type` | 网络资源配置日志 |
| `GET` | `/api/logs/hardware` | `device_id`, `metric_type` | 硬件资源性能日志 |

---

## cURL 示例

```bash
# === 网络接口 ===
curl http://localhost:5000/api/interfaces
curl http://localhost:5000/api/interfaces/eth0
curl http://localhost:5000/api/interfaces/eth0/tsn

# === 日志查询 ===
# 时间同步日志 — 全部
curl "http://localhost:5000/api/logs/timesync"

# 时间同步 — 过滤 ERROR 级别 + 指定设备
curl "http://localhost:5000/api/logs/timesync?level=ERROR&device_id=SW-01"

# 时间同步 — 过滤事件类型 + 分页
curl "http://localhost:5000/api/logs/timesync?event_type=PERIODIC_STATS&page_size=3"

# 流量调度 — 过滤 Qbv 类型
curl "http://localhost:5000/api/logs/scheduling?schedule_type=802.1Qbv-TAS"

# 流过滤 — 过滤 Red 判定（超出警管速率）
curl "http://localhost:5000/api/logs/filtering?status=Red"

# 资源配置 — 过滤配置下发事件
curl "http://localhost:5000/api/logs/config?event_type=CONFIG_DEPLOY"

# 硬件资源 — 过滤温度指标
curl "http://localhost:5000/api/logs/hardware?metric_type=thermal"

# 翻页超出范围（返回空数组）
curl "http://localhost:5000/api/logs/hardware?page=99&page_size=20"
```

---

## 日志格式

所有日志文件使用 `|` 分隔符，每行一条记录。`kv_pairs` 字段以 `k1=v1,k2=v2` 格式存储可变键值对。

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

---

## 架构设计

### 路由模块化

每个 `routers/*.py` 都是独立的路由模块，通过 `APIRouter` 注册到主应用：

```python
# main.py
from routers import interfaces, logs

app.include_router(interfaces.router)  # /api/interfaces, /api/interfaces/{name}/...
app.include_router(logs.router)        # /api/logs/timesync, /api/logs/scheduling, ...
```

新增功能只需写一个 router 文件并 `include_router`，无需改动已有代码。

### 日志查询流程

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

### 后台缓存刷新（网卡数据）

网卡数据不是每次请求都读磁盘，而是：
1. 启动时加载到内存缓存
2. 后台每 10 秒自动刷新
3. 所有接口从缓存读取，I/O 开销几乎为零

---

## 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| **FastAPI** | ≥0.115 | 异步 Web 框架 |
| **Uvicorn** | ≥0.30 | ASGI 服务器 |
| **Pydantic** | ≥2.0 | 数据校验与序列化 |
| **aiofiles** | ≥24.0 | 异步文件 I/O（网卡数据） |
| **Requests** | ≥2.32 | HTTP 客户端测试 |
| **Python** | 3.10+ | 运行环境 |

---

## 版本路线

| 阶段 | 状态 | 内容 |
|------|------|------|
| **Phase 1** | ✅ 完成 | mock 日志文件 + 五类查询端点 + 分页过滤 |
| **Phase 2** | 待开发 | 接入设备 `/var/log/tsn/` 真实日志路径 |
| **Phase 3** | 规划中 | 时间范围过滤 + 日志级别阈值告警 |

---

## License

MIT
