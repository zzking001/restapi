# TSN Device REST API
zzking+ai

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-lightgrey.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个基于 Flask 的 **TSN（时间敏感网络）设备管理 REST API**，提供设备 CRUD、TSN 流管理、系统监控、网络接口查询和 PTP 同步状态等 12 个接口，同时附带一个健壮的 Python 客户端。

A Flask-based **TSN (Time-Sensitive Networking) Device Management REST API** with 12 endpoints covering device CRUD, stream management, system monitoring, network interface query, and PTP status — plus a robust Python client.

---

## 目录

- [功能概览](#功能概览)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [API 文档](#api-文档)
- [客户端使用](#客户端使用)
- [数据说明](#数据说明)

---

## 功能概览

| 模块 | 路由 | 方法 | 说明 |
|------|------|------|------|
| **设备管理** | `/api/devices` | GET / POST | 列出所有设备 / 新增设备 |
| | `/api/devices/<id>` | GET / PUT / DELETE | 查单台 / 全量更新 / 删除 |
| **系统监控** | `/api/cpus` | GET | CPU 信息（核数、型号、频率） |
| | `/api/memory` | GET | 内存信息（总量、空闲、缓存等） |
| | `/api/uptime` | GET | 系统运行时间 |
| **网络接口** | `/api/interfaces` | GET | 列出所有网卡 |
| | `/api/interfaces/<name>` | GET | 指定网卡详情（IP、MAC、速率） |
| | `/api/interfaces/<name>/tsn` | GET | 指定网卡的 TSN 能力 |
| **TSN 流管理** | `/api/tsn/streams` | GET / POST | 列出所有流 / 新增流 |
| | `/api/tsn/streams/<id>` | GET / PUT / DELETE | 查单条 / 更新 / 删除 |
| **PTP 同步** | `/api/tsn/ptp/status` | GET | PTP 时钟同步状态 |

### 客户端特性

- ⏱️ **超时控制** — 默认 5 秒超时，防止无限期挂起
- 🔄 **自动重试** — 传输层失败最多重试 3 次，指数退避
- 📝 **完整日志** — 同时输出到控制台和 `client.log` 文件
- 🌍 **环境配置** — 通过 `TSN_API_BASE` 环境变量切换服务器地址
- ✅ **响应校验** — 自动检查 JSON 结构和必需字段

---

## 项目结构

```
.
├── server.py              # Flask REST API 服务（12 个路由）
├── client.py              # Python 客户端（CRUD + 系统监控测试）
├── requirements.txt       # Python 依赖
├── .gitignore
└── data/                  # 模拟系统数据文件
    ├── cpuinfo.txt        #   /proc/cpuinfo 格式
    ├── meminfo.txt        #   /proc/meminfo 格式
    ├── uptime.txt         #   /proc/uptime 格式
    ├── interfaces.json    #   网卡列表 + TSN 能力
    └── ptp_status.txt     #   PTP 同步状态
```

---

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone https://github.com/zzking001/restapi.git
cd restapi

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python server.py
```

服务默认监听 `0.0.0.0:5000`，启动后访问 http://localhost:5000/api/devices 即可看到设备列表。

### 3. 运行客户端测试

```bash
# 确保服务已启动，然后在另一个终端运行：
python client.py
```

客户端会依次测试所有 12 个接口，并打印请求/响应结果。

---

## API 文档

### 基础信息

- Base URL: `http://localhost:5000/api`
- Content-Type: `application/json`
- 所有成功响应均返回 JSON 格式

### 设备管理

<details>
<summary><b>GET /api/devices</b> — 获取设备列表</summary>

```bash
curl http://localhost:5000/api/devices
```

**响应示例：**
```json
[
  {
    "id": 1,
    "name": "TSN-Talker-01",
    "type": "talker",
    "mac": "00:1b:44:11:3a:b7",
    "stream_id": "a0-00-00-00-00-00-00-01",
    "vlan": 100,
    "pcp": 3,
    "status": "online"
  }
]
```
</details>

<details>
<summary><b>POST /api/devices</b> — 新增设备</summary>

```bash
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{"name":"TSN-Talker-03","type":"talker","mac":"00:1b:44:11:3a:c3","vlan":300,"pcp":5,"status":"online"}'
```

> `name` 为必填字段，`id` 自动生成。
</details>

<details>
<summary><b>GET /api/devices/:id</b> — 获取单个设备</summary>

```bash
curl http://localhost:5000/api/devices/1
```
</details>

<details>
<summary><b>PUT /api/devices/:id</b> — 更新设备</summary>

```bash
curl -X PUT http://localhost:5000/api/devices/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"offline"}'
```
</details>

<details>
<summary><b>DELETE /api/devices/:id</b> — 删除设备</summary>

```bash
curl -X DELETE http://localhost:5000/api/devices/2
# → 204 No Content
```
</details>

### 系统监控

| 接口 | 示例 | 返回内容 |
|------|------|----------|
| `GET /api/cpus` | `curl /api/cpus` | `{"count": 2, "cpus": [{...}, {...}]}` |
| `GET /api/memory` | `curl /api/memory` | `{"MemTotal": ..., "MemFree": ..., ...}` |
| `GET /api/uptime` | `curl /api/uptime` | `{"uptime_seconds": ..., "uptime_days": ...}` |

### 网络接口

| 接口 | 示例 | 返回内容 |
|------|------|----------|
| `GET /api/interfaces` | `curl /api/interfaces` | 网卡列表（含 IP、MAC、速率、TSN 能力） |
| `GET /api/interfaces/eth0` | `curl /api/interfaces/eth0` | eth0 详情 |
| `GET /api/interfaces/eth0/tsn` | `curl /api/interfaces/eth0/tsn` | `{"interface":"eth0","tsn":{"enabled":true,...}}` |

### TSN 流管理

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/tsn/streams` | 列出所有流 |
| POST | `/api/tsn/streams` | 新增流（需 `stream_id` 字段） |
| GET | `/api/tsn/streams/:id` | 查单条流 |
| PUT | `/api/tsn/streams/:id` | 更新流 |
| DELETE | `/api/tsn/streams/:id` | 删除流 |

### PTP 同步状态

```bash
curl http://localhost:5000/api/tsn/ptp/status
```

```json
{
  "interface": "eth0",
  "ptp4l_state": "SLAVE",
  "clock_id": "000000.0000.000001",
  "master_offset_ns": "250",
  "path_delay_ns": "500",
  "sync_rate": "2/s"
}
```

---

## 客户端使用

`client.py` 既是集成测试脚本，也是客户端使用范例：

```python
from client import req, safe_json, validate

# 获取设备列表
r = req("GET", "/devices")
if r and r.status_code == 200:
    devices = safe_json(r)
    print(f"共 {len(devices)} 台设备")

# 新增一个 Talker
r = req("POST", "/devices", json={
    "name": "TSN-Talker-New",
    "type": "talker",
    "mac": "00:1b:44:11:3a:ff",
    "vlan": 400,
    "pcp": 6,
    "status": "online"
})
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TSN_API_BASE` | `http://127.0.0.1:5000/api` | API 服务器地址 |

```bash
# 指向远程服务器
export TSN_API_BASE=http://192.168.1.100:5000/api
python client.py
```

---

## 数据说明

`data/` 目录存放模拟的系统文件，用于开发和测试：

| 文件 | 格式 | 模拟来源 | 用途 |
|------|------|----------|------|
| `cpuinfo.txt` | `/proc/cpuinfo` | Linux procfs | CPU 型号、核数、频率 |
| `meminfo.txt` | `/proc/meminfo` | Linux procfs | 内存总量/空闲/缓存 |
| `uptime.txt` | `/proc/uptime` | Linux procfs | 系统运行秒数 |
| `interfaces.json` | JSON 数组 | 自定义 | 网卡配置 + TSN 能力 |
| `ptp_status.txt` | `key=value` | `pmc` 输出 | PTP 时钟同步状态 |

> 💡 **设计思路**：数据文件模拟了 Linux `/proc` 和网卡信息的格式，以后可无缝替换为读取真实系统文件（如 `/proc/cpuinfo`）或通过 `psutil` 库获取实时数据。

---

## 技术栈

- **Web 框架**: Flask 3.1
- **HTTP 客户端**: Requests 2.34
- **生产部署**: Gunicorn 26（可选）
- **Python**: 3.8+

---

## 路线图

- [ ] 数据持久化（SQLite / PostgreSQL）
- [ ] 认证与授权（JWT）
- [ ] WebSocket 实时推送设备状态
- [ ] Docker 容器化部署
- [ ] OpenAPI / Swagger 文档自动生成
- [ ] 替换模拟数据为真实系统读取（psutil）

---

## License

MIT
