# TSN Log API

部署在 TSN 设备（端系统 / 交换机）上的日志查询 REST API，提供五类设备本地运行日志的分页查询与多维过滤。

---

## 项目结构

```
restapi/
├── main.py                 # FastAPI 应用入口 & /health 端点
├── models.py               # Pydantic 数据模型（五类日志 + 响应结构）
├── requirements.txt        # Python 依赖
├── data/                   # 日志文件目录（默认路径，可通过环境变量切换）
│   ├── timesync.log        # 时间同步状态日志
│   ├── scheduling.log      # 流量整形与调度日志
│   ├── filtering.log       # 流过滤与警管日志
│   ├── config.log          # 网络资源配置日志
│   └── hardware.log        # 硬件资源性能日志
└── routers/
    ├── __init__.py
    └── logs.py             # 日志查询路由 & 流式加载器
```

---

## 环境要求

| 组件 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.10+ | Ubuntu 22.04 自带 3.10，Ubuntu 20.04 需手动安装 |
| pip | 随 Python | 包管理器 |

### 系统依赖（Ubuntu）

```bash
sudo apt install -y python3-venv build-essential libssl-dev
```

### Python 依赖安装

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 部署

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `TSN_LOG_DIR` | 否 | `项目目录/data/` | 日志文件存放路径。交换机上通常设为 `/var/log/tsn` 或 `/opt/tsn/logs` |

不设置 `TSN_LOG_DIR` 时，自动回退到项目内置的 `data/` 目录（本地开发/演示用）。

### 启动命令

```bash
# 开发 / 演示
uvicorn main:app --reload --host 0.0.0.0 --port 5000

# 生产（交换机部署）
export TSN_LOG_DIR=/var/log/tsn
uvicorn main:app --host 127.0.0.1 --port 5000 --no-access-log
```

生产启动参数说明：

| 参数 | 说明 |
|------|------|
| `--host 127.0.0.1` | 仅本机监听，外部通过 Nginx 反向代理接入 |
| `--port 5000` | 服务监听端口 |
| `--no-access-log` | 关闭 HTTP 访问日志，减少磁盘 IO |
| **不要加 `--reload`** | 生产环境开启热重载会额外消耗内存，且有代码被意外写入导致静默重启的风险 |

### systemd 服务（推荐）

```ini
# /etc/systemd/system/tsn-log-api.service
[Unit]
Description=TSN Log API Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/tsn-restapi
Environment=TSN_LOG_DIR=/var/log/tsn
ExecStart=/opt/tsn-restapi/venv/bin/uvicorn main:app --host 127.0.0.1 --port 5000 --no-access-log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tsn-log-api
```

---

## API 端点

### 健康检查

```
GET /health
→ {"status": "ok"}
```

零 IO，瞬时返回，供负载均衡器/反向代理/k8s liveness probe 探活使用。

### 日志查询（5 个端点）

所有端点统一分页参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码，从 1 开始 |
| `page_size` | int | 20 | 每页条数，范围 1-200 |

响应统一结构：

```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "logs": [...]
}
```

#### 1. `GET /api/logs/timesync` — 时间同步状态日志

过滤参数：`level`, `device_id`, `port`, `event_type`, `clock_role`

日志格式（`|` 分隔）：

```
timestamp|device_id|port|level|gptp_domain|clock_role|event_type|kv_pairs|description
```

示例行：

```
2025-01-15T08:30:00.123456Z|SW-01|PORT-01|WARN|0|Slave|OFFSET_ALARM|offset=850,threshold=500,delay=120|主从时钟偏移超出阈值
```

#### 2. `GET /api/logs/scheduling` — 流量整形与调度日志

过滤参数：`level`, `device_id`, `port`, `schedule_type`, `queue`, `stream_id`, `event`

日志格式：

```
timestamp|device_id|port|level|schedule_type|queue|stream_id|event|kv_pairs
```

#### 3. `GET /api/logs/filtering` — 流过滤与警管日志

过滤参数：`level`, `device_id`, `port`, `operation`, `resource_type`, `config_id`, `status`

日志格式：

```
timestamp|device_id|port|level|operation|resource_type|config_id|status|kv_pairs
```

#### 4. `GET /api/logs/config` — 网络资源配置日志

过滤参数：`level`, `device_id`, `event_type`

日志格式：

```
timestamp|device_id|level|event_type|description|kv_pairs
```

#### 5. `GET /api/logs/hardware` — 硬件资源性能日志

过滤参数：`level`, `device_id`, `metric_type`

日志格式：

```
timestamp|device_id|level|metric_type|kv_pairs
```

---

## 关键技术实现

### 流式读取

日志查询采用流式加载策略：打开文件 → 逐行读取 → 解析当前行 → 过滤判断 → 命中后按页码跳过 / 保留。

**无论日志文件多大（50MB、100MB...），内存占用始终控制在 `page_size` 条记录级别（通常 ≤200 条）**，避免嵌入式设备 OOM。

核心实现见 `routers/logs.py` 中的 `_stream_file()` 函数。

### 数据模型

五类日志模型定义在 `models.py`，均使用 Pydantic v2，提供：

- 枚举约束（`LogLevel`: FATAL/ERROR/WARN/INFO/DEBUG；`ClockRole`: GM/BC/Slave 等）
- 灵活扩展字段（`kv_pairs: dict[str, str]` 承载各日志类型专属键值对）
- 自动数据校验与序列化

### KV 键值对约定

日志中可变字段统一折叠进 `k1=v1,k2=v2` 格式的键值对字符串，由 `_parse_kv()` 解析为 dict。空值或占位符 `-` 解析为空 dict。

---

## 待实现优化项

以下在生产环境中建议补上，当前版本暂未包含：

| 优化项 | 优先级 | 说明 |
|--------|--------|------|
| Token 鉴权 | 高 | 环境变量 `TSN_API_TOKEN` + 请求头 `X-API-Token` 校验，防止局域网内任意访问 |
| Nginx 反向代理 | 中 | 前端统一 80/443 端口，SSL 终止，限流，访问控制 |
| 请求日志接入 syslog | 中 | 统一日志采集，便于集中监控 |
| 日志文件按天轮转 | 中 | 避免单文件无限增长，需与交换机的日志写入方协调 |
| API 文档自动托管 | 低 | FastAPI 自带 `/docs` (Swagger UI)，生产可关闭或加 IP 白名单 |

---

## 快速验证

部署后在交换机本地执行：

```bash
# 探活
curl http://127.0.0.1:5000/health

# 查第一页时间同步日志
curl "http://127.0.0.1:5000/api/logs/timesync?page=1&page_size=5"

# 按级别过滤
curl "http://127.0.0.1:5000/api/logs/timesync?level=ERROR"

# 交互式 API 文档
# 浏览器访问 http://<交换机IP>:5000/docs
```
