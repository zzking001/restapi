import logging
import os
import time

import requests
from requests.exceptions import ConnectionError, Timeout

#.get(先去系统环境变量里找的值，默认值)
#配置过程类似于在终端中输入：export TSN_API_BASE="http://127.0.0.1:5000/api" 
BASE = os.environ.get("TSN_API_BASE", "http://127.0.0.1:5000/api")
TIMEOUT = 5  # 秒：超过这个时间没响应就放弃，不让脚本无限期挂着
MAX_RETRIES = 3  # 失败最多重试几次

# 日志配置：同时输出到控制台和文件 client.log
logging.basicConfig(
    level=logging.INFO,#只显示info以上的日志，debug级别的日志不会显示
    format="%(asctime)s [%(levelname)s] %(message)s",#定义日志输出格式
    handlers=[#指明日志输出的方式，StreamHandler表示输出到控制台，FileHandler表示输出到文件
        logging.StreamHandler(),
        logging.FileHandler("client.log", encoding="utf-8"),
    ],
)

log = logging.getLogger("client")
#对应上面定义格式中的message
log.info(f"启动：BASE={BASE}，TIMEOUT={TIMEOUT}s，MAX_RETRIES={MAX_RETRIES}")

# ========== 工具函数层 ==========
def req(method, path, **kwargs):
    """统一封装：带超时 + 传输层错误处理 + 重试退避 + 日志。"""
    #log封装日志
    url = f"{BASE}{path}"
    for attempt in range(1, MAX_RETRIES + 1):
        start = time.time()
        try:#正常请求+计算耗时
            r = requests.request(method, url, timeout=TIMEOUT, **kwargs)
            elapsed = time.time() - start
            log.info(f"{method} {url} -> {r.status_code} ({elapsed:.3f}s)")
            return r
        except Timeout:#请求超时
            elapsed = time.time() - start
            log.warning(f"{method} {url} -> 超时 ({elapsed:.3f}s)")
        except ConnectionError:#连接错误
            elapsed = time.time() - start
            log.warning(f"{method} {url} -> 连接失败 ({elapsed:.3f}s)")
        if attempt < MAX_RETRIES:#如果还没到最大重试次数，计算退避时间并等待
            wait = 2 ** (attempt - 1)
            log.info(f"重试 {attempt}/{MAX_RETRIES}，{wait}s 后重试")
            time.sleep(wait)
    log.error(f"{method} {url} 重试 {MAX_RETRIES} 次仍失败")
    return None


def safe_json(r):
    """安全解析响应体为 JSON。非 JSON 或空响应体 → 返回 None，不抛异常。"""
    try:
        return r.json()
    except Exception:
        body = r.text[:200] if r.text else "(空响应体)"
        log.warning(f"响应体不是有效 JSON：{body}")
        return None


def validate(data, required_fields, context=""):
    """检查 data 是 dict 且包含所有必需字段。不达标 → 记日志，返回 False。"""
    if not isinstance(data, dict):
        log.warning(f"{context}：期望 dict，实际 {type(data).__name__}")
        return False
    missing = [f for f in required_fields if f not in data]
    if missing:
        log.warning(f"{context}：缺少字段 {missing}")
        return False
    return True





# ==================== 日志查询测试 ====================

def check_logs(data, name=""):
    """校验日志分页响应结构：total、page、page_size、logs 数组。"""
    if not validate(data, ["total", "page", "page_size", "logs"], name):
        return False
    log_list = data.get("logs", [])
    if not isinstance(log_list, list):
        log.warning(f"{name}：logs 不是数组")
        return False
    return True


# ======== 1. 时间同步日志 ========
print("\n=== GET /logs/timesync（时间同步 - 全部）===")
r = req("GET", "/logs/timesync")
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "时间同步日志"):
        print(r.status_code, f"-> total={data['total']}, page={data['page']}, 返回 {len(data['logs'])} 条")

# 按日志级别过滤
print("=== GET /logs/timesync?level=ERROR&device_id=SW-01 ===")
r = req("GET", "/logs/timesync", params={"level": "ERROR", "device_id": "SW-01"})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "时间同步-ERROR"):
        print(r.status_code, f"-> total={data['total']} 条 ERROR 日志(SW-01)")

# 按事件类型 + 分页
print("=== GET /logs/timesync?event_type=PERIODIC_STATS&page_size=3 ===")
r = req("GET", "/logs/timesync", params={"event_type": "PERIODIC_STATS", "page_size": 3})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "时间同步-PERIODIC_STATS"):
        print(r.status_code, f"-> total={data['total']}, page_size=3, 返回 {len(data['logs'])} 条")


# ======== 2. 流量调度日志 ========
print("\n=== GET /logs/scheduling（流量调度 - 全部）===")
r = req("GET", "/logs/scheduling")
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "调度日志"):
        print(r.status_code, f"-> total={data['total']}, 返回 {len(data['logs'])} 条")

# 按调度类型过滤
print("=== GET /logs/scheduling?schedule_type=802.1Qbv-TAS ===")
r = req("GET", "/logs/scheduling", params={"schedule_type": "802.1Qbv-TAS"})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "调度-Qbv"):
        print(r.status_code, f"-> total={data['total']} 条 Qbv 相关日志")

# 按设备 + 队列过滤
print("=== GET /logs/scheduling?device_id=SW-01&queue=Q0 ===")
r = req("GET", "/logs/scheduling", params={"device_id": "SW-01", "queue": "Q0"})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "调度-SW-01-Q0"):
        print(r.status_code, f"-> total={data['total']} 条 SW-01 Q0 日志")


# ======== 3. 流过滤与警管日志 ========
print("\n=== GET /logs/filtering（流过滤 - 全部）===")
r = req("GET", "/logs/filtering")
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "过滤日志"):
        print(r.status_code, f"-> total={data['total']}, 返回 {len(data['logs'])} 条")

# 按状态过滤（Red = 超出警管速率）
print("=== GET /logs/filtering?status=Red ===")
r = req("GET", "/logs/filtering", params={"status": "Red"})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "过滤-Red"):
        print(r.status_code, f"-> total={data['total']} 条 Red 判定日志")

# 按资源类型 + 动作过滤
print("=== GET /logs/filtering?resource_type=警管&operation=限流 ===")
r = req("GET", "/logs/filtering", params={"resource_type": "警管", "operation": "限流"})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "过滤-警管限流"):
        print(r.status_code, f"-> total={data['total']} 条警管限流日志")


# ======== 4. 网络资源配置日志 ========
print("\n=== GET /logs/config（资源配置 - 全部）===")
r = req("GET", "/logs/config")
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "配置日志"):
        print(r.status_code, f"-> total={data['total']}, 返回 {len(data['logs'])} 条")

# 按事件类型过滤
print("=== GET /logs/config?event_type=CONFIG_DEPLOY ===")
r = req("GET", "/logs/config", params={"event_type": "CONFIG_DEPLOY"})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "配置-下发"):
        print(r.status_code, f"-> total={data['total']} 条配置下发日志")

# 过滤 WARN 级别
print("=== GET /logs/config?level=WARN&page_size=5 ===")
r = req("GET", "/logs/config", params={"level": "WARN", "page_size": 5})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "配置-WARN"):
        print(r.status_code, f"-> total={data['total']} 条 WARN, 返回 {len(data['logs'])} 条")


# ======== 5. 硬件资源性能日志 ========
print("\n=== GET /logs/hardware（硬件资源 - 全部）===")
r = req("GET", "/logs/hardware")
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "硬件日志"):
        print(r.status_code, f"-> total={data['total']}, 返回 {len(data['logs'])} 条")

# 按指标类型过滤
print("=== GET /logs/hardware?metric_type=thermal ===")
r = req("GET", "/logs/hardware", params={"metric_type": "thermal"})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "硬件-thermal"):
        print(r.status_code, f"-> total={data['total']} 条温度/散热日志")

# 多条件：设备 + 告警级别
print("=== GET /logs/hardware?device_id=SW-02&level=WARN ===")
r = req("GET", "/logs/hardware", params={"device_id": "SW-02", "level": "WARN"})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "硬件-SW-02-WARN"):
        print(r.status_code, f"-> total={data['total']} 条 SW-02 WARN 硬件日志")

# 边界：翻页超出范围
print("=== GET /logs/hardware?page=99&page_size=20（空页）===")
r = req("GET", "/logs/hardware", params={"page": 99, "page_size": 20})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and check_logs(data, "硬件-空页"):
        print(r.status_code, f"-> total={data['total']}, 返回 {len(data['logs'])} 条（预期 0）")
