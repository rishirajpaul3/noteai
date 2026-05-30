# FastAPI entry point — Sales Call Notetaker (internal tool)
# Run: venv/bin/uvicorn main:app --reload --port 8000

import asyncio
import logging
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.auth import router as auth_router
from routers.bots import router as bots_router
from routers.demo import router as demo_router
from routers.calls import router as calls_router
from routers.hubspot import router as hubspot_router
from routers.webhook import router as webhook_router
from routers.settings import router as settings_router
from routers.live import router as live_router
from services.poller import poll_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Sales Call Notetaker", version="1.0.0")


@app.on_event("startup")
async def startup():
    asyncio.create_task(poll_loop())

_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(bots_router)
app.include_router(demo_router)
app.include_router(calls_router)
app.include_router(hubspot_router)
app.include_router(settings_router)
app.include_router(live_router)
