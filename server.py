import os
import json

from flask import Flask, jsonify, request

app = Flask(__name__)  # 创建 Flask 应用对象，所有路由和配置都挂在它上面

# data/ 目录路径：模拟系统数据文件存放处（以后换成 /proc 或 psutil 读取真实数据）
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# ========== 辅助函数：读取模拟数据文件 ==========

def read_text_file(filename):
    """读取 data/ 目录下的文本文件，返回内容字符串。文件不存在返回 None。"""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def read_json_file(filename):
    """读取 data/ 目录下的 JSON 文件，返回解析后的对象。文件不存在返回 None。"""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def parse_cpuinfo(text):
    """解析 /proc/cpuinfo 格式的文本，返回 CPU 字典列表。

    格式：每个 CPU 用空行分隔，每行 "key\\t: value"。
    """
    cpus = []
    for block in text.strip().split("\n\n"):
        cpu = {}
        for line in block.strip().split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                cpu[key.strip()] = value.strip()
        if cpu:
            cpus.append(cpu)
    return cpus


def parse_meminfo(text):
    """解析 /proc/meminfo 格式的文本，返回内存字典。

    格式：每行 "key:   value kB"，去掉 kB 后缀转成整数。
    """
    mem = {}
    for line in text.strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip()
            if value.endswith("kB"):
                value = value[:-2].strip()
            try:
                mem[key.strip()] = int(value)
            except ValueError:
                mem[key.strip()] = value
    return mem


def parse_uptime(text):
    """解析 /proc/uptime 格式的文本，返回运行时间信息。

    格式："uptime_seconds idle_seconds"，两个浮点数空格分隔。
    """
    parts = text.strip().split()
    uptime_seconds = float(parts[0]) if len(parts) > 0 else 0
    idle_seconds = float(parts[1]) if len(parts) > 1 else 0
    return {
        "uptime_seconds": uptime_seconds,
        "idle_seconds": idle_seconds,
        "uptime_days": round(uptime_seconds / 86400, 2),
    }


def parse_ptp_status(text):
    """解析 PTP 状态文本（key=value 格式），返回字典。"""
    status = {}
    for line in text.strip().split("\n"):
        if "=" in line:
            key, _, value = line.partition("=")
            status[key.strip()] = value.strip()
    return status


def next_id(items):
    """生成下一个自增 id（通用版，devices 和 streams 都用）。"""
    return max(d["id"] for d in items) + 1 if items else 1


# ========== TSN 设备 CRUD（原有，保留） ==========

# TSN 设备种子数据（内存存储）
devices = [
    {
        "id": 1,
        "name": "TSN-Talker-01",
        "type": "talker",
        "mac": "00:1b:44:11:3a:b7",
        "stream_id": "a0-00-00-00-00-00-00-01",
        "vlan": 100,
        "pcp": 3,
        "status": "online",
    },
    {
        "id": 2,
        "name": "TSN-Listener-01",
        "type": "listener",
        "mac": "00:1b:44:11:3a:b8",
        "stream_id": "a0-00-00-00-00-00-00-01",
        "vlan": 100,
        "pcp": 3,
        "status": "online",
    },
    {
        "id": 3,
        "name": "TSN-Bridge-A",
        "type": "bridge",
        "mac": "00:1b:44:11:3a:b9",
        "stream_id": "-",
        "vlan": 100,
        "pcp": 3,
        "status": "online",
    },
]


# GET /api/devices —— 列出所有设备
@app.route("/api/devices", methods=["GET"])
def list_devices():
    return jsonify(devices)


# GET /api/devices/<id> —— 取单台设备
@app.route("/api/devices/<int:device_id>", methods=["GET"])
def get_device(device_id):
    device = next((d for d in devices if d["id"] == device_id), None)
    if device:
        return jsonify(device)
    return jsonify({"error": "未找到"}), 404


# POST /api/devices —— 新增设备
@app.route("/api/devices", methods=["POST"])
def add_device():
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "缺少 name 字段"}), 400
    data["id"] = next_id(devices)
    devices.append(data)
    return jsonify(data), 201


# PUT /api/devices/<id> —— 全量更新设备
@app.route("/api/devices/<int:device_id>", methods=["PUT"])
def update_device(device_id):
    device = next((d for d in devices if d["id"] == device_id), None)
    if not device:
        return jsonify({"error": "未找到"}), 404
    data = request.get_json()
    device.update(data)
    return jsonify(device)


# DELETE /api/devices/<id> —— 删除设备
@app.route("/api/devices/<int:device_id>", methods=["DELETE"])
def delete_device(device_id):
    device = next((d for d in devices if d["id"] == device_id), None)
    if not device:
        return jsonify({"error": "未找到"}), 404
    devices.remove(device)
    return "", 204


# ========== 系统监控类（只读） ==========

# GET /api/cpus —— 返回 CPU 信息
@app.route("/api/cpus", methods=["GET"])
def get_cpus():
    text = read_text_file("cpuinfo.txt")
    if text is None:
        return jsonify({"error": "cpuinfo.txt 不存在"}), 500
    cpus = parse_cpuinfo(text)
    return jsonify({"count": len(cpus), "cpus": cpus})


# GET /api/memory —— 返回内存信息
@app.route("/api/memory", methods=["GET"])
def get_memory():
    text = read_text_file("meminfo.txt")
    if text is None:
        return jsonify({"error": "meminfo.txt 不存在"}), 500
    mem = parse_meminfo(text)
    return jsonify(mem)


# GET /api/uptime —— 返回运行时间
@app.route("/api/uptime", methods=["GET"])
def get_uptime():
    text = read_text_file("uptime.txt")
    if text is None:
        return jsonify({"error": "uptime.txt 不存在"}), 500
    uptime = parse_uptime(text)
    return jsonify(uptime)


# ========== 网络接口类（只读） ==========

# GET /api/interfaces —— 列出所有网卡
@app.route("/api/interfaces", methods=["GET"])
def list_interfaces():
    data = read_json_file("interfaces.json")
    if data is None:
        return jsonify({"error": "interfaces.json 不存在"}), 500
    return jsonify(data)


# GET /api/interfaces/<name> —— 返回指定网卡详情
@app.route("/api/interfaces/<string:name>", methods=["GET"])
def get_interface(name):
    data = read_json_file("interfaces.json")
    if data is None:
        return jsonify({"error": "interfaces.json 不存在"}), 500
    iface = next((i for i in data if i.get("name") == name), None)
    if iface:
        return jsonify(iface)
    return jsonify({"error": f"接口 {name} 不存在"}), 404


# GET /api/interfaces/<name>/tsn —— 返回指定网卡的 TSN 能力
@app.route("/api/interfaces/<string:name>/tsn", methods=["GET"])
def get_interface_tsn(name):
    data = read_json_file("interfaces.json")
    if data is None:
        return jsonify({"error": "interfaces.json 不存在"}), 500
    iface = next((i for i in data if i.get("name") == name), None)
    if not iface:
        return jsonify({"error": f"接口 {name} 不存在"}), 404
    tsn = iface.get("tsn", {})
    return jsonify({"interface": name, "tsn": tsn})


# ========== TSN 配置类（读写） ==========

# TSN 流种子数据（内存存储）
streams = [
    {
        "id": 1,
        "stream_id": "a0-00-00-00-00-00-00-01",
        "talker": "TSN-Talker-01",
        "listener": "TSN-Listener-01",
        "vlan": 100,
        "pcp": 3,
        "bandwidth": "100Mbps",
        "status": "active",
    },
    {
        "id": 2,
        "stream_id": "a0-00-00-00-00-00-00-02",
        "talker": "TSN-Talker-02",
        "listener": "TSN-Listener-01",
        "vlan": 200,
        "pcp": 2,
        "bandwidth": "50Mbps",
        "status": "active",
    },
]


# GET /api/tsn/streams —— 列出所有流
@app.route("/api/tsn/streams", methods=["GET"])
def list_streams():
    return jsonify(streams)


# GET /api/tsn/streams/<id> —— 取单条流
@app.route("/api/tsn/streams/<int:sid>", methods=["GET"])
def get_stream(sid):
    stream = next((s for s in streams if s["id"] == sid), None)
    if stream:
        return jsonify(stream)
    return jsonify({"error": "未找到"}), 404


# POST /api/tsn/streams —— 新增流
@app.route("/api/tsn/streams", methods=["POST"])
def add_stream():
    data = request.get_json()
    if not data or "stream_id" not in data:
        return jsonify({"error": "缺少 stream_id 字段"}), 400
    data["id"] = next_id(streams)
    streams.append(data)
    return jsonify(data), 201


# PUT /api/tsn/streams/<id> —— 更新流
@app.route("/api/tsn/streams/<int:sid>", methods=["PUT"])
def update_stream(sid):
    stream = next((s for s in streams if s["id"] == sid), None)
    if not stream:
        return jsonify({"error": "未找到"}), 404
    data = request.get_json()
    stream.update(data)
    return jsonify(stream)


# DELETE /api/tsn/streams/<id> —— 删除流
@app.route("/api/tsn/streams/<int:sid>", methods=["DELETE"])
def delete_stream(sid):
    stream = next((s for s in streams if s["id"] == sid), None)
    if not stream:
        return jsonify({"error": "未找到"}), 404
    streams.remove(stream)
    return "", 204


# GET /api/tsn/ptp/status —— 返回 PTP 同步状态（只读）
@app.route("/api/tsn/ptp/status", methods=["GET"])
def get_ptp_status():
    text = read_text_file("ptp_status.txt")
    if text is None:
        return jsonify({"error": "ptp_status.txt 不存在"}), 500
    status = parse_ptp_status(text)
    return jsonify(status)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)