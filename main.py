"""TSN REST API —— FastAPI 版本。"""

import logging
from fastapi import FastAPI
from routers import logs

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="TSN REST API", version="2.0.0")
app.include_router(logs.router)
