# TSN Device REST API — FastAPI Edition

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-2.0+-e92063.svg)](https://docs.pydantic.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

基于 **FastAPI** 的 TSN（时间敏感网络）设备管理 REST API，采用模块化异步架构，提供设备 CRUD、TSN 流管理、系统监控、网络接口查询和 PTP 同步状态共 12+ 个接口，附带自动生成的 Swagger 文档。

---

## 项目亮点

与 Flask 单文件版本相比，本版本聚焦生产级特性：

- 🚀 **异步架构** — 全链路 `async/await`，`aiofiles` 异步文件 I/O
- 🧱 **模块化路由** — 按职责拆分为 system / interfaces / devices / tsn 四个路由模块
- ✅ **Pydantic 校验** — 请求/响应自动校验，类型安全，字段级文档
- 🔄 **双更新模式** — `PUT`（全量替换）+ `PATCH`（部分更新），完整 RESTful 语义
- 🔒 **并发安全** — `asyncio.Lock` 保护内存存储，多协程无竞态
- 🔃 **后台缓存刷新** — 网卡数据定时自动刷新（默认 10 秒），减少磁盘 I/O
- 📖 **自动文档** — 启动后访问 `/docs`（Swagger）和 `/redoc`（ReDoc）
- 🪝 **生命周期管理** — `lifespan` 事件在启动时初始化缓存，关闭时清理资源

---

## 项目结构

```
restapi-fastapi/
├── main.py                 # FastAPI 入口：创建 app、注册路由、配置 lifespan
├── models.py               # Pydantic 数据模型（请求/响应结构定义）
├── client.py               # Python 测试客户端（PUT + PATCH 全覆盖）
├── requirements.txt        # Python 依赖
├── .gitignore
├── data/                   # 模拟系统数据文件
│   ├── cpuinfo.txt
│   ├── meminfo.txt
│   ├── uptime.txt
│   ├── interfaces.json
│   └── ptp_status.txt
└── routers/                # 路由模块（按职责拆分）
    ├── __init__.py
    ├── system.py           # CPU / 内存 / 运行时间（只读）
    ├── interfaces.py       # 网卡列表 / 详情 / TSN 能力（只读 + 缓存）
    ├── devices.py          # 设备 CRUD（PUT + PATCH）
    └── tsn.py              # TSN 流 CRUD + PTP 状态
```

---

## 快速开始

### 1. 安装依赖

```bash
cd restapi-fastapi
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

### 设备管理

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/devices` | 列出所有设备 |
| `POST` | `/api/devices` | 新增设备 |
| `GET` | `/api/devices/{id}` | 查询单台设备 |
| `PUT` | `/api/devices/{id}` | **全量替换**（所有字段必传） |
| `PATCH` | `/api/devices/{id}` | **部分更新**（只传要改的字段） |
| `DELETE` | `/api/devices/{id}` | 删除设备 |

### 系统监控

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/cpus` | CPU 信息（Pydantic 模型校验） |
| `GET` | `/api/memory` | 内存信息 |
| `GET` | `/api/uptime` | 系统运行时间 |

### 网络接口

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/interfaces` | 列出所有网卡（缓存读取） |
| `GET` | `/api/interfaces/{name}` | 指定网卡详情 |
| `GET` | `/api/interfaces/{name}/tsn` | 指定网卡 TSN 能力 |

### TSN 流管理

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/tsn/streams` | 列出所有流 |
| `POST` | `/api/tsn/streams` | 新增流 |
| `GET` | `/api/tsn/streams/{id}` | 查询单条流 |
| `PUT` | `/api/tsn/streams/{id}` | **全量替换**流 |
| `PATCH` | `/api/tsn/streams/{id}` | **部分更新**流 |
| `DELETE` | `/api/tsn/streams/{id}` | 删除流 |

### PTP 同步

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/tsn/ptp/status` | PTP 时钟同步状态 |

---

## cURL 示例

```bash
# === 设备管理 ===
# 获取设备列表
curl http://localhost:5000/api/devices

# 新增设备（Pydantic 自动校验）
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{"name":"TSN-Talker-03","type":"talker","mac":"00:1b:44:11:3a:c3","vlan":300,"pcp":5,"status":"online"}'

# 部分更新 — 只改状态（PATCH）
curl -X PATCH http://localhost:5000/api/devices/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"offline"}'

# 全量替换 — 所有字段必传（PUT）
curl -X PUT http://localhost:5000/api/devices/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"TSN-Replaced","type":"bridge","mac":"ff:ff:ff:ff:ff:ff","stream_id":"-","vlan":1,"pcp":0,"status":"offline"}'

# 删除设备
curl -X DELETE http://localhost:5000/api/devices/2

# === 系统监控 ===
curl http://localhost:5000/api/cpus
curl http://localhost:5000/api/memory

# === PTP 状态 ===
curl http://localhost:5000/api/tsn/ptp/status
```

---

## PUT vs PATCH

本版本是 **首个支持 PATCH 的版本**，与 Flask 版本的关键区别：

| | PUT | PATCH |
|------|-----|--------|
| 语义 | 全量替换 | 部分更新 |
| 请求体 | 所有字段必传 | 只传要改的字段 |
| 未传字段 | 被重置为默认值/空 | 保持原值不变 |
| 适用场景 | 完整覆写一条记录 | 快速切换状态、修正单个属性 |

```bash
# Flask 版本只有 PUT，改状态却要传全部字段：
curl -X PUT /api/devices/1 -d '{"name":"...","type":"...","mac":"...",...}'

# FastAPI 版本用 PATCH，一行搞定：
curl -X PATCH /api/devices/1 -d '{"status":"offline"}'
```

---

## 架构设计

### 路由模块化

每个 `routers/*.py` 都是独立的路由模块，通过 `APIRouter` 注册到主应用：

```python
# main.py
app.include_router(system.router)      # /api/cpus, /api/memory, /api/uptime
app.include_router(interfaces.router)  # /api/interfaces, /api/interfaces/{name}/...
app.include_router(devices.router)     # /api/devices, /api/devices/{id}
app.include_router(tsn.router)         # /api/tsn/streams, /api/tsn/ptp/status
```

新增功能只需写一个 router 文件并 `include_router`，无需改动已有代码。

### 并发安全

所有读写共享内存数据的路由都使用 `asyncio.Lock` 保护：

```python
async with _lock:
    # 安全读写 _devices / _streams
```

### 后台缓存刷新

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
| **aiofiles** | ≥24.0 | 异步文件 I/O |
| **Gunicorn** | ≥23.0 | 生产部署（可选） |
| **Requests** | ≥2.32 | HTTP 客户端测试 |
| **Python** | 3.10+ | 运行环境 |

---

## 与 Flask 版本的对比

| 维度 | Flask 版（restapi-main） | FastAPI 版（本仓库） |
|------|--------------------------|---------------------------|
| 架构 | 单文件 `server.py` | 模块化 `routers/` + `models.py` |
| 更新模式 | 仅 PUT | PUT + PATCH 双模式 |
| I/O 模型 | 同步 | 异步（async/await） |
| 数据校验 | 手动校验 | Pydantic 自动校验 |
| API 文档 | 无 | Swagger + ReDoc 自动生成 |
| 并发保护 | 无 | asyncio.Lock |
| 网卡缓存 | 每次读文件 | 内存缓存 + 定时刷新 |
| 学习门槛 | 低，适合快速原型 | 中，适合生产部署 |

---

## License

MIT
