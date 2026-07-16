"""TSN REST API —— 日志查询服务。

部署在 TSN 设备（端系统/交换机）上，提供设备本地运行日志的分页查询与多维过滤。
"""

import logging
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

app = FastAPI(title="TSN Log API", version="2.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


from routers import logs
app.include_router(logs.router)
log.info("已注册：日志路由 /api/logs/*")
