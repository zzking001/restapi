import requests

BASE = "http://127.0.0.1:5000/api"

# === GET：查列表 ===
print("=== GET /devices（查列表）===")
r = requests.get(f"{BASE}/devices")
print(r.status_code, "->", len(r.json()), "台设备")

# === GET：查单台 ===
print("=== GET /devices/1（查单台）===")
r = requests.get(f"{BASE}/devices/1")
print(r.status_code, "->", r.json())

# === POST：新增一台 Talker ===
print("=== POST /devices（新增）===")
r = requests.post(
    f"{BASE}/devices",
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
print(r.status_code, "->", r.json())

# === PUT：更新 id=1 的状态为 offline ===
print("=== PUT /devices/1（更新状态）===")
r = requests.put(f"{BASE}/devices/1", json={"status": "offline"})
print(r.status_code, "->", r.json())

# === DELETE：删除 id=2 ===
print("=== DELETE /devices/2（删除）===")
r = requests.delete(f"{BASE}/devices/2")
print(r.status_code, "-> 无响应体（204 正常）")

# === GET：验证已删除 ===
print("=== GET /devices/2（应 404）===")
r = requests.get(f"{BASE}/devices/2")
print(r.status_code, "->", r.json())

# === GET：最终列表，确认变化 ===
print("=== GET /devices（最终列表）===")
r = requests.get(f"{BASE}/devices")
print(r.status_code, "->", len(r.json()), "台设备")