"""TSN REST API —— FastAPI 版本。

通过 TSN_API_MODULES 环境变量控制启用的路由模块：
  - all（默认）: 注册全部路由（日志 + 网管）
  - logs   : 仅日志轨 —— 端系统 / 交换机本地查询
  - mgmt   : 仅网管轨 —— 机载网络控制器上报查询
"""

import logging
import os
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

MODULES = os.environ.get("TSN_API_MODULES", "all").lower().replace(" ", "")

app = FastAPI(title="TSN REST API", version="2.0.0")

# 日志轨：端系统 / 交换机本地日志查询
if MODULES in ("all", "logs"):
    from routers import logs
    app.include_router(logs.router)
    log.info("已注册：日志路由 /api/logs/*")

# 网管轨：机载网络控制器 NETCONF / SNMP 上报查询
if MODULES in ("all", "mgmt"):
    from routers import mgmt
    app.include_router(mgmt.router)
    log.info("已注册：网管路路由 /api/mgmt/*")
