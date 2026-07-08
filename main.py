"""TSN REST API —— FastAPI 版本。"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from routers import interfaces, logs

logging.basicConfig(level=logging.INFO)

@asynccontextmanager#生命周期，启动时初始化和关闭时清理都在这里
async def lifespan(app: FastAPI):
    await interfaces.init_interfaces_cache()
    yield

#创建应用，类似创建实例
app = FastAPI(title="TSN REST API", version="2.0.0", lifespan=lifespan)
#注册路由，组装模块，新增功能只需加一行
#注册路由 = 告诉 app，收到某类请求时交给谁处理
app.include_router(interfaces.router)
app.include_router(logs.router)
