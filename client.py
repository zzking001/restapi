import logging
import os
import time

import requests
from requests.exceptions import ConnectionError, Timeout

BASE = os.environ.get("TSN_API_BASE", "http://127.0.0.1:5000/api")
TIMEOUT = 5  # 秒：超过这个时间没响应就放弃，不让脚本无限期挂着
MAX_RETRIES = 3  # 传输层失败最多重试几次

# 日志配置：同时输出到控制台和文件 client.log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("client.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("client")
log.info(f"启动：BASE={BASE}，TIMEOUT={TIMEOUT}s，MAX_RETRIES={MAX_RETRIES}")


def req(method, path, **kwargs):
    """统一封装：带超时 + 传输层错误处理 + 重试退避 + 日志。"""
    url = f"{BASE}{path}"
    for attempt in range(1, MAX_RETRIES + 1):
        start = time.time()
        try:
            r = requests.request(method, url, timeout=TIMEOUT, **kwargs)
            elapsed = time.time() - start
            log.info(f"{method} {url} -> {r.status_code} ({elapsed:.3f}s)")
            return r
        except Timeout:
            elapsed = time.time() - start
            log.warning(f"{method} {url} -> 超时 ({elapsed:.3f}s)")
        except ConnectionError:
            elapsed = time.time() - start
            log.warning(f"{method} {url} -> 连接失败 ({elapsed:.3f}s)")
        if attempt < MAX_RETRIES:
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


# === GET：查列表 ===
print("=== GET /devices（查列表）===")
r = req("GET", "/devices")
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if isinstance(data, list):
        print(r.status_code, "->", len(data), "台设备")
    else:
        print(f"  [结构错误] 期望 list，实际 {type(data).__name__}")
else:
    print(f"  [应用错误] {r.status_code} {r.reason}")

# === GET：查单台 ===
print("=== GET /devices/1（查单台）===")
r = req("GET", "/devices/1")
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and validate(data, ["id", "name", "status"], "设备详情"):
        print(r.status_code, "->", data)
else:
    print(f"  [应用错误] {r.status_code} {r.reason}")

# === POST：新增一台 Talker ===
print("=== POST /devices（新增）===")
r = req(
    "POST",
    "/devices",
    json={
        "name": "TSN-Talker-02",
        "type": "talker",
        "mac": "00:1b:44:11:3a:c1",
        "stream_id": "a0-00-00-00-00-00-00-02",
        "vlan": 200,
        "pcp": 2,
        "status": "online",
    },
)
if r is None:
    pass
elif r.status_code in (200, 201):
    data = safe_json(r)
    if data and validate(data, ["id"], "新增设备响应"):
        print(r.status_code, "->", data)
else:
    print(f"  [应用错误] {r.status_code} {r.reason}")

# === PUT：更新 id=1 的状态为 offline ===
print("=== PUT /devices/1（更新状态）===")
r = req("PUT", "/devices/1", json={"status": "offline"})
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if data and validate(data, ["id", "status"], "更新后设备"):
        print(r.status_code, "->", data)
else:
    print(f"  [应用错误] {r.status_code} {r.reason}")

# === DELETE：删除 id=2 ===
print("=== DELETE /devices/2（删除）===")
r = req("DELETE", "/devices/2")
if r is None:
    pass
elif r.status_code in (200, 204):
    print(r.status_code, "-> 无响应体（204 正常）")
else:
    print(f"  [应用错误] {r.status_code} {r.reason}")

# === GET：验证已删除（404 是预期结果）===
print("=== GET /devices/2（应 404）===")
r = req("GET", "/devices/2")
if r is None:
    pass
elif r.status_code == 404:
    print(r.status_code, "-> 已删除确认（404 正确）")
elif r.status_code == 200:
    data = safe_json(r)
    if data and validate(data, ["id"], "设备详情"):
        print(r.status_code, "-> 没删掉？设备还在", data)
else:
    print(f"  [应用错误] {r.status_code} {r.reason}")

# === GET：最终列表，确认变化 ===
print("=== GET /devices（最终列表）===")
r = req("GET", "/devices")
if r is None:
    pass
elif r.status_code == 200:
    data = safe_json(r)
    if isinstance(data, list):
        print(r.status_code, "->", len(data), "台设备")
    else:
        print(f"  [结构错误] 期望 list，实际 {type(data).__name__}")
else:
    print(f"  [应用错误] {r.status_code} {r.reason}")