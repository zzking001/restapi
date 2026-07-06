from flask import Flask, jsonify, request

app = Flask(__name__)#创建 Flask 应用对象，所有路由和配置都挂在它上面

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


def next_id():#用来给新设备分配唯一 id
    """生成下一个自增 id"""
    return max(d["id"] for d in devices) + 1 if devices else 1


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
    data["id"] = next_id()
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)