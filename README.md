# TSN Device REST API — Flask Edition

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-lightgrey.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

基于 **Flask** 的 TSN（时间敏感网络）设备管理 REST API，单文件架构，提供设备 CRUD、TSN 流管理、系统监控、网络接口查询和 PTP 同步状态共 12 个接口，附带一个健壮的 Python 测试客户端。

---

## 项目特点

- 🧩 **单文件服务** — `server.py` 一个文件包含全部 12 个路由，便于快速理解和修改
- 🔄 **重试 + 超时** — 客户端内置 3 次指数退避重试 + 5 秒超时保护
- 📝 **完整日志** — 客户端同时输出到控制台和 `client.log`
- 🌍 **环境配置** — 通过 `TSN_API_BASE` 环境变量灵活切换服务器地址
- 📁 **模拟数据** — `data/` 目录模拟 Linux `/proc` 文件系统，可无缝替换为真实数据源

---

## 项目结构

```
restapi-main/
├── server.py              # Flask REST API（单文件，12 个路由）
├── client.py              # Python 测试客户端（CRUD + 监控全覆盖）
├── requirements.txt       # Python 依赖
├── .gitignore
└── data/                  # 模拟系统数据文件
    ├── cpuinfo.txt        # /proc/cpuinfo 格式
    ├── meminfo.txt        # /proc/meminfo 格式
    ├── uptime.txt         # /proc/uptime 格式
    ├── interfaces.json    # 网卡列表 + TSN 能力
    └── ptp_status.txt     # PTP 同步状态
```

---

## 快速开始

### 1. 安装依赖

```bash
cd restapi-main
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### 2. 启动服务

```bash
python server.py
```

服务默认监听 `0.0.0.0:5000`，启动后访问 http://localhost:5000/api/devices 即可看到设备列表。

### 3. 运行客户端测试

```bash
# 确保服务已启动，另开终端：
python client.py
```

客户端会依次测试所有 12 个接口并打印结果。

---

## API 概览

### 设备管理

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/devices` | 列出所有设备 |
| `POST` | `/api/devices` | 新增设备（`name` 必填） |
| `GET` | `/api/devices/<id>` | 查询单台设备 |
| `PUT` | `/api/devices/<id>` | 全量更新设备 |
| `DELETE` | `/api/devices/<id>` | 删除设备 |

### 系统监控

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/cpus` | CPU 信息（核数、型号、频率） |
| `GET` | `/api/memory` | 内存信息（总量、空闲、缓存等） |
| `GET` | `/api/uptime` | 系统运行时间 |

### 网络接口

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/interfaces` | 列出所有网卡 |
| `GET` | `/api/interfaces/<name>` | 指定网卡详情（IP、MAC、速率） |
| `GET` | `/api/interfaces/<name>/tsn` | 指定网卡的 TSN 能力 |

### TSN 流管理

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/tsn/streams` | 列出所有流 |
| `POST` | `/api/tsn/streams` | 新增流（`stream_id` 必填） |
| `GET` | `/api/tsn/streams/<id>` | 查询单条流 |
| `PUT` | `/api/tsn/streams/<id>` | 更新流 |
| `DELETE` | `/api/tsn/streams/<id>` | 删除流 |

### PTP 同步

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/tsn/ptp/status` | PTP 时钟同步状态 |

---

## cURL 示例

```bash
# 获取设备列表
curl http://localhost:5000/api/devices

# 新增设备
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{"name":"TSN-Talker-03","type":"talker","mac":"00:1b:44:11:3a:c3","vlan":300,"pcp":5,"status":"online"}'

# 更新设备状态
curl -X PUT http://localhost:5000/api/devices/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"offline"}'

# 删除设备
curl -X DELETE http://localhost:5000/api/devices/2

# CPU 信息
curl http://localhost:5000/api/cpus

# PTP 同步状态
curl http://localhost:5000/api/tsn/ptp/status
```

---

## 客户端使用

```python
from client import req, safe_json

# 获取设备列表
r = req("GET", "/devices")
if r and r.status_code == 200:
    devices = safe_json(r)
    print(f"共 {len(devices)} 台设备")

# 新增设备
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
export TSN_API_BASE=http://192.168.1.100:5000/api
python client.py
```

---

## 数据说明

`data/` 目录存放模拟的系统文件，设计上模拟 Linux `/proc` 格式，可无缝替换为真实系统读取：

| 文件 | 格式 | 模拟来源 | 用途 |
|------|------|----------|------|
| `cpuinfo.txt` | `/proc/cpuinfo` | Linux procfs | CPU 型号、核数、频率 |
| `meminfo.txt` | `/proc/meminfo` | Linux procfs | 内存总量/空闲/缓存 |
| `uptime.txt` | `/proc/uptime` | Linux procfs | 系统运行秒数 |
| `interfaces.json` | JSON 数组 | 自定义 | 网卡配置 + TSN 能力 |
| `ptp_status.txt` | `key=value` | `pmc` 输出 | PTP 时钟同步状态 |

---

## 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| **Flask** | 3.1 | Web 框架 |
| **Requests** | 2.34 | HTTP 客户端 |
| **Gunicorn** | 26 | 生产部署（可选） |
| **Python** | 3.8+ | 运行环境 |

---

## 与 FastAPI 版本的对比

> 本仓库另有一个 **FastAPI 版本**（`restapi-fastapi`），提供了以下增强：
> - Pydantic 模型校验请求/响应
> - PUT（全量替换）+ PATCH（部分更新）双模式
> - 异步 I/O + 后台缓存刷新
> - 模块化路由拆分
> - 自动生成 Swagger/OpenAPI 文档
>
> 如果你需要快速理解或修改路由逻辑，**Flask 单文件版**更适合你；如果你需要生产级特性，推荐 **FastAPI 版**。

---

## License

MIT
