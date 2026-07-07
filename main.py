"""TSN REST API —— FastAPI 版本。"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from routers import system, interfaces, devices, tsn

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await interfaces.init_interfaces_cache()
    yield

app = FastAPI(title="TSN REST API", version="2.0.0", lifespan=lifespan)
app.include_router(system.router)
app.include_router(interfaces.router)
app.include_router(devices.router)
app.include_router(tsn.router)
